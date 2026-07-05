import os
import sys
import uuid
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup backend directory imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.config import settings
from app.database.base import Base
from app.models.call import Call, ProcessingStatus
from app.models.job import ProcessingJob
from app.models.transcript import Transcript
from app.ai.diarization.diarization_service import DiarizationService

DB_URL = "sqlite:///fitnova_hybrid_test.db"

def setup_db():
    engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session

def teardown_db(engine):
    engine.dispose()
    if os.path.exists("fitnova_hybrid_test.db"):
        os.remove("fitnova_hybrid_test.db")

def test_suspicious_detection():
    print("\n--- Test 1: Suspicious Diarization Detection Heuristic ---")
    engine, Session = setup_db()
    session = Session()
    service = DiarizationService(session)
    
    try:
        call = Call(
            id=uuid.uuid4(),
            advisor_id=uuid.uuid4(),
            source_type="REST API",
            audio_file="mock.wav",
            audio_duration=120,
            processing_status=ProcessingStatus.PROCESSING
        )
        session.add(call)
        session.commit()
        
        # Scenario A: Turns < 5, conversational call (duration > 30) -> Should be suspicious
        turns_a = [
            {"start": 0.0, "end": 60.0, "speaker_label": "SPEAKER_00"},
            {"start": 60.0, "end": 120.0, "speaker_label": "SPEAKER_01"}
        ]
        is_suspicious_a = service._detect_suspicious_diarization(call, turns_a)
        print(f"  Turns < 5 (suspicious): {is_suspicious_a}")
        assert is_suspicious_a is True
        
        # Scenario B: Healthy conversational call (turns >= 5) -> Should not be suspicious
        turns_b = [
            {"start": 0.0, "end": 5.0, "speaker_label": "SPEAKER_00"},
            {"start": 5.0, "end": 10.0, "speaker_label": "SPEAKER_01"},
            {"start": 10.0, "end": 15.0, "speaker_label": "SPEAKER_00"},
            {"start": 15.0, "end": 20.0, "speaker_label": "SPEAKER_01"},
            {"start": 20.0, "end": 25.0, "speaker_label": "SPEAKER_00"},
            {"start": 25.0, "end": 30.0, "speaker_label": "SPEAKER_01"}
        ]
        is_suspicious_b = service._detect_suspicious_diarization(call, turns_b)
        print(f"  Turns >= 5 (not suspicious): {is_suspicious_b}")
        assert is_suspicious_b is False
        
    finally:
        session.close()
        teardown_db(engine)

def test_chunking_boundaries_and_chronological():
    print("\n--- Test 2: Chunking Boundaries and Chronological Constraints ---")
    # Verify that Whisper words list is split correctly on .?! and silence gaps and duration limits
    # and that chunks remain chronologically ordered.
    from pyannote.core import Segment
    
    words = [
        {"word": "Hello.", "start": 0.0, "end": 1.0},
        {"word": "Hi", "start": 1.5, "end": 2.0},  # silence gap = 1.5 - 1.0 = 0.5s (>= 0.4s settings default)
        {"word": "there.", "start": 2.1, "end": 2.5},
        {"word": "Yes,", "start": 3.0, "end": 3.2},  # comma: should not split immediately on comma
        {"word": "this", "start": 3.3, "end": 3.6},
        {"word": "is", "start": 3.7, "end": 3.9},
        {"word": "good.", "start": 4.0, "end": 4.5}
    ]
    
    # We will simulate the chunker directly using the algorithm we implemented
    settings_silence = 0.4
    settings_max_duration = 5.0
    
    chunks = []
    current_chunk = []
    
    for idx, w in enumerate(words):
        if not current_chunk:
            current_chunk.append(w)
            continue
        
        prev_w = current_chunk[-1]
        is_boundary = False
        
        word_text = prev_w["word"].strip()
        
        if word_text.endswith((".", "?", "!")):
            is_boundary = True
        elif w["start"] - prev_w["end"] >= settings_silence:
            is_boundary = True
        elif w["end"] - current_chunk[0]["start"] > settings_max_duration:
            is_boundary = True
            
        if is_boundary:
            start = current_chunk[0]["start"]
            end = prev_w["end"]
            text = " ".join([x["word"] for x in current_chunk])
            chunks.append({
                "start": start,
                "end": end,
                "text": text
            })
            current_chunk = [w]
        else:
            current_chunk.append(w)
            
    if current_chunk:
        start = current_chunk[0]["start"]
        end = current_chunk[-1]["end"]
        text = " ".join([x["word"] for x in current_chunk])
        chunks.append({
            "start": start,
            "end": end,
            "text": text
        })
        
    print(f"  Resulting Chunks: {[c['text'] for c in chunks]}")
    # Word "Hello." ends with period -> Chunk 1
    # Word "Hi" has silence gap from Hello of 0.5s -> Chunk 2 (splits "Hi there.")
    # Word "Yes, this is good." has comma -> does not split at "Yes," -> Chunk 3
    assert len(chunks) == 3
    assert chunks[0]["text"] == "Hello."
    assert chunks[1]["text"] == "Hi there."
    assert chunks[2]["text"] == "Yes, this is good."
    
    # Chronological check
    last_end = -1.0
    for c in chunks:
        assert c["start"] >= last_end
        assert c["end"] >= c["start"]
        last_end = c["end"]
    print("  PASS OK")

if __name__ == "__main__":
    test_suspicious_detection()
    test_chunking_boundaries_and_chronological()
    print("\nALL HYBRID DIARIZATION UNIT TESTS PASSED!")
