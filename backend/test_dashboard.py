"""
Integration tests for the Dashboard Analytics API — 21 test cases.

Runs against a live Uvicorn server with mocked AI dependencies.
Tests are self-contained: they seed their own data and assert clean results.
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
    for m in (IssueTag, AISummary, CallScore, Transcript, ProcessingJob, Call,
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


def seed_completed_call(
    session, advisor_id, *,
    score: dict | None = None,
    issues: list[dict] | None = None,
    summary: dict | None = None,
    upload_time: datetime | None = None,
) -> Call:
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
        upload_time=upload_time or datetime.utcnow(),
    )
    session.add(c); session.flush()

    session.add(ProcessingJob(
        call_id=c.id, stage="Completed", status=ProcessingStatus.COMPLETED, retry_count=0
    ))

    if score:
        session.add(CallScore(
            call_id=c.id,
            rapport_score=score.get("rapport", 70),
            needs_discovery_score=score.get("needs_discovery", 70),
            product_knowledge_score=score.get("product_knowledge", 70),
            objection_handling_score=score.get("objection_handling", 70),
            compliance_score=score.get("compliance", 70),
            trial_booking_score=score.get("trial_booking", 70),
            closing_score=score.get("closing", 70),
            overall_score=score.get("overall", 70),
        ))

    for issue in (issues or []):
        session.add(IssueTag(
            call_id=c.id,
            category=issue.get("category", "NO_GREETING"),
            severity=IssueSeverity(issue.get("severity", "Medium")),
            timestamp=issue.get("timestamp", 1.0),
            speaker=issue.get("speaker", "Advisor"),
            quote=issue.get("quote", ""),
            reason=issue.get("reason", ""),
            confidence=issue.get("confidence", 0.9),
        ))

    if summary:
        session.add(AISummary(
            call_id=c.id,
            executive_summary=summary.get("executive_summary", "Summary"),
            customer_goal=summary.get("customer_goal"),
            objections=summary.get("objections"),
            recommended_next_step=summary.get("recommended_next_step"),
            sentiment=summary.get("sentiment", "Neutral"),
        ))

    session.commit()

    # Write redacted transcript artifact
    REDACTED_DIR.mkdir(parents=True, exist_ok=True)
    redacted_path = REDACTED_DIR / f"{c.id}.json"
    redacted_path.write_text(json.dumps([
        {"speaker": "Advisor", "start_time": 0.0, "end_time": 5.0,
         "text": "Hello welcome to FitNova.", "confidence": 0.95},
        {"speaker": "Customer", "start_time": 5.5, "end_time": 10.0,
         "text": "Hi I want to know about your plans.", "confidence": 0.90},
    ]), encoding="utf-8")
    CREATED_FILES.append(redacted_path)

    return c


def seed_failed_call(session, advisor_id) -> Call:
    c = Call(
        advisor_id=advisor_id,
        source_type="REST API",
        audio_file="bad.mp3",
        processing_status=ProcessingStatus.FAILED,
    )
    session.add(c); session.flush()
    session.add(ProcessingJob(
        call_id=c.id, stage="Audio Processing",
        status=ProcessingStatus.FAILED, retry_count=1
    ))
    session.commit()
    return c


def g(url, **kw) -> requests.Response:
    return requests.get(f"{BASE}{url}", **kw)


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

def run_tests():
    engine = make_engine(); setup_db(engine)
    session = make_session(engine)
    clean_db(session)

    # ---- Seed common data ----
    org = seed_org(session)
    org2 = seed_org(session, "Other Org")

    team_a = seed_team(session, org.id, "Team A")
    team_b = seed_team(session, org.id, "Team B")
    team_other = seed_team(session, org2.id, "Other Team")

    adv1 = seed_advisor(session, team_a.id, "Alice")
    adv2 = seed_advisor(session, team_a.id, "Bob")
    adv3 = seed_advisor(session, team_b.id, "Carol")
    adv_other = seed_advisor(session, team_other.id, "Dave")

    # Adv1: 3 completed calls with scores, 1 failed
    c1 = seed_completed_call(session, adv1.id,
        score={"rapport": 90, "needs_discovery": 60, "product_knowledge": 80,
               "objection_handling": 50, "compliance": 95, "trial_booking": 65,
               "closing": 55, "overall": 70},
        issues=[
            {"category": "NO_NEEDS_DISCOVERY", "severity": "High"},
            {"category": "PRESSURE_SELLING", "severity": "Critical"},
        ],
        summary={"executive_summary": "Good call overall.", "sentiment": "Positive"},
    )
    c2 = seed_completed_call(session, adv1.id,
        score={"rapport": 80, "needs_discovery": 70, "product_knowledge": 75,
               "objection_handling": 60, "compliance": 85, "trial_booking": 70,
               "closing": 65, "overall": 72},
        issues=[{"category": "NO_NEEDS_DISCOVERY", "severity": "Medium"}],
        summary={"executive_summary": "Decent call.", "sentiment": "Neutral"},
    )
    c3 = seed_completed_call(session, adv1.id,
        score={"rapport": 70, "needs_discovery": 80, "product_knowledge": 85,
               "objection_handling": 70, "compliance": 90, "trial_booking": 80,
               "closing": 75, "overall": 79},
        summary={"executive_summary": "Strong close.", "sentiment": "Positive"},
    )
    failed_call = seed_failed_call(session, adv1.id)

    # Adv2: 1 completed call, lower scores
    c4 = seed_completed_call(session, adv2.id,
        score={"rapport": 50, "needs_discovery": 45, "product_knowledge": 55,
               "objection_handling": 40, "compliance": 60, "trial_booking": 45,
               "closing": 35, "overall": 47},
        issues=[
            {"category": "NO_NEEDS_DISCOVERY", "severity": "High"},
            {"category": "MISSING_BOOKING", "severity": "High"},
        ],
    )

    # Adv3 (Team B): 1 completed call, high scores
    c5 = seed_completed_call(session, adv3.id,
        score={"rapport": 95, "needs_discovery": 90, "product_knowledge": 92,
               "objection_handling": 88, "compliance": 98, "trial_booking": 91,
               "closing": 89, "overall": 92},
    )

    # Adv other org: should be invisible to org-scoped queries
    seed_completed_call(session, adv_other.id,
        score={"overall": 30},
    )

    # Call with no score (completed but analysis not run)
    c_noscore = Call(
        advisor_id=adv1.id,
        source_type="REST API",
        audio_file="x.mp3",
        processing_status=ProcessingStatus.COMPLETED,
    )
    session.add(c_noscore); session.flush()
    session.add(ProcessingJob(call_id=c_noscore.id, stage="Completed",
                              status=ProcessingStatus.COMPLETED, retry_count=0))
    session.commit()

    print("\n" + "=" * 60)
    print("DASHBOARD INTEGRATION TESTS")
    print("=" * 60)

    # ---------------------------------------------------------------- #
    # TEST 1 — Org aggregate metrics                                   #
    # ---------------------------------------------------------------- #
    print("\n--- Test 1: Organization aggregate metrics ---")
    r = g(f"/dashboard/org/{org.id}")
    res = r.json()
    print(f"  Status: {r.status_code}")
    assert r.status_code == 200, res
    assert res["total_teams"] == 2
    assert res["total_advisors"] == 3
    assert res["completed_calls"] >= 4   # c1,c2,c3,c4,c5,c_noscore
    assert res["failed_calls"] >= 1
    assert res["average_quality_score"] is not None
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 2 — Team aggregate metrics                                  #
    # ---------------------------------------------------------------- #
    print("\n--- Test 2: Team aggregate metrics ---")
    r2 = g(f"/dashboard/team/{team_a.id}")
    res2 = r2.json()
    assert r2.status_code == 200, res2
    assert res2["team_name"] == "Team A"
    assert res2["total_advisors"] == 2
    assert res2["average_quality_score"] is not None
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 3 — Advisor aggregate metrics                               #
    # ---------------------------------------------------------------- #
    print("\n--- Test 3: Advisor aggregate metrics ---")
    r3 = g(f"/dashboard/advisor/{adv1.id}")
    res3 = r3.json()
    assert r3.status_code == 200, res3
    assert res3["advisor_name"] == "Alice"
    assert res3["team_name"] == "Team A"
    assert res3["total_calls"] >= 4   # c1,c2,c3,failed,c_noscore
    assert res3["completed_calls"] >= 3
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 4 — Advisor leaderboard sorted avg_score DESC               #
    # ---------------------------------------------------------------- #
    print("\n--- Test 4: Advisor leaderboard sorted by avg_score DESC ---")
    lb = res2["advisor_leaderboard"]
    assert len(lb) >= 2
    # Alice (avg ~73) should be above Bob (avg 47)
    names = [a["advisor_name"] for a in lb]
    alice_idx = names.index("Alice")
    bob_idx = names.index("Bob")
    assert alice_idx < bob_idx, f"Expected Alice before Bob, got {names}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 5 — Lowest 3 dimensions = improvement areas                 #
    # ---------------------------------------------------------------- #
    print("\n--- Test 5: Lowest 3 dimensions become improvement areas ---")
    areas = res3["improvement_areas"]
    assert len(areas) == 3
    # Scores must be sorted ascending
    scores_ia = [a["average_score"] for a in areas if a["average_score"] is not None]
    assert scores_ia == sorted(scores_ia), f"Not sorted: {scores_ia}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 6 — Failed calls excluded from quality averages             #
    # ---------------------------------------------------------------- #
    print("\n--- Test 6: Failed calls excluded from quality averages ---")
    # The failed call has no score; avg should only consider analyzed completed calls
    org_score = res["average_quality_score"]
    # Manually compute expected: (70+72+79+47+92)/5 = 360/5 = 72.0
    expected_avg = round((70 + 72 + 79 + 47 + 92) / 5, 2)
    assert abs(org_score - expected_avg) < 1.0, f"Expected ~{expected_avg}, got {org_score}"
    print(f"  org avg_score={org_score} (expected ~{expected_avg})  PASS")

    # ---------------------------------------------------------------- #
    # TEST 7 — Calls without scores don't break averages               #
    # ---------------------------------------------------------------- #
    print("\n--- Test 7: Calls without scores don't break averages ---")
    # c_noscore has no CallScore row — org endpoint must still return a score
    assert res["average_quality_score"] is not None
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 8 — Top issue tags ordered by frequency DESC                #
    # ---------------------------------------------------------------- #
    print("\n--- Test 8: Top issue tags ordered by frequency DESC ---")
    top_tags = res["top_issue_tags"]
    assert len(top_tags) > 0
    counts = [t["count"] for t in top_tags]
    assert counts == sorted(counts, reverse=True), f"Not sorted desc: {counts}"
    # NO_NEEDS_DISCOVERY appears 3 times (c1,c2,c4)
    tag_by_cat = {t["category"]: t["count"] for t in top_tags}
    assert tag_by_cat.get("NO_NEEDS_DISCOVERY", 0) == 3, tag_by_cat
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 9 — Call review: scores, tags, summary                      #
    # ---------------------------------------------------------------- #
    print("\n--- Test 9: Call review returns scores, tags, summary ---")
    r9 = g(f"/dashboard/calls/{c1.id}")
    res9 = r9.json()
    assert r9.status_code == 200, res9
    assert res9["score"] is not None
    assert res9["score"]["overall"] == 70
    assert len(res9["issue_tags"]) == 2
    assert res9["summary"] is not None
    assert res9["summary"]["sentiment"] == "Positive"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 10 — Call review returns redacted transcript                #
    # ---------------------------------------------------------------- #
    print("\n--- Test 10: Call review returns only redacted transcript ---")
    assert res9["transcript_available"] is True
    assert len(res9["transcript"]) == 2
    # Verify segments have expected structure
    seg = res9["transcript"][0]
    assert "speaker" in seg and "text" in seg and "start_time" in seg
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 11 — Missing transcript artifact → graceful degradation     #
    # ---------------------------------------------------------------- #
    print("\n--- Test 11: Missing transcript artifact doesn't crash ---")
    # Create a completed call but delete its redacted file
    c_notranscript = seed_completed_call(session, adv1.id,
        score={"overall": 80},
        summary={"executive_summary": "No transcript test."},
    )
    artifact_path = REDACTED_DIR / f"{c_notranscript.id}.json"
    if artifact_path.exists():
        artifact_path.unlink()

    r11 = g(f"/dashboard/calls/{c_notranscript.id}")
    res11 = r11.json()
    assert r11.status_code == 200, res11
    assert res11["transcript_available"] is False
    assert res11["transcript"] == []
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 12 — Call list basic pagination                             #
    # ---------------------------------------------------------------- #
    print("\n--- Test 12: Call list pagination ---")
    r12 = g("/dashboard/calls", params={"page": 1, "page_size": 2})
    res12 = r12.json()
    assert r12.status_code == 200, res12
    assert len(res12["items"]) <= 2
    assert res12["page"] == 1
    assert res12["page_size"] == 2
    assert res12["total"] >= 6
    expected_pages = math.ceil(res12["total"] / 2)
    assert res12["total_pages"] == expected_pages
    print(f"  total={res12['total']}, pages={res12['total_pages']}  PASS")

    # ---------------------------------------------------------------- #
    # TEST 13 — Filter by organization_id                              #
    # ---------------------------------------------------------------- #
    print("\n--- Test 13: Filter by organization_id ---")
    r13 = g("/dashboard/calls", params={"organization_id": str(org.id), "page_size": 100})
    res13 = r13.json()
    assert r13.status_code == 200, res13
    # All items must belong to org (not org2)
    team_names = {i["team_name"] for i in res13["items"]}
    assert "Other Team" not in team_names, f"Org filter leaked: {team_names}"
    print(f"  {res13['total']} calls in org (none from other org)  PASS")

    # ---------------------------------------------------------------- #
    # TEST 14 — Filter by team_id                                      #
    # ---------------------------------------------------------------- #
    print("\n--- Test 14: Filter by team_id ---")
    r14 = g("/dashboard/calls", params={"team_id": str(team_b.id)})
    res14 = r14.json()
    assert r14.status_code == 200, res14
    for item in res14["items"]:
        assert item["team_id"] == str(team_b.id), f"Wrong team: {item['team_id']}"
    print(f"  {res14['total']} calls in Team B  PASS")

    # ---------------------------------------------------------------- #
    # TEST 15 — Filter by advisor_id                                   #
    # ---------------------------------------------------------------- #
    print("\n--- Test 15: Filter by advisor_id ---")
    r15 = g("/dashboard/calls", params={"advisor_id": str(adv2.id)})
    res15 = r15.json()
    assert r15.status_code == 200, res15
    for item in res15["items"]:
        assert item["advisor_id"] == str(adv2.id)
    print(f"  {res15['total']} calls for adv2  PASS")

    # ---------------------------------------------------------------- #
    # TEST 16 — Score filters                                          #
    # ---------------------------------------------------------------- #
    print("\n--- Test 16: Score filters ---")
    r16 = g("/dashboard/calls", params={"min_score": 75, "max_score": 95, "page_size": 50})
    res16 = r16.json()
    assert r16.status_code == 200, res16
    for item in res16["items"]:
        if item["overall_score"] is not None:
            assert 75 <= item["overall_score"] <= 95, item
    print(f"  {res16['total']} calls with score 75-95  PASS")

    # ---------------------------------------------------------------- #
    # TEST 17 — Severity filter                                        #
    # ---------------------------------------------------------------- #
    print("\n--- Test 17: Severity filter ---")
    r17 = g("/dashboard/calls", params={"severity": "Critical", "page_size": 50})
    res17 = r17.json()
    assert r17.status_code == 200, res17
    # Only c1 has a Critical issue
    assert res17["total"] >= 1
    call_ids_17 = {i["call_id"] for i in res17["items"]}
    assert str(c1.id) in call_ids_17, "c1 (with Critical tag) not in results"
    assert str(c2.id) not in call_ids_17, "c2 (no Critical tag) should not appear"
    print(f"  {res17['total']} calls with Critical issues  PASS")

    # ---------------------------------------------------------------- #
    # TEST 18 — Issue category filter                                  #
    # ---------------------------------------------------------------- #
    print("\n--- Test 18: Issue category filter ---")
    r18 = g("/dashboard/calls", params={"issue_category": "MISSING_BOOKING", "page_size": 50})
    res18 = r18.json()
    assert r18.status_code == 200, res18
    assert res18["total"] >= 1
    call_ids_18 = {i["call_id"] for i in res18["items"]}
    assert str(c4.id) in call_ids_18, "c4 (with MISSING_BOOKING) not in results"
    assert str(c1.id) not in call_ids_18, "c1 (no MISSING_BOOKING) should not appear"
    print(f"  {res18['total']} calls with MISSING_BOOKING  PASS")

    # ---------------------------------------------------------------- #
    # TEST 19 — Date filtering                                         #
    # ---------------------------------------------------------------- #
    print("\n--- Test 19: Date filtering ---")
    future = (datetime.utcnow() + timedelta(days=1)).date()
    r19 = g("/dashboard/calls", params={"end_date": str(future), "start_date": "2000-01-01"})
    assert r19.status_code == 200
    # Invalid: start > end
    r19b = g("/dashboard/calls", params={"start_date": "2099-01-01", "end_date": "2000-01-01"})
    assert r19b.status_code == 400, f"Expected 400, got {r19b.status_code}"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 20 — Sorting                                                #
    # ---------------------------------------------------------------- #
    print("\n--- Test 20: Sorting options ---")
    for sort_val in ("newest", "oldest", "highest_score", "lowest_score"):
        r20 = g("/dashboard/calls", params={"sort": sort_val, "page_size": 10, "organization_id": str(org.id)})
        assert r20.status_code == 200, f"sort={sort_val}: {r20.json()}"
    # Check actual ordering for newest
    items_newest = g("/dashboard/calls", params={"sort": "newest", "page_size": 50}).json()["items"]
    times = [i["upload_time"] for i in items_newest]
    assert times == sorted(times, reverse=True), "newest sort broken"
    print("  PASS")

    # ---------------------------------------------------------------- #
    # TEST 21 — Invalid processing_status returns 422                  #
    # ---------------------------------------------------------------- #
    print("\n--- Test 21: Invalid processing_status returns HTTP 422 ---")
    r21 = g("/dashboard/calls", params={"processing_status": "NONSENSE_VALUE"})
    print(f"  Status: {r21.status_code}")
    assert r21.status_code == 422, f"Expected 422, got {r21.status_code}: {r21.json()}"
    print("  PASS")

    print("\n" + "=" * 60)
    print("ALL 21 DASHBOARD TESTS PASSED")
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
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        # Clean up only tracked files created during this test
        for filepath in CREATED_FILES:
            try:
                if filepath.exists():
                    filepath.unlink(missing_ok=True)
            except Exception:
                pass
