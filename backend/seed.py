import os
import sys
import uuid
import random
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database.base import Base
from app.models.organization import Organization
from app.models.team import Team
from app.models.advisor import Advisor, AdvisorStatus
from app.models.call import Call, ProcessingStatus
from app.models.score import CallScore
from app.models.summary import AISummary
from app.models.issue import IssueTag, IssueSeverity
from app.models.feedback import Feedback, FeedbackType
from app.core.config import settings

def seed_database():
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        if db.query(Organization).first():
            print("Database already contains organizations. Skipping seed.")
            return

        print("Seeding database with initial data...")

        org = Organization(id=uuid.uuid4(), name="FitNova Global", industry="Fitness Tech")
        db.add(org)

        team_alpha = Team(id=uuid.uuid4(), organization_id=org.id, name="Alpha Sales", description="Top tier sales")
        team_beta = Team(id=uuid.uuid4(), organization_id=org.id, name="Beta Onboarding", description="New client onboarding")
        db.add_all([team_alpha, team_beta])

        advisors = [
    Advisor(
        id=uuid.uuid4(),
        team_id=team_alpha.id,
        employee_code="EMP001",
        name="Alice Smith",
        email="alice@fitnova.com",
        status=AdvisorStatus.ACTIVE,
    ),
    Advisor(
        id=uuid.uuid4(),
        team_id=team_alpha.id,
        employee_code="EMP002",
        name="Bob Jones",
        email="bob@fitnova.com",
        status=AdvisorStatus.ACTIVE,
    ),
    Advisor(
        id=uuid.uuid4(),
        team_id=team_beta.id,
        employee_code="EMP003",
        name="Charlie Brown",
        email="charlie@fitnova.com",
        status=AdvisorStatus.ACTIVE,
    ),
    Advisor(
        id=uuid.uuid4(),
        team_id=team_beta.id,
        employee_code="EMP004",
        name="Diana Prince",
        email="diana@fitnova.com",
        status=AdvisorStatus.ACTIVE,
    ),
]
        db.add_all(advisors)

        db.commit()

        now = datetime.now(timezone.utc)
        for i in range(15):
            advisor = random.choice(advisors)
            call_id = uuid.uuid4()
            upload_time = now - timedelta(days=random.randint(0, 14), hours=random.randint(1, 12))
            
            call = Call(
                id=call_id,
                advisor_id=advisor.id,
                audio_file=f"storage/audio/processed/{call_id}.wav",
                upload_time=upload_time,
                processing_status=ProcessingStatus.COMPLETED,
                audio_duration=random.randint(300, 1800),
                language="en",
                source_type="Auto-Dialer"
            )
            db.add(call)

            score = CallScore(
                call_id=call_id,
                rapport_score=random.randint(60, 95),
                needs_discovery_score=random.randint(50, 95),
                product_knowledge_score=random.randint(70, 95),
                objection_handling_score=random.randint(40, 90),
                compliance_score=random.randint(80, 100),
                trial_booking_score=random.randint(50, 95),
                closing_score=random.randint(50, 90),
            )
            score.overall_score = int(round(sum([score.rapport_score, score.needs_discovery_score, score.product_knowledge_score, score.objection_handling_score, score.compliance_score, score.trial_booking_score, score.closing_score]) / 7.0))
            db.add(score)

            summary = AISummary(
                call_id=call_id,
                executive_summary="The advisor had a productive call but missed some compliance steps.",
                customer_goal="Weight loss and muscle gain",
                objections="Price was too high initially.",
                recommended_next_step="Send follow-up email with discount link.",
                sentiment=random.choice(["Positive", "Neutral", "Negative"])
            )
            db.add(summary)

            if random.random() > 0.5:
                tag = IssueTag(
                    id=uuid.uuid4(),
                    call_id=call_id,
                    category=random.choice(["MISSING_RISK_DISCLOSURE", "NO_NEEDS_DISCOVERY", "AGGRESSIVE_CLOSE", "MISSING_BOOKING"]),
                    severity=random.choice(list(IssueSeverity)),
                    timestamp=random.randint(10, 200),
                    speaker="Advisor",
                    quote="Let's just sign you up right now.",
                    reason="Advisor pushed for close without discovering needs.",
                    confidence=random.uniform(0.7, 0.99)
                )
                db.add(tag)

                if random.random() > 0.7:
                    feedback = Feedback(
                        id=uuid.uuid4(),
                        call_id=call_id,
                        reviewer_name="Manager Admin",
                        feedback_type=FeedbackType.TAG,
                        original_value=json.dumps({"action": "reject", "issue_tag_id": str(tag.id)}),
                        corrected_value=json.dumps({"rejected": True}),
                        comments="Not an aggressive close, just standard pitch.",
                        reviewed_at=upload_time + timedelta(hours=1)
                    )
                    db.add(feedback)
                    
                    score_feedback = Feedback(
                        id=uuid.uuid4(),
                        call_id=call_id,
                        reviewer_name="Manager Admin",
                        feedback_type=FeedbackType.SCORE,
                        original_value=json.dumps({"dimension": "closing", "score": score.closing}),
                        corrected_value=json.dumps({"dimension": "closing", "score": score.closing + 10}),
                        comments="Advisor actually closed well here.",
                        reviewed_at=upload_time + timedelta(hours=1, minutes=5)
                    )
                    db.add(score_feedback)

        db.commit()
        print("Database seeded successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
