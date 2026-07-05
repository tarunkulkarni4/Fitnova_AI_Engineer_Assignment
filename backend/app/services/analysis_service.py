from loguru import logger
from sqlalchemy.orm import Session

class AnalysisService:
    """
    Service responsible for triggering AI quality evaluations and managing scores.
    """
    def __init__(self, db: Session) -> None:
        self.db = db
