import os
import json
import uuid
from pathlib import Path
from loguru import logger
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob
from app.models.transcript import Transcript

class TranscriptService:
    """
    Service responsible for building, managing, merging, and retrieving call transcripts.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    async def build_transcript(self, call_id: uuid.UUID) -> dict:
        # 1. Fetch Call and Job
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Call record with ID {call_id} not found."
            )

        job = self.db.query(ProcessingJob).filter(ProcessingJob.call_id == call_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processing job for Call ID {call_id} not found."
            )

        # 2. Transition status to Processing
        try:
            call.processing_status = ProcessingStatus.PROCESSING
            job.status = ProcessingStatus.PROCESSING
            job.stage = "Transcript Building"
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Failed to transition database status to transcript building: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database status transition failed."
            )

        whisper_json_path = Path(f"app/storage/transcripts/{call_id}_whisper.json")
        diarization_json_path = Path(f"app/storage/transcripts/{call_id}_diarization.json")

        if whisper_json_path.exists() and diarization_json_path.exists():
            logger.info(f"Running high-fidelity speaker alignment and text splitting for Call ID {call_id}...")
            try:
                with open(whisper_json_path, "r", encoding="utf-8") as f:
                    whisper_data = json.load(f)
                with open(diarization_json_path, "r", encoding="utf-8") as f:
                    diarization_data = json.load(f)

                raw_segments = whisper_data.get("segments", [])
                diarization_turns = diarization_data.get("diarization_turns", [])
                role_mapping = diarization_data.get("role_mapping", {})
                role_mapping_confidence = diarization_data.get("role_mapping_confidence", 0.0)

                # Safe mapping function preserving neutral speaker names if confidence is low
                def map_speaker(spk):
                    if role_mapping_confidence >= 0.5:
                        return role_mapping.get(spk, spk)
                    return spk

                # Logging diarization timestamp ranges
                logger.debug(f"[Alignment] Diarization turns: {[(t['start'], t['end'], t['speaker_label']) for t in diarization_turns]}")

                # Load existing db transcripts to get their speaker assignment as fallback
                db_transcripts = self.db.query(Transcript).filter(Transcript.call_id == call_id).order_by(Transcript.start_time.asc()).all()
                db_speaker_map = {t.start_time: t.speaker for t in db_transcripts}

                all_split_segments = []

                for seg_idx, seg in enumerate(raw_segments):
                    seg_start = float(seg["start"])
                    seg_end = float(seg["end"])
                    seg_text = str(seg["text"]).strip()
                    conf = seg.get("confidence")
                    if conf is not None:
                        try:
                            conf = float(conf)
                        except ValueError:
                            conf = None

                    logger.debug(f"[Alignment] Whisper segment {seg_idx}: start={seg_start:.2f}, end={seg_end:.2f}, text='{seg_text}'")

                    words_list = seg.get("words", [])
                    word_timestamps = []

                    if words_list:
                        # Use actual word timestamps from Whisper
                        for w in words_list:
                            word_timestamps.append({
                                "word": str(w["word"]).strip(),
                                "start": float(w["start"]),
                                "end": float(w["end"]),
                                "confidence": float(w.get("probability", 1.0))
                            })
                    else:
                        # Estimate word timestamps linearly proportional to character lengths
                        words = seg_text.split()
                        if words:
                            char_lengths = [len(w) for w in words]
                            total_chars = sum(char_lengths)
                            duration = seg_end - seg_start
                            current_time = seg_start
                            for w, length in zip(words, char_lengths):
                                w_dur = duration * (length / total_chars) if total_chars > 0 else (duration / len(words))
                                word_timestamps.append({
                                    "word": w,
                                    "start": current_time,
                                    "end": current_time + w_dur,
                                    "confidence": conf
                                })
                                current_time += w_dur

                    # Helper to map a word to a speaker label
                    def get_word_speaker(w_start, w_end, default_speaker):
                        mid = (w_start + w_end) / 2.0
                        # 1. Check if midpoint falls inside any turn
                        for turn in diarization_turns:
                            if turn["start"] <= mid <= turn["end"]:
                                return turn["speaker_label"]
                        # 2. Check for turn with max temporal overlap
                        best_spk = None
                        max_overlap = 0.0
                        for turn in diarization_turns:
                            overlap = max(0.0, min(w_end, turn["end"]) - max(w_start, turn["start"]))
                            if overlap > max_overlap:
                                max_overlap = overlap
                                best_spk = turn["speaker_label"]
                        if best_spk:
                            return best_spk
                        # 3. Match closest turn
                        if diarization_turns:
                            closest = min(diarization_turns, key=lambda t: min(abs(w_start - t["end"]), abs(w_end - t["start"])))
                            return closest["speaker_label"]
                        return default_speaker

                    # Assign each word to a speaker label and map to its role
                    default_spk = db_speaker_map.get(seg_start, "Unknown")
                    
                    split_groups = []
                    current_words = []
                    current_spk = None

                    for w in word_timestamps:
                        spk_label = get_word_speaker(w["start"], w["end"], default_spk)
                        spk = map_speaker(spk_label)
                        logger.debug(f"[Alignment] Word '{w['word']}' ({w['start']:.2f}-{w['end']:.2f}) -> speaker '{spk}'")
                        
                        if current_spk is None:
                            current_spk = spk
                            current_words.append(w)
                        elif spk == current_spk:
                            current_words.append(w)
                        else:
                            split_groups.append((current_spk, current_words))
                            current_spk = spk
                            current_words = [w]
                    if current_words:
                        split_groups.append((current_spk, current_words))

                    for spk, words in split_groups:
                        start_time = words[0]["start"]
                        end_time = words[-1]["end"]
                        text = " ".join([w["word"] for w in words]).strip()
                        avg_conf = sum([w["confidence"] for w in words if w["confidence"] is not None]) / len(words) if words else conf
                        
                        all_split_segments.append({
                            "speaker": spk,
                            "start_time": start_time,
                            "end_time": end_time,
                            "text": text,
                            "confidence": avg_conf
                        })

                # Write split segments to Database, replacing existing ones
                self.db.query(Transcript).filter(Transcript.call_id == call_id).delete()
                self.db.flush()

                for s_item in all_split_segments:
                    transcript_seg = Transcript(
                        call_id=call_id,
                        speaker=s_item["speaker"],
                        start_time=s_item["start_time"],
                        end_time=s_item["end_time"],
                        text=s_item["text"],
                        confidence=s_item["confidence"]
                    )
                    self.db.add(transcript_seg)
                self.db.commit()
                logger.info(f"Database successfully updated with {len(all_split_segments)} split segments.")
            except Exception as e:
                self.db.rollback()
                logger.exception(f"Error during high-fidelity speaker splitting: {e}")
                self._handle_failure(call, job, f"High-fidelity speaker splitting failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"High-fidelity speaker splitting failed: {e}"
                )

        # 3. Fetch and validate existing transcript segments
        segments = self.db.query(Transcript).filter(Transcript.call_id == call_id).order_by(Transcript.start_time.asc()).all()
        if not segments:
            self._handle_failure(call, job, "No transcript segments found for this call.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcript segments found. Run transcription and diarization first."
            )

        # Validate segment timestamps
        for seg in segments:
            if seg.start_time < 0 or seg.end_time < 0:
                self._handle_failure(call, job, f"Negative timestamp detected in segment ID {seg.id}.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid segment timestamps. Negative values are not allowed (start={seg.start_time}, end={seg.end_time})."
                )
            if seg.end_time <= seg.start_time:
                self._handle_failure(call, job, f"End time before or equal to start time in segment ID {seg.id}.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid segment timestamps. End time must be after start time (start={seg.start_time}, end={seg.end_time})."
                )

        # 4. Merge Logic
        merged_groups = []
        current_group = []

        for seg in segments:
            if not current_group:
                current_group.append(seg)
                continue
            
            last_seg = current_group[-1]
            time_gap = seg.start_time - last_seg.end_time
            
            # Merging conditions:
            # - Same speaker label
            # - Time gap <= 1.5 seconds
            # And do NOT merge different speakers, large gaps, or Unknown/neutral with known
            can_merge = (
                seg.speaker == last_seg.speaker and
                time_gap <= 1.5
            )
            
            if can_merge:
                current_group.append(seg)
            else:
                merged_groups.append(current_group)
                current_group = [seg]
                
        if current_group:
            merged_groups.append(current_group)

        # Formulate merged segments list
        merged_segments = []
        for group in merged_groups:
            start_time = group[0].start_time
            end_time = group[-1].end_time
            speaker = group[0].speaker
            text = " ".join([s.text.strip() for s in group]).strip()

            # Calculate duration-weighted average confidence
            total_weighted_conf = 0.0
            total_duration = 0.0
            for s in group:
                duration = s.end_time - s.start_time
                if s.confidence is not None:
                    total_weighted_conf += duration * float(s.confidence)
                    total_duration += duration

            if total_duration > 0.0:
                confidence = round(total_weighted_conf / total_duration, 4)
            else:
                confidence = None

            merged_segments.append({
                "speaker": speaker,
                "start_time": start_time,
                "end_time": end_time,
                "text": text,
                "confidence": confidence
            })
            logger.debug(f"[Alignment] Final merged turn: speaker={speaker}, start={start_time:.2f}, end={end_time:.2f}, text='{text}'")

        # 5. Atomically Save Structured JSON Artifact
        storage_dir = Path("app/storage/transcripts")
        try:
            storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.exception(f"Failed to create transcripts storage directory: {e}")
            self._handle_failure(call, job, "Storage initialization failed.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage initialization failed."
            )

        final_path = storage_dir / f"{call_id}.json"
        tmp_path = storage_dir / f"{call_id}.json.tmp"

        structured_transcript = {
            "call_id": str(call_id),
            "language": call.language,
            "duration": call.audio_duration or 0,
            "segments": merged_segments
        }

        try:
            # Write atomically
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(structured_transcript, f, indent=2, ensure_ascii=False)
            # Rename temp file to final destination
            os.replace(str(tmp_path), str(final_path))
        except Exception as e:
            if tmp_path.exists():
                os.remove(tmp_path)
            logger.exception(f"Filesystem write failed for transcript JSON: {e}")
            self._handle_failure(call, job, f"Filesystem write failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write structured transcript to storage: {str(e)}"
            )

        # 6. Database Update
        try:
            call.processing_status = ProcessingStatus.READY_FOR_PII_REDACTION
            job.status = ProcessingStatus.READY_FOR_PII_REDACTION
            job.stage = "Ready For PII Redaction"
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # Clean up the created file on database failure
            if final_path.exists():
                os.remove(final_path)
            logger.exception(f"Database commit failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed. Transcript build rolled back."
            )

        logger.info(f"Successfully built structured transcript for Call ID {call_id} containing {len(merged_segments)} merged segments.")
        return {
            "call_id": call_id,
            "segments_count": len(merged_segments)
        }

    def _handle_failure(self, call: Call, job: ProcessingJob, error_msg: str) -> None:
        try:
            call.processing_status = ProcessingStatus.FAILED
            job.status = ProcessingStatus.FAILED
            job.error_message = error_msg
            self.db.commit()
            logger.warning(f"Transcript building job failed: {error_msg} for Call ID: {call.id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record transcript building job failure in database: {e}")
