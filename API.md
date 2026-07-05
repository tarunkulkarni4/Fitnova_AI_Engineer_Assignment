# API Documentation

The FitNova Backend exposes a RESTful API utilizing OpenAPI (Swagger). When the backend is running, the interactive documentation is available at `http://127.0.0.1:8000/docs`.

## Core Modules

### 1. Dashboard API (`/api/v1/dashboard`)
Provides aggregate analytics and drill-down metrics.
- `GET /organizations` - Org-level aggregate KPIs, dimension averages, and team performance rollups.
- `GET /team/{team_id}` - Team-level metrics and advisor leaderboards.
- `GET /advisor/{advisor_id}` - Individual advisor performance and improvement areas.
- `GET /calls` - Paginated, filterable, and sortable call registry.

### 2. Call Operations API (`/api/v1/calls`, `/api/v1/pipeline`)
Handles file uploads and triggers the AI pipeline.
- `POST /calls/upload` - Uploads an audio file and creates a new Call record in `UPLOADED` status.
- `POST /pipeline/{call_id}/run` - Initiates the asynchronous AI pipeline. Resumes from the last failed stage if re-invoked.
- `GET /pipeline/{call_id}/status` - Checks current processing status and logs.

### 3. Feedback API (`/api/v1/feedback`)
Provides human-in-the-loop review functionality.
- `GET /{call_id}/reviewed` - Retrieves the `effective_view` of a call, merging original AI output with all manager corrections.
- `POST /{call_id}/score` - Submits a correction for a dimensional score.
- `POST /{call_id}/tags/{tag_id}/reject` - Rejects a hallucinated AI issue tag.
- `POST /{call_id}/summary` - Corrects a field in the AI summary.
- `GET /dataset/export` - Exports a chronological log of all historical feedback activity for audit and AI model retraining.

### 4. Lookups API (`/api/v1/lookups`)
Provides lightweight reference data for frontend selectors and filters.
- `GET /organizations`, `GET /teams`, `GET /advisors`
- `GET /issue-taxonomy` - Defines the compliance issue categories used across the platform.
