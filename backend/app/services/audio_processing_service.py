import os
import uuid
from pathlib import Path
from loguru import logger
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from pydub import AudioSegment
from pydub.effects import normalize

from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob

class AudioProcessingService:
    """
    Service responsible for loading uploaded audio, validating format details,
    converting to 16kHz mono WAV format, and normalising output gain.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    async def process_audio(self, call_id: uuid.UUID) -> dict:
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
            job.stage = "Audio Processing"
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Failed to transition status to processing: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error during status transition."
            )

        # 3. Validate Uploaded File Existence
        input_path = Path(call.audio_file)
        if not input_path.exists() or not input_path.is_file():
            self._handle_failure(call, job, "Uploaded audio file not found on disk.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio file not found on disk."
            )

        # 4. Load and Process Audio via Pydub
        try:
            sound = AudioSegment.from_file(str(input_path))
        except Exception as e:
            self._handle_failure(call, job, f"Failed to decode audio file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to decode audio file. It might be corrupted or FFmpeg is missing. Error: {str(e)}"
            )

        duration = sound.duration_seconds
        if duration <= 0:
            self._handle_failure(call, job, "Audio file has invalid duration (0 or negative).")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file has invalid duration (0 or negative)."
            )

        # Initialize output directories
        processed_dir = Path("app/storage/audio/processed")
        try:
            processed_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.exception(f"Failed to create processed audio storage directory: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage initialization failed."
            )

        unique_filename = f"{uuid.uuid4().hex}.wav"
        dest_path = processed_dir / unique_filename
        db_processed_path = str(dest_path.resolve())

        # Conversion: volume normalization, 16kHz sample rate, Mono, WAV format
        try:
            # Volume Normalization
            normalized_sound = normalize(sound)
            # Downsample to 16kHz
            normalized_sound = normalized_sound.set_frame_rate(16000)
            # Merge channels to Mono
            normalized_sound = normalized_sound.set_channels(1)
            # Save processed audio file
            normalized_sound.export(str(dest_path), format="wav")
        except Exception as e:
            if dest_path.exists():
                os.remove(dest_path)
            self._handle_failure(call, job, f"FFmpeg processing failure: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"FFmpeg audio processing failed: {str(e)}"
            )

        # 5. Extract Metadata from Processed File
        try:
            processed_sound = AudioSegment.from_file(str(dest_path))
            processed_size = dest_path.stat().st_size
            
            # WAV files bitrate calculation: sample_rate * channels * sample_width * 8
            bitrate = processed_sound.frame_rate * processed_sound.channels * processed_sound.sample_width * 8

            metadata = {
                "duration": processed_sound.duration_seconds,
                "sample_rate": processed_sound.frame_rate,
                "channels": processed_sound.channels,
                "bitrate": bitrate,
                "format": "wav",
                "size": processed_size,
                "processed_file": db_processed_path
            }
        except Exception as e:
            if dest_path.exists():
                os.remove(dest_path)
            self._handle_failure(call, job, f"Failed to read processed metadata: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to read processed file metadata."
            )

        # 6. Database Update
        try:
            call.processed_audio_file = db_processed_path
            call.audio_duration = int(round(metadata["duration"]))
            call.processing_status = ProcessingStatus.READY_FOR_TRANSCRIPTION
            
            job.status = ProcessingStatus.READY_FOR_TRANSCRIPTION
            job.stage = "Ready For Transcription"
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            if dest_path.exists():
                os.remove(dest_path)
            logger.exception(f"Database commit failed for processed call: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed. Audio processing transaction rolled back."
            )

        logger.info(f"Successfully processed call ID {call_id}. WAV duration={call.audio_duration}s saved to {call.processed_audio_file}")
        return metadata

    def _handle_failure(self, call: Call, job: ProcessingJob, error_msg: str) -> None:
        try:
            call.processing_status = ProcessingStatus.FAILED
            job.status = ProcessingStatus.FAILED
            job.error_message = error_msg
            self.db.commit()
            logger.warning(f"Job failed: {error_msg} for Call ID: {call.id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record job failure in database: {e}")
