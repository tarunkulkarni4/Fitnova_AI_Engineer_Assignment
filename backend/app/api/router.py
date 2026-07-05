from fastapi import APIRouter
from app.api.routes import health, calls, audio, transcription, diarization, transcripts, pii, analysis, pipeline, dashboard, feedback, lookups

api_router = APIRouter()

# Include versioned routers.
api_router.include_router(health.router, tags=["health"])
api_router.include_router(calls.router, tags=["calls"])
api_router.include_router(audio.router, tags=["audio"])
api_router.include_router(transcription.router, tags=["transcription"])
api_router.include_router(diarization.router, tags=["diarization"])
api_router.include_router(transcripts.router, tags=["transcripts"])
api_router.include_router(pii.router, tags=["pii"])
api_router.include_router(analysis.router, tags=["analysis"])
api_router.include_router(pipeline.router, tags=["pipeline"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(feedback.router, tags=["feedback"])
api_router.include_router(lookups.router, tags=["lookups"])




