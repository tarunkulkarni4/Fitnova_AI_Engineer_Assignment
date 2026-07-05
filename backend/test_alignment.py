"""
Unit tests for TranscriptService's high-fidelity speaker alignment and text splitting logic.
Verifies all 6 required scenarios:
1. Customer -> Advisor -> Customer inside one Whisper segment.
2. Rapid alternating turns.
3. Short responses such as "Yes".
4. Overlapping boundary timestamps.
5. Adjacent same-speaker chunks.
6. Stable Advisor/Customer role mapping (confidence-based).
"""

import os
import json
import uuid
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.organization import Organization
from app.models.team import Team
from app.models.advisor import Advisor, AdvisorStatus
from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob
from app.models.transcript import Transcript
from app.services.transcript_service import TranscriptService

DB_URL = "sqlite:///fitnova_alignment_test.db"
STORAGE_DIR = Path("app/storage/transcripts")

def setup_db():
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session

def teardown_db(engine):
    engine.dispose()
    if os.path.exists("fitnova_alignment_test.db"):
        os.remove("fitnova_alignment_test.db")

def create_base_entities(session):
    org = Organization(name="Test Org", industry="Fitness")
    session.add(org)
    session.flush()
    team = Team(organization_id=org.id, name="Test Team", description="Diarization alignment test")
    session.add(team)
    session.flush()
    advisor = Advisor(
        team_id=team.id, employee_code="EMP002",
        name="Tester", email="tester2@pipeline.test",
        status=AdvisorStatus.ACTIVE,
    )
    session.add(advisor)
    session.commit()
    return advisor.id

def create_call_job(session, advisor_id):
    call_id = uuid.uuid4()
    call = Call(
        id=call_id,
        advisor_id=advisor_id,
        source_type="REST API",
        audio_file="mock.wav",
        processed_audio_file="mock_processed.wav",
        audio_duration=60,
        processing_status=ProcessingStatus.READY_FOR_TRANSCRIPT_MERGE,
        language="en"
    )
    session.add(call)
    job = ProcessingJob(
        call_id=call_id,
        stage="Speaker Diarization",
        status=ProcessingStatus.READY_FOR_TRANSCRIPT_MERGE
    )
    session.add(job)
    session.commit()
    return call_id

def cleanup_files(call_id):
    for suffix in ["_whisper.json", "_diarization.json", ".json"]:
        file_path = STORAGE_DIR / f"{call_id}{suffix}"
        if file_path.exists():
            file_path.unlink()

def run_alignment_test():
    engine, Session = setup_db()
    session = Session()
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        advisor_id = create_base_entities(session)

        # ---------------------------------------------------------------------
        # TEST 1: Customer -> Advisor -> Customer inside one Whisper segment (linear estimation)
        # ---------------------------------------------------------------------
        print("\n--- Test 1: Customer -> Advisor -> Customer inside one segment ---")
        call_id = create_call_job(session, advisor_id)

        # 1 Whisper segment spanning 10.0 to 16.0
        whisper_data = {
            "segments": [
                {
                    "start": 10.0,
                    "end": 16.0,
                    "text": "firstsecond thirdfourth fifthsixth", # 6 words, 2 per speaker segment
                    "confidence": 0.95
                }
            ]
        }
        with open(STORAGE_DIR / f"{call_id}_whisper.json", "w", encoding="utf-8") as f:
            json.dump(whisper_data, f)

        # Diarization turns:
        # 10.0 to 12.0: SPEAKER_01 (Customer)
        # 12.0 to 14.0: SPEAKER_00 (Advisor)
        # 14.0 to 16.0: SPEAKER_01 (Customer)
        diarization_data = {
            "diarization_turns": [
                {"start": 10.0, "end": 12.0, "speaker_label": "SPEAKER_01"},
                {"start": 12.0, "end": 14.0, "speaker_label": "SPEAKER_00"},
                {"start": 14.0, "end": 16.0, "speaker_label": "SPEAKER_01"}
            ],
            "role_mapping": {"SPEAKER_00": "Advisor", "SPEAKER_01": "Customer"},
            "role_mapping_confidence": 0.90
        }
        with open(STORAGE_DIR / f"{call_id}_diarization.json", "w", encoding="utf-8") as f:
            json.dump(diarization_data, f)

        # Seed initial database segment (as DiarizationService would have done roughly)
        initial_seg = Transcript(
            call_id=call_id,
            speaker="Customer", # best overlapping speaker
            start_time=10.0,
            end_time=16.0,
            text="firstsecond thirdfourth fifthsixth",
            confidence=0.95
        )
        session.add(initial_seg)
        session.commit()

        # Run Transcript Building
        service = TranscriptService(session)
        res = session.query(Call).filter(Call.id == call_id).first()
        res_dict = asyncio_run_helper(service.build_transcript(call_id))

        # Assertions
        db_segs = session.query(Transcript).filter(Transcript.call_id == call_id).order_by(Transcript.start_time.asc()).all()
        print(f"  Split DB segments: {[(s.speaker, s.start_time, s.end_time, s.text) for s in db_segs]}")
        assert len(db_segs) == 3
        assert db_segs[0].speaker == "Customer"
        assert db_segs[1].speaker == "Advisor"
        assert db_segs[2].speaker == "Customer"
        assert db_segs[0].text == "firstsecond"
        assert db_segs[1].text == "thirdfourth"
        assert db_segs[2].text == "fifthsixth"

        with open(STORAGE_DIR / f"{call_id}.json", "r", encoding="utf-8") as f:
            final_transcript = json.load(f)
        print(f"  Final Merged: {final_transcript['segments']}")
        assert len(final_transcript["segments"]) == 3
        print("  PASS OK")
        cleanup_files(call_id)

        # ---------------------------------------------------------------------
        # TEST 2: Rapid alternating turns with word-level timestamps
        # ---------------------------------------------------------------------
        print("\n--- Test 2: Rapid alternating turns with word-level timestamps ---")
        call_id = create_call_job(session, advisor_id)

        whisper_data = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 4.0,
                    "text": "hello hi yes fine",
                    "confidence": 0.98,
                    "words": [
                        {"word": "hello", "start": 0.2, "end": 0.8, "probability": 0.99},
                        {"word": "hi", "start": 1.2, "end": 1.8, "probability": 0.99},
                        {"word": "yes", "start": 2.2, "end": 2.8, "probability": 0.99},
                        {"word": "fine", "start": 3.2, "end": 3.8, "probability": 0.99}
                    ]
                }
            ]
        }
        with open(STORAGE_DIR / f"{call_id}_whisper.json", "w", encoding="utf-8") as f:
            json.dump(whisper_data, f)

        # Rapidly alternating speaker turns
        diarization_data = {
            "diarization_turns": [
                {"start": 0.0, "end": 1.0, "speaker_label": "SPEAKER_00"},
                {"start": 1.0, "end": 2.0, "speaker_label": "SPEAKER_01"},
                {"start": 2.0, "end": 3.0, "speaker_label": "SPEAKER_00"},
                {"start": 3.0, "end": 4.0, "speaker_label": "SPEAKER_01"}
            ],
            "role_mapping": {"SPEAKER_00": "Advisor", "SPEAKER_01": "Customer"},
            "role_mapping_confidence": 0.95
        }
        with open(STORAGE_DIR / f"{call_id}_diarization.json", "w", encoding="utf-8") as f:
            json.dump(diarization_data, f)

        initial_seg = Transcript(
            call_id=call_id,
            speaker="Advisor",
            start_time=0.0,
            end_time=4.0,
            text="hello hi yes fine",
            confidence=0.98
        )
        session.add(initial_seg)
        session.commit()

        asyncio_run_helper(service.build_transcript(call_id))

        db_segs = session.query(Transcript).filter(Transcript.call_id == call_id).order_by(Transcript.start_time.asc()).all()
        print(f"  Split DB segments: {[(s.speaker, s.start_time, s.end_time, s.text) for s in db_segs]}")
        assert len(db_segs) == 4
        assert db_segs[0].speaker == "Advisor"
        assert db_segs[1].speaker == "Customer"
        assert db_segs[2].speaker == "Advisor"
        assert db_segs[3].speaker == "Customer"
        assert db_segs[0].text == "hello"
        assert db_segs[1].text == "hi"
        assert db_segs[2].text == "yes"
        assert db_segs[3].text == "fine"
        print("  PASS OK")
        cleanup_files(call_id)

        # ---------------------------------------------------------------------
        # TEST 3: Short responses such as "Yes"
        # ---------------------------------------------------------------------
        print("\n--- Test 3: Short responses such as 'Yes' ---")
        call_id = create_call_job(session, advisor_id)

        whisper_data = {
            "segments": [
                {
                    "start": 20.0,
                    "end": 20.5,
                    "text": "Yes",
                    "confidence": 0.90
                }
            ]
        }
        with open(STORAGE_DIR / f"{call_id}_whisper.json", "w", encoding="utf-8") as f:
            json.dump(whisper_data, f)

        # Midpoint of word "Yes" (20.25) is inside the diarization turn
        diarization_data = {
            "diarization_turns": [
                {"start": 19.8, "end": 20.6, "speaker_label": "SPEAKER_01"}
            ],
            "role_mapping": {"SPEAKER_01": "Customer"},
            "role_mapping_confidence": 0.85
        }
        with open(STORAGE_DIR / f"{call_id}_diarization.json", "w", encoding="utf-8") as f:
            json.dump(diarization_data, f)

        initial_seg = Transcript(
            call_id=call_id,
            speaker="Customer",
            start_time=20.0,
            end_time=20.5,
            text="Yes",
            confidence=0.90
        )
        session.add(initial_seg)
        session.commit()

        asyncio_run_helper(service.build_transcript(call_id))

        db_segs = session.query(Transcript).filter(Transcript.call_id == call_id).all()
        assert len(db_segs) == 1
        assert db_segs[0].speaker == "Customer"
        assert db_segs[0].text == "Yes"
        print("  PASS OK")
        cleanup_files(call_id)

        # ---------------------------------------------------------------------
        # TEST 4: Overlapping boundary timestamps
        # ---------------------------------------------------------------------
        print("\n--- Test 4: Overlapping boundary timestamps ---")
        call_id = create_call_job(session, advisor_id)

        # Segment words starts at 0.5, 1.5, 2.5
        whisper_data = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 3.0,
                    "text": "worda wordb wordc",
                    "confidence": 0.95
                }
            ]
        }
        with open(STORAGE_DIR / f"{call_id}_whisper.json", "w", encoding="utf-8") as f:
            json.dump(whisper_data, f)

        # Overlapping diarization boundaries:
        # Turn 1: 0.0 to 1.8 (SPEAKER_00)
        # Turn 2: 1.2 to 3.0 (SPEAKER_01)
        # Overlap region: 1.2 to 1.8.
        # Word midpoints:
        # "worda" midpoint = 0.5 -> matches Turn 1
        # "wordb" midpoint = 1.5 -> matches Turn 1 (inside overlap, but Turn 1 has it)
        # "wordc" midpoint = 2.5 -> matches Turn 2
        diarization_data = {
            "diarization_turns": [
                {"start": 0.0, "end": 1.8, "speaker_label": "SPEAKER_00"},
                {"start": 1.2, "end": 3.0, "speaker_label": "SPEAKER_01"}
            ],
            "role_mapping": {"SPEAKER_00": "Advisor", "SPEAKER_01": "Customer"},
            "role_mapping_confidence": 0.99
        }
        with open(STORAGE_DIR / f"{call_id}_diarization.json", "w", encoding="utf-8") as f:
            json.dump(diarization_data, f)

        initial_seg = Transcript(
            call_id=call_id,
            speaker="Advisor",
            start_time=0.0,
            end_time=3.0,
            text="worda wordb wordc",
            confidence=0.95
        )
        session.add(initial_seg)
        session.commit()

        asyncio_run_helper(service.build_transcript(call_id))

        db_segs = session.query(Transcript).filter(Transcript.call_id == call_id).order_by(Transcript.start_time.asc()).all()
        print(f"  Overlapping DB split: {[(s.speaker, s.start_time, s.end_time, s.text) for s in db_segs]}")
        assert len(db_segs) == 2
        assert db_segs[0].speaker == "Advisor"
        assert db_segs[1].speaker == "Customer"
        assert db_segs[0].text == "worda wordb"
        assert db_segs[1].text == "wordc"
        print("  PASS OK")
        cleanup_files(call_id)

        # ---------------------------------------------------------------------
        # TEST 5: Adjacent same-speaker chunks (merged)
        # ---------------------------------------------------------------------
        print("\n--- Test 5: Adjacent same-speaker chunks merged ---")
        call_id = create_call_job(session, advisor_id)

        whisper_data = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "first chunk",
                    "confidence": 0.90
                },
                {
                    "start": 3.0,
                    "end": 5.0,
                    "text": "second chunk",
                    "confidence": 0.90
                }
            ]
        }
        with open(STORAGE_DIR / f"{call_id}_whisper.json", "w", encoding="utf-8") as f:
            json.dump(whisper_data, f)

        # Same speaker for both segments, gap = 3.0 - 2.0 = 1.0s (<= 1.5s)
        diarization_data = {
            "diarization_turns": [
                {"start": 0.0, "end": 5.0, "speaker_label": "SPEAKER_00"}
            ],
            "role_mapping": {"SPEAKER_00": "Advisor"},
            "role_mapping_confidence": 0.90
        }
        with open(STORAGE_DIR / f"{call_id}_diarization.json", "w", encoding="utf-8") as f:
            json.dump(diarization_data, f)

        for s_idx, text, start, end in [(1, "first chunk", 0.0, 2.0), (2, "second chunk", 3.0, 5.0)]:
            session.add(Transcript(
                call_id=call_id,
                speaker="Advisor",
                start_time=start,
                end_time=end,
                text=text,
                confidence=0.90
            ))
        session.commit()

        asyncio_run_helper(service.build_transcript(call_id))

        with open(STORAGE_DIR / f"{call_id}.json", "r", encoding="utf-8") as f:
            final_transcript = json.load(f)
        print(f"  Final Merged: {final_transcript['segments']}")
        assert len(final_transcript["segments"]) == 1
        assert final_transcript["segments"][0]["speaker"] == "Advisor"
        assert final_transcript["segments"][0]["text"] == "first chunk second chunk"
        print("  PASS OK")
        cleanup_files(call_id)

        # ---------------------------------------------------------------------
        # TEST 6: Stable Advisor/Customer role mapping (confidence test)
        # ---------------------------------------------------------------------
        print("\n--- Test 6: Stable Advisor/Customer role mapping confidence test ---")
        call_id = create_call_job(session, advisor_id)

        whisper_data = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 2.0,
                    "text": "test sentence",
                    "confidence": 0.95
                }
            ]
        }
        with open(STORAGE_DIR / f"{call_id}_whisper.json", "w", encoding="utf-8") as f:
            json.dump(whisper_data, f)

        # Low confidence (< 0.5) -> speaker identity stays neutral (SPEAKER_00)
        diarization_data = {
            "diarization_turns": [
                {"start": 0.0, "end": 2.0, "speaker_label": "SPEAKER_00"}
            ],
            "role_mapping": {"SPEAKER_00": "Advisor"},
            "role_mapping_confidence": 0.30
        }
        with open(STORAGE_DIR / f"{call_id}_diarization.json", "w", encoding="utf-8") as f:
            json.dump(diarization_data, f)

        initial_seg = Transcript(
            call_id=call_id,
            speaker="SPEAKER_00",
            start_time=0.0,
            end_time=2.0,
            text="test sentence",
            confidence=0.95
        )
        session.add(initial_seg)
        session.commit()

        asyncio_run_helper(service.build_transcript(call_id))

        db_segs = session.query(Transcript).filter(Transcript.call_id == call_id).all()
        print(f"  Diarization low-confidence speaker: {db_segs[0].speaker}")
        assert db_segs[0].speaker == "SPEAKER_00" # identity preserved
        print("  PASS OK")
        cleanup_files(call_id)

        print("\n" + "="*50)
        print("ALL TRANSCRIPT ALIGNMENT TESTS PASSED SUCCESSFULLY!")
        print("="*50)

    finally:
        session.close()
        teardown_db(engine)

def asyncio_run_helper(coro):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

if __name__ == "__main__":
    run_alignment_test()
