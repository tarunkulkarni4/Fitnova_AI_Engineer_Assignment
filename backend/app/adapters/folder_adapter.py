import uuid
from pathlib import Path
from app.adapters.base_adapter import BaseAdapter
from app.schemas.call_input import CallInput

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a"}

class FolderAdapter(BaseAdapter):
    """
    Adapter for processing call audio files placed in a local directory.
    """
    def __init__(self, file_path: str, advisor_id: uuid.UUID) -> None:
        self.file_path = file_path
        self.advisor_id = advisor_id

    def load_call(self) -> CallInput:
        path = Path(self.file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Folder audio file '{self.file_path}' not found.")
            
        ext = path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported folder file format '{ext}'.")

        return CallInput(
            source_type="Folder",
            source_reference=path.name,
            advisor_id=self.advisor_id,
            audio_path=str(path.resolve()),
            metadata={
                "directory": str(path.parent.resolve()),
                "filename": path.name,
                "file_size": path.stat().st_size
            }
        )
