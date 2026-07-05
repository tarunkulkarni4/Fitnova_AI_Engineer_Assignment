import uuid
from app.adapters.base_adapter import BaseAdapter
from app.schemas.call_input import CallInput

class ExotelAdapter(BaseAdapter):
    """
    Mock adapter for Exotel call recordings.
    """
    def __init__(self, exotel_payload: dict) -> None:
        self.exotel_payload = exotel_payload

    def load_call(self) -> CallInput:
        call_sid = self.exotel_payload.get("CallSid")
        advisor_id_str = self.exotel_payload.get("AdvisorId")
        recording_url = self.exotel_payload.get("RecordingUrl")

        if not call_sid or not advisor_id_str or not recording_url:
            raise ValueError("Exotel payload missing required fields: CallSid, AdvisorId, or RecordingUrl.")

        try:
            advisor_id = uuid.UUID(advisor_id_str)
        except ValueError:
            raise ValueError(f"Invalid advisor_id UUID format in Exotel payload: '{advisor_id_str}'")

        return CallInput(
            source_type="Exotel",
            source_reference=call_sid,
            advisor_id=advisor_id,
            audio_path=recording_url,
            metadata={
                "call_sid": call_sid,
                "recording_url": recording_url,
                "status": self.exotel_payload.get("Status"),
                "date_created": self.exotel_payload.get("DateCreated")
            }
        )
