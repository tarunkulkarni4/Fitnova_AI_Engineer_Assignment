from app.adapters.base_adapter import BaseAdapter
from app.adapters.rest_adapter import RestAdapter
from app.adapters.folder_adapter import FolderAdapter
from app.adapters.csv_adapter import CSVAdapter
from app.adapters.twilio_adapter import TwilioAdapter
from app.adapters.exotel_adapter import ExotelAdapter

class AdapterFactory:
    """
    Factory class responsible for instantiating the appropriate source adapter
    and returning it as a BaseAdapter.
    """
    @staticmethod
    def get_adapter(source_type: str, *args, **kwargs) -> BaseAdapter:
        source_normalized = source_type.strip().lower()
        if source_normalized in ("rest", "rest api", "rest_api", "upload"):
            return RestAdapter(*args, **kwargs)
        elif source_normalized in ("folder", "local folder", "local_folder"):
            return FolderAdapter(*args, **kwargs)
        elif source_normalized in ("csv", "crm", "crm export", "crm_export", "csv export", "csv_export"):
            return CSVAdapter(*args, **kwargs)
        elif source_normalized == "twilio":
            return TwilioAdapter(*args, **kwargs)
        elif source_normalized == "exotel":
            return ExotelAdapter(*args, **kwargs)
        else:
            raise ValueError(f"Unsupported source type: '{source_type}'")
