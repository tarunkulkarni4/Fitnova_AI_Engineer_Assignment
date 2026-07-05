import uuid
from app.adapters.base_adapter import BaseAdapter
from app.schemas.call_input import CallInput

class RestAdapter(BaseAdapter):
    """
    Adapter for direct HTTP REST file uploads.
    """
    def __init__(self, file_path: str, advisor_id: uuid.UUID, filename: str) -> None:
        self.file_path = file_path
        self.advisor_id = advisor_id
        self.filename = filename

    def load_call(self) -> CallInput:
        return CallInput(
            source_type="REST API",
            source_reference=self.filename,
            advisor_id=self.advisor_id,
            audio_path=self.file_path,
            metadata={"original_filename": self.filename}
        )
