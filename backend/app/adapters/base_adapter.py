from abc import ABC, abstractmethod
from app.schemas.call_input import CallInput

class BaseAdapter(ABC):
    """
    Abstract Base Class representing a common ingestion source adapter.
    """
    @abstractmethod
    def load_call(self) -> CallInput:
        """
        Processes data injected during constructor instantiation and
        returns a standardized CallInput object.
        """
        pass
