"""
Integration tests for the Human Review and Feedback Loop API — 22 test cases.

Runs against a live Uvicorn server with mocked AI and database configs.
Each test case is fully verified against API responses.
"""
import json
import math
import os
import struct
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from app.models.organization import Organization
from app.models.team import Team
from app.models.advisor import Advisor, AdvisorStatus
from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob
from app.models.score import CallScore
from app.models.summary import AISummary
from app.models.issue import IssueTag, IssueSeverity
from app.models.feedback import Feedback, FeedbackType
from app.models.transcript import Transcript

DB_URL = "sqlite:///fitnova.db"
BASE = "http://127.0.0.1:8000/api/v1"
REDACTED_DIR = Path("app/storage/transcripts/redacted")
PROCESSED_DIR = Path("app/storage/audio/processed")
CREATED_FILES = []

# ---------------------------------------------------------------------------
# WAV helper
# ---------------------------------------------------------------------------

def make_wav(path: Path, secs: int = 2) -> None:
    sr, ch, bps = 16000, 1, 16
    n = sr * secs
    data_size = n * ch * (bps // 8)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"RIFF"); f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE"); f.write(b"fmt "); f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1)); f.write(struct.pack("<H", ch))
        f.write(struct.pack("<I", sr)); f.write(struct.pack("<I", sr * ch * bps // 8))
        f.write(struct.pack("<H", ch * bps // 8)); f.write(struct.pack("<H", bps))
        f.write(b"data"); f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def make_engine():
    return create_engine(DB_URL, connect_args={"check_same_thread": False})

def make_session(engine):
    return sessionmaker(bind=engine)()

def setup_db(engine):
    from app.database.base import Base
    Base.metadata.create_all(engine)

def clean_db(session):
    for m in (Feedback, IssueTag, AISummary, CallScore, Transcript, ProcessingJob, Call,
              Advisor, Team, Organization):
        session.query(m).delete()
    session.commit()


def seed_org(session, name="Test Org") -> Organization:
    org = Organization(name=name, industry="Fitness")
    session.add(org); session.flush()
    return org


def seed_team(session, org_id, name="Team A") -> Team:
    t = Team(organization_id=org_id, name=name, description="")
    session.add(t); session.flush()
    return t


def seed_advisor(session, team_id, name="Adv", email=None) -> Advisor:
    adv = Advisor(
        team_id=team_id,
        employee_code=str(uuid.uuid4())[:8],
        name=name,
        email=email or f"{uuid.uuid4().hex[:6]}@test.com",
        status=AdvisorStatus.ACTIVE,
    )
    session.add(adv); session.flush()
    return adv


def seed_call_with_data(
    session, advisor_id, *,
    score: dict,
    issues: list[dict],
    summary: dict,
) -> tuple[Call, CallScore, list[IssueTag], AISummary]:
    wav = PROCESSED_DIR / f"{uuid.uuid4().hex}.wav"
    make_wav(wav)
    CREATED_FILES.append(wav)
    c = Call(
        advisor_id=advisor_id,
        source_type="REST API",
        audio_file=str(wav),
        processed_audio_file=str(wav),
        audio_duration=120,
        language="en",
        processing_status=ProcessingStatus.COMPLETED,
        upload_time=datetime.utcnow() - timedelta(days=2),
    )
    session.add(c); session.flush()

    session.add(ProcessingJob(
        call_id=c.id, stage="Completed", status=ProcessingStatus.COMPLETED, retry_count=0
    ))

    cs = CallScore(
        call_id=c.id,
        rapport_score=score.get("rapport"),
        needs_discovery_score=score.get("needs_discovery"),
        product_knowledge_score=score.get("product_knowledge"),
        objection_handling_score=score.get("objection_handling"),
        compliance_score=score.get("compliance"),
        trial_booking_score=score.get("trial_booking"),
        closing_score=score.get("closing"),
        overall_score=score.get("overall"),
    )
    session.add(cs)

    db_tags = []
    for issue in issues:
        it = IssueTag(
            id=issue.get("id", uuid.uuid4()),
            call_id=c.id,
            category=issue.get("category"),
            severity=IssueSeverity(issue.get("severity")),
            timestamp=issue.get("timestamp"),
            speaker=issue.get("speaker"),
            quote=issue.get("quote"),
            reason=issue.get("reason"),
            confidence=issue.get("confidence", 0.9),
        )
        session.add(it)
        db_tags.append(it)

    sm = AISummary(
        call_id=c.id,
        executive_summary=summary.get("executive_summary"),
        customer_goal=summary.get("customer_goal"),
        objections=summary.get("objections"),
        recommended_next_step=summary.get("recommended_next_step"),
        sentiment=summary.get("sentiment"),
    )
    session.add(sm)
    session.commit()

    # Write original redacted transcript JSON artifact
    REDACTED_DIR.mkdir(parents=True, exist_ok=True)
    redacted_path = REDACTED_DIR / f"{c.id}.json"
    redacted_path.write_text(json.dumps({
        "call_id": str(c.id),
        "language": "en",
        "duration": 120,
        "segments": [
            {"speaker": "Advisor", "start_time": 0.0, "end_time": 5.0, "text": "Hello welcome to FitNova.", "confidence": 0.95},
            {"speaker": "Customer", "start_time": 5.5, "end_time": 10.0, "text": "Hi I want to book a trial.", "confidence": 0.90},
            {"speaker": "Advisor", "start_time": 10.5, "end_time": 15.0, "text": "Today's offer expires in 10 minutes so sign up now.", "confidence": 0.94},
            {"speaker": "SPEAKER_02", "start_time": 15.5, "end_time": 20.0, "text": "This is a third person speaking.", "confidence": 0.88},
        ]
    }), encoding="utf-8")
    CREATED_FILES.append(redacted_path)

    return c, cs, db_tags, sm


def run_tests():
    engine = make_engine(); setup_db(engine)
    session = make_session(engine)
    clean_db(session)

    org = seed_org(session)
    team = seed_team(session, org.id)
    adv = seed_advisor(session, team.id)

    tag1_id = uuid.uuid4()
    call, call_score, db_tags, summary = seed_call_with_data(
        session, adv.id,
        score={
            "rapport": 80, "needs_discovery": 70, "product_knowledge": 80,
            "objection_handling": 50, "compliance": 90, "trial_booking": 60,
            "closing": 70, "overall": 70
        },
        issues=[
            {
                "id": tag1_id,
                "category": "PRESSURE_TACTIC",
                "severity": "High",
                "timestamp": 12.5,
                "speaker": "Advisor",
                "quote": "Today's offer expires.",
                "reason": "Used high pressure tactics."
            }
        ],
        summary={
            "executive_summary": "Summary text",
            "customer_goal": "Customer goal text",
            "objections": "Objections",
            "recommended_next_step": "Next step",
            "sentiment": "Neutral"
        }
    )

    print("\n" + "=" * 60)
    print("FEEDBACK LOOP INTEGRATION TESTS")
    print("=" * 60)

    # ---------------------------------------------------------------- #
    # TEST 1, 2, 3: Correct score dimension & overall recalculation    #
    # ---------------------------------------------------------------- #
    print("\n--- Test 1, 2, 3: Correct score dimension & overall score recalculation ---")
    payload = {
        "reviewer_name": "Team Lead A",
        "dimension": "objection_handling",
        "corrected_score": 72,
        "comments": "Acknowledged objection better."
    }
    r = requests.post(f"{BASE}/feedback/{call.id}/score", json=payload)
    assert r.status_code == 201, r.json()
    res = r.json()
    assert res["reviewer_name"] == "Team Lead A"
    assert res["original_value"]["score"] == 50
    assert res["corrected_value"]["score"] == 72

    # Verify original CallScore row in DB is unchanged
    session.expire_all()
    db_score = session.query(CallScore).filter(CallScore.call_id == call.id).one()
    assert db_score.objection_handling_score == 50, f"Expected 50, got {db_score.objection_handling_score}"
    assert db_score.overall_score == 70

    # Verify recalculated effective overall score in reviewed view
    # Weights: rapport (10%), needs_discovery (20%), product_knowledge (10%),
    # objection_handling (15%), compliance (20%), trial_booking (15%), closing (10%)
    # Expected overall: (80*0.1 + 70*0.2 + 80*0.1 + 72*0.15 + 90*0.2 + 60*0.15 + 70*0.1) = 74.8 -> 75
    r_rev = requests.get(f"{BASE}/feedback/{call.id}/reviewed")
    rev = r_rev.json()
    assert rev["effective_score"]["objection_handling"] == 72
    assert rev["effective_score"]["overall"] == 75, f"Expected recalculated score 75, got {rev['effective_score']['overall']}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 4: Multiple corrections to same score: latest wins          #
    # ---------------------------------------------------------------- #
    print("\n--- Test 4: Multiple corrections to same score: latest wins ---")
    payload = {
        "reviewer_name": "Team Lead A",
        "dimension": "objection_handling",
        "corrected_score": 80,
        "comments": "Correction update."
    }
    r4 = requests.post(f"{BASE}/feedback/{call.id}/score", json=payload)
    assert r4.status_code == 201

    r_rev = requests.get(f"{BASE}/feedback/{call.id}/reviewed")
    rev = r_rev.json()
    assert rev["effective_score"]["objection_handling"] == 80
    # Expected overall: (80*0.1 + 70*0.2 + 80*0.1 + 80*0.15 + 90*0.2 + 60*0.15 + 70*0.1) = 76.0 -> 76
    assert rev["effective_score"]["overall"] == 76, f"Expected 76, got {rev['effective_score']['overall']}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 5, 6: Reject AI issue tag & preserve original row            #
    # ---------------------------------------------------------------- #
    print("\n--- Test 5, 6: Reject AI issue tag & original tag unchanged ---")
    payload = {
        "reviewer_name": "Team Lead A",
        "comments": "This was not a pressure tactic."
    }
    r5 = requests.post(f"{BASE}/feedback/{call.id}/tags/{tag1_id}/reject", json=payload)
    assert r5.status_code == 201
    res5 = r5.json()
    assert res5["original_value"]["action"] == "reject"
    assert res5["corrected_value"]["rejected"] is True

    # Verify original tag exists in DB
    db_tag = session.query(IssueTag).filter(IssueTag.id == tag1_id).one()
    assert db_tag.category == "PRESSURE_TACTIC"

    # Verify effective tags does not contain the rejected tag
    r_rev = requests.get(f"{BASE}/feedback/{call.id}/reviewed")
    rev = r_rev.json()
    eff_tag_ids = {t["id"] for t in rev["effective_issue_tags"]}
    assert str(tag1_id) not in eff_tag_ids, "Rejected tag still present in effective view"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 7, 8: Correct AI issue tag & derive severity from taxonomy  #
    # ---------------------------------------------------------------- #
    print("\n--- Test 7, 8: Correct AI issue tag & derive severity from server taxonomy ---")
    # Category: POOR_OBJECTION_HANDLING. Server taxonomy severity: Medium.
    # Note: request payload does not accept severity at all.
    payload = {
        "reviewer_name": "Team Lead A",
        "category": "POOR_OBJECTION_HANDLING",
        "timestamp": 12.5,
        "quote": "Today's offer expires.",
        "reason": "Objection handling was poor.",
        "comments": "Corrected category"
    }
    r7 = requests.post(f"{BASE}/feedback/{call.id}/tags/{tag1_id}/correct", json=payload)
    assert r7.status_code == 201
    res7 = r7.json()
    assert res7["corrected_value"]["tag"]["category"] == "POOR_OBJECTION_HANDLING"
    assert res7["corrected_value"]["tag"]["severity"] == "Medium", "Severity not derived correctly"

    # Verify effective tag severity matches taxonomy
    r_rev = requests.get(f"{BASE}/feedback/{call.id}/reviewed")
    rev = r_rev.json()
    eff_tags = {t["id"]: t for t in rev["effective_issue_tags"]}
    # The tag is restored/corrected in the effective view!
    assert str(tag1_id) in eff_tags
    assert eff_tags[str(tag1_id)]["category"] == "POOR_OBJECTION_HANDLING"
    assert eff_tags[str(tag1_id)]["severity"] == "Medium"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 9: Invented quote rejected (HTTP 400)                       #
    # ---------------------------------------------------------------- #
    print("\n--- Test 9: Invented quote rejected (HTTP 400) ---")
    payload = {
        "reviewer_name": "Team Lead A",
        "category": "POOR_OBJECTION_HANDLING",
        "quote": "This is a hallucinated quote not present in transcript.",
        "reason": "Test"
    }
    r9 = requests.post(f"{BASE}/feedback/{call.id}/tags/{tag1_id}/correct", json=payload)
    assert r9.status_code == 400, f"Expected 400, got {r9.status_code}: {r9.json()}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 10: Correct segment start time matched to quote             #
    # ---------------------------------------------------------------- #
    print("\n--- Test 10: Correct segment details matched to quote ---")
    # Quote: "Hello welcome to FitNova" matches index 0 segment: start_time=0.0, speaker=Advisor
    payload = {
        "reviewer_name": "Team Lead A",
        "category": "PRESSURE_TACTIC",
        "quote": "Hello welcome to FitNova",
        "reason": "Pressure selling"
    }
    r10 = requests.post(f"{BASE}/feedback/{call.id}/tags/{tag1_id}/correct", json=payload)
    assert r10.status_code == 201
    res10 = r10.json()
    assert res10["corrected_value"]["tag"]["timestamp"] == 0.0
    assert res10["corrected_value"]["tag"]["speaker"] == "Advisor"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 11: Add missed absence-based tag (null quote/timestamp)     #
    # ---------------------------------------------------------------- #
    print("\n--- Test 11: Add missed absence-based tag (null quote allowed) ---")
    payload = {
        "reviewer_name": "Team Lead A",
        "category": "NO_TRIAL_BOOKING",
        "quote": None,
        "timestamp": None,
        "reason": "Missed trial booking behavior."
    }
    r11 = requests.post(f"{BASE}/feedback/{call.id}/tags/add", json=payload)
    assert r11.status_code == 201
    res11 = r11.json()
    assert res11["corrected_value"]["tag"]["category"] == "NO_TRIAL_BOOKING"
    assert res11["corrected_value"]["tag"]["severity"] == "High"
    assert res11["corrected_value"]["tag"]["quote"] is None
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 12: Invalid taxonomy category rejected (HTTP 422)           #
    # ---------------------------------------------------------------- #
    print("\n--- Test 12: Invalid taxonomy category rejected (HTTP 422) ---")
    payload = {
        "reviewer_name": "Team Lead A",
        "category": "NONSENSE_CATEGORY",
        "reason": "Nonsense"
    }
    r12 = requests.post(f"{BASE}/feedback/{call.id}/tags/add", json=payload)
    assert r12.status_code == 422, f"Expected 422, got {r12.status_code}: {r12.json()}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 13, 14: Correct summary field & sentiment allowlist         #
    # ---------------------------------------------------------------- #
    print("\n--- Test 13, 14: Correct summary field & sentiment allowlist ---")
    payload = {
        "reviewer_name": "Team Lead A",
        "field": "sentiment",
        "corrected_value": "Positive",
        "comments": "Corrected sentiment."
    }
    r13 = requests.post(f"{BASE}/feedback/{call.id}/summary", json=payload)
    assert r13.status_code == 201

    # Verify invalid sentiment is rejected (HTTP 422)
    payload_bad = {
        "reviewer_name": "Team Lead A",
        "field": "sentiment",
        "corrected_value": "SuperPositive",
        "comments": "Bad sentiment"
    }
    r13b = requests.post(f"{BASE}/feedback/{call.id}/summary", json=payload_bad)
    assert r13b.status_code == 422

    # Verify summary correction field works
    payload_step = {
        "reviewer_name": "Team Lead A",
        "field": "recommended_next_step",
        "corrected_value": "Call Friday afternoon.",
        "comments": "Coached follow-up"
    }
    r13c = requests.post(f"{BASE}/feedback/{call.id}/summary", json=payload_step)
    assert r13c.status_code == 201
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 15: Correct transcript speaker (validation & SPEAKER_*)     #
    # ---------------------------------------------------------------- #
    print("\n--- Test 15: Correct transcript speaker validation ---")
    # Allowed: Advisor, Customer, Unknown, and existing SPEAKER_02
    payload = {
        "reviewer_name": "Team Lead A",
        "segment_index": 0,
        "corrected_speaker": "Customer",
        "corrected_text": "Good morning.",
        "comments": "Speaker fix"
    }
    r15 = requests.post(f"{BASE}/feedback/{call.id}/transcript", json=payload)
    assert r15.status_code == 201

    # Try existing label: SPEAKER_02
    payload_exists = {
        "reviewer_name": "Team Lead A",
        "segment_index": 0,
        "corrected_speaker": "SPEAKER_02",
        "corrected_text": "Good morning.",
        "comments": "Speaker fix"
    }
    r15b = requests.post(f"{BASE}/feedback/{call.id}/transcript", json=payload_exists)
    assert r15b.status_code == 201

    # Try arbitrary invented label SPEAKER_99 (should fail with HTTP 422)
    payload_bad = {
        "reviewer_name": "Team Lead A",
        "segment_index": 0,
        "corrected_speaker": "SPEAKER_99",
        "corrected_text": "Good morning.",
        "comments": "Bad speaker"
    }
    r15c = requests.post(f"{BASE}/feedback/{call.id}/transcript", json=payload_bad)
    assert r15c.status_code == 422, f"Expected 422, got {r15c.status_code}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 16, 17, 18: Correct transcript text & PII redaction & file  #
    # ---------------------------------------------------------------- #
    print("\n--- Test 16, 17, 18: Transcript text correction & PII redaction ---")
    payload = {
        "reviewer_name": "Team Lead A",
        "segment_index": 1,
        "corrected_speaker": "Customer",
        "corrected_text": "My phone is 9876543210 and email is secret@gmail.com",
        "comments": "Customer gave PII"
    }
    r16 = requests.post(f"{BASE}/feedback/{call.id}/transcript", json=payload)
    assert r16.status_code == 201
    res16 = r16.json()
    redacted_text = res16["corrected_value"]["segment"]["text"]
    assert "[PHONE]" in redacted_text
    assert "[EMAIL]" in redacted_text
    assert "9876543210" not in redacted_text
    assert "secret@gmail.com" not in redacted_text

    # Verify original redacted transcript file remains unchanged on disk
    redacted_path = REDACTED_DIR / f"{call.id}.json"
    original_data = json.loads(redacted_path.read_text(encoding="utf-8"))
    orig_seg1 = original_data["segments"][1]
    assert orig_seg1["text"] == "Hi I want to book a trial.", f"Original file mutated: {orig_seg1['text']}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 19: Composing active corrections in reviewed view           #
    # ---------------------------------------------------------------- #
    print("\n--- Test 19: Composed effective reviewed view ---")
    r19 = requests.get(f"{BASE}/feedback/{call.id}/reviewed")
    assert r19.status_code == 200
    res19 = r19.json()
    # Check effective score
    assert res19["effective_score"]["objection_handling"] == 80
    assert res19["effective_score"]["overall"] == 76
    # Check effective summary
    assert res19["effective_summary"]["sentiment"] == "Positive"
    assert res19["effective_summary"]["recommended_next_step"] == "Call Friday afternoon."
    # Check effective tags — last correction (Test 10) was PRESSURE_TACTIC; NO_TRIAL_BOOKING added (Test 11)
    eff_cats = {t["category"] for t in res19["effective_issue_tags"]}
    assert "PRESSURE_TACTIC" in eff_cats, f"Expected PRESSURE_TACTIC in effective tags, got: {eff_cats}"
    assert "NO_TRIAL_BOOKING" in eff_cats, f"Expected NO_TRIAL_BOOKING in effective tags, got: {eff_cats}"
    # Check effective transcript has corrections applied
    eff_trans = res19["effective_transcript"]
    assert eff_trans[0]["speaker"] == "SPEAKER_02"  # Last correction wins
    assert "[PHONE]" in eff_trans[1]["text"]
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 20: Feedback history ordered newest first (reviewed_at DESC)#
    # ---------------------------------------------------------------- #
    print("\n--- Test 20: Feedback history ordered newest first ---")
    r20 = requests.get(f"{BASE}/feedback/{call.id}")
    assert r20.status_code == 200
    res20 = r20.json()
    times = [item["reviewed_at"] for item in res20]
    assert times == sorted(times, reverse=True), f"History not sorted DESC: {times}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 21, 22: Export dataset, filters & PII check                #
    # ---------------------------------------------------------------- #
    print("\n--- Test 21, 22: Feedback export dataset and filters ---")
    r21 = requests.get(f"{BASE}/feedback/dataset/export")
    assert r21.status_code == 200
    res21 = r21.json()
    assert len(res21) > 0

    # Ensure no raw PII in exported records
    for item in res21:
        text_rep = json.dumps(item)
        assert "9876543210" not in text_rep
        assert "secret@gmail.com" not in text_rep

    # Test type filter
    r21b = requests.get(f"{BASE}/feedback/dataset/export", params={"feedback_type": "Transcript"})
    assert r21b.status_code == 200
    for item in r21b.json():
        assert item["feedback_type"] == "Transcript"

    # Test date filters
    today = datetime.utcnow().date()
    r21c = requests.get(f"{BASE}/feedback/dataset/export", params={"start_date": str(today), "end_date": str(today)})
    assert r21c.status_code == 200
    assert len(r21c.json()) > 0
    print("  PASS")

    print("\n" + "=" * 60)
    print("ALL 22 FEEDBACK LOOP TESTS PASSED")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    engine = make_engine(); setup_db(engine)
    session = make_session(engine)
    clean_db(session)
    session.close()

    env = os.environ.copy()
    env.update({
        "DATABASE_URL": DB_URL,
        "WHISPER_MOCK": "True",
        "DIARIZATION_MOCK": "True",
        "LLM_PROVIDER": "mock",
    })

    proc = subprocess.Popen(
        [".\\venv\\Scripts\\python.exe", "-m", "uvicorn", "app.main:app", "--port", "8000"],
        env=env,
    )
    time.sleep(6)
    try:
        run_tests()
    finally:
        proc.terminate()
        # Clean up only tracked files created during this test
        for filepath in CREATED_FILES:
            try:
                if filepath.exists():
                    filepath.unlink(missing_ok=True)
            except Exception:
                pass
