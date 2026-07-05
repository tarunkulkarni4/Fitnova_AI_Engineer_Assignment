import uuid
from app.adapters.base_adapter import BaseAdapter
from app.schemas.call_input import CallInput

class TwilioAdapter(BaseAdapter):
    """
    Mock adapter for Twilio call recordings.
    """
    def __init__(self, twilio_payload: dict) -> None:
        self.twilio_payload = twilio_payload

    def load_call(self) -> CallInput:
        recording_sid = self.twilio_payload.get("RecordingSid")
        advisor_id_str = self.twilio_payload.get("AdvisorId")
        recording_url = self.twilio_payload.get("RecordingUrl")

        if not recording_sid or not advisor_id_str or not recording_url:
            raise ValueError("Twilio payload missing required fields: RecordingSid, AdvisorId, or RecordingUrl.")

        try:
            advisor_id = uuid.UUID(advisor_id_str)
        except ValueError:
            raise ValueError(f"Invalid advisor_id UUID format in Twilio payload: '{advisor_id_str}'")

        return CallInput(
            source_type="Twilio",
            source_reference=recording_sid,
            advisor_id=advisor_id,
            audio_path=recording_url,
            metadata={
                "recording_sid": recording_sid,
                "account_sid": self.twilio_payload.get("AccountSid"),
                "call_sid": self.twilio_payload.get("CallSid"),
                "recording_duration": self.twilio_payload.get("RecordingDuration")
            }
        )
