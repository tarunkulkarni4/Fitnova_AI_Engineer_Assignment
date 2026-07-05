"""
DashboardService: read-only analytics across Org → Team → Advisor → Call.

Query design:
- No N+1 queries. All aggregates use SQL GROUP BY / func.avg().
- Call review: 2-step load to avoid Cartesian row multiplication.
- Call list issue filters: EXISTS correlated subqueries to keep
  one-row-per-call for correct pagination and total counts.
- No LLM calls. All values come from stored database records.
"""
import json
import math
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func, case, distinct, exists, and_
from sqlalchemy.orm import Session, joinedload

from app.models.advisor import Advisor
from app.models.call import Call, ProcessingStatus
from app.models.issue import IssueTag, IssueSeverity
from app.models.organization import Organization
from app.models.score import CallScore
from app.models.summary import AISummary
from app.models.team import Team
from app.models.transcript import Transcript

from app.schemas.dashboard import (
    AdvisorDashboardResponse,
    AdvisorListItem,
    AdvisorPerformanceSummary,
    AISummaryDetail,
    CallListItem,
    CallMetadata,
    CallReviewResponse,
    CallScoreDetail,
    DimensionAverages,
    ImprovementArea,
    IssueTagCount,
    IssueTagDetail,
    OrganizationDashboardResponse,
    PaginatedAdvisorListResponse,
    PaginatedCallListResponse,
    RecentCall,
    TeamDashboardResponse,
    TeamPerformanceSummary,
    TranscriptSegment,
)

# Path convention for redacted transcript artifacts
REDACTED_TRANSCRIPT_DIR = Path("app/storage/transcripts/redacted")

# Human-readable dimension name → CallScore column name
DIMENSION_MAP: dict[str, str] = {
    "Rapport": "rapport_score",
    "Needs Discovery": "needs_discovery_score",
    "Product Knowledge": "product_knowledge_score",
    "Objection Handling": "objection_handling_score",
    "Compliance": "compliance_score",
    "Trial Booking": "trial_booking_score",
    "Closing": "closing_score",
}


def _round2(value) -> float | None:
    """Round to 2 decimal places or return None."""
    if value is None:
        return None
    return round(float(value), 2)


def _build_dim_averages(row) -> DimensionAverages:
    """Build DimensionAverages from a SQLAlchemy aggregation result row."""
    return DimensionAverages(
        rapport=_round2(row.rapport),
        needs_discovery=_round2(row.needs_discovery),
        product_knowledge=_round2(row.product_knowledge),
        objection_handling=_round2(row.objection_handling),
        compliance=_round2(row.compliance),
        trial_booking=_round2(row.trial_booking),
        closing=_round2(row.closing),
    )


def _empty_dim_averages() -> DimensionAverages:
    return DimensionAverages()


def _compute_improvement_areas(dims: DimensionAverages) -> list[ImprovementArea]:
    """
    Deterministically select the 3 lowest-scoring dimensions.
    Dimensions with null averages are excluded.
    """
    pairs = [
        ("Rapport", dims.rapport),
        ("Needs Discovery", dims.needs_discovery),
        ("Product Knowledge", dims.product_knowledge),
        ("Objection Handling", dims.objection_handling),
        ("Compliance", dims.compliance),
        ("Trial Booking", dims.trial_booking),
        ("Closing", dims.closing),
    ]
    scored = [(name, val) for name, val in pairs if val is not None]
    scored.sort(key=lambda x: x[1])
    return [ImprovementArea(dimension=name, average_score=val) for name, val in scored[:3]]


def _load_redacted_transcript(call_id: uuid.UUID) -> tuple[bool, list[TranscriptSegment]]:
    """
    Load the redacted transcript JSON artifact from disk.
    Returns (available, segments). Never raises — degraded gracefully.
    """
    path = REDACTED_TRANSCRIPT_DIR / f"{call_id}.json"
    if not path.exists():
        logger.warning(f"Redacted transcript not found at {path}")
        return False, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        segments_raw = data if isinstance(data, list) else data.get("segments", [])
        segments = [
            TranscriptSegment(
                speaker=seg.get("speaker", "Unknown"),
                start_time=float(seg.get("start_time", seg.get("start", 0.0))),
                end_time=float(seg.get("end_time", seg.get("end", 0.0))),
                text=seg.get("text", ""),
                confidence=seg.get("confidence"),
            )
            for seg in segments_raw
        ]
        return True, segments
    except Exception as exc:
        logger.error(f"Failed to parse redacted transcript {path}: {exc}")
        return False, []


def _top_issue_tags(db: Session, call_ids_subquery, limit: int = 10) -> list[IssueTagCount]:
    """
    Return top-N issue categories by count within a set of call IDs.
    Uses a subquery so we can reuse this logic across all three dashboard levels.
    """
    rows = (
        db.query(
            IssueTag.category,
            func.count(IssueTag.id).label("cnt"),
            # Most common severity for this category
            func.max(IssueTag.severity).label("top_severity"),
        )
        .filter(IssueTag.call_id.in_(call_ids_subquery))
        .group_by(IssueTag.category)
        .order_by(func.count(IssueTag.id).desc())
        .limit(limit)
        .all()
    )
    return [
        IssueTagCount(category=r.category, count=r.cnt, severity=r.top_severity)
        for r in rows
    ]


def _call_status_counts(
    db: Session, call_ids_subquery
) -> tuple[int, int, int, int]:
    """
    Return (total, completed, failed, processing) call counts for a set of call IDs.
    Single aggregation query.
    """
    row = db.query(
        func.count(Call.id).label("total"),
        func.sum(
            case((Call.processing_status == ProcessingStatus.COMPLETED, 1), else_=0)
        ).label("completed"),
        func.sum(
            case((Call.processing_status == ProcessingStatus.FAILED, 1), else_=0)
        ).label("failed"),
        func.sum(
            case((Call.processing_status == ProcessingStatus.PROCESSING, 1), else_=0)
        ).label("processing"),
    ).filter(Call.id.in_(call_ids_subquery)).one()

    return (
        int(row.total or 0),
        int(row.completed or 0),
        int(row.failed or 0),
        int(row.processing or 0),
    )


def _dimension_avgs(db: Session, call_ids_subquery):
    """
    Return a row of 7 dimension averages scoped to completed calls with scores.
    Uses a single GROUP-less aggregation.
    """
    return (
        db.query(
            func.avg(CallScore.rapport_score).label("rapport"),
            func.avg(CallScore.needs_discovery_score).label("needs_discovery"),
            func.avg(CallScore.product_knowledge_score).label("product_knowledge"),
            func.avg(CallScore.objection_handling_score).label("objection_handling"),
            func.avg(CallScore.compliance_score).label("compliance"),
            func.avg(CallScore.trial_booking_score).label("trial_booking"),
            func.avg(CallScore.closing_score).label("closing"),
            func.avg(CallScore.overall_score).label("overall"),
        )
        .join(Call, Call.id == CallScore.call_id)
        .filter(
            Call.id.in_(call_ids_subquery),
            Call.processing_status == ProcessingStatus.COMPLETED,
        )
        .one()
    )


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 1. Organization Dashboard
    # ------------------------------------------------------------------

    def get_org_dashboard(
        self,
        organization_id: uuid.UUID,
        team_id: uuid.UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> OrganizationDashboardResponse:
        org = self.db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Organization {organization_id} not found.")

        # Subquery: all team IDs under this org (optionally narrowed to one team context)
        team_ids_sq = (
            self.db.query(Team.id)
            .filter(Team.organization_id == organization_id)
        )
        if team_id is not None:
            team_ids_sq = team_ids_sq.filter(Team.id == team_id)
        team_ids_sq = team_ids_sq.subquery()

        # Subquery: all advisor IDs under those teams
        advisor_ids_sq = (
            self.db.query(Advisor.id)
            .filter(Advisor.team_id.in_(team_ids_sq))
            .subquery()
        )

        # Subquery: all call IDs — optionally date-filtered
        call_q = self.db.query(Call.id).filter(Call.advisor_id.in_(advisor_ids_sq))
        call_q = _apply_date_filter(call_q, start_date, end_date)
        call_ids_sq = call_q.subquery()

        # Counts
        total_teams_query = self.db.query(func.count(Team.id)).filter(
            Team.organization_id == organization_id
        )
        if team_id is not None:
            total_teams_query = total_teams_query.filter(Team.id == team_id)
        total_teams = total_teams_query.scalar() or 0
        total_advisors = self.db.query(func.count(Advisor.id)).filter(
            Advisor.team_id.in_(team_ids_sq)
        ).scalar() or 0

        total, completed, failed, processing = _call_status_counts(self.db, call_ids_sq)

        # Dimension averages (completed analyzed calls only)
        dim_row = _dimension_avgs(self.db, call_ids_sq)
        dims = _build_dim_averages(dim_row)

        # Top issue tags
        top_issues = _top_issue_tags(self.db, call_ids_sq)

        # Per-team performance
        team_perf = self._team_performance_for_org(organization_id, call_ids_sq, team_id)

        return OrganizationDashboardResponse(
            organization_id=org.id,
            organization_name=org.name,
            total_teams=total_teams,
            total_advisors=total_advisors,
            total_calls=total,
            completed_calls=completed,
            failed_calls=failed,
            processing_calls=processing,
            average_quality_score=_round2(dim_row.overall),
            average_dimension_scores=dims,
            top_issue_tags=top_issues,
            team_performance=team_perf,
        )

    def _team_performance_for_org(
        self, organization_id: uuid.UUID, call_ids_sq, team_id: uuid.UUID | None = None
    ) -> list[TeamPerformanceSummary]:
        """Per-team: completed call counts + avg score in one GROUP BY query."""
        rows_query = (
            self.db.query(
                Team.id.label("team_id"),
                Team.name.label("team_name"),
                func.count(
                    case((Call.processing_status == ProcessingStatus.COMPLETED, Call.id))
                ).label("completed_calls"),
                func.avg(CallScore.overall_score).label("avg_score"),
            )
            .join(Advisor, Advisor.team_id == Team.id)
            .join(Call, Call.advisor_id == Advisor.id)
            .outerjoin(CallScore, and_(
                CallScore.call_id == Call.id,
                Call.processing_status == ProcessingStatus.COMPLETED,
            ))
            .filter(
                Team.organization_id == organization_id,
                Call.id.in_(call_ids_sq),
            )
        )
        if team_id is not None:
            rows_query = rows_query.filter(Team.id == team_id)
        rows = (
            rows_query
            .group_by(Team.id, Team.name)
            .order_by(func.avg(CallScore.overall_score).desc().nullslast())
            .all()
        )
        return [
            TeamPerformanceSummary(
                team_id=r.team_id,
                team_name=r.team_name,
                average_score=_round2(r.avg_score),
                completed_calls=int(r.completed_calls or 0),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # 2. Team Dashboard
    # ------------------------------------------------------------------

    def get_team_dashboard(
        self,
        team_id: uuid.UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TeamDashboardResponse:
        team = (
            self.db.query(Team)
            .options(joinedload(Team.organization))
            .filter(Team.id == team_id)
            .first()
        )
        if not team:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Team {team_id} not found.")

        advisor_ids_sq = (
            self.db.query(Advisor.id).filter(Advisor.team_id == team_id).subquery()
        )

        call_q = self.db.query(Call.id).filter(Call.advisor_id.in_(advisor_ids_sq))
        call_q = _apply_date_filter(call_q, start_date, end_date)
        call_ids_sq = call_q.subquery()

        total_advisors = self.db.query(func.count(Advisor.id)).filter(
            Advisor.team_id == team_id
        ).scalar() or 0
        total, completed, failed, processing = _call_status_counts(self.db, call_ids_sq)

        dim_row = _dimension_avgs(self.db, call_ids_sq)
        dims = _build_dim_averages(dim_row)
        top_issues = _top_issue_tags(self.db, call_ids_sq)
        leaderboard = self._advisor_leaderboard(team_id, call_ids_sq)

        return TeamDashboardResponse(
            team_id=team.id,
            team_name=team.name,
            organization_id=team.organization.id,
            organization_name=team.organization.name,
            total_advisors=total_advisors,
            total_calls=total,
            completed_calls=completed,
            failed_calls=failed,
            processing_calls=processing,
            average_quality_score=_round2(dim_row.overall),
            average_dimension_scores=dims,
            top_issue_tags=top_issues,
            advisor_leaderboard=leaderboard,
        )

    def _advisor_leaderboard(
        self, team_id: uuid.UUID, call_ids_sq
    ) -> list[AdvisorPerformanceSummary]:
        """
        Per-advisor: completed calls, avg overall score, critical issue count.
        All in two queries to avoid row multiplication.
        """
        # Query 1: call counts + avg score per advisor
        perf_rows = (
            self.db.query(
                Advisor.id.label("advisor_id"),
                Advisor.name.label("advisor_name"),
                func.count(
                    case((Call.processing_status == ProcessingStatus.COMPLETED, Call.id))
                ).label("completed_calls"),
                func.avg(CallScore.overall_score).label("avg_score"),
            )
            .join(Call, Call.advisor_id == Advisor.id)
            .outerjoin(CallScore, and_(
                CallScore.call_id == Call.id,
                Call.processing_status == ProcessingStatus.COMPLETED,
            ))
            .filter(
                Advisor.team_id == team_id,
                Call.id.in_(call_ids_sq),
            )
            .group_by(Advisor.id, Advisor.name)
            .order_by(func.avg(CallScore.overall_score).desc().nullslast())
            .all()
        )

        if not perf_rows:
            return []

        # Query 2: critical issue counts per advisor (single query, not N+1)
        advisor_ids = [r.advisor_id for r in perf_rows]
        critical_rows = (
            self.db.query(
                Call.advisor_id.label("advisor_id"),
                func.count(IssueTag.id).label("critical_count"),
            )
            .join(IssueTag, IssueTag.call_id == Call.id)
            .filter(
                Call.advisor_id.in_(advisor_ids),
                Call.id.in_(call_ids_sq),
                IssueTag.severity == IssueSeverity.CRITICAL,
            )
            .group_by(Call.advisor_id)
            .all()
        )
        critical_by_advisor = {str(r.advisor_id): int(r.critical_count) for r in critical_rows}

        return [
            AdvisorPerformanceSummary(
                advisor_id=r.advisor_id,
                advisor_name=r.advisor_name,
                completed_calls=int(r.completed_calls or 0),
                average_score=_round2(r.avg_score),
                critical_issue_count=critical_by_advisor.get(str(r.advisor_id), 0),
            )
            for r in perf_rows
        ]

    # ------------------------------------------------------------------
    # 3. Advisor Dashboard
    # ------------------------------------------------------------------

    def get_advisor_dashboard(
        self,
        advisor_id: uuid.UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> AdvisorDashboardResponse:
        advisor = (
            self.db.query(Advisor)
            .options(joinedload(Advisor.team).joinedload(Team.organization))
            .filter(Advisor.id == advisor_id)
            .first()
        )
        if not advisor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Advisor {advisor_id} not found.")

        call_q = self.db.query(Call.id).filter(Call.advisor_id == advisor_id)
        call_q = _apply_date_filter(call_q, start_date, end_date)
        call_ids_sq = call_q.subquery()

        total, completed, failed, processing = _call_status_counts(self.db, call_ids_sq)
        dim_row = _dimension_avgs(self.db, call_ids_sq)
        dims = _build_dim_averages(dim_row)
        top_issues = _top_issue_tags(self.db, call_ids_sq)
        recent = self._recent_calls(advisor_id, call_ids_sq)
        improvement_areas = _compute_improvement_areas(dims)

        return AdvisorDashboardResponse(
            advisor_id=advisor.id,
            advisor_name=advisor.name,
            advisor_email=advisor.email,
            advisor_status=advisor.status.value,
            team_id=advisor.team.id,
            team_name=advisor.team.name,
            organization_id=advisor.team.organization.id,
            organization_name=advisor.team.organization.name,
            total_calls=total,
            completed_calls=completed,
            failed_calls=failed,
            processing_calls=processing,
            average_quality_score=_round2(dim_row.overall),
            average_dimension_scores=dims,
            top_issue_tags=top_issues,
            recent_calls=recent,
            improvement_areas=improvement_areas,
        )

    def _recent_calls(self, advisor_id: uuid.UUID, call_ids_sq) -> list[RecentCall]:
        """Last 10 calls, newest first. Issue count loaded in a second bounded query."""
        calls = (
            self.db.query(Call)
            .outerjoin(CallScore, CallScore.call_id == Call.id)
            .filter(
                Call.advisor_id == advisor_id,
                Call.id.in_(call_ids_sq),
            )
            .order_by(Call.upload_time.desc())
            .limit(10)
            .all()
        )
        if not calls:
            return []

        call_ids = [c.id for c in calls]
        issue_counts_rows = (
            self.db.query(
                IssueTag.call_id.label("call_id"),
                func.count(IssueTag.id).label("cnt"),
            )
            .filter(IssueTag.call_id.in_(call_ids))
            .group_by(IssueTag.call_id)
            .all()
        )
        issue_by_call = {str(r.call_id): int(r.cnt) for r in issue_counts_rows}

        score_rows = (
            self.db.query(CallScore.call_id, CallScore.overall_score)
            .filter(CallScore.call_id.in_(call_ids))
            .all()
        )
        score_by_call = {str(r.call_id): r.overall_score for r in score_rows}

        return [
            RecentCall(
                call_id=c.id,
                upload_time=c.upload_time,
                duration=c.audio_duration,
                overall_score=score_by_call.get(str(c.id)),
                issue_count=issue_by_call.get(str(c.id), 0),
                processing_status=c.processing_status.value,
            )
            for c in calls
        ]

    # ------------------------------------------------------------------
    # 4. Call Review
    # ------------------------------------------------------------------

    def get_call_review(self, call_id: uuid.UUID) -> CallReviewResponse:
        """
        Two-step load to avoid Cartesian row multiplication.
        Step 1: one-to-one relationships via joinedload.
        Step 2: separate bounded IssueTag query.
        """
        call = (
            self.db.query(Call)
            .options(
                joinedload(Call.advisor).joinedload(Advisor.team).joinedload(Team.organization),
                joinedload(Call.score),
                joinedload(Call.summary),
            )
            .filter(Call.id == call_id)
            .first()
        )
        if not call:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Call {call_id} not found.")

        # Step 2: issue tags (separate query)
        tags = (
            self.db.query(IssueTag)
            .filter(IssueTag.call_id == call_id)
            .order_by(IssueTag.timestamp.asc().nullslast())
            .all()
        )

        # Load redacted transcript from disk (graceful degradation)
        transcript_available, segments = _load_redacted_transcript(call_id)
        if not transcript_available:
            # Fall back to database Transcript table rows
            db_segments = (
                self.db.query(Transcript)
                .filter(Transcript.call_id == call_id)
                .order_by(Transcript.start_time.asc())
                .all()
            )
            if db_segments:
                import os
                logger.info(f"Disk redacted transcript missing. Falling back to DB transcripts for call {call_id} (count: {len(db_segments)})")
                
                # Check privacy / apply PII redaction safely using PIIRedactionService
                from app.ai.pii.pii_redaction_service import PIIRedactionService
                pii_service = PIIRedactionService(self.db)
                
                redacted_segments = []
                for db_seg in db_segments:
                    raw_text = db_seg.text or ""
                    
                    # Apply redaction rules
                    txt, _ = pii_service.redact_phones(raw_text)
                    txt, _ = pii_service.redact_cards(txt)
                    txt, _ = pii_service.redact_aadhaar(txt)
                    txt, _ = pii_service.redact_pan(txt)
                    txt, _ = pii_service.redact_emails(txt)
                    txt, _ = pii_service.redact_upis(txt)
                    
                    redacted_segments.append(
                        TranscriptSegment(
                            speaker=db_seg.speaker or "Unknown",
                            start_time=float(db_seg.start_time),
                            end_time=float(db_seg.end_time),
                            text=txt,
                            confidence=float(db_seg.confidence) if db_seg.confidence is not None else None,
                        )
                    )
                
                segments = redacted_segments
                transcript_available = True
                
                # Rebuild/re-cache the missing redacted JSON artifact on disk so next load is fast/native
                try:
                    dict_segments = [
                        {
                            "speaker": s.speaker,
                            "start_time": s.start_time,
                            "end_time": s.end_time,
                            "text": s.text,
                            "confidence": s.confidence
                        }
                        for s in redacted_segments
                    ]
                    
                    REDACTED_TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
                    final_path = REDACTED_TRANSCRIPT_DIR / f"{call_id}.json"
                    
                    tmp_path = REDACTED_TRANSCRIPT_DIR / f"{call_id}.json.tmp"
                    redacted_transcript = {
                        "call_id": str(call_id),
                        "language": call.language,
                        "duration": call.audio_duration or 0,
                        "segments": dict_segments
                    }
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        json.dump(redacted_transcript, f, indent=2, ensure_ascii=False)
                    os.replace(str(tmp_path), str(final_path))
                    logger.info(f"Rebuilt and saved missing redacted transcript JSON file on disk for call {call_id}")
                except Exception as rebuild_err:
                    logger.warning(f"Could not rebuild missing redacted transcript file for call {call_id}: {rebuild_err}")

        advisor = call.advisor
        team = advisor.team
        org = team.organization

        metadata = CallMetadata(
            call_id=call.id,
            advisor_id=advisor.id,
            advisor_name=advisor.name,
            team_id=team.id,
            team_name=team.name,
            upload_time=call.upload_time,
            processing_status=call.processing_status.value,
            language=call.language,
            duration=call.audio_duration,
            source_type=call.source_type,
            call_type=getattr(call, "call_type", "SALES_CALL"),
            is_sales_call=getattr(call, "is_sales_call", True),
            non_sales_reason=getattr(call, "non_sales_reason", None),
            classification_confidence=getattr(call, "classification_confidence", None),
        )

        score_detail: CallScoreDetail | None = None
        if call.score:
            s = call.score
            score_detail = CallScoreDetail(
                rapport=s.rapport_score,
                needs_discovery=s.needs_discovery_score,
                product_knowledge=s.product_knowledge_score,
                objection_handling=s.objection_handling_score,
                compliance=s.compliance_score,
                trial_booking=s.trial_booking_score,
                closing=s.closing_score,
                overall=s.overall_score,
            )

        tag_details = [
            IssueTagDetail(
                category=t.category,
                severity=t.severity.value,
                timestamp=t.timestamp,
                speaker=t.speaker,
                quote=t.quote,
                reason=t.reason,
                confidence=float(t.confidence) if t.confidence is not None else None,
            )
            for t in tags
        ]

        summary_detail: AISummaryDetail | None = None
        if call.summary:
            sm = call.summary
            summary_detail = AISummaryDetail(
                executive_summary=sm.executive_summary,
                customer_goal=sm.customer_goal,
                objections=sm.objections,
                recommended_next_step=sm.recommended_next_step,
                sentiment=sm.sentiment,
            )

        return CallReviewResponse(
            metadata=metadata,
            score=score_detail,
            issue_tags=tag_details,
            summary=summary_detail,
            transcript_available=transcript_available,
            transcript=segments,
        )

    # ------------------------------------------------------------------
    # 5. Paginated / Filtered Call List
    # ------------------------------------------------------------------

    def get_call_list(
        self,
        page: int,
        page_size: int,
        organization_id: uuid.UUID | None = None,
        team_id: uuid.UUID | None = None,
        advisor_id: uuid.UUID | None = None,
        processing_status: ProcessingStatus | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        severity: IssueSeverity | None = None,
        issue_category: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        has_source_reference: bool | None = None,
        sort: Literal["newest", "oldest", "highest_score", "lowest_score"] = "newest",
    ) -> PaginatedCallListResponse:

        # Base query: Call with LEFT JOIN to Advisor and Team for name resolution
        query = (
            self.db.query(
                Call.id.label("call_id"),
                Call.advisor_id,
                Advisor.name.label("advisor_name"),
                Team.id.label("team_id"),
                Team.name.label("team_name"),
                Call.upload_time,
                Call.processing_status,
                Call.audio_duration,
                CallScore.overall_score,
                Call.call_type,
                Call.is_sales_call,
                Call.non_sales_reason,
                Call.classification_confidence,
                Call.source_type,
                Call.source_reference,
            )
            .join(Advisor, Advisor.id == Call.advisor_id)
            .join(Team, Team.id == Advisor.team_id)
            .outerjoin(CallScore, CallScore.call_id == Call.id)
        )

        # ---- Scope filters ----
        if organization_id:
            # Use query directly for IN to avoid SAWarning
            org_advisor_q = (
                self.db.query(Advisor.id)
                .join(Team, Team.id == Advisor.team_id)
                .filter(Team.organization_id == organization_id)
            )
            query = query.filter(Call.advisor_id.in_(org_advisor_q))

        if team_id:
            team_advisor_q = (
                self.db.query(Advisor.id).filter(Advisor.team_id == team_id)
            )
            query = query.filter(Call.advisor_id.in_(team_advisor_q))

        if advisor_id:
            query = query.filter(Call.advisor_id == advisor_id)

        if processing_status:
            query = query.filter(Call.processing_status == processing_status)

        # ---- Score filters (require a CallScore row) ----
        if min_score is not None:
            query = query.filter(CallScore.overall_score >= min_score)
        if max_score is not None:
            query = query.filter(CallScore.overall_score <= max_score)

        # ---- Date filter ----
        query = _apply_date_filter(query, start_date, end_date)

        # ---- Telephony / External Reference filter ----
        if has_source_reference is not None:
            if has_source_reference:
                query = query.filter(Call.source_reference.isnot(None))
            else:
                query = query.filter(Call.source_reference.is_(None))

        # ---- Issue filters: EXISTS subqueries (no row multiplication) ----
        if severity:
            query = query.filter(
                self.db.query(IssueTag)
                .filter(
                    IssueTag.call_id == Call.id,
                    IssueTag.severity == severity,
                )
                .exists()
            )

        if issue_category:
            query = query.filter(
                self.db.query(IssueTag)
                .filter(
                    IssueTag.call_id == Call.id,
                    IssueTag.category == issue_category,
                )
                .exists()
            )

        # ---- Count total (before pagination) ----
        total = query.count()

        # ---- Sorting ----
        if sort == "newest":
            query = query.order_by(Call.upload_time.desc())
        elif sort == "oldest":
            query = query.order_by(Call.upload_time.asc())
        elif sort == "highest_score":
            query = query.order_by(CallScore.overall_score.desc().nullslast())
        elif sort == "lowest_score":
            query = query.order_by(CallScore.overall_score.asc().nullsfirst())

        # ---- Pagination ----
        offset = (page - 1) * page_size
        rows = query.offset(offset).limit(page_size).all()

        # ---- Issue counts per call (single follow-up query, not N+1) ----
        call_ids = [r.call_id for r in rows]
        issue_count_rows = (
            self.db.query(
                IssueTag.call_id.label("call_id"),
                func.count(IssueTag.id).label("cnt"),
            )
            .filter(IssueTag.call_id.in_(call_ids))
            .group_by(IssueTag.call_id)
            .all()
        ) if call_ids else []
        issue_by_call = {str(r.call_id): int(r.cnt) for r in issue_count_rows}

        items = [
            CallListItem(
                call_id=r.call_id,
                advisor_id=r.advisor_id,
                advisor_name=r.advisor_name,
                team_id=r.team_id,
                team_name=r.team_name,
                upload_time=r.upload_time,
                processing_status=r.processing_status.value,
                duration=r.audio_duration,
                overall_score=r.overall_score,
                issue_count=issue_by_call.get(str(r.call_id), 0),
                call_type=getattr(r, "call_type", "SALES_CALL"),
                is_sales_call=getattr(r, "is_sales_call", True),
                non_sales_reason=getattr(r, "non_sales_reason", None),
                classification_confidence=getattr(r, "classification_confidence", None),
                source_type=getattr(r, "source_type", "MANUAL"),
                source_reference=getattr(r, "source_reference", None),
            )
            for r in rows
        ]

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return PaginatedCallListResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    # ------------------------------------------------------------------
    # 6. Advisor List (analytics, for /dashboard/advisors)
    # ------------------------------------------------------------------

    def get_advisor_list(
        self,
        organization_id: uuid.UUID | None = None,
        team_id: uuid.UUID | None = None,
        search: str | None = None,
        advisor_status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedAdvisorListResponse:
        """
        Paginated advisor list with analytics.

        Reuses the same aggregation pattern as _advisor_leaderboard():
        - Query 1: completed calls + avg score per advisor (GROUP BY)
        - Query 2: critical issue counts per advisor (single GROUP BY)
        No N+1.
        """
        from app.models.advisor import AdvisorStatus

        # Build base advisor query with optional filters
        advisor_q = (
            self.db.query(
                Advisor.id.label("advisor_id"),
                Advisor.name.label("advisor_name"),
                Advisor.email.label("advisor_email"),
                Advisor.status.label("advisor_status"),
                Team.id.label("team_id"),
                Team.name.label("team_name"),
                Team.organization_id.label("organization_id"),
            )
            .join(Team, Team.id == Advisor.team_id)
        )

        if organization_id is not None:
            advisor_q = advisor_q.filter(Team.organization_id == organization_id)
        if team_id is not None:
            advisor_q = advisor_q.filter(Advisor.team_id == team_id)
        if search:
            advisor_q = advisor_q.filter(
                Advisor.name.ilike(f"%{search.strip()}%")
            )
        if advisor_status:
            try:
                status_enum = AdvisorStatus(advisor_status)
                advisor_q = advisor_q.filter(Advisor.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid status value '{advisor_status}'. Allowed: Active, Inactive.",
                )

        advisor_q = advisor_q.order_by(Advisor.name)

        # Total count (before pagination)
        total = advisor_q.count()
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        offset = (page - 1) * page_size
        base_rows = advisor_q.offset(offset).limit(page_size).all()

        if not base_rows:
            return PaginatedAdvisorListResponse(
                items=[], page=page, page_size=page_size,
                total=total, total_pages=total_pages,
            )

        advisor_ids = [r.advisor_id for r in base_rows]

        # Query 2a: completed calls + avg score per advisor on this page
        perf_rows = (
            self.db.query(
                Call.advisor_id.label("advisor_id"),
                func.count(
                    case((Call.processing_status == ProcessingStatus.COMPLETED, Call.id))
                ).label("completed_calls"),
                func.avg(CallScore.overall_score).label("avg_score"),
            )
            .outerjoin(CallScore, and_(
                CallScore.call_id == Call.id,
                Call.processing_status == ProcessingStatus.COMPLETED,
            ))
            .filter(Call.advisor_id.in_(advisor_ids))
            .group_by(Call.advisor_id)
            .all()
        )
        perf_by_advisor: dict[str, tuple[int, float | None]] = {
            str(r.advisor_id): (int(r.completed_calls or 0), _round2(r.avg_score))
            for r in perf_rows
        }

        # Query 2b: critical issue counts per advisor on this page
        critical_rows = (
            self.db.query(
                Call.advisor_id.label("advisor_id"),
                func.count(IssueTag.id).label("critical_count"),
            )
            .join(IssueTag, IssueTag.call_id == Call.id)
            .filter(
                Call.advisor_id.in_(advisor_ids),
                IssueTag.severity == IssueSeverity.CRITICAL,
            )
            .group_by(Call.advisor_id)
            .all()
        )
        critical_by_advisor: dict[str, int] = {
            str(r.advisor_id): int(r.critical_count) for r in critical_rows
        }

        # Fetch org names in one query
        org_ids = list({r.organization_id for r in base_rows})
        from app.models.organization import Organization
        org_rows = (
            self.db.query(Organization.id, Organization.name)
            .filter(Organization.id.in_(org_ids))
            .all()
        )
        org_names: dict[str, str] = {str(r.id): r.name for r in org_rows}

        items = [
            AdvisorListItem(
                advisor_id=r.advisor_id,
                advisor_name=r.advisor_name,
                advisor_email=r.advisor_email,
                advisor_status=r.advisor_status.value if hasattr(r.advisor_status, "value") else str(r.advisor_status),
                team_id=r.team_id,
                team_name=r.team_name,
                organization_id=r.organization_id,
                organization_name=org_names.get(str(r.organization_id), ""),
                completed_calls=perf_by_advisor.get(str(r.advisor_id), (0, None))[0],
                average_score=perf_by_advisor.get(str(r.advisor_id), (0, None))[1],
                critical_issue_count=critical_by_advisor.get(str(r.advisor_id), 0),
            )
            for r in base_rows
        ]

        return PaginatedAdvisorListResponse(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _apply_date_filter(query, start_date: date | None, end_date: date | None):
    """Apply upload_time date range filter to any query that touches Call."""
    if start_date:
        query = query.filter(Call.upload_time >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(Call.upload_time <= datetime.combine(end_date, datetime.max.time()))
    return query
