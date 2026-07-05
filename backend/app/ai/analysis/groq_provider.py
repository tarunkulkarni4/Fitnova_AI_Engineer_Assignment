import json
import logging
from groq import AsyncGroq
from app.ai.analysis.base_provider import BaseProvider

logger = logging.getLogger(__name__)

class GroqProvider(BaseProvider):
    """
    Groq-specific client implementation executing structured completion tasks.
    """
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        self.client = AsyncGroq(api_key=api_key)
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

IMPORTANT INSTRUCTION: You MUST return ONLY valid JSON matching the exact expected structure below. Do not wrap the JSON in Markdown formatting. Just return the raw JSON object.

EXPECTED JSON SCHEMA:
{{
  "scores": {{
    "rapport": {{"score": 0}},
    "needs_discovery": {{"score": 0}},
    "product_knowledge": {{"score": 0}},
    "objection_handling": {{"score": 0}},
    "compliance": {{"score": 0}},
    "trial_booking": {{"score": 0}},
    "closing": {{"score": 0}}
  }},
  "issue_tags": [
    {{
      "category": "string",
      "severity": "string",
      "timestamp": "string or null",
      "speaker": "string",
      "quote": "string or null",
      "reason": "string",
      "confidence": 0.0
    }}
  ],
  "summary": {{
    "executive_summary": "string",
    "customer_goal": "string",
    "objections": "string",
    "recommended_next_step": "string",
    "sentiment": "Positive|Neutral|Negative|Mixed"
  }}
}}
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
        
        # Robust parsing: remove potential markdown fences if they still slip through
        raw_text = raw_text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
            
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        raw_text = raw_text.strip()
        
        try:
            parsed_json = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Groq response as JSON. Raw output snippet: {{raw_text[:200]}}...")
            raise e
            
        # Temporary SAFE debug logging
        logger.info("Groq response top-level keys: %s", list(parsed_json.keys()))
        logger.debug("Groq parsed response: %s", parsed_json)

        # Normalize semantic equivalent keys
        if "scores" not in parsed_json:
            for alt in ["scoring", "call_scores"]:
                if alt in parsed_json:
                    parsed_json["scores"] = parsed_json.pop(alt)
                    break

        if "issue_tags" not in parsed_json:
            for alt in ["issues", "tags"]:
                if alt in parsed_json:
                    parsed_json["issue_tags"] = parsed_json.pop(alt)
                    break

        if "summary" not in parsed_json:
            for alt in ["ai_summary"]:
                if alt in parsed_json:
                    parsed_json["summary"] = parsed_json.pop(alt)
                    break
            
        # Basic schema validation to ensure downstream code doesn't fail on missing keys
        required_keys = ["scores", "issue_tags", "summary"]
        for key in required_keys:
            if key not in parsed_json:
                raise ValueError(f"Groq response is missing required key: {key}")
                
        return parsed_json

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
        raw_text = raw_text.strip()
        
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()
        
        parsed_json = json.loads(raw_text)
        
        required_keys = ["call_type", "is_sales_call", "confidence", "reason"]
        for key in required_keys:
            if key not in parsed_json:
                raise ValueError(f"Groq classification response is missing required key: {key}")
                
        return parsed_json
