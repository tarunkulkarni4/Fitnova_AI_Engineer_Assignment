from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FitNova AI Backend",
        "version": "1.0.0"
    }
