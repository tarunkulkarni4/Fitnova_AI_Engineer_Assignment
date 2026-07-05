"""
Integration tests for lookup and advisor-list endpoints.
Uses the same pattern as test_feedback.py:
- starts uvicorn with SQLite in-process
- seeds test data via direct SQLAlchemy
- makes HTTP requests via requests library
"""
import json
import os
import subprocess
import sys
import time
import uuid
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
from app.models.issue import IssueTag, IssueSeverity
from app.models.summary import AISummary
from app.models.transcript import Transcript

DB_URL = "sqlite:///fitnova_lookup_test.db"
BASE = "http://127.0.0.1:8765/api/v1"


def make_engine():
    return create_engine(DB_URL, connect_args={"check_same_thread": False})


def setup_db(engine):
    from app.database.base import Base
    Base.metadata.create_all(engine)


def clean_db(session):
    for m in (IssueTag, AISummary, CallScore, ProcessingJob, Call,
              Advisor, Team, Organization):
        session.query(m).delete()
    session.commit()


def seed(session):
    org1 = Organization(name="FitNova Global", industry="Fitness")
    org2 = Organization(name="Health Corp", industry="Healthcare")
    session.add_all([org1, org2])
    session.flush()

    team1 = Team(organization_id=org1.id, name="Alpha Team")
    team2 = Team(organization_id=org1.id, name="Beta Team")
    team3 = Team(organization_id=org2.id, name="Gamma Team")
    session.add_all([team1, team2, team3])
    session.flush()

    adv1 = Advisor(team_id=team1.id, employee_code="A001", name="Alice Smith",
                   email="alice@test.com", status=AdvisorStatus.ACTIVE)
    adv2 = Advisor(team_id=team1.id, employee_code="A002", name="Bob Jones",
                   email="bob@test.com", status=AdvisorStatus.INACTIVE)
    adv3 = Advisor(team_id=team2.id, employee_code="A003", name="Carol White",
                   email="carol@test.com", status=AdvisorStatus.ACTIVE)
    session.add_all([adv1, adv2, adv3])
    session.flush()

    # One completed call with score for alice
    call = Call(
        advisor_id=adv1.id, source_type="REST API",
        audio_file="dummy.wav", processing_status=ProcessingStatus.COMPLETED,
    )
    session.add(call); session.flush()
    session.add(ProcessingJob(call_id=call.id, stage="Completed",
                              status=ProcessingStatus.COMPLETED, retry_count=0))
    session.add(CallScore(call_id=call.id, rapport_score=80, overall_score=75))
    session.add(IssueTag(call_id=call.id, category="PRESSURE_TACTIC",
                         severity=IssueSeverity.CRITICAL, quote="some quote",
                         reason="reason", confidence=0.9))
    session.commit()

    return org1, org2, team1, team2, team3, adv1, adv2, adv3


def run_tests():
    # ------------------------------------------------------------------ #
    # Start uvicorn on port 8765 with SQLite                              #
    # ------------------------------------------------------------------ #
    env = os.environ.copy()
    env["DATABASE_URL"] = DB_URL
    env["LLM_PROVIDER"] = "mock"
    env["WHISPER_MOCK"] = "True"
    env["DIARIZATION_MOCK"] = "True"

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", "8765", "--log-level", "warning"],
        env=env,
    )

    # Wait for server to start
    for _ in range(30):
        try:
            requests.get(f"http://127.0.0.1:8765/api/v1/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    engine = make_engine()
    setup_db(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    clean_db(session)
    org1, org2, team1, team2, team3, adv1, adv2, adv3 = seed(session)

    try:
        print()
        print("=" * 60)
        print("LOOKUP + ADVISOR-LIST ENDPOINT TESTS")
        print("=" * 60)

        # -------------------------------------------------------------- #
        # Test 1: GET /lookups/organizations                              #
        # -------------------------------------------------------------- #
        print("\n--- Test 1: GET /lookups/organizations ---")
        r = requests.get(f"{BASE}/lookups/organizations")
        assert r.status_code == 200, f"{r.status_code}: {r.text}"
        orgs = r.json()
        assert isinstance(orgs, list) and len(orgs) >= 2, f"Expected 2+ orgs, got {orgs}"
        names = {o["name"] for o in orgs}
        assert "FitNova Global" in names
        assert "Health Corp" in names
        for o in orgs:
            assert "id" in o and "name" in o
        print(f"  PASS — {len(orgs)} organizations")

        # -------------------------------------------------------------- #
        # Test 2: GET /lookups/teams (unfiltered)                         #
        # -------------------------------------------------------------- #
        print("\n--- Test 2: GET /lookups/teams ---")
        r = requests.get(f"{BASE}/lookups/teams")
        assert r.status_code == 200, f"{r.status_code}: {r.text}"
        teams = r.json()
        assert len(teams) >= 3
        for t in teams:
            assert all(k in t for k in ("id", "name", "organization_id", "organization_name"))
        print(f"  PASS — {len(teams)} teams")

        # -------------------------------------------------------------- #
        # Test 3: GET /lookups/teams?organization_id= filters             #
        # -------------------------------------------------------------- #
        print("\n--- Test 3: GET /lookups/teams filtered by org ---")
        r = requests.get(f"{BASE}/lookups/teams?organization_id={org1.id}")
        assert r.status_code == 200
        filtered = r.json()
        assert len(filtered) == 2, f"Expected 2 teams for org1, got {len(filtered)}"
        for t in filtered:
            assert str(t["organization_id"]) == str(org1.id)
        print(f"  PASS — {len(filtered)} teams for FitNova Global")

        # -------------------------------------------------------------- #
        # Test 4: GET /lookups/advisors (unfiltered)                      #
        # -------------------------------------------------------------- #
        print("\n--- Test 4: GET /lookups/advisors ---")
        r = requests.get(f"{BASE}/lookups/advisors")
        assert r.status_code == 200
        advisors = r.json()
        assert len(advisors) == 3
        for a in advisors:
            assert all(k in a for k in ("id", "name", "email", "status", "team_id", "team_name"))
        print(f"  PASS — {len(advisors)} advisors")

        # -------------------------------------------------------------- #
        # Test 5: GET /lookups/advisors?status=Active                     #
        # -------------------------------------------------------------- #
        print("\n--- Test 5: GET /lookups/advisors?status=Active ---")
        r = requests.get(f"{BASE}/lookups/advisors?status=Active")
        assert r.status_code == 200
        active = r.json()
        assert len(active) == 2, f"Expected 2 active, got {len(active)}"
        for a in active:
            assert a["status"] == "Active"
        print(f"  PASS — {len(active)} active advisors")

        # -------------------------------------------------------------- #
        # Test 6: GET /lookups/advisors?status=Inactive                   #
        # -------------------------------------------------------------- #
        print("\n--- Test 6: GET /lookups/advisors?status=Inactive ---")
        r = requests.get(f"{BASE}/lookups/advisors?status=Inactive")
        assert r.status_code == 200
        inactive = r.json()
        assert len(inactive) == 1
        assert inactive[0]["status"] == "Inactive"
        print(f"  PASS — {len(inactive)} inactive advisors")

        # -------------------------------------------------------------- #
        # Test 7: GET /lookups/advisors?status=INVALID -> 422             #
        # -------------------------------------------------------------- #
        print("\n--- Test 7: GET /lookups/advisors?status=INVALID -> 422 ---")
        r = requests.get(f"{BASE}/lookups/advisors?status=INVALID")
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        print("  PASS — invalid status returns 422")

        # -------------------------------------------------------------- #
        # Test 8: GET /lookups/advisors?team_id= filter                   #
        # -------------------------------------------------------------- #
        print("\n--- Test 8: GET /lookups/advisors?team_id= ---")
        r = requests.get(f"{BASE}/lookups/advisors?team_id={team1.id}")
        assert r.status_code == 200
        team_advisors = r.json()
        assert len(team_advisors) == 2
        for a in team_advisors:
            assert str(a["team_id"]) == str(team1.id)
        print(f"  PASS — {len(team_advisors)} advisors for Alpha Team")

        # -------------------------------------------------------------- #
        # Test 9: GET /lookups/advisors?search= partial name              #
        # -------------------------------------------------------------- #
        print("\n--- Test 9: GET /lookups/advisors?search=ali ---")
        r = requests.get(f"{BASE}/lookups/advisors?search=ali")
        assert r.status_code == 200
        found = r.json()
        assert len(found) == 1
        assert "Alice" in found[0]["name"]
        print(f"  PASS — found '{found[0]['name']}'")

        # -------------------------------------------------------------- #
        # Test 10: GET /lookups/issue-taxonomy                            #
        # -------------------------------------------------------------- #
        print("\n--- Test 10: GET /lookups/issue-taxonomy ---")
        r = requests.get(f"{BASE}/lookups/issue-taxonomy")
        assert r.status_code == 200, f"{r.status_code}: {r.text}"
        taxonomy = r.json()
        assert len(taxonomy) > 0
        cats = {item["category"] for item in taxonomy}
        for expected in ["NO_NEEDS_DISCOVERY", "GUARANTEED_RESULTS", "NO_TRIAL_BOOKING",
                         "PRESSURE_TACTIC", "MISSING_NEXT_STEP"]:
            assert expected in cats, f"Missing: {expected}"
        for item in taxonomy:
            assert item["severity"] in ("Critical", "High", "Medium", "Low")
            assert isinstance(item["absence_based"], bool)
        absence_cats = {i["category"] for i in taxonomy if i["absence_based"]}
        for ab in ["NO_NEEDS_DISCOVERY", "NO_TRIAL_BOOKING", "MISSING_NEXT_STEP"]:
            assert ab in absence_cats, f"Expected absence_based for {ab}"
        non_absence = {i["category"] for i in taxonomy if not i["absence_based"]}
        assert "PRESSURE_TACTIC" in non_absence
        print(f"  PASS — {len(taxonomy)} taxonomy items, absence flags correct")

        # -------------------------------------------------------------- #
        # Test 11: GET /dashboard/advisors (analytics listing)            #
        # -------------------------------------------------------------- #
        print("\n--- Test 11: GET /dashboard/advisors ---")
        r = requests.get(f"{BASE}/dashboard/advisors")
        assert r.status_code == 200, f"{r.status_code}: {r.text}"
        body = r.json()
        assert "items" in body and "total" in body and "page" in body
        assert body["total"] == 3
        for item in body["items"]:
            assert all(k in item for k in (
                "advisor_id", "advisor_name", "advisor_email", "advisor_status",
                "team_id", "team_name", "organization_id", "organization_name",
                "completed_calls", "average_score", "critical_issue_count",
            ))
        # Alice should have completed_calls=1, average_score not None
        alice = next(i for i in body["items"] if i["advisor_name"] == "Alice Smith")
        assert alice["completed_calls"] == 1, f"Expected 1, got {alice['completed_calls']}"
        assert alice["average_score"] is not None
        # Bob has no calls
        bob = next(i for i in body["items"] if i["advisor_name"] == "Bob Jones")
        assert bob["completed_calls"] == 0
        assert bob["average_score"] is None
        print(f"  PASS — {body['total']} advisors with analytics")

        # -------------------------------------------------------------- #
        # Test 12: /dashboard/advisors?status=Active                      #
        # -------------------------------------------------------------- #
        print("\n--- Test 12: GET /dashboard/advisors?status=Active ---")
        r = requests.get(f"{BASE}/dashboard/advisors?status=Active")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        for item in body["items"]:
            assert item["advisor_status"] == "Active"
        print(f"  PASS — {body['total']} active advisors")

        # -------------------------------------------------------------- #
        # Test 13: /dashboard/advisors?status=INVALID -> 422              #
        # -------------------------------------------------------------- #
        print("\n--- Test 13: GET /dashboard/advisors?status=INVALID -> 422 ---")
        r = requests.get(f"{BASE}/dashboard/advisors?status=INVALID")
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"
        print("  PASS — invalid status returns 422")

        # -------------------------------------------------------------- #
        # Test 14: /dashboard/advisors?team_id= filter                    #
        # -------------------------------------------------------------- #
        print("\n--- Test 14: GET /dashboard/advisors?team_id= ---")
        r = requests.get(f"{BASE}/dashboard/advisors?team_id={team1.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        for item in body["items"]:
            assert str(item["team_id"]) == str(team1.id)
        print(f"  PASS — {body['total']} advisors for Alpha Team")

        # -------------------------------------------------------------- #
        # Test 15: /dashboard/advisors pagination                         #
        # -------------------------------------------------------------- #
        print("\n--- Test 15: GET /dashboard/advisors?page=1&page_size=1 ---")
        r = requests.get(f"{BASE}/dashboard/advisors?page=1&page_size=1")
        assert r.status_code == 200
        body = r.json()
        assert body["page"] == 1 and body["page_size"] == 1
        assert len(body["items"]) == 1
        assert body["total"] == 3 and body["total_pages"] == 3
        print(f"  PASS — pagination: 1 item per page, 3 total pages")

        # -------------------------------------------------------------- #
        # Test 16: /dashboard/advisors critical_issue_count               #
        # -------------------------------------------------------------- #
        print("\n--- Test 16: critical_issue_count for Alice ---")
        r = requests.get(f"{BASE}/dashboard/advisors")
        body = r.json()
        alice = next(i for i in body["items"] if i["advisor_name"] == "Alice Smith")
        assert alice["critical_issue_count"] == 1, \
            f"Expected 1 critical issue, got {alice['critical_issue_count']}"
        print(f"  PASS — Alice has 1 critical issue tag")

        print()
        print("=" * 60)
        print("ALL 16 LOOKUP + ADVISOR-LIST TESTS PASSED")
        print("=" * 60)

    finally:
        server.terminate()
        session.close()
        import sqlite3
        try:
            Path("fitnova_lookup_test.db").unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    run_tests()
