from loguru import logger
from sqlalchemy.orm import Session

class CallService:
    """
    Service responsible for managing sales call metadata, queries, and deletions.
    """
    def __init__(self, db: Session) -> None:
        self.db = db
