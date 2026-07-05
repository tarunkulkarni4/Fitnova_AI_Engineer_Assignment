# AI Analysis Engine
# FitNova AI Sales Intelligence Platform

**Version:** 1.0  
**Status:** Draft  
**Primary Model:** OpenAI GPT-5 (Structured Output) *(or GPT-4.1 if GPT-5 is unavailable)*

---

# 1. Overview

The AI Analysis Engine is responsible for converting structured sales call transcripts into reliable, evidence-backed business insights.

Unlike a conversational chatbot, this engine always produces structured JSON that can be validated, stored in PostgreSQL, displayed in dashboards, and corrected by human reviewers.

The AI never analyzes raw audio directly. It operates only on the transcript produced by the transcription pipeline.

---

# 2. Responsibilities

The engine performs the following tasks:

- Generate executive summary
- Score advisor performance
- Detect sales issues
- Detect compliance violations
- Generate coaching suggestions
- Classify customer sentiment
- Determine call outcome
- Extract customer goals
- Identify objections
- Produce structured JSON

---

# 3. AI Pipeline

```mermaid
flowchart LR

Transcript

-->

Prompt Builder

-->

OpenAI GPT

-->

Structured JSON

-->

Pydantic Validation

-->

Business Rules Validation

-->

Database

-->

Dashboard

Reviewer

-->

Feedback

-->

Future Prompt Improvements
```

---

# 4. Input

The AI receives a normalized transcript.

Example

```json
{
  "call_id":"CALL001",
  "duration":620,
  "language":"English",
  "advisor":"Rahul",
  "team":"Weight Loss",
  "transcript":[
    {
      "speaker":"Advisor",
      "start":0,
      "end":6,
      "text":"Welcome to FitNova."
    },
    {
      "speaker":"Customer",
      "start":6,
      "end":12,
      "text":"I want to lose weight."
    }
  ]
}
```

---

# 5. Expected Output

The model must return valid JSON only.

```json
{
  "overall_score":84,
  "summary":"...",
  "sentiment":"Positive",
  "booking_status":"Booked",
  "scores":{},
  "issues":[],
  "coaching":[]
}
```

No Markdown.

No explanations.

No extra text.

---

# 6. Scoring Rubric

| Category | Weight |
|----------|---------|
| Rapport Building | 10 |
| Needs Discovery | 20 |
| Product Knowledge | 15 |
| Objection Handling | 20 |
| Compliance | 15 |
| Trial Booking | 10 |
| Closing | 10 |

Total Score = 100

Overall score is a weighted average.

---

# 7. Issue Taxonomy

Only the following categories are allowed.

| Category | Severity |
|----------|----------|
| No Needs Discovery | High |
| Guaranteed Results | Critical |
| Hidden Charges | Critical |
| Pressure Selling | High |
| Price Before Value | Medium |
| Talking Over Customer | Medium |
| Weak Closing | Medium |
| Missing Trial Booking | High |
| Missing Next Step | Medium |
| Compliance Violation | Critical |

The model must never invent new categories.

---

# 8. Required Evidence

Every detected issue must contain:

- Category
- Severity
- Timestamp
- Speaker
- Exact Quote
- Reason
- Confidence

Example

```json
{
  "category":"Pressure Selling",
  "severity":"High",
  "timestamp":"08:12",
  "speaker":"Advisor",
  "quote":"Today's offer expires.",
  "reason":"Advisor created artificial urgency.",
  "confidence":0.94
}
```

---

# 9. Prompt Strategy

The engine uses:

- System Prompt
- Developer Instructions
- Dynamic Transcript
- Output Schema
- Business Rules

The transcript is the only source of truth.

The model must not use outside knowledge.

---

# 10. System Prompt

```
You are an AI Quality Assurance reviewer for FitNova.

Evaluate sales calls using ONLY the provided transcript.

Never invent information.

Never infer missing conversations.

Every issue must contain evidence.

Every issue must include:

• timestamp
• speaker
• quote
• reason

If evidence is unavailable,
do not generate the issue.

Return valid JSON only.

Never output Markdown.

Never explain your reasoning outside JSON.
```

---

# 11. Business Rules

The AI must:

✓ Never create unsupported findings.

✓ Never invent timestamps.

✓ Never invent speakers.

✓ Never invent quotations.

✓ Never score outside 0–100.

✓ Never create unknown issue categories.

---

# 12. JSON Schema

Top-level structure

```text
overall_score

summary

sentiment

booking_status

customer_goal

objections

scores

issues

coaching
```

---

# 13. Pydantic Response Model

```python
CallAnalysis

overall_score: int

summary: str

sentiment: str

booking_status: str

customer_goal: str

objections: list[str]

scores: list

issues: list

coaching: list[str]
```

---

# 14. Validation Layer

Every AI response is validated.

Validation includes:

- Valid JSON
- Required fields
- Score range
- Valid issue category
- Valid severity
- Timestamp format
- Confidence value
- Quote exists in transcript

If validation fails:

↓

Retry

Maximum retries: 3

---

# 15. Hallucination Prevention

An issue is accepted only if:

✓ Quote exists.

✓ Timestamp exists.

✓ Speaker exists.

✓ Quote matches transcript.

Otherwise:

Reject output.

Retry generation.

---

# 16. Confidence Thresholds

| Confidence | Action |
|------------|--------|
| > 0.90 | Accept |
| 0.70–0.90 | Accept |
| 0.50–0.69 | Flag for review |
| < 0.50 | Manual review required |

---

# 17. Coaching Generation

Generate a maximum of five coaching suggestions.

Examples

- Ask more discovery questions.
- Explain program benefits before discussing price.
- Handle objections more thoroughly.
- Reduce interruptions.
- End the conversation with a clear next step.

Suggestions must reference actual behavior observed in the transcript.

---

# 18. Executive Summary

Generate a concise summary containing:

- Customer objective
- Advisor approach
- Main objections
- Products discussed
- Call outcome
- Recommended next action

Maximum length:

200 words.

---

# 19. Sentiment Classification

Possible values

- Positive
- Neutral
- Negative
- Mixed

Sentiment should reflect the customer's overall attitude.

---

# 20. Call Outcome Classification

Possible values

- Trial Booked
- Follow-up Required
- Not Interested
- Wrong Number
- Internal Call
- Unknown

---

# 21. Edge Cases

## Poor Audio

If transcript confidence is low:

Return

```
manual_review_required = true
```

---

## Mono Recording

Unknown speakers are allowed.

Lower confidence.

---

## Hindi-English Code Switching

Preserve the original language.

Do not translate.

---

## Wrong Number

Skip scoring.

Return

```
call_type = Wrong Number
```

---

## Empty Transcript

Return

```
processing_failed
```

---

# 22. Retry Strategy

Retry if:

- Invalid JSON
- Timeout
- Missing required fields
- Parsing failure
- Schema mismatch

Maximum retries:

3

---

# 23. Human Feedback Loop

Managers may:

- Accept findings
- Reject findings
- Edit scores
- Remove issue tags
- Add comments

Corrections are stored for future prompt improvements and evaluation.

---

# 24. Future Improvements

- Multi-agent evaluation
- Ensemble scoring
- RAG-based policy validation
- Organization-specific scoring rubrics
- Fine-tuned fitness-domain models
- Emotion detection
- Conversation embeddings
- Semantic transcript search

---

# 25. Summary

The AI Analysis Engine transforms transcripts into structured, evidence-backed intelligence using prompt engineering, schema validation, business-rule enforcement, and human review. This approach minimizes hallucinations, improves consistency, and produces reliable outputs suitable for dashboards, coaching, compliance monitoring, and long-term analytics.