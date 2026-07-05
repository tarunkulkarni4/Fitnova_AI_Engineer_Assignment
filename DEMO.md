# Demonstration Guide

This guide outlines a typical user flow to demonstrate the core value of the FitNova Sales Intelligence platform.

## 1. Dashboard & Analytics
- Navigate to the **Overview Dashboard**. Show the aggregate organizational metrics (Average Quality Score, Total Calls).
- Highlight the **Team Performance** grid to show how different teams stack up.
- Click into a specific team and drill down into the **Advisor Leaderboard** to pinpoint top performers and those needing coaching.

## 2. Call Ingestion
- Navigate to the **Call Operations** tab (Upload).
- Select an advisor and upload a sample MP3/WAV file from the `sample_calls` directory.
- Click **Run Pipeline** and watch the real-time execution of the asynchronous AI orchestrator (Transcription -> Diarization -> PII Redaction -> AI Analysis).

## 3. Human-in-the-Loop Review
- Navigate to the **Call Registry** and select the newly processed call to enter the **Call Review** interface.
- **Transcript**: Show the redacted transcript (e.g., notice how names and numbers are replaced with [PERSON] and [PHONE]).
- **Scorecard**: Review the AI-generated dimensional scores. Click on a score, change its value, and submit a comment. The UI will instantly reflect the "Effective" score.
- **Issues**: Reject a hallucinated issue tag.

## 4. Feedback Audit Trail
- Navigate to the **Feedback Activity** page.
- Show the chronological audit log of the corrections just made. This demonstrates the data provenance needed to safely retrain internal models over time.
