from abc import ABC, abstractmethod

class BaseProvider(ABC):
    """
    Abstract interface for LLM analysis provider.
    """
    @abstractmethod
    async def analyze(
        self,
        transcript_text: str,
        rubric: str,
        taxonomy: str,
        pre_checks: dict,
        system_prompt: str
    ) -> dict:
        """
        Executes analysis on the transcript text using provided criteria guidelines.
        Returns a raw parsed dictionary matching the Pydantic schema structure.
        """
        pass

    @abstractmethod
    async def classify(self, transcript_text: str) -> dict:
        """
        Classifies the call into sales or non-sales categories.
        Returns a dictionary with call_type, is_sales_call, confidence, reason, evidence.
        """
        pass
