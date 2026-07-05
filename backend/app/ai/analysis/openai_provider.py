import json
from openai import AsyncOpenAI
from app.ai.analysis.base_provider import BaseProvider

class OpenAIProvider(BaseProvider):
    """
    OpenAI-specific client implementation executing structured completion tasks.
    """
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def analyze(
        self,
        transcript_text: str,
        rubric: str,
        taxonomy: str,
        pre_checks: dict,
        system_prompt: str
    ) -> dict:
        user_content = f"""
CONVERSATION METRICS:
{json.dumps(pre_checks, indent=2)}

RUBRIC CRITERIA:
{rubric}

TAXONOMY ALLOWLIST:
{taxonomy}

TRANSCRIPT:
{transcript_text}
"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        raw_text = response.choices[0].message.content
        return json.loads(raw_text)

    async def classify(self, transcript_text: str) -> dict:
        system_prompt = """You are an expert AI call classifier for a fitness sales coaching platform.
Your task is to classify the call transcript into one of the following types:
- SALES_CALL: A call where an advisor discusses fitness goals, coaching programs, packages, or pricing with a prospective or existing customer.
- WRONG_NUMBER: A call that immediately ends or is identified as a wrong number (e.g. "Sorry, wrong number", "No, I am not Rahul").
- INTERNAL_CALL: A test call, internal employee discussion, or call where no actual sales conversation happens (e.g. testing the audio line, internal check-in).
- OTHER_NON_SALES: Any other call that does not involve a sales conversation (e.g., spam, hang-ups, general inquiries unrelated to purchasing coaching).

You MUST return ONLY valid JSON matching the exact expected structure below. Do not wrap the JSON in Markdown formatting. Just return the raw JSON object.

EXPECTED JSON SCHEMA:
{
  "call_type": "SALES_CALL|WRONG_NUMBER|INTERNAL_CALL|OTHER_NON_SALES",
  "is_sales_call": true|false,
  "confidence": 0.0 to 1.0,
  "reason": "Clear explanation of why this call was classified this way.",
  "evidence": "Exact quote from transcript proving the classification, or null if none."
}
"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TRANSCRIPT:\n{transcript_text}"}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        raw_text = response.choices[0].message.content
        return json.loads(raw_text)
