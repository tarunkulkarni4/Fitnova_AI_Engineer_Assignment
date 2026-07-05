# Product Requirements Document (PRD)
# FitNova AI Sales Intelligence Platform

**Version:** 1.0  
**Status:** Draft  
**Project Type:** AI Engineer Take-Home Assignment  
**Prepared By:** Tarun Kulkarni  
**Date:** July 2026

---

# 1. Introduction

FitNova is an online fitness and wellness coaching platform where potential customers typically enroll after speaking with a tele-advisor. These conversations play a critical role in building trust, understanding customer needs, addressing objections, recommending suitable coaching plans, and ultimately converting leads into paying customers.

Currently, reviewing sales calls manually is time-consuming, inconsistent, and difficult to scale. Managers can only review a small percentage of calls, making it hard to identify coaching opportunities, maintain quality standards, or ensure compliance across the organization.

The FitNova AI Sales Intelligence Platform automates the end-to-end analysis of sales calls by transforming raw audio recordings into actionable business insights. The system transcribes conversations, identifies speakers, evaluates advisor performance, detects quality issues, generates coaching recommendations, and presents the results through role-based dashboards.

The platform is designed to support organizations of any size while remaining independent of any specific telephony or CRM provider.

---

# 2. Problem Statement

Sales conversations directly influence customer trust and revenue. However, manual call reviews introduce several challenges:

- Only a small percentage of calls are reviewed.
- Quality evaluations vary between reviewers.
- Coaching opportunities are often missed.
- Compliance violations may go unnoticed.
- Managers spend significant time listening to recordings.
- Performance trends are difficult to identify across teams.

FitNova requires an automated, scalable, and intelligent solution that can analyze every sales call consistently and provide actionable insights for advisors, team leaders, and sales directors.

---

# 3. Product Vision

To build an AI-powered Sales Call Intelligence Platform that automatically processes customer conversations, evaluates call quality, identifies coaching opportunities, detects compliance risks, and enables continuous improvement across the sales organization.

---

# 4. Objectives

The platform should:

- Automatically ingest call recordings from multiple sources.
- Convert speech into structured transcripts.
- Separate advisor and customer conversations.
- Score advisor performance using predefined quality metrics.
- Detect sales mistakes and compliance violations.
- Generate AI-powered coaching suggestions.
- Store structured analysis for future reporting.
- Present insights through interactive dashboards.
- Support human review and feedback for continuous improvement.

---

# 5. Target Users

## 5.1 Sales Director

Responsibilities:

- Monitor overall organization performance.
- Compare team performance.
- Identify coaching trends.
- Monitor compliance.
- Track quality KPIs.

Needs:

- Organization-level dashboards.
- Team comparisons.
- Critical issue monitoring.
- Advisor rankings.
- Performance trends.

---

## 5.2 Team Leader

Responsibilities:

- Coach advisors.
- Review team performance.
- Identify weak calls.
- Validate AI analysis.

Needs:

- Team dashboard.
- Call reviews.
- Coaching recommendations.
- Feedback tools.
- Advisor score trends.

---

## 5.3 Advisor

Responsibilities:

- Conduct sales calls.
- Improve sales quality.
- Increase conversions.

Needs:

- Personal dashboard.
- Call transcript.
- AI score.
- Coaching suggestions.
- Previous call history.

---

# 6. Scope

## In Scope

### Call Ingestion

- Audio upload
- Folder ingestion
- API ingestion
- CRM import
- Telephony adapters
- Source-agnostic architecture

---

### Audio Processing

- Audio validation
- Audio normalization
- Metadata extraction

---

### Speech Processing

- Speech-to-text transcription
- Speaker diarization
- Timestamp generation
- Language detection

---

### AI Analysis

- Call summarization
- Quality scoring
- Issue detection
- Coaching recommendations
- Compliance evaluation
- Sentiment analysis
- Next-step identification

---

### Data Management

- Transcript storage
- Score storage
- Metadata storage
- Issue storage
- Feedback storage

---

### Dashboard

- Organization dashboard
- Team dashboard
- Advisor dashboard
- Call details page
- Transcript viewer
- Analytics

---

### Human Review

- Manual score correction
- Tag correction
- Feedback collection
- Continuous improvement

---

# Out of Scope

The following features are intentionally excluded from Version 1.0:

- Live call monitoring
- Real-time speech analysis
- Automatic CRM updates
- Multi-tenant SaaS billing
- Mobile applications
- Predictive sales forecasting
- Fine-tuned custom language models

These can be added in future releases.

---

# 7. Functional Requirements

## FR-01

The system shall ingest audio recordings from multiple configurable sources.

---

## FR-02

The system shall convert speech into text.

---

## FR-03

The system shall identify different speakers within the conversation.

---

## FR-04

The system shall generate timestamped transcripts.

---

## FR-05

The system shall automatically redact Personally Identifiable Information (PII).

---

## FR-06

The system shall analyze conversations using Large Language Models.

---

## FR-07

The system shall calculate quality scores for each call.

---

## FR-08

The system shall detect predefined sales and compliance issues.

---

## FR-09

Each detected issue shall include:

- Severity
- Timestamp
- Speaker
- Supporting quotation
- Reason

---

## FR-10

The system shall generate coaching recommendations.

---

## FR-11

The system shall store transcripts, scores, metadata, and AI analysis.

---

## FR-12

The system shall provide dashboards for different organizational roles.

---

## FR-13

The system shall allow human reviewers to correct AI results.

---

## FR-14

The system shall maintain historical call analysis.

---

## FR-15

The system shall support organizational hierarchies consisting of:

Organization

↓

Teams

↓

Advisors

---

# 8. Non-Functional Requirements

## Performance

- Process calls asynchronously.
- Support concurrent processing.
- Handle large audio files efficiently.

---

## Scalability

- Support multiple organizations.
- Add new advisors without code changes.
- Add new telephony providers using adapters.

---

## Reliability

- Retry failed processing.
- Prevent duplicate processing.
- Log failures.
- Recover from interruptions.

---

## Security

- Redact sensitive customer information.
- Encrypt stored data where applicable.
- Secure API endpoints.

---

## Maintainability

- Modular architecture.
- Configurable prompts.
- Configurable scoring rules.
- Extensible ingestion adapters.

---

## Usability

- Simple dashboard.
- Clear visualizations.
- Easy navigation.
- Minimal learning curve.

---

# 9. Success Metrics

The platform will be considered successful if it can:

- Process uploaded calls successfully.
- Generate accurate transcripts.
- Separate speakers correctly.
- Produce structured AI analysis.
- Detect predefined issues.
- Display dashboards correctly.
- Support manual review.
- Store all analysis data.

---

# 10. Assumptions

- Audio recordings are legally collected.
- Users have permission to access call recordings.
- Telephony providers expose APIs or downloadable recordings.
- AI APIs are available during processing.
- Advisors belong to one team at a time.

---

# 11. Risks

| Risk | Mitigation |
|-------|------------|
| Poor audio quality | Audio preprocessing + confidence score |
| API failures | Retry mechanism + idempotency |
| Hallucinated AI output | JSON schema validation |
| Incorrect speaker separation | Confidence score + manual correction |
| Mixed languages | Multilingual speech recognition |
| Duplicate uploads | Unique Call ID + checksum |

---

# 12. Future Enhancements

- Real-time call monitoring
- Automatic CRM synchronization
- Conversation search using vector embeddings
- AI-powered call comparison
- Weekly coaching summaries
- Trend prediction
- Agent benchmarking
- Voice emotion analysis
- Multi-language dashboards

---

# 13. Assignment Requirement Mapping

| Assignment Requirement | Covered |
|-------------------------|---------|
| Source-agnostic ingestion | ✅ |
| Transcription | ✅ |
| Speaker diarization | ✅ |
| Analysis engine | ✅ |
| Quality scoring | ✅ |
| Issue tagging | ✅ |
| Structured storage | ✅ |
| Dashboards | ✅ |
| Human feedback loop | ✅ |
| Organization hierarchy | ✅ |
| Data modeling | ✅ |
| Edge case handling | ✅ |
| Automation prioritization | ✅ |
| End-to-end workflow | ✅ |

---

# 14. Conclusion

The FitNova AI Sales Intelligence Platform provides a scalable and extensible solution for automated sales call analysis. By combining speech recognition, speaker diarization, AI-powered evaluation, structured data storage, and role-based dashboards, the platform enables organizations to consistently monitor call quality, improve advisor performance, and drive better customer outcomes. The architecture is designed to remain vendor-independent, allowing FitNova to integrate with multiple telephony and CRM systems while supporting future growth with minimal changes.