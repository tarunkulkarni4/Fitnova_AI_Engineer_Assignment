from loguru import logger
from sqlalchemy.orm import Session

class ProcessingService:
    """
    Service responsible for coordinating background processing jobs and state transitions.
    """
    def __init__(self, db: Session) -> None:
        self.db = db
