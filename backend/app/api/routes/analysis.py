from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.database import get_db
from app.schemas.analysis import AnalysisBuildResponse
from app.ai.analysis.analysis_service import AnalysisService

router = APIRouter()

@router.post(
    "/analysis/{call_id}",
    response_model=AnalysisBuildResponse,
    status_code=status.HTTP_200_OK,
    summary="Run AI Analysis on redacted transcript",
    description="Loads PII redacted transcript JSON, calculates conversation metrics, evaluates scores and issue tags with anti-hallucination evidence filters, and persists scores/tags/summary to DB.",
    responses={
        200: {"model": AnalysisBuildResponse, "description": "Call successfully analyzed"},
        400: {"description": "Redacted transcript JSON missing, empty, or has invalid schema"},
        404: {"description": "Call or job not found"},
        500: {"description": "LLM provider failure, database error, or generic runtime failure"}
    }
)
async def analyze_call_audio(
    call_id: UUID,
    db: Session = Depends(get_db)
):
    service = AnalysisService(db)
    result = await service.analyze_call(call_id)
    return AnalysisBuildResponse(
        success=True,
        message="Call analysis completed successfully.",
        call_id=result["call_id"],
        overall_score=result["overall_score"],
        issue_tags_count=result["issue_tags_count"],
        processing_status="Completed"
    )
