# System Architecture

## High-Level Architecture

FitNova Sales Intelligence is built using a modern, decoupled client-server architecture:
- **Frontend**: A Single Page Application (SPA) built with React and TypeScript, running in the browser.
- **Backend**: A REST API built with FastAPI and Python, handling business logic, database interaction, and orchestrating the AI pipeline.
- **Database**: PostgreSQL (via SQLAlchemy ORM) for persistent storage of structured data, and local file storage for large unstructured assets (audio, transcripts).

## AI Pipeline Orchestrator

The core intellectual property of the platform is the Asynchronous AI Pipeline, defined in `app/pipelines/call_pipeline.py`. When a new sales call is uploaded, the orchestrator routes it through a sequential series of stages:

1. **Audio Processing**: Validates and normalizes uploaded audio files (e.g., standardizing format and sample rate for Whisper).
2. **Transcription**: Converts raw audio to text using OpenAI Whisper.
3. **Speaker Diarization**: Uses Pyannote Audio to identify unique speakers and generate timestamped speaker segments.
4. **Transcript Building**: Merges Whisper text segments with Pyannote speaker labels into a cohesive, structured conversation log.
5. **PII Redaction**: Scrubs sensitive personal information using Microsoft Presidio to ensure data privacy before sending to external LLMs.
6. **AI Analysis**: Prompts GPT-4o with the sanitized transcript to generate compliance issue tags, dimensional scoring, and an executive summary.

The orchestrator supports resume functionality. If a stage fails (e.g., due to an API timeout), the pipeline pauses and can be resumed from the exact point of failure without re-running expensive prior steps like transcription.

## Data Storage Strategy

- **Relational Data**: Stored in PostgreSQL. Includes Organizations, Teams, Advisors, Calls, Scores, Summaries, and Issue Tags.
- **Audio Assets**: Stored on disk at `app/storage/audio/processed`. (In production, this should migrate to AWS S3 or GCS).
- **Transcripts**: Large JSON blobs of segmented transcripts and their redacted versions are stored on disk at `app/storage/transcripts/raw` and `app/storage/transcripts/redacted`.

## Feedback Loop Architecture

To account for AI hallucinations and inaccuracies, the platform utilizes an immutable feedback history architecture.
- When a human manager makes a correction (e.g., rejecting an AI tag, modifying a score), the original AI-generated data in the database is **never overwritten**.
- Instead, an entry is added to the `FeedbackHistory` table, recording the `original_value` and `corrected_value`.
- When the frontend requests a Call Review, the backend dynamically applies the historical corrections on top of the base AI data to produce an `effective_view` for the user.

## Frontend Architecture

The frontend is a React application built with Vite and TailwindCSS.
- **State Management**: `TanStack Query` (React Query) handles all server state, caching, and background refetching.
- **Routing**: `React Router` handles client-side navigation with Route-Level Code Splitting (`React.lazy`) to minimize initial bundle size.
- **Context**: A lightweight `AppContext` provides global state for selected Organization and Team scope, persisting preferences to `localStorage`.
- **Components**: Adheres to a strict component hierarchy (e.g., `components/common`, `components/dashboard`, `components/callreview`). Raw data fetching is restricted to top-level page components, which pass data down via props.
