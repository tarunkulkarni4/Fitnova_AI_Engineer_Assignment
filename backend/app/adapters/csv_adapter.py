import uuid
from app.adapters.base_adapter import BaseAdapter
from app.schemas.call_input import CallInput

class CSVAdapter(BaseAdapter):
    """
    Adapter for processing records from a CRM CSV export.
    """
    def __init__(self, csv_row: dict) -> None:
        self.csv_row = csv_row

    def load_call(self) -> CallInput:
        advisor_id_str = self.csv_row.get("advisor_id")
        audio_path = self.csv_row.get("audio_path")
        source_reference = self.csv_row.get("source_reference")

        if not advisor_id_str or not audio_path or not source_reference:
            raise ValueError("CSV row missing required fields: advisor_id, audio_path, or source_reference.")

        try:
            advisor_id = uuid.UUID(advisor_id_str)
        except ValueError:
            raise ValueError(f"Invalid advisor_id UUID format in CSV: '{advisor_id_str}'")

        return CallInput(
            source_type="CRM Export",
            source_reference=source_reference,
            advisor_id=advisor_id,
            audio_path=audio_path,
            metadata=self.csv_row
        )
