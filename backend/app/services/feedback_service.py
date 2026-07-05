import json
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.ai.analysis.validators import ALLOWED_CATEGORIES, SEVERITY_MAP, ABSENCE_TAGS, normalize_text
from app.ai.pii.pii_redaction_service import PIIRedactionService
from app.models.advisor import Advisor
from app.models.call import Call
from app.models.feedback import Feedback, FeedbackType
from app.models.issue import IssueTag, IssueSeverity
from app.models.score import CallScore
from app.models.summary import AISummary

REDACTED_TRANSCRIPT_DIR = Path("app/storage/transcripts/redacted")

OFFICIAL_WEIGHTS = {
    "rapport": 0.10,
    "needs_discovery": 0.20,
    "product_knowledge": 0.10,
    "objection_handling": 0.15,
    "compliance": 0.20,
    "trial_booking": 0.15,
    "closing": 0.10,
}


def _load_redacted_transcript(call_id: uuid.UUID) -> list[dict]:
    """Helper to load redacted transcript from disk or raise 400."""
    path = REDACTED_TRANSCRIPT_DIR / f"{call_id}.json"
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redacted transcript file missing on disk."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return data.get("segments", [])
    except Exception as exc:
        logger.exception(f"Failed to load or parse transcript JSON: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redacted transcript file is corrupt or invalid JSON."
        )


def _redact_text(db: Session, text: str) -> str:
    """Helper to apply existing PII redactions on a string."""
    service = PIIRedactionService(db)
    text_redacted, _ = service.redact_phones(text)
    text_redacted, _ = service.redact_cards(text_redacted)
    text_redacted, _ = service.redact_aadhaar(text_redacted)
    text_redacted, _ = service.redact_pan(text_redacted)
    text_redacted, _ = service.redact_emails(text_redacted)
    text_redacted, _ = service.redact_upis(text_redacted)
    return text_redacted


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # 1. Score Correction
    # -----------------------------------------------------------------------

    def correct_score(
        self,
        call_id: uuid.UUID,
        reviewer_name: str,
        dimension: str,
        corrected_score: int,
        comments: str | None = None,
    ) -> Feedback:
        # Validate Call exists
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found.")

        # Validate CallScore exists
        score_row = self.db.query(CallScore).filter(CallScore.call_id == call_id).first()
        if not score_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call score not found.")

        # Validate dimension
        field_name = f"{dimension}_score"
        if not hasattr(score_row, field_name):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid score dimension.")

        # Retrieve original value
        original_score = getattr(score_row, field_name)

        feedback = Feedback(
            call_id=call_id,
            reviewer_name=reviewer_name,
            feedback_type=FeedbackType.SCORE,
            original_value=json.dumps({"dimension": dimension, "score": original_score}),
            corrected_value=json.dumps({"dimension": dimension, "score": corrected_score}),
            comments=comments,
            reviewed_at=datetime.utcnow()
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    # -----------------------------------------------------------------------
    # 2. Issue Tag Review
    # -----------------------------------------------------------------------

    def reject_tag(
        self,
        call_id: uuid.UUID,
        issue_tag_id: uuid.UUID,
        reviewer_name: str,
        comments: str | None = None,
    ) -> Feedback:
        # Validate Call exists
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found.")

        # Validate IssueTag exists
        tag = self.db.query(IssueTag).filter(IssueTag.id == issue_tag_id).first()
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue tag not found.")

        if tag.call_id != call_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue tag belongs to another call."
            )

        feedback = Feedback(
            call_id=call_id,
            reviewer_name=reviewer_name,
            feedback_type=FeedbackType.TAG,
            original_value=json.dumps({"action": "reject", "issue_tag_id": str(issue_tag_id)}),
            corrected_value=json.dumps({"rejected": True}),
            comments=comments,
            reviewed_at=datetime.utcnow()
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def correct_tag(
        self,
        call_id: uuid.UUID,
        issue_tag_id: uuid.UUID,
        reviewer_name: str,
        category: str,
        timestamp: float | None = None,
        quote: str | None = None,
        reason: str | None = None,
        comments: str | None = None,
    ) -> Feedback:
        # Validate Call exists
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found.")

        # Validate IssueTag exists
        tag = self.db.query(IssueTag).filter(IssueTag.id == issue_tag_id).first()
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue tag not found.")

        if tag.call_id != call_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue tag belongs to another call."
            )

        # Validate taxonomy category
        if category not in ALLOWED_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Category {category} not in official taxonomy."
            )

        # Derive severity exclusively from server-side taxonomy
        severity = SEVERITY_MAP[category].value

        # Load redacted transcript segments to verify quote
        segments = _load_redacted_transcript(call_id)

        corrected_timestamp = timestamp
        corrected_speaker = tag.speaker

        if category in ABSENCE_TAGS:
            # Absence tags don't require quote verification
            corrected_quote = None
            corrected_timestamp = None
            corrected_speaker = None
        else:
            if not quote:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quote is required for this issue category."
                )
            norm_quote = normalize_text(quote)
            matched_seg = None
            for seg in segments:
                norm_seg = normalize_text(seg.get("text", ""))
                if norm_quote in norm_seg:
                    matched_seg = seg
                    break

            if not matched_seg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Hallucinated evidence quote. Quote must exist in redacted transcript."
                )

            # Auto-correct timestamp & speaker to match the transcript segment
            corrected_quote = quote
            corrected_timestamp = float(matched_seg["start_time"])
            corrected_speaker = matched_seg["speaker"]

        original_tag_dict = {
            "category": tag.category,
            "severity": tag.severity.value if hasattr(tag.severity, "value") else str(tag.severity),
            "timestamp": tag.timestamp,
            "speaker": tag.speaker,
            "quote": tag.quote,
            "reason": tag.reason,
            "confidence": float(tag.confidence) if tag.confidence is not None else 1.0,
        }

        corrected_tag_dict = {
            "category": category,
            "severity": severity,
            "timestamp": corrected_timestamp,
            "speaker": corrected_speaker,
            "quote": corrected_quote,
            "reason": reason or tag.reason,
            "confidence": 1.0,
        }

        feedback = Feedback(
            call_id=call_id,
            reviewer_name=reviewer_name,
            feedback_type=FeedbackType.TAG,
            original_value=json.dumps({
                "action": "correct",
                "issue_tag_id": str(issue_tag_id),
                "tag": original_tag_dict
            }),
            corrected_value=json.dumps({
                "tag": corrected_tag_dict
            }),
            comments=comments,
            reviewed_at=datetime.utcnow()
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    def add_tag(
        self,
        call_id: uuid.UUID,
        reviewer_name: str,
        category: str,
        timestamp: float | None = None,
        quote: str | None = None,
        reason: str | None = None,
        comments: str | None = None,
    ) -> Feedback:
        # Validate Call exists
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found.")

        # Validate taxonomy category
        if category not in ALLOWED_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Category {category} not in official taxonomy."
            )

        # Derive severity exclusively from server-side taxonomy
        severity = SEVERITY_MAP[category].value

        # Load redacted transcript segments to verify quote
        segments = _load_redacted_transcript(call_id)

        corrected_timestamp = timestamp
        corrected_speaker = "Advisor"  # Default fallback if quote not matched

        if category in ABSENCE_TAGS:
            corrected_quote = None
            corrected_timestamp = None
            corrected_speaker = None
        else:
            if not quote:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quote is required for this issue category."
                )
            norm_quote = normalize_text(quote)
            matched_seg = None
            for seg in segments:
                norm_seg = normalize_text(seg.get("text", ""))
                if norm_quote in norm_seg:
                    matched_seg = seg
                    break

            if not matched_seg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Hallucinated evidence quote. Quote must exist in redacted transcript."
                )

            # Auto-correct timestamp & speaker to match the transcript segment
            corrected_quote = quote
            corrected_timestamp = float(matched_seg["start_time"])
            corrected_speaker = matched_seg["speaker"]

        new_tag_id = str(uuid.uuid4())
        new_tag_dict = {
            "id": new_tag_id,
            "category": category,
            "severity": severity,
            "timestamp": corrected_timestamp,
            "speaker": corrected_speaker,
            "quote": corrected_quote,
            "reason": reason or "Manually flagged issue.",
            "confidence": 1.0,
        }

        feedback = Feedback(
            call_id=call_id,
            reviewer_name=reviewer_name,
            feedback_type=FeedbackType.TAG,
            original_value=json.dumps({"action": "add"}),
            corrected_value=json.dumps({"tag": new_tag_dict}),
            comments=comments,
            reviewed_at=datetime.utcnow()
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    # -----------------------------------------------------------------------
    # 3. Summary Correction
    # -----------------------------------------------------------------------

    def correct_summary(
        self,
        call_id: uuid.UUID,
        reviewer_name: str,
        field: str,
        corrected_value: str,
        comments: str | None = None,
    ) -> Feedback:
        # Validate Call exists
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found.")

        # Validate AISummary exists
        summary = self.db.query(AISummary).filter(AISummary.call_id == call_id).first()
        if not summary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI summary not found.")

        # Validate summary fields
        allowed_fields = {"executive_summary", "customer_goal", "objections", "recommended_next_step", "sentiment"}
        if field not in allowed_fields:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid summary field.")

        # Sentiment specific values validation
        if field == "sentiment":
            allowed_sentiments = {"Positive", "Neutral", "Negative", "Mixed"}
            if corrected_value not in allowed_sentiments:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Sentiment must be one of {allowed_sentiments}."
                )

        original_val = getattr(summary, field)

        feedback = Feedback(
            call_id=call_id,
            reviewer_name=reviewer_name,
            feedback_type=FeedbackType.SUMMARY,
            original_value=json.dumps({"field": field, "value": original_val}),
            corrected_value=json.dumps({"field": field, "value": corrected_value}),
            comments=comments,
            reviewed_at=datetime.utcnow()
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    # -----------------------------------------------------------------------
    # 4. Transcript Correction
    # -----------------------------------------------------------------------

    def correct_transcript(
        self,
        call_id: uuid.UUID,
        reviewer_name: str,
        segment_index: int,
        corrected_speaker: str,
        corrected_text: str,
        comments: str | None = None,
    ) -> Feedback:
        # Validate Call exists
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if not call:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found.")

        # Load redacted transcript segments to verify index & speaker
        segments = _load_redacted_transcript(call_id)

        if segment_index < 0 or segment_index >= len(segments):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcript segment index {segment_index} not found."
            )

        # Validate transcript speaker
        allowed_speakers = {"Advisor", "Customer", "Unknown"}
        if corrected_speaker not in allowed_speakers:
            # If it is a neutral SPEAKER_XX label
            if re.match(r"^SPEAKER_\d+$", corrected_speaker):
                # Only allow it if it already exists in the call's original redacted transcript
                original_speakers = {seg.get("speaker") for seg in segments}
                if corrected_speaker not in original_speakers:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Speaker label '{corrected_speaker}' is not present in original transcript."
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid speaker label format."
                )

        original_seg = segments[segment_index]

        # Apply deterministic PII redaction on corrected text
        redacted_text = _redact_text(self.db, corrected_text)

        original_val = {
            "segment_index": segment_index,
            "segment": {
                "speaker": original_seg.get("speaker", "Unknown"),
                "start_time": float(original_seg.get("start_time", original_seg.get("start", 0.0))),
                "end_time": float(original_seg.get("end_time", original_seg.get("end", 0.0))),
                "text": original_seg.get("text", "")
            }
        }

        corrected_val = {
            "segment_index": segment_index,
            "segment": {
                "speaker": corrected_speaker,
                "start_time": float(original_seg.get("start_time", original_seg.get("start", 0.0))),
                "end_time": float(original_seg.get("end_time", original_seg.get("end", 0.0))),
                "text": redacted_text
            }
        }

        feedback = Feedback(
            call_id=call_id,
            reviewer_name=reviewer_name,
            feedback_type=FeedbackType.TRANSCRIPT,
            original_value=json.dumps(original_val),
            corrected_value=json.dumps(corrected_val),
            comments=comments,
            reviewed_at=datetime.utcnow()
        )
        self.db.add(feedback)
        self.db.commit()
        self.db.refresh(feedback)
        return feedback

    # -----------------------------------------------------------------------
    # 5. Effective Reviewed View
    # -----------------------------------------------------------------------

    def get_effective_reviewed_view(self, call_id: uuid.UUID) -> dict:
        call = (
            self.db.query(Call)
            .options(
                joinedload(Call.score),
                joinedload(Call.summary),
                joinedload(Call.issue_tags),
            )
            .filter(Call.id == call_id)
            .first()
        )
        if not call:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Call not found.")

        # Load chronologically ordered feedback history
        feedbacks = (
            self.db.query(Feedback)
            .filter(Feedback.call_id == call_id)
            .order_by(Feedback.reviewed_at.asc())
            .all()
        )

        # Build original score detail
        orig_score = call.score
        score_detail = None
        if orig_score:
            score_detail = {
                "rapport": orig_score.rapport_score,
                "needs_discovery": orig_score.needs_discovery_score,
                "product_knowledge": orig_score.product_knowledge_score,
                "objection_handling": orig_score.objection_handling_score,
                "compliance": orig_score.compliance_score,
                "trial_booking": orig_score.trial_booking_score,
                "closing": orig_score.closing_score,
                "overall": orig_score.overall_score,
            }

        # Build original issue tags
        orig_tags = []
        for t in call.issue_tags:
            orig_tags.append({
                "id": str(t.id),
                "category": t.category,
                "severity": t.severity.value if hasattr(t.severity, "value") else str(t.severity),
                "timestamp": t.timestamp,
                "speaker": t.speaker,
                "quote": t.quote,
                "reason": t.reason,
                "confidence": float(t.confidence) if t.confidence is not None else 1.0,
            })

        # Build original summary
        orig_summary = call.summary
        summary_detail = None
        if orig_summary:
            summary_detail = {
                "executive_summary": orig_summary.executive_summary,
                "customer_goal": orig_summary.customer_goal,
                "objections": orig_summary.objections,
                "recommended_next_step": orig_summary.recommended_next_step,
                "sentiment": orig_summary.sentiment,
            }

        # Build original transcript
        orig_transcript = []
        try:
            orig_transcript = _load_redacted_transcript(call_id)
        except Exception:
            # Degrade gracefully if no transcript file
            pass

        # Prepare effective views
        eff_score = dict(score_detail) if score_detail else {}
        eff_tags_dict = {str(t["id"]): dict(t) for t in orig_tags}
        eff_summary = dict(summary_detail) if summary_detail else {}
        eff_transcript = [dict(s) for s in orig_transcript]

        score_corrected = False

        # Apply corrections chronologically
        for fb in feedbacks:
            try:
                c_val = json.loads(fb.corrected_value)
                o_val = json.loads(fb.original_value)
            except Exception:
                continue

            if fb.feedback_type == FeedbackType.SCORE:
                dim = c_val.get("dimension")
                val = c_val.get("score")
                if dim in eff_score:
                    eff_score[dim] = val
                    score_corrected = True

            elif fb.feedback_type == FeedbackType.TAG:
                action = o_val.get("action")
                if action == "reject":
                    tag_id = o_val.get("issue_tag_id")
                    if tag_id in eff_tags_dict:
                        eff_tags_dict.pop(tag_id)
                elif action == "correct":
                    tag_id = o_val.get("issue_tag_id")
                    corrected_tag = c_val.get("tag", {})
                    if tag_id in eff_tags_dict:
                        # Tag exists — update in-place
                        eff_tags_dict[tag_id].update(corrected_tag)
                    else:
                        # Tag was previously rejected; correction restores it
                        entry = {"id": tag_id}
                        entry.update(corrected_tag)
                        eff_tags_dict[tag_id] = entry
                elif action == "add":
                    new_tag = c_val.get("tag")
                    tag_id = new_tag.get("id")
                    eff_tags_dict[tag_id] = new_tag

            elif fb.feedback_type == FeedbackType.SUMMARY:
                field = c_val.get("field")
                val = c_val.get("value")
                if field in eff_summary:
                    eff_summary[field] = val

            elif fb.feedback_type == FeedbackType.TRANSCRIPT:
                seg_idx = c_val.get("segment_index")
                corrected_seg = c_val.get("segment")
                if 0 <= seg_idx < len(eff_transcript):
                    eff_transcript[seg_idx]["speaker"] = corrected_seg.get("speaker")
                    eff_transcript[seg_idx]["text"] = corrected_seg.get("text")

        # Recalculate overall score if dimension was corrected
        if score_corrected and eff_score:
            weighted_sum = 0.0
            for k, weight in OFFICIAL_WEIGHTS.items():
                val = eff_score.get(k)
                if val is not None:
                    weighted_sum += val * weight
            eff_score["overall"] = int(round(weighted_sum))

        # Compose output history (descending reviewed_at)
        history = []
        for fb in feedbacks[::-1]:
            try:
                orig_parsed = json.loads(fb.original_value)
                corr_parsed = json.loads(fb.corrected_value)
            except Exception:
                orig_parsed = fb.original_value
                corr_parsed = fb.corrected_value

            history.append({
                "feedback_id": fb.id,
                "feedback_type": fb.feedback_type.value,
                "reviewer_name": fb.reviewer_name,
                "original_value": orig_parsed,
                "corrected_value": corr_parsed,
                "comments": fb.comments,
                "reviewed_at": fb.reviewed_at
            })

        return {
            "call_id": call_id,
            "original_score": score_detail,
            "effective_score": eff_score or None,
            "original_issue_tags": orig_tags,
            "effective_issue_tags": list(eff_tags_dict.values()),
            "original_summary": summary_detail,
            "effective_summary": eff_summary or None,
            "original_transcript": orig_transcript,
            "effective_transcript": eff_transcript,
            "feedback_history": history,
        }

    # -----------------------------------------------------------------------
    # 6. Feedback History
    # -----------------------------------------------------------------------

    def get_feedback_history(self, call_id: uuid.UUID) -> list[dict]:
        feedbacks = (
            self.db.query(Feedback)
            .filter(Feedback.call_id == call_id)
            .order_by(Feedback.reviewed_at.desc())
            .all()
        )
        history = []
        for fb in feedbacks:
            try:
                orig_parsed = json.loads(fb.original_value)
                corr_parsed = json.loads(fb.corrected_value)
            except Exception:
                orig_parsed = fb.original_value
                corr_parsed = fb.corrected_value

            history.append({
                "feedback_id": fb.id,
                "feedback_type": fb.feedback_type.value,
                "reviewer_name": fb.reviewer_name,
                "original_value": orig_parsed,
                "corrected_value": corr_parsed,
                "comments": fb.comments,
                "reviewed_at": fb.reviewed_at
            })
        return history

    # -----------------------------------------------------------------------
    # 7. Safe Feedback Export Dataset
    # -----------------------------------------------------------------------

    def export_feedback_dataset(
        self,
        feedback_type: FeedbackType | None = None,
        team_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        query = self.db.query(Feedback)

        if team_id is not None:
            advisor_ids_sq = self.db.query(Advisor.id).filter(Advisor.team_id == team_id).subquery()
            query = query.join(Call, Call.id == Feedback.call_id).filter(Call.advisor_id.in_(advisor_ids_sq))

        if feedback_type:
            query = query.filter(Feedback.feedback_type == feedback_type)

        if start_date:
            query = query.filter(Feedback.reviewed_at >= datetime.combine(start_date, datetime.min.time()))

        if end_date:
            query = query.filter(Feedback.reviewed_at <= datetime.combine(end_date, datetime.max.time()))

        feedbacks = query.order_by(Feedback.reviewed_at.desc()).all()

        dataset = []
        for fb in feedbacks:
            try:
                orig_parsed = json.loads(fb.original_value)
                corr_parsed = json.loads(fb.corrected_value)
            except Exception:
                orig_parsed = fb.original_value
                corr_parsed = fb.corrected_value

            dataset.append({
                "call_id": fb.call_id,
                "feedback_type": fb.feedback_type.value,
                "original_value": orig_parsed,
                "corrected_value": corr_parsed,
                "comments": fb.comments,
                "reviewed_at": fb.reviewed_at
            })
        return dataset
