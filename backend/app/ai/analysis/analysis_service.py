import os
import json
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from loguru import logger
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob
from app.models.score import CallScore
from app.models.summary import AISummary
from app.models.issue import IssueTag

from app.ai.analysis.openai_provider import OpenAIProvider
from app.ai.analysis.groq_provider import GroqProvider
from app.ai.analysis.mock_provider import MockProvider
from app.ai.analysis.validators import validate_and_correct_tag, ALLOWED_CATEGORIES, SEVERITY_MAP
from app.prompts.sales_analysis_v1 import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

class AnalysisService:
    """
    Main orchestrator service for the AI Analysis Engine.
    Computes deterministic metrics, queries LLM providers with retry safety bounds,
    runs anti-hallucination evidence checks, and persists outcomes idempotently.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    async def analyze_call(self, call_id: uuid.UUID) -> dict:
        start_time_perf = time_ns_perf() if 'time_ns_perf' in locals() else None
        
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
            job.stage = "AI Analysis"
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Failed to transition database status to AI analysis processing: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database status transition failed."
            )

        # 3. Load Redacted Structured Transcript
        redacted_path = Path("app/storage/transcripts/redacted") / f"{call_id}.json"
        if not redacted_path.exists():
            # If redacted transcript is missing, check if unredacted is available
            unredacted_path = Path("app/storage/transcripts") / f"{call_id}.json"
            if not unredacted_path.exists():
                self._handle_failure(call, job, "Structured transcript JSON artifact not found on disk.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Structured transcript artifact not found. Please run transcript builder first."
                )
            else:
                self._handle_failure(call, job, "PII Redacted transcript JSON artifact not found on disk.")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PII Redacted transcript not found. Never submit unredacted text to AI models."
                )

        try:
            with open(redacted_path, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)
        except Exception as e:
            logger.exception(f"Failed to parse redacted transcript JSON: {e}")
            self._handle_failure(call, job, f"Failed to parse redacted transcript JSON: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Redacted transcript file on disk is malformed or invalid JSON."
            )

        segments = transcript_data.get("segments", [])
        if not segments:
            self._handle_failure(call, job, "Redacted transcript contains no segments.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Structured transcript contains no conversation segments. Cannot analyze empty call."
            )

        # 4. Deterministic Pre-checks Calculation
        pre_checks = self._calculate_conversation_metrics(transcript_data)

        # 5. Instantiate Active Provider
        provider_name = (settings.LLM_PROVIDER or "mock").lower()
        provider = None
        
        if provider_name == "openai":
            if not settings.OPENAI_API_KEY:
                self._handle_failure(call, job, "OpenAI API Key is missing from settings.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="LLM authentication configuration error."
                )
            provider = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL or "gpt-4o"
            )
        elif provider_name == "groq":
            if not settings.GROQ_API_KEY:
                self._handle_failure(call, job, "Groq API Key is missing from settings.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="LLM authentication configuration error."
                )
            provider = GroqProvider(
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL or "llama-3.3-70b-versatile"
            )
        else:
            provider = MockProvider()

        # 5b. Classify Call (Sales vs Non-Sales)
        classification = None
        # First check deterministic signals
        classification = self._get_deterministic_classification(segments)
        
        if classification is None:
            # Execute Classifier with Bounded Retries for Transient Errors
            max_classify_attempts = 3
            classify_attempt = 0
            while classify_attempt < max_classify_attempts:
                classify_attempt += 1
                try:
                    logger.info(f"Submitting call {call_id} classification to provider {provider_name} (Attempt {classify_attempt}/{max_classify_attempts})")
                    classification_raw = await provider.classify(json.dumps(segments, ensure_ascii=False))
                    classification = {
                        "call_type": str(classification_raw.get("call_type", "SALES_CALL")),
                        "is_sales_call": bool(classification_raw.get("is_sales_call", True)),
                        "confidence": float(classification_raw.get("confidence", 1.0)) if classification_raw.get("confidence") is not None else None,
                        "reason": str(classification_raw.get("reason", "Classifier processed.")),
                        "evidence": classification_raw.get("evidence")
                    }
                    break
                except (asyncio.TimeoutError, ConnectionError) as e:
                    logger.warning(f"Transient error on classification attempt {classify_attempt}: {str(e)}")
                    if classify_attempt >= max_classify_attempts:
                        self._handle_failure(
                            call,
                            job,
                            f"LLM classification execution failed after {max_classify_attempts} attempts: Timeout/Network error.",
                            retry_count=classify_attempt
                        )
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="AI classifier request timed out or network failed. Retries exhausted."
                        )
                    await asyncio.sleep(2 ** classify_attempt)
                except Exception as e:
                    logger.exception(f"Permanent provider classification error encountered: {e}")
                    self._handle_failure(call, job, f"LLM classification execution failed: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="AI classifier provider encountered a permanent error."
                    )

        # Handle non-sales call outcome
        if not classification["is_sales_call"]:
            logger.info(f"Call {call_id} classified as NON-SALES ({classification['call_type']}). Reason: {classification['reason']}. Skipping sales analysis.")
            try:
                # Idempotency step: clear existing analysis outputs for the call ID first
                self.db.query(CallScore).filter(CallScore.call_id == call_id).delete()
                self.db.query(AISummary).filter(AISummary.call_id == call_id).delete()
                self.db.query(IssueTag).filter(IssueTag.call_id == call_id).delete()
                self.db.flush()

                # Save classification details to Call record
                call.call_type = classification["call_type"]
                call.is_sales_call = False
                call.non_sales_reason = classification["reason"]
                call.classification_confidence = classification["confidence"]

                # Insert minimal AISummary containing classification details
                ai_summary = AISummary(
                    call_id=call_id,
                    executive_summary=classification["reason"],
                    customer_goal=None,
                    objections=None,
                    recommended_next_step=classification.get("evidence"),
                    sentiment="Neutral"
                )
                self.db.add(ai_summary)

                # Complete pipeline successfully
                call.processing_status = ProcessingStatus.COMPLETED
                job.status = ProcessingStatus.COMPLETED
                job.stage = "Completed"
                job.completed_at = datetime.utcnow()
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                logger.exception(f"Database write operation failed during non-sales call save: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database persistence error. Non-sales call save rolled back."
                )
            
            return {
                "is_sales_call": False,
                "call_type": classification["call_type"],
                "reason": classification["reason"]
            }

        # Otherwise, update Call record for SALES_CALL and proceed
        call.call_type = "SALES_CALL"
        call.is_sales_call = True
        call.non_sales_reason = None
        call.classification_confidence = classification["confidence"]
        self.db.flush()

        # 6. Execute Analysis Call with Bounded Retries for Transient Errors
        raw_result = None
        max_attempts = 3
        attempt = 0
        prompt_version = "sales_analysis_v1"
        start_time_call = datetime.utcnow()

        while attempt < max_attempts:
            attempt += 1
            try:
                logger.info(f"Submitting call {call_id} analysis to provider {provider_name} (Attempt {attempt}/{max_attempts})")
                raw_result = await provider.analyze(
                    transcript_text=json.dumps(segments, ensure_ascii=False),
                    rubric="Dimensions: Rapport (10%), Needs Discovery (20%), Product Knowledge (10%), Objection Handling (15%), Compliance (20%), Trial Booking (15%), Closing (10%)",
                    taxonomy=list(ALLOWED_CATEGORIES),
                    pre_checks=pre_checks,
                    system_prompt=SYSTEM_PROMPT
                )
                break  # Succeeded!
            except (asyncio.TimeoutError, ConnectionError) as e:
                logger.warning(f"Transient error on attempt {attempt}: {str(e)}")
                if attempt >= max_attempts:
                    self._handle_failure(
                        call,
                        job,
                        f"LLM execution failed after {max_attempts} attempts: Timeout/Network error.",
                        retry_count=attempt
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="AI provider request timed out or network failed. Retries exhausted."
                    )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                # Permanent or authentication error - do not retry
                logger.exception(f"Permanent provider error encountered: {e}")
                self._handle_failure(call, job, f"LLM execution failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="AI analysis provider encountered a permanent error."
                )

        duration_call = (datetime.utcnow() - start_time_call).total_seconds()
        used_model = settings.OPENAI_MODEL if provider_name == "openai" else (settings.GROQ_MODEL if provider_name == "groq" else "mock")
        logger.info(f"AI Analysis completed. Provider: {provider_name}, Model: {used_model}, Attempt: {attempt}, Duration: {duration_call:.2f}s")

        # 7. Quality Scores Extraction and Weighted Overall Calculation
        try:
            scores_data = raw_result["scores"]
            rapport = int(scores_data["rapport"]["score"])
            needs_discovery = int(scores_data["needs_discovery"]["score"])
            product_knowledge = int(scores_data["product_knowledge"]["score"])
            objection_handling = int(scores_data["objection_handling"]["score"])
            compliance = int(scores_data["compliance"]["score"])
            trial_booking = int(scores_data["trial_booking"]["score"])
            closing = int(scores_data["closing"]["score"])

            # Backend-only calculated weighted score
            overall_score = (
                rapport * 0.10
                + needs_discovery * 0.20
                + product_knowledge * 0.10
                + objection_handling * 0.15
                + compliance * 0.20
                + trial_booking * 0.15
                + closing * 0.10
            )
            # Round score to two decimal places
            overall_score = round(overall_score, 2)
        except Exception as e:
            logger.exception(f"Failed to extract scores or calculate overall score: {e}")
            self._handle_failure(call, job, f"Invalid score schema returned by provider: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse scoring metrics from provider output."
            )

        # 8. Anti-Hallucination Evidence Filter & Verification
        valid_tags = []
        raw_tags = raw_result.get("issue_tags", [])
        for tag_data in raw_tags:
            is_valid, corrected_tag = validate_and_correct_tag(tag_data, segments)
            if is_valid and corrected_tag:
                valid_tags.append(corrected_tag)

        # 9. Extract AISummary fields
        try:
            summary_data = raw_result["summary"]
            exec_summary = summary_data["executive_summary"]
            customer_goal = summary_data.get("customer_goal")
            objections = summary_data.get("objections")
            next_step = summary_data.get("recommended_next_step")
            sentiment = summary_data.get("sentiment", "Neutral")
            
            # Enforce sentiment allowlist boundary
            if sentiment not in {"Positive", "Neutral", "Negative", "Mixed"}:
                sentiment = "Neutral"
        except Exception as e:
            logger.exception(f"Failed to extract summary: {e}")
            self._handle_failure(call, job, f"Invalid summary schema returned by provider: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to parse summary metrics from provider output."
            )

        # 10. Persist Everything in One Idempotent Database Transaction
        try:
            # Idempotency step: clear existing analysis outputs for the call ID first
            self.db.query(CallScore).filter(CallScore.call_id == call_id).delete()
            self.db.query(AISummary).filter(AISummary.call_id == call_id).delete()
            self.db.query(IssueTag).filter(IssueTag.call_id == call_id).delete()
            self.db.flush()

            # Insert CallScore
            call_score = CallScore(
                call_id=call_id,
                rapport_score=rapport,
                needs_discovery_score=needs_discovery,
                product_knowledge_score=product_knowledge,
                objection_handling_score=objection_handling,
                compliance_score=compliance,
                trial_booking_score=trial_booking,
                closing_score=closing,
                overall_score=int(overall_score + 0.5)
            )
            self.db.add(call_score)

            # Insert AISummary
            ai_summary = AISummary(
                call_id=call_id,
                executive_summary=exec_summary,
                customer_goal=customer_goal,
                objections=objections,
                recommended_next_step=next_step,
                sentiment=sentiment
            )
            self.db.add(ai_summary)

            # Insert validated IssueTags
            for tag in valid_tags:
                db_tag = IssueTag(
                    call_id=call_id,
                    category=tag["category"],
                    severity=tag["severity"],
                    timestamp=tag["timestamp"],
                    speaker=tag["speaker"],
                    quote=tag["quote"],
                    reason=tag["reason"],
                    confidence=tag["confidence"]
                )
                self.db.add(db_tag)

            # Finalize call and job processing status
            call.processing_status = ProcessingStatus.COMPLETED
            job.status = ProcessingStatus.COMPLETED
            job.stage = "Completed"
            job.completed_at = datetime.utcnow()

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Database write operation failed during analysis save: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database persistence error. Analysis transaction rolled back."
            )

        return {
            "call_id": call_id,
            "overall_score": overall_score,
            "issue_tags_count": len(valid_tags)
        }

    def _calculate_conversation_metrics(self, transcript_data: dict) -> dict:
        segments = transcript_data.get("segments", [])
        total_duration = float(transcript_data.get("duration") or 0)
        
        # fallback computation if duration is 0
        if total_duration <= 0 and segments:
            total_duration = max(float(s["end_time"]) for s in segments)

        advisor_speaking_time = 0.0
        customer_speaking_time = 0.0
        advisor_turn_count = 0
        customer_turn_count = 0
        advisor_questions_count = 0

        for s in segments:
            start = float(s["start_time"])
            end = float(s["end_time"])
            duration = max(0.0, end - start)
            speaker = s.get("speaker", "")
            text = s.get("text", "")

            if speaker == "Advisor":
                advisor_speaking_time += duration
                advisor_turn_count += 1
                if "?" in text:
                    # Count how many question marks are present in Advisor segment
                    advisor_questions_count += text.count("?")
            elif speaker == "Customer":
                customer_speaking_time += duration
                customer_turn_count += 1

        advisor_talk_ratio = 0.0
        customer_talk_ratio = 0.0
        if total_duration > 0:
            advisor_talk_ratio = min(1.0, advisor_speaking_time / total_duration)
            customer_talk_ratio = min(1.0, customer_speaking_time / total_duration)

        return {
            "total_duration": total_duration,
            "advisor_speaking_time": advisor_speaking_time,
            "customer_speaking_time": customer_speaking_time,
            "advisor_talk_ratio": advisor_talk_ratio,
            "customer_talk_ratio": customer_talk_ratio,
            "advisor_turn_count": advisor_turn_count,
            "customer_turn_count": customer_turn_count,
            "advisor_questions_count": advisor_questions_count
        }

    def _handle_failure(self, call: Call, job: ProcessingJob, error_msg: str, retry_count: int = None) -> None:
        try:
            call.processing_status = ProcessingStatus.FAILED
            job.status = ProcessingStatus.FAILED
            job.error_message = error_msg
            if retry_count is not None:
                job.retry_count = retry_count
            else:
                job.retry_count = (job.retry_count or 0) + 1
            self.db.commit()
            logger.warning(f"AI Analysis job failed: {error_msg} for Call ID: {call.id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record AI Analysis failure in database: {e}")

    def _get_deterministic_classification(self, segments: list[dict]) -> dict | None:
        total_words = 0
        text_content = ""
        for seg in segments:
            text_content += " " + seg.get("text", "")
            total_words += len(seg.get("text", "").split())
            
        text_lower = text_content.lower().strip()
        
        # Test/Internal Call markers - strong explicit evidence
        if "test call" in text_lower or "internal test" in text_lower or "testing line" in text_lower:
            evidence_str = None
            for seg in segments:
                s_text = seg.get("text", "")
                if any(x in s_text.lower() for x in ["test call", "internal test", "testing line"]):
                    evidence_str = s_text
                    break
            return {
                "call_type": "INTERNAL_CALL",
                "is_sales_call": False,
                "confidence": 1.0,
                "reason": "Deterministic marker found indicating an internal/test call.",
                "evidence": evidence_str
            }
            
        return None
