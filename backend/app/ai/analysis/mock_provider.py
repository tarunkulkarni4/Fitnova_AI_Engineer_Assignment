import asyncio
from app.ai.analysis.base_provider import BaseProvider

class MockProvider(BaseProvider):
    """
    Mock LLM provider returning deterministic analysis results tailored for integration tests.
    """
    async def analyze(
        self,
        transcript_text: str,
        rubric: str,
        taxonomy: str,
        pre_checks: dict,
        system_prompt: str
    ) -> dict:
        text_lower = transcript_text.lower()

        # Simulate timeout trigger
        if "timeout" in text_lower:
            await asyncio.sleep(1.0)
            raise asyncio.TimeoutError("LLM request timed out (Mock).")

        # Start with a base happy-path response
        result = {
            "scores": {
                "rapport": {
                    "score": 90,
                    "reason": "Advisor established great rapport and welcoming tone.",
                    "evidence": [{"timestamp": 0.0, "quote": "Hello and welcome to FitNova."}]
                },
                "needs_discovery": {
                    "score": 85,
                    "reason": "Advisor asked goal-oriented needs discovery questions.",
                    "evidence": [{"timestamp": 11.0, "quote": "I am John."}]
                },
                "product_knowledge": {
                    "score": 90,
                    "reason": "Advisor described FitNova personal coaching options clearly.",
                    "evidence": []
                },
                "objection_handling": {
                    "score": 85,
                    "reason": "Advisor responded gracefully to objections.",
                    "evidence": []
                },
                "compliance": {
                    "score": 95,
                    "reason": "No false guarantees or hidden costs were mentioned.",
                    "evidence": []
                },
                "trial_booking": {
                    "score": 85,
                    "reason": "Proactive and clear booking for a free trial.",
                    "evidence": []
                },
                "closing": {
                    "score": 90,
                    "reason": "Clear next steps were defined and committed to.",
                    "evidence": []
                }
            },
            "issue_tags": [],
            "summary": {
                "executive_summary": "A clean sales call with constructive next actions.",
                "customer_goal": "Wants to build muscle and lose fat.",
                "objections": "Cost of the program.",
                "recommended_next_step": "Send membership trial login details.",
                "sentiment": "Positive"
            }
        }

        # Modify mock outputs based on keywords in transcript text:
        
        # 1. NO_NEEDS_DISCOVERY
        if "no needs discovery" in text_lower:
            result["scores"]["needs_discovery"]["score"] = 25
            result["scores"]["needs_discovery"]["reason"] = "Advisor skipped exploring customer goals entirely."
            result["issue_tags"].append({
                "category": "NO_NEEDS_DISCOVERY",
                "quote": None,
                "timestamp": None,
                "speaker": None,
                "reason": "No goal or constraint questions were asked.",
                "confidence": 0.95
            })

        # 2. GUARANTEED_RESULTS
        if "guaranteed" in text_lower:
            result["scores"]["compliance"]["score"] = 30
            result["scores"]["compliance"]["reason"] = "Advisor made false guarantees of weight loss results."
            
            # Sub-test triggers
            tag_quote = "reduce 10kg in 1 month guaranteed"
            tag_timestamp = 10.0
            tag_severity = "Low"  # Intentional wrong severity to test validator replacement
            
            if "wrong timestamp" in text_lower:
                tag_timestamp = 0.0  # Intentional wrong timestamp to test validator correction
                
            if "wrong severity" in text_lower:
                tag_severity = "Low"

            result["issue_tags"].append({
                "category": "GUARANTEED_RESULTS",
                "severity": tag_severity,
                "quote": tag_quote,
                "timestamp": tag_timestamp,
                "speaker": "Advisor",
                "reason": "Made weight loss guarantee.",
                "confidence": 0.98
            })

        # 3. PRESSURE_TACTIC
        if "pressure tactic" in text_lower:
            result["issue_tags"].append({
                "category": "PRESSURE_TACTIC",
                "quote": "discount only for next 10 minutes",
                "timestamp": 11.0,
                "speaker": "Advisor",
                "reason": "Applied artificial urgency pressure.",
                "confidence": 0.88
            })

        # 4. PRICE_BEFORE_VALUE
        if "price before value" in text_lower:
            result["issue_tags"].append({
                "category": "PRICE_BEFORE_VALUE",
                "quote": "price is 5000",
                "timestamp": 11.0,
                "speaker": "Advisor",
                "reason": "Pitched cost details before discovering goals.",
                "confidence": 0.78
            })

        # 5. NO_TRIAL_BOOKING
        if "no trial booking" in text_lower:
            result["scores"]["trial_booking"]["score"] = 20
            result["issue_tags"].append({
                "category": "NO_TRIAL_BOOKING",
                "quote": None,
                "timestamp": None,
                "speaker": None,
                "reason": "No free trial sessions were offered or scheduled.",
                "confidence": 0.95
            })

        # 6. WEAK_TRIAL_BOOKING
        if "weak trial booking" in text_lower:
            result["scores"]["trial_booking"]["score"] = 40
            result["issue_tags"].append({
                "category": "WEAK_TRIAL_BOOKING",
                "quote": "we will see",
                "timestamp": 11.0,
                "speaker": "Advisor",
                "reason": "Loose appointment setup without calendar lock.",
                "confidence": 0.85
            })

        # 7. POOR_OBJECTION_HANDLING
        if "poor objection handling" in text_lower:
            result["scores"]["objection_handling"]["score"] = 35
            result["issue_tags"].append({
                "category": "POOR_OBJECTION_HANDLING",
                "quote": "you don't understand",
                "timestamp": 11.0,
                "speaker": "Advisor",
                "reason": "Dismissed budget concern defensively.",
                "confidence": 0.82
            })

        # 8. MISSING_NEXT_STEP
        if "missing next step" in text_lower:
            result["scores"]["closing"]["score"] = 30
            result["issue_tags"].append({
                "category": "MISSING_NEXT_STEP",
                "quote": None,
                "timestamp": None,
                "speaker": None,
                "reason": "Advisor failed to agree on concrete follow-up actions.",
                "confidence": 0.90
            })

        # 9. Unsupported Category
        if "unsupported category" in text_lower:
            result["issue_tags"].append({
                "category": "INVALID_CATEGORY",
                "quote": "I am John.",
                "timestamp": 11.0,
                "speaker": "Advisor",
                "reason": "This has an invalid category name.",
                "confidence": 0.99
            })

        # 10. Invented Quote
        if "invented quote" in text_lower:
            result["issue_tags"].append({
                "category": "GUARANTEED_RESULTS",
                "quote": "I will steal your money",  # Fake quote
                "timestamp": 11.0,
                "speaker": "Advisor",
                "reason": "This quote does not exist in transcript.",
                "confidence": 0.99
            })

        # 11. Hindi-English code-switched case
        if "hindi english" in text_lower:
            result["summary"]["sentiment"] = "Neutral"
            result["scores"]["rapport"]["evidence"] = [{"timestamp": 0.0, "quote": "kaise ho"}]

        return result

    async def classify(self, transcript_text: str) -> dict:
        text_lower = transcript_text.lower()
        if "wrong number" in text_lower or "wrong_number" in text_lower:
            return {
                "call_type": "WRONG_NUMBER",
                "is_sales_call": False,
                "confidence": 0.95,
                "reason": "Transcript contains explicit indication of a wrong number.",
                "evidence": "Sorry, wrong number."
            }
        elif "internal check-in" in text_lower or "internal_call" in text_lower or "test call" in text_lower:
            return {
                "call_type": "INTERNAL_CALL",
                "is_sales_call": False,
                "confidence": 0.98,
                "reason": "Transcript references an internal check-in or test.",
                "evidence": "internal check-in"
            }
        elif "spam" in text_lower or "other_non_sales" in text_lower:
            return {
                "call_type": "OTHER_NON_SALES",
                "is_sales_call": False,
                "confidence": 0.90,
                "reason": "Interaction is flagged as spam or general inquiry unrelated to fitness sales.",
                "evidence": "spam call"
            }
        else:
            return {
                "call_type": "SALES_CALL",
                "is_sales_call": True,
                "confidence": 0.99,
                "reason": "Call involves fitness sales consultation.",
                "evidence": None
            }
