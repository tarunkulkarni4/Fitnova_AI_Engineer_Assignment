import os
import uuid
from pathlib import Path
from loguru import logger
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob
from app.models.transcript import Transcript


# Conditional import of pyannote.audio
if not settings.DIARIZATION_MOCK:
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        Pipeline = None
else:
    Pipeline = None


class DiarizationService:
    """
    Service responsible for loading Pyannote diarization pipeline,
    separating speakers into neutral labels (SPEAKER_00, etc.),
    mapping roles (Advisor, Customer) using text heuristics,
    aligning speech segments using temporal overlap,
    and updating database transcript entries.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    async def diarize_call(self, call_id: uuid.UUID) -> dict:

        # 1. Fetch Call and Job
        call = self.db.query(Call).filter(Call.id == call_id).first()

        if not call:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Call record with ID {call_id} not found."
            )

        job = (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.call_id == call_id)
            .first()
        )

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing job for Call ID {call_id} not found."
            )

        # 2. Fetch existing transcript segments
        transcript_segments = (
            self.db.query(Transcript)
            .filter(Transcript.call_id == call_id)
            .order_by(Transcript.start_time)
            .all()
        )

        if not transcript_segments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No transcript segments found for this call. "
                    "Please run transcription first."
                )
            )

        # 3. Transition database status to Processing
        try:
            call.processing_status = ProcessingStatus.PROCESSING
            job.status = ProcessingStatus.PROCESSING
            job.stage = "Speaker Diarization"

            self.db.commit()

        except Exception as e:
            self.db.rollback()

            logger.exception(
                f"Failed to transition database status "
                f"to diarization processing: {e}"
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database status transition failed."
            )

        # 4. Validate processed audio file path
        if not call.processed_audio_file:
            self._handle_failure(
                call,
                job,
                "Processed WAV file path is not set in Call record."
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No processed audio file found. "
                    "Run audio processing first."
                )
            )

        audio_path = call.processed_audio_file

        if not os.path.exists(audio_path):
            self._handle_failure(
                call,
                job,
                f"Processed WAV file not found on disk at: {audio_path}"
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Processed WAV file not found on disk at: {audio_path}"
            )

        # 5. Execute Speaker Diarization
        diarization_turns = []

        if settings.DIARIZATION_MOCK:

            logger.info("Pyannote running in MOCK mode.")

            diarization_turns = self._get_mock_diarization(
                call.audio_duration or 10
            )

        else:

            if Pipeline is None:
                self._handle_failure(
                    call,
                    job,
                    "pyannote.audio library is not installed "
                    "in the python environment."
                )

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        "Diarization engine library missing. "
                        "Install dependencies or enable DIARIZATION_MOCK."
                    )
                )

            if not settings.HF_TOKEN:
                self._handle_failure(
                    call,
                    job,
                    "Hugging Face authentication token "
                    "(HF_TOKEN) is not set."
                )

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "HF_TOKEN environment variable required "
                        "for Pyannote model authorization."
                    )
                )

            # Load Pyannote pipeline
            try:

                logger.info(
                    "Initializing pyannote.audio "
                    "speaker diarization pipeline..."
                )

                pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=settings.HF_TOKEN
                )

                if pipeline is None:
                    raise RuntimeError(
                        "Pretrained pipeline failed to load from HuggingFace."
                    )

                # Configure Pyannote pipeline parameters and log configuration
                logger.info(
                    f"Diarization configuration: clustering_threshold={settings.PYANNOTE_CLUSTERING_THRESHOLD}, "
                    f"num_speakers={settings.DIARIZATION_NUM_SPEAKERS}"
                )
                pipeline.instantiate({
                    "clustering": {
                        "threshold": settings.PYANNOTE_CLUSTERING_THRESHOLD
                    }
                })

            except Exception as e:

                self._handle_failure(
                    call,
                    job,
                    f"Failed to load Pyannote pipeline: {str(e)}"
                )

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Pyannote model load failed: {str(e)}"
                )

            # Run diarization
            try:

                logger.info(
                    f"Running speaker diarization on WAV: {audio_path}..."
                )

                # Run Pyannote pipeline with speaker count
                kwargs = {}
                if settings.DIARIZATION_NUM_SPEAKERS is not None:
                    kwargs["num_speakers"] = settings.DIARIZATION_NUM_SPEAKERS
                result = pipeline(audio_path, **kwargs)

                # IMPORTANT FIX:
                # New pyannote.audio versions return DiarizeOutput.
                # Old versions directly return Annotation.
                if hasattr(result, "speaker_diarization"):
                    logger.info(
                        "Detected new Pyannote DiarizeOutput format. "
                        "Extracting speaker_diarization annotation..."
                    )

                    annotation = result.speaker_diarization

                else:
                    logger.info(
                        "Detected legacy Pyannote Annotation format."
                    )

                    annotation = result

                # Convert speaker turns into our internal structure
                for turn, _, speaker in annotation.itertracks(
                    yield_label=True
                ):
                    diarization_turns.append({
                        "start": float(turn.start),
                        "end": float(turn.end),
                        "speaker_label": str(speaker)
                    })

                logger.info(
                    f"Pyannote detected "
                    f"{len(diarization_turns)} speaker turns."
                )

            except Exception as e:

                self._handle_failure(
                    call,
                    job,
                    f"Pyannote diarization failed: {str(e)}"
                )

                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        f"Pyannote diarization execution failed: {str(e)}"
                    )
                )

        # Check for suspicious diarization and apply hybrid strategy fallback
        if settings.DIARIZATION_STRATEGY == "hybrid" and not settings.DIARIZATION_MOCK:
            is_suspicious = self._detect_suspicious_diarization(call, diarization_turns)
            if is_suspicious:
                logger.info("Suspicious diarization detected. Triggering hybrid speaker diarization fallback...")
                try:
                    diarization_turns = self._run_hybrid_fallback(call, audio_path, diarization_turns)
                    logger.info(f"Hybrid speaker diarization finished. Reconstructed {len(diarization_turns)} speaker turns.")
                except Exception as ex:
                    logger.exception(f"Hybrid diarization fallback failed: {ex}. Proceeding with primary diarization.")

        # 6. Extract unique speakers
        unique_speakers = {
            turn["speaker_label"]
            for turn in diarization_turns
        }

        logger.info(
            f"Unique speakers detected: {unique_speakers}"
        )

        # Build transcript dictionaries for role mapping
        segment_dicts = [
            {
                "text": seg.text,
                "start": seg.start_time,
                "end": seg.end_time
            }
            for seg in transcript_segments
        ]

        # Match transcript segments with neutral speakers
        for idx, seg in enumerate(transcript_segments):

            best_spk = self._get_best_overlapping_speaker(
                seg,
                diarization_turns
            )

            if best_spk:
                segment_dicts[idx]["speaker_label"] = best_spk

        # Map speakers to Advisor / Customer
        role_mapping, role_mapping_confidence = (
            self.map_speaker_roles(
                segment_dicts,
                unique_speakers
            )
        )

        # 7. Update transcript records
        try:

            for seg in transcript_segments:

                best_speaker = self._get_best_overlapping_speaker(
                    seg,
                    diarization_turns
                )

                if best_speaker:

                    mapped_role = role_mapping.get(
                        best_speaker,
                        best_speaker
                    )

                    # Low-confidence preservation
                    if seg.speaker != "Unknown":

                        if role_mapping_confidence >= 0.5:
                            seg.speaker = mapped_role

                    else:
                        seg.speaker = mapped_role

                else:

                    if seg.speaker == "Unknown":
                        seg.speaker = "Unknown"

            # Cache raw diarization turns and role mapping to a JSON file for high-fidelity alignment in later stages
            storage_dir = Path("app/storage/transcripts")
            try:
                storage_dir.mkdir(parents=True, exist_ok=True)
                diarization_json_path = storage_dir / f"{call_id}_diarization.json"
                import json
                with open(diarization_json_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "diarization_turns": diarization_turns,
                        "role_mapping": role_mapping,
                        "role_mapping_confidence": role_mapping_confidence
                    }, f, indent=2, ensure_ascii=False)
                logger.info(f"Cached raw Diarization turns to {diarization_json_path}")
            except Exception as e:
                logger.warning(f"Failed to save raw diarization JSON cache: {e}")

            # Move pipeline to next stage
            call.processing_status = (
                ProcessingStatus.READY_FOR_TRANSCRIPT_MERGE
            )

            job.status = (
                ProcessingStatus.READY_FOR_TRANSCRIPT_MERGE
            )

            job.stage = "Ready For Transcript Merge"

            self.db.commit()

        except Exception as e:

            self.db.rollback()

            logger.exception(
                f"Failed to update transcript speaker labels "
                f"in database: {e}"
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Database operation failed during "
                    "transcript speaker alignment."
                )
            )

        logger.info(
            f"Successfully completed speaker diarization "
            f"for Call ID {call_id}. "
            f"Detected speakers: {len(unique_speakers)}"
        )

        return {
            "speakers_detected": len(unique_speakers),
            "role_mapping": role_mapping,
            "confidence": role_mapping_confidence
        }

    def map_speaker_roles(
        self,
        segments: list,
        speakers: set
    ) -> tuple[dict, float]:

        """
        Map neutral speakers to Advisor and Customer.

        1. FitNova greeting -> Advisor (0.95 confidence)
        2. Two speakers, no greeting -> first speaker Advisor (0.60)
        3. Other cases -> keep neutral labels
        """

        mapping = {}
        confidence = 0.0

        if not speakers:
            return {}, 0.0

        # Default neutral mapping
        for spk in speakers:
            mapping[spk] = spk

        if len(speakers) == 2:

            greeting_speaker = None

            early_segments = [
                segment
                for segment in segments
                if segment.get("start", 0) < 30.0
            ]

            if not early_segments:
                early_segments = segments[:3]

            # Search for FitNova introduction
            for seg in early_segments:

                text = seg.get("text", "").lower()
                spk = seg.get("speaker_label")

                if (
                    spk in speakers
                    and (
                        "fitnova" in text
                        or "fit nova" in text
                    )
                ):
                    greeting_speaker = spk
                    break

            if greeting_speaker:

                other_speaker = list(
                    speakers - {greeting_speaker}
                )[0]

                mapping[greeting_speaker] = "Advisor"
                mapping[other_speaker] = "Customer"

                confidence = 0.95

                logger.info(
                    f"Heuristic Match: Speaker "
                    f"{greeting_speaker} opened with "
                    f"FitNova greeting. "
                    f"Advisor mapped. Confidence: 0.95"
                )

            else:

                # Fallback: first detected speaker = Advisor
                first_speaker = None

                for seg in segments:

                    spk = seg.get("speaker_label")

                    if spk in speakers:
                        first_speaker = spk
                        break

                if first_speaker:

                    other_speaker = list(
                        speakers - {first_speaker}
                    )[0]

                    mapping[first_speaker] = "Advisor"
                    mapping[other_speaker] = "Customer"

                    confidence = 0.60

                    logger.info(
                        f"Fallback Heuristic: First speaker "
                        f"{first_speaker} assumed Advisor. "
                        f"Confidence: 0.60"
                    )

                else:

                    confidence = 0.0

                    logger.info(
                        "Uncertain role mapping. "
                        "Keeping neutral speaker labels."
                    )

        else:

            confidence = 0.0

            logger.info(
                f"Detected {len(speakers)} speakers. "
                f"Keeping neutral speaker labels."
            )

        return mapping, confidence

    def _get_best_overlapping_speaker(
        self,
        seg: Transcript,
        turns: list
    ) -> str | None:

        """
        Match transcript segment with the diarized speaker
        having the greatest overlap duration.
        """

        best_speaker = None
        max_overlap = 0.0

        seg_start = seg.start_time
        seg_end = seg.end_time

        for turn in turns:

            turn_start = turn["start"]
            turn_end = turn["end"]

            overlap_start = max(
                seg_start,
                turn_start
            )

            overlap_end = min(
                seg_end,
                turn_end
            )

            overlap = max(
                0.0,
                overlap_end - overlap_start
            )

            if overlap > max_overlap:

                max_overlap = overlap
                best_speaker = turn["speaker_label"]

        return best_speaker

    def _get_mock_diarization(
        self,
        duration: int
    ) -> list:

        """
        Generate mock neutral diarization turns.
        """

        turns = []

        seg_duration = 8.0

        num_turns = int(
            duration // seg_duration
        ) + 1

        for i in range(num_turns):

            start = i * seg_duration

            end = min(
                start + seg_duration,
                float(duration)
            )

            if start >= duration:
                break

            speaker = f"SPEAKER_{i:02d}"

            turns.append({
                "start": start,
                "end": end,
                "speaker_label": speaker
            })

        return turns

    def _handle_failure(
        self,
        call: Call,
        job: ProcessingJob,
        error_msg: str
    ) -> None:

        try:

            call.processing_status = ProcessingStatus.FAILED
            job.status = ProcessingStatus.FAILED
            job.error_message = error_msg

            self.db.commit()

            logger.warning(
                f"Diarization job failed: "
                f"{error_msg} "
                f"for Call ID: {call.id}"
            )

        except Exception as e:

            self.db.rollback()

            logger.error(
                f"Failed to record diarization job "
                f"failure in database: {e}"
            )

    def _detect_suspicious_diarization(self, call, diarization_turns) -> bool:
        call_id = call.id
        call_duration = call.audio_duration or 10.0
        
        # 1. Very few turns for a conversational call
        if len(diarization_turns) < 5 and call_duration > 30.0:
            return True
            
        # 2. Check for long turns containing multiple conversational boundaries
        whisper_json_path = Path(f"app/storage/transcripts/{call_id}_whisper.json")
        if not whisper_json_path.exists():
            for turn in diarization_turns:
                if (turn["end"] - turn["start"]) > 15.0:
                    return True
            return False
            
        try:
            with open(whisper_json_path, "r", encoding="utf-8") as f:
                whisper_data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load whisper cache for suspicious check: {e}")
            for turn in diarization_turns:
                if (turn["end"] - turn["start"]) > 15.0:
                    return True
            return False
            
        for turn in diarization_turns:
            turn_start = turn["start"]
            turn_end = turn["end"]
            turn_dur = turn_end - turn_start
            
            if turn_dur > 15.0:
                # Find all Whisper words inside this turn
                words_in_turn = []
                for seg in whisper_data.get("segments", []):
                    for w in seg.get("words", []):
                        w_start = float(w["start"])
                        w_end = float(w["end"])
                        if turn_start <= (w_start + w_end)/2.0 <= turn_end:
                            words_in_turn.append(w)
                            
                if not words_in_turn:
                    continue
                    
                sentence_endings = 0
                silence_gaps = 0
                
                for i, w in enumerate(words_in_turn):
                    word_text = w["word"].strip()
                    if word_text.endswith((".", "?", "!")):
                        sentence_endings += 1
                    if i > 0:
                        gap = w["start"] - words_in_turn[i-1]["end"]
                        if gap >= settings.DIARIZATION_SILENCE_GAP_SECONDS:
                            silence_gaps += 1
                            
                if sentence_endings >= 3 or silence_gaps >= 2:
                    return True
                    
        return False

    def _run_hybrid_fallback(self, call, audio_path, original_turns) -> list[dict]:
        import json
        import numpy as np
        from pyannote.audio import Model, Inference
        from pyannote.core import Segment
        from sklearn.cluster import AgglomerativeClustering
        
        call_id = call.id
        whisper_json_path = Path(f"app/storage/transcripts/{call_id}_whisper.json")
        if not whisper_json_path.exists():
            logger.warning(f"Whisper json cache not found at {whisper_json_path}. Cannot run hybrid fallback.")
            return []
            
        try:
            with open(whisper_json_path, "r", encoding="utf-8") as f:
                whisper_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load whisper json cache for hybrid fallback: {e}")
            return []
            
        # Collect all words
        all_words = []
        for seg in whisper_data.get("segments", []):
            for w in seg.get("words", []):
                all_words.append({
                    "word": w["word"].strip(),
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                    "probability": float(w.get("probability", 1.0))
                })
                
        if not all_words:
            logger.warning("No words found in whisper transcription. Hybrid fallback returning empty.")
            return []
            
        # Chunking using word timestamps (sentence endings `.?!`, silence gaps, or max duration)
        chunks = []
        current_chunk = []
        
        for idx, w in enumerate(all_words):
            if not current_chunk:
                current_chunk.append(w)
                continue
            
            prev_w = current_chunk[-1]
            is_boundary = False
            
            word_text = prev_w["word"].strip()
            
            # 1. Punctuation boundary (only sentence-ending . ? !)
            if word_text.endswith((".", "?", "!")):
                is_boundary = True
            # 2. Silence gap boundary
            elif w["start"] - prev_w["end"] >= settings.DIARIZATION_SILENCE_GAP_SECONDS:
                is_boundary = True
            # 3. Max duration boundary
            elif w["end"] - current_chunk[0]["start"] > settings.DIARIZATION_CHUNK_MAX_SECONDS:
                is_boundary = True
                
            if is_boundary:
                start = current_chunk[0]["start"]
                end = prev_w["end"]
                text = " ".join([x["word"] for x in current_chunk])
                chunks.append({
                    "start": start,
                    "end": end,
                    "words": current_chunk,
                    "text": text
                })
                current_chunk = [w]
            else:
                current_chunk.append(w)
                
        if current_chunk:
            start = current_chunk[0]["start"]
            end = current_chunk[-1]["end"]
            text = " ".join([x["word"] for x in current_chunk])
            chunks.append({
                "start": start,
                "end": end,
                "words": current_chunk,
                "text": text
            })
            
        # Extract acoustic embeddings
        model = Model.from_pretrained("pyannote/wespeaker-voxceleb-resnet34-LM", token=settings.HF_TOKEN)
        inference = Inference(model, window="whole")
        
        embeddings = []
        valid_chunk_indices = []
        
        for idx, chunk in enumerate(chunks):
            duration = chunk["end"] - chunk["start"]
            if duration >= settings.DIARIZATION_MIN_EMBEDDING_SECONDS:
                try:
                    emb = inference.crop(audio_path, Segment(chunk["start"], chunk["end"]))
                    if not np.isnan(emb).any():
                        embeddings.append(emb)
                        valid_chunk_indices.append(idx)
                except Exception:
                    pass
                    
        if len(embeddings) < 2:
            logger.warning("Fewer than 2 valid speaker embeddings extracted. Fallback to default speaker SPEAKER_00.")
            reconstructed = []
            for chunk in chunks:
                reconstructed.append({
                    "start": chunk["start"],
                    "end": chunk["end"],
                    "speaker_label": "SPEAKER_00"
                })
            return reconstructed
            
        embeddings = np.array(embeddings)
        # L2 normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized_embeddings = embeddings / (norms + 1e-12)
        
        # Cluster into exactly 2 speakers
        clustering = AgglomerativeClustering(n_clusters=2, metric='cosine', linkage='average')
        cluster_labels = clustering.fit_predict(normalized_embeddings)
        
        # Calculate cluster centroids for similarity checks
        cluster_0_embs = normalized_embeddings[cluster_labels == 0]
        cluster_1_embs = normalized_embeddings[cluster_labels == 1]
        
        centroid_0 = np.mean(cluster_0_embs, axis=0) if len(cluster_0_embs) > 0 else np.zeros(256)
        centroid_1 = np.mean(cluster_1_embs, axis=0) if len(cluster_1_embs) > 0 else np.zeros(256)
        
        centroid_0 = centroid_0 / (np.linalg.norm(centroid_0) + 1e-12)
        centroid_1 = centroid_1 / (np.linalg.norm(centroid_1) + 1e-12)
        
        chunk_speakers = {}
        for i, idx in enumerate(valid_chunk_indices):
            chunk_speakers[idx] = int(cluster_labels[i])
            
        # Build mapping from original Pyannote speaker labels to our cluster IDs (0 and 1)
        original_spk_overlap_0 = {}
        original_spk_overlap_1 = {}
        
        for idx, chunk in enumerate(chunks):
            if idx in chunk_speakers:
                assigned_cluster = chunk_speakers[idx]
                for turn in original_turns:
                    overlap = max(0.0, min(chunk["end"], turn["end"]) - max(chunk["start"], turn["start"]))
                    if overlap > 0.0:
                        spk = turn["speaker_label"]
                        if assigned_cluster == 0:
                            original_spk_overlap_0[spk] = original_spk_overlap_0.get(spk, 0.0) + overlap
                        else:
                            original_spk_overlap_1[spk] = original_spk_overlap_1.get(spk, 0.0) + overlap
                            
        original_spk_mapping = {}
        all_original_speakers = set(original_spk_overlap_0.keys()).union(set(original_spk_overlap_1.keys()))
        for spk in all_original_speakers:
            overlap_0 = original_spk_overlap_0.get(spk, 0.0)
            overlap_1 = original_spk_overlap_1.get(spk, 0.0)
            if overlap_0 >= overlap_1:
                original_spk_mapping[spk] = 0
            else:
                original_spk_mapping[spk] = 1

        # Resolve short replies using the requested priority list
        for idx, chunk in enumerate(chunks):
            if idx in chunk_speakers:
                continue
                
            # Rule a: Direct acoustic embedding if valid
            # (Already covered above in initial loop for valid_chunk_indices)
            
            # Rule b: Similarity against the two cluster centroids
            try:
                emb = inference.crop(audio_path, Segment(chunk["start"], chunk["end"]))
                if not np.isnan(emb).any():
                    emb = emb / (np.linalg.norm(emb) + 1e-12)
                    sim_0 = float(np.dot(emb, centroid_0))
                    sim_1 = float(np.dot(emb, centroid_1))
                    chunk_speakers[idx] = 0 if sim_0 >= sim_1 else 1
                    logger.debug(f"[Hybrid Fallback] Short chunk {idx} assigned via centroid similarity: sim_0={sim_0:.3f}, sim_1={sim_1:.3f}")
                    continue
            except Exception:
                pass
                
            # Rule c: Overlap with fine-grained Pyannote boundary evidence
            best_spk = None
            max_overlap = 0.0
            for turn in original_turns:
                overlap = max(0.0, min(chunk["end"], turn["end"]) - max(chunk["start"], turn["start"]))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_spk = turn["speaker_label"]
                    
            if best_spk is not None and best_spk in original_spk_mapping:
                chunk_speakers[idx] = original_spk_mapping[best_spk]
                logger.debug(f"[Hybrid Fallback] Short chunk {idx} assigned via Pyannote boundary overlap with {best_spk}")
                continue
                
            # Rule d: Neighboring acoustic continuity only as the final fallback
            best_neighbor_idx = None
            min_gap = float("inf")
            
            for v_idx in valid_chunk_indices:
                v_chunk = chunks[v_idx]
                if v_chunk["end"] <= chunk["start"]:
                    gap = chunk["start"] - v_chunk["end"]
                elif chunk["end"] <= v_chunk["start"]:
                    gap = v_chunk["start"] - chunk["end"]
                else:
                    gap = 0.0
                    
                if gap < min_gap:
                    min_gap = gap
                    best_neighbor_idx = v_idx
                    
            if best_neighbor_idx is not None:
                chunk_speakers[idx] = chunk_speakers[best_neighbor_idx]
                logger.debug(f"[Hybrid Fallback] Short chunk {idx} assigned via temporal neighbor fallback (gap={min_gap:.2f}s)")
            else:
                chunk_speakers[idx] = 0 # absolute fallback

        # Reconstruct turns
        reconstructed_turns = []
        current_turn = None
        
        for idx, chunk in enumerate(chunks):
            spk = f"SPEAKER_{chunk_speakers[idx]:02d}"
            if current_turn is None:
                current_turn = {
                    "start": chunk["start"],
                    "end": chunk["end"],
                    "speaker_label": spk
                }
            elif current_turn["speaker_label"] == spk:
                current_turn["end"] = chunk["end"]
            else:
                reconstructed_turns.append(current_turn)
                current_turn = {
                    "start": chunk["start"],
                    "end": chunk["end"],
                    "speaker_label": spk
                }
                
        if current_turn is not None:
            reconstructed_turns.append(current_turn)
            
        return reconstructed_turns