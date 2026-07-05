import os
import re
import json
import uuid
from pathlib import Path
from loguru import logger
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob

class PIIRedactionService:
    """
    Service responsible for loading structured transcript JSON from disk,
    detecting and redacting PII values using regex and Luhn checks,
    saving redacted transcript JSON to /redacted/ subfolder, and updating DB status.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    async def redact_transcript(self, call_id: uuid.UUID) -> dict:
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
            job.stage = "PII Redaction"
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Failed to transition database status to PII redaction: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database status transition failed."
            )

        # 3. Load structured transcript JSON
        storage_dir = Path("app/storage/transcripts")
        orig_path = storage_dir / f"{call_id}.json"
        
        if not orig_path.exists():
            self._handle_failure(call, job, "Structured transcript JSON file not found on disk.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Structured transcript not found for this call. Please run transcript builder first."
            )

        try:
            with open(orig_path, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)
        except Exception as e:
            logger.exception(f"Failed to read or parse original JSON: {e}")
            self._handle_failure(call, job, f"Failed to read original JSON: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Structured transcript file on disk is malformed or invalid JSON."
            )

        # Validate structured transcript schema
        if "segments" not in transcript_data or not isinstance(transcript_data["segments"], list):
            self._handle_failure(call, job, "Transcript JSON does not contain 'segments' list.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Structured transcript schema is invalid."
            )

        # 4. Redaction Processing
        redact_stats = {
            "phone": 0,
            "email": 0,
            "card": 0,
            "aadhaar": 0,
            "pan": 0,
            "upi": 0,
            "total": 0
        }

        redacted_segments = []
        for seg in transcript_data["segments"]:
            # Ensure required keys exist
            if not all(k in seg for k in ("speaker", "start_time", "end_time", "text")):
                self._handle_failure(call, job, "Segment is missing one of required fields: speaker, start_time, end_time, text.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Structured transcript segment schema is invalid."
                )

            original_text = seg["text"]
            
            # Apply redactions in specific order
            text_redacted, phone_cnt = self.redact_phones(original_text)
            text_redacted, card_cnt = self.redact_cards(text_redacted)
            text_redacted, aadhaar_cnt = self.redact_aadhaar(text_redacted)
            text_redacted, pan_cnt = self.redact_pan(text_redacted)
            text_redacted, email_cnt = self.redact_emails(text_redacted)
            text_redacted, upi_cnt = self.redact_upis(text_redacted)

            # Update stats
            redact_stats["phone"] += phone_cnt
            redact_stats["card"] += card_cnt
            redact_stats["aadhaar"] += aadhaar_cnt
            redact_stats["pan"] += pan_cnt
            redact_stats["email"] += email_cnt
            redact_stats["upi"] += upi_cnt

            # Build segment preserving speaker, timestamps, confidence
            redacted_seg = {
                "speaker": seg["speaker"],
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "text": text_redacted,
                "confidence": seg.get("confidence")
            }
            redacted_segments.append(redacted_seg)

        redact_stats["total"] = sum(v for k, v in redact_stats.items() if k != "total")

        # 5. Atomically save redacted transcript to storage/transcripts/redacted/{call_id}.json
        redacted_dir = storage_dir / "redacted"
        try:
            redacted_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.exception(f"Failed to create redacted subdirectory: {e}")
            self._handle_failure(call, job, "Failed to initialize redacted storage directory.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage initialization failed."
            )

        final_path = redacted_dir / f"{call_id}.json"
        tmp_path = redacted_dir / f"{call_id}.json.tmp"

        redacted_transcript = {
            "call_id": transcript_data["call_id"],
            "language": transcript_data.get("language"),
            "duration": transcript_data.get("duration", 0),
            "segments": redacted_segments
        }

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(redacted_transcript, f, indent=2, ensure_ascii=False)
            os.replace(str(tmp_path), str(final_path))
        except Exception as e:
            if tmp_path.exists():
                os.remove(tmp_path)
            logger.exception(f"Failed to write redacted JSON file to disk: {e}")
            self._handle_failure(call, job, f"Filesystem write failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Filesystem operation failed. Redacted transcript was not saved."
            )

        # 6. Database Update
        try:
            call.processing_status = ProcessingStatus.READY_FOR_AI_ANALYSIS
            job.status = ProcessingStatus.READY_FOR_AI_ANALYSIS
            job.stage = "Ready For AI Analysis"
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            if final_path.exists():
                os.remove(final_path)
            logger.exception(f"Failed to commit database transaction for PII redaction: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database operation failed. PII Redaction changes rolled back."
            )

        logger.info(f"Successfully redacted PII from transcript for Call ID {call_id}. Redactions stats: {redact_stats}")
        return {
            "call_id": call_id,
            "redactions": redact_stats
        }

    # Deterministic redaction rules methods
    def redact_emails(self, text: str) -> tuple[str, int]:
        pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
        matches = pattern.findall(text)
        count = len(matches)
        for m in matches:
            text = text.replace(m, "[EMAIL]")
        return text, count

    def redact_upis(self, text: str) -> tuple[str, int]:
        pattern = re.compile(r'\b[A-Za-z0-9.\-_]+@[A-Za-z0-9\-]{2,64}\b')
        matches = []
        candidates = pattern.findall(text)
        for c in candidates:
            parts = c.split("@")
            if len(parts) == 2 and "." not in parts[1]:
                if c.upper() != "[EMAIL]":
                    matches.append(c)
        count = len(matches)
        for m in matches:
            text = text.replace(m, "[UPI]")
        return text, count

    def redact_phones(self, text: str) -> tuple[str, int]:
        """
        Detect and redact Indian mobile phone numbers.

        Supported formats (all must strip to exactly 10 digits starting 6-9):
          9988776655           (plain 10-digit)
          9988-776655          (hyphen separator)
          9988 776655          (space separator)
          9988 -776655         (space then hyphen — Whisper artefact)
          99887 76655          (5+5 split)
          +91 9988776655       (country code + space)
          +91-9988776655       (country code + hyphen)
          +91 99887 76655      (country code + 5+5 split)

        Not matched:
          9988 rupees          (too few digits)
          9:30                 (time)
          12345                (5-digit price/code)
          2024-01-15           (date)
        """
        candidate_pat = re.compile(
            r'(?<![+\d])'          # not preceded by digit or '+'
            r'(?:\+?91[\s\-]?)?'  # optional +91 / 91 country code
            r'[6-9]'              # first mobile digit must be 6–9
            r'[\d\s\-]{9,15}'     # 9–15 more chars (digits + at most 3 seps)
            r'(?!\d)',            # not followed by a digit
            re.ASCII
        )
        count = 0
        matches_to_replace = []
        for m in candidate_pat.finditer(text):
            candidate = m.group(0)
            # Strip country code prefix before digit counting
            stripped = re.sub(r'^\+?91[\s\-]?', '', candidate)
            digits_only = re.sub(r'\D', '', stripped)
            sep_count = len(re.findall(r'[\s\-]', stripped))
            # Accept only if exactly 10 mobile digits and ≤3 separator characters
            if len(digits_only) == 10 and digits_only[0] in '6789' and sep_count <= 3:
                matches_to_replace.append((m.start(), m.end()))
                count += 1
        # Replace right-to-left to preserve indices
        for start, end in reversed(matches_to_replace):
            text = text[:start] + '[PHONE]' + text[end:]
        return text, count

    def redact_cards(self, text: str) -> tuple[str, int]:
        pattern = re.compile(r'\b(?:\d[\s\-]*?){13,19}\b')
        matches = pattern.findall(text)
        
        valid_cards = set()
        for m in matches:
            clean = re.sub(r'[\s\-]', '', m)
            if 13 <= len(clean) <= 19 and self._is_valid_luhn(clean):
                valid_cards.add(m)
                
        count = 0
        for vc in sorted(list(valid_cards), key=len, reverse=True):
            occurrences = text.count(vc)
            text = text.replace(vc, "[CARD]")
            count += occurrences
        return text, count

    def redact_aadhaar(self, text: str) -> tuple[str, int]:
        pattern = re.compile(
            r'(?<!\d)(?<!\d[\s\-])\b\d{4}\s\d{4}\s\d{4}\b(?![\s\-]?\d)|'
            r'(?<!\d)(?<!\d[\s\-])\b\d{4}-\d{4}-\d{4}\b(?![\s\-]?\d)|'
            r'(?<!\d)(?<!\+)(?<!\+91)\b\d{12}\b(?![\s\-]?\d)'
        )
        matches = pattern.findall(text)
        unique_matches = sorted(list(set(matches)), key=len, reverse=True)
        count = 0
        for m in unique_matches:
            if m:
                occurrences = text.count(m)
                text = text.replace(m, "[AADHAAR]")
                count += occurrences
        return text, count

    def redact_pan(self, text: str) -> tuple[str, int]:
        pattern = re.compile(r'\b[A-Za-z]{5}\d{4}[A-Za-z]\b')
        matches = pattern.findall(text)
        unique_matches = sorted(list(set(matches)), key=len, reverse=True)
        count = 0
        for m in unique_matches:
            occurrences = text.count(m)
            text = text.replace(m, "[PAN]")
            count += occurrences
        return text, count

    def _is_valid_luhn(self, card_str: str) -> bool:
        try:
            digits = [int(c) for c in card_str if c.isdigit()]
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(divmod(d * 2, 10))
            return checksum % 10 == 0
        except Exception:
            return False

    def _handle_failure(self, call: Call, job: ProcessingJob, error_msg: str) -> None:
        try:
            call.processing_status = ProcessingStatus.FAILED
            job.status = ProcessingStatus.FAILED
            job.error_message = error_msg
            self.db.commit()
            logger.warning(f"PII redaction job failed: {error_msg} for Call ID: {call.id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record PII redaction job failure in database: {e}")
