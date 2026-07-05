import re
from loguru import logger
from app.models.issue import IssueSeverity

# Allowlisted categories
ALLOWED_CATEGORIES = {
    "NO_NEEDS_DISCOVERY",
    "GUARANTEED_RESULTS",
    "PRESSURE_TACTIC",
    "PRICE_BEFORE_VALUE",
    "UNDISCLOSED_COSTS",
    "WEAK_TRIAL_BOOKING",
    "NO_TRIAL_BOOKING",
    "TALKING_OVER_CUSTOMER",
    "POOR_OBJECTION_HANDLING",
    "MISSING_NEXT_STEP"
}

# Fixed severity taxonomy mapping
SEVERITY_MAP = {
    "NO_NEEDS_DISCOVERY": IssueSeverity.HIGH,
    "GUARANTEED_RESULTS": IssueSeverity.CRITICAL,
    "PRESSURE_TACTIC": IssueSeverity.HIGH,
    "PRICE_BEFORE_VALUE": IssueSeverity.MEDIUM,
    "UNDISCLOSED_COSTS": IssueSeverity.CRITICAL,
    "WEAK_TRIAL_BOOKING": IssueSeverity.MEDIUM,
    "NO_TRIAL_BOOKING": IssueSeverity.HIGH,
    "TALKING_OVER_CUSTOMER": IssueSeverity.MEDIUM,
    "POOR_OBJECTION_HANDLING": IssueSeverity.MEDIUM,
    "MISSING_NEXT_STEP": IssueSeverity.HIGH
}

# Absence-based tags allowlist
ABSENCE_TAGS = {
    "NO_NEEDS_DISCOVERY",
    "NO_TRIAL_BOOKING",
    "MISSING_NEXT_STEP"
}

def normalize_text(text: str) -> str:
    """
    Cleans text by converting to lowercase and stripping punctuation and whitespace
    to make quote comparisons resilient to minor Whisper segment variations.
    """
    if not text:
        return ""
    # Remove punctuation, convert to lowercase, compress multiple spaces
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    return " ".join(cleaned.split())

def validate_and_correct_tag(tag: dict, transcript_segments: list) -> tuple[bool, dict | None]:
    """
    Validates a single LLM-emitted issue tag against FitNova anti-hallucination rules.
    - Category check
    - Severity replacement from server-side taxonomy
    - Quote substring checking
    - Timestamp & speaker corrections
    
    Returns (is_valid, corrected_tag_dict).
    """
    category = tag.get("category")
    if not category or category not in ALLOWED_CATEGORIES:
        logger.warning(f"Rejected issue tag: Category '{category}' is not in the allowlist.")
        return False, None

    # Enforce TALKING_OVER_CUSTOMER restriction (requires diarization overlaps; none present in JSON)
    if category == "TALKING_OVER_CUSTOMER":
        logger.warning("Rejected issue tag: 'TALKING_OVER_CUSTOMER' is not supported due to lack of overlap diarization evidence.")
        return False, None

    # Map fixed severity
    severity = SEVERITY_MAP[category]

    # Handle absence-based tags
    if category in ABSENCE_TAGS:
        return True, {
            "category": category,
            "severity": severity,
            "quote": None,
            "timestamp": None,
            "speaker": None,
            "reason": tag.get("reason", "Missing required criteria behavior."),
            "confidence": float(tag.get("confidence", 1.0))
        }

    # Handle quote-based evidence validation
    raw_quote = tag.get("quote")
    if not raw_quote:
        logger.warning(f"Rejected issue tag: Category '{category}' requires a supporting quote.")
        return False, None

    norm_quote = normalize_text(raw_quote)
    if not norm_quote:
        logger.warning(f"Rejected issue tag: Empty quote after normalization: '{raw_quote}'")
        return False, None

    # Search for quote match in transcript segments
    matched_segment = None
    for seg in transcript_segments:
        norm_seg_text = normalize_text(seg.get("text", ""))
        if norm_quote in norm_seg_text:
            matched_segment = seg
            break

    if not matched_segment:
        logger.warning(f"Rejected issue tag: Hallucinated quote '{raw_quote}' not found in redacted transcript.")
        return False, None

    # Timestamp & speaker correction
    corrected_timestamp = float(matched_segment["start_time"])
    corrected_speaker = matched_segment["speaker"]

    return True, {
        "category": category,
        "severity": severity,
        "quote": raw_quote,
        "timestamp": corrected_timestamp,
        "speaker": corrected_speaker,
        "reason": tag.get("reason", "Issue observed in conversation."),
        "confidence": float(tag.get("confidence", 1.0))
    }
