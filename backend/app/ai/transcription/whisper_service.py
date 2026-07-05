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

# Conditional import of whisper to prevent memory/GPU crashes in dev if mocked
if not settings.WHISPER_MOCK:
    try:
        import whisper
    except ImportError:
        whisper = None
else:
    whisper = None

class WhisperService:
    """
    Service responsible for loading local OpenAI Whisper models, running transcription,
    detecting language, parsing text segments, and storing transcripts.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    async def transcribe_call(self, call_id: uuid.UUID) -> dict:
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
            job.stage = "Transcription"
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Failed to transition database status to transcription processing: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database status transition failed."
            )

        # 3. Validate processed audio file existence
        if not call.processed_audio_file:
            self._handle_failure(call, job, "Processed WAV file path is not set in Call record.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No processed audio file found. Run audio processing first."
            )

        audio_path = call.processed_audio_file
        if not os.path.exists(audio_path):
            self._handle_failure(call, job, f"Processed WAV file not found on disk at: {audio_path}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Processed WAV file not found on disk at: {audio_path}"
            )

        # 4. Transcribe (Mock vs Real)
        if settings.WHISPER_MOCK:
            logger.info("Whisper running in MOCK mode.")
            result = self._get_mock_transcription(call.audio_duration or 10, call.audio_file or "")
        else:
            if whisper is None:
                self._handle_failure(call, job, "openai-whisper library is not installed in the python environment.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Whisper engine library missing. Install dependencies or enable WHISPER_MOCK."
                )
            
            try:
                logger.info(f"Loading local Whisper model: '{settings.WHISPER_MODEL}'...")
                model = whisper.load_model(settings.WHISPER_MODEL)
            except Exception as e:
                self._handle_failure(call, job, f"Whisper model load failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Whisper model load failed: {str(e)}"
                )

            try:
                logger.info(f"Running Whisper transcription on audio file: {audio_path}...")
                result = model.transcribe(audio_path, word_timestamps=True, task="transcribe")
            except Exception as e:
                self._handle_failure(call, job, f"Whisper transcription failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Whisper transcription failed: {str(e)}"
                )

        detected_language = result.get("language", "en")
        language_confidence = result.get("language_probability") or result.get("language_confidence")
        if language_confidence is not None:
            try:
                language_confidence = float(language_confidence)
            except ValueError:
                language_confidence = None

        segments = result.get("segments", [])

        # Save raw whisper output to a cache file for high-fidelity alignment in later stages
        storage_dir = Path("app/storage/transcripts")
        storage_dir.mkdir(parents=True, exist_ok=True)
        whisper_json_path = storage_dir / f"{call_id}_whisper.json"
        try:
            import json
            with open(whisper_json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"Cached raw Whisper output to {whisper_json_path}")
        except Exception as e:
            logger.warning(f"Failed to save raw whisper JSON cache: {e}")

        # 5. Save segments and update database records
        try:
            # Delete any existing transcript records for this call (ensures idempotency)
            self.db.query(Transcript).filter(Transcript.call_id == call_id).delete()

            for seg in segments:
                # Calculate confidence score if available, or default to standard float
                conf = seg.get("confidence")
                if conf is not None:
                    try:
                        conf = float(conf)
                    except ValueError:
                        conf = None

                transcript_seg = Transcript(
                    call_id=call_id,
                    speaker="Unknown",  # Default placeholder for non-diarized segments
                    start_time=float(seg["start"]),
                    end_time=float(seg["end"]),
                    text=str(seg["text"]).strip(),
                    confidence=conf
                )
                self.db.add(transcript_seg)

            # Update Call language, language_confidence, and status
            call.language = detected_language
            call.language_confidence = language_confidence
            call.processing_status = ProcessingStatus.READY_FOR_DIARIZATION

            # Update Job stage and status
            job.status = ProcessingStatus.READY_FOR_DIARIZATION
            job.stage = "Ready For Diarization"

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Failed to save transcription segments to database: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed while saving transcription results."
            )

        logger.info(f"Successfully transcribed Call ID {call_id}. Language: {detected_language} (confidence: {language_confidence}), Segments: {len(segments)}")
        return {
            "language": detected_language,
            "language_confidence": language_confidence,
            "segments_count": len(segments)
        }

    def _get_mock_transcription(self, duration: int, audio_file: str = "") -> dict:
        """
        Generates realistic mock transcription segments based on the call duration and audio file language markers.
        """
        audio_lower = audio_file.lower()
        if "kannada" in audio_lower or "kanglish" in audio_lower or "kn" in audio_lower:
            language = "kn"
            language_probability = 0.98
            mock_phrases = [
                "ಹಲೋ, FitNova ಗೆ ಸ್ವಾಗತ. ನನ್ನ ಹೆಸರು ಜಾನ್. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
                "ನನ್ನ ತೂಕ ಕಡಿಮೆ ಮಾಡಬೇಕು.",
                "ಖಂಡಿತ! We offer customized weight loss coaching, muscle building, and nutrition planning.",
                "Nanna weight around eight kilos reduce madbeku.",
                "ಆದರೆ ಬೆಲೆ ಎಷ್ಟು ಎಂದು ಹೇಳಿ?",
                "We have standard coaching packages starting at ninety-nine dollars per week.",
                "ಓಕೆ, ಅದು ನನ್ನ ಬಜೆಟ್‌ಗೆ ಸರಿಹೊಂದುತ್ತದೆ. Can we schedule an intake session for this Friday?",
                "ಹೌದು, ನಾನು ಶುಕ್ರವಾರ ಬೆಳಿಗ್ಗೆ 10 ಗಂಟೆಗೆ ಬುಕ್ ಮಾಡಬಹುದು. I will send over the forms now.",
                "ಧನ್ಯವಾದಗಳು ಜಾನ್. Looking forward to getting started."
            ]
        elif "hindi" in audio_lower or "hinglish" in audio_lower or "hi" in audio_lower:
            language = "hi"
            language_probability = 0.97
            mock_phrases = [
                "नमस्ते, FitNova में आपका स्वागत है। मेरा नाम जॉन है। मैं आपकी क्या मदद कर सकता हूँ?",
                "मुझे तीन महीने में वजन कम करना है।",
                "बिल्कुल! We offer customized weight loss coaching, muscle building, and nutrition planning.",
                "Mujhe three months mein weight lose karna hai.",
                "कीमत क्या है साप्ताहिक सत्रों की?",
                "We have standard coaching packages starting at ninety-nine dollars per week.",
                "ठीक है, यह मेरे बजट में है। Can we schedule an intake session for this Friday?",
                "हाँ, मैं शुक्रवार सुबह दस बजे बुक कर सकता हूँ। I will send over the forms now.",
                "बहुत धन्यवाद जॉन। Looking forward to getting started."
            ]
        else:
            language = "en"
            language_probability = 0.99
            mock_phrases = [
                "Hello, thank you for calling FitNova. My name is John. How can I help you today?",
                "Hi John, I am interested in learning more about your personal training programs.",
                "Absolutely! We offer customized weight loss coaching, muscle building, and nutrition planning.",
                "That sounds perfect. What are the pricing options for weekly sessions?",
                "We have standard coaching packages starting at ninety-nine dollars per week.",
                "Okay, that fits my budget. Can we schedule an intake session for this Friday?",
                "Yes, I can book you for Friday morning at ten A.M. I will send over the forms now.",
                "Great, thank you John. Looking forward to getting started.",
                "You are welcome! Have a fantastic day, and we will speak on Friday."
            ]
        
        segments = []
        seg_duration = 8.0
        num_segments = int(duration // seg_duration) + 1
        
        for i in range(num_segments):
            start = i * seg_duration
            end = min(start + seg_duration, float(duration))
            if start >= duration:
                break
            
            phrase_idx = i % len(mock_phrases)
            text = mock_phrases[phrase_idx]
            
            words = text.split()
            word_list = []
            dur = end - start
            num_words = len(words)
            if num_words > 0:
                word_dur = dur / num_words
                for w_idx, w in enumerate(words):
                    word_list.append({
                        "word": w,
                        "start": start + w_idx * word_dur,
                        "end": start + (w_idx + 1) * word_dur,
                        "probability": 0.95
                    })

            segments.append({
                "start": start,
                "end": end,
                "text": text,
                "confidence": 0.92 - (0.01 * (i % 5)),
                "words": word_list
            })

        return {
            "language": language,
            "language_probability": language_probability,
            "segments": segments
        }

    def _handle_failure(self, call: Call, job: ProcessingJob, error_msg: str) -> None:
        try:
            call.processing_status = ProcessingStatus.FAILED
            job.status = ProcessingStatus.FAILED
            job.error_message = error_msg
            self.db.commit()
            logger.warning(f"Transcription job failed: {error_msg} for Call ID: {call.id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record transcription job failure in database: {e}")
