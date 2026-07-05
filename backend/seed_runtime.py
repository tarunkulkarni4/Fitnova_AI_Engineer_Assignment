import os
import uuid
from datetime import datetime, timezone
from app.database.base import Base
from app.database.database import SessionLocal
from app.models.organization import Organization
from app.models.team import Team
from app.models.advisor import Advisor, AdvisorStatus
from app.models.call import Call, ProcessingStatus
from app.models.score import CallScore
from app.models.summary import AISummary
from app.models.issue import IssueTag, IssueSeverity

os.environ['DATABASE_URL'] = 'sqlite:///fitnova.db'

Base.metadata.create_all(SessionLocal().bind)
s = SessionLocal()
s.query(Call).delete()
s.query(CallScore).delete()
s.query(AISummary).delete()
s.query(IssueTag).delete()
s.query(Advisor).delete()
s.query(Team).delete()
s.query(Organization).delete()
s.commit()

org = Organization(id=uuid.uuid4(), name='FitNova Global', industry='Fitness Tech')
s.add(org)
s.flush()
team_alpha = Team(id=uuid.uuid4(), organization_id=org.id, name='Alpha Sales', description='Sales')
team_beta = Team(id=uuid.uuid4(), organization_id=org.id, name='Beta Onboarding', description='Onboarding')
s.add_all([team_alpha, team_beta])
s.flush()
advisors = [
    Advisor(id=uuid.uuid4(), team_id=team_alpha.id, employee_code='EMP001', name='Alice Smith', email='alice@fitnova.com', status=AdvisorStatus.ACTIVE),
    Advisor(id=uuid.uuid4(), team_id=team_alpha.id, employee_code='EMP002', name='Bob Jones', email='bob@fitnova.com', status=AdvisorStatus.ACTIVE),
    Advisor(id=uuid.uuid4(), team_id=team_beta.id, employee_code='EMP003', name='Charlie Brown', email='charlie@fitnova.com', status=AdvisorStatus.ACTIVE),
    Advisor(id=uuid.uuid4(), team_id=team_beta.id, employee_code='EMP004', name='Diana Prince', email='diana@fitnova.com', status=AdvisorStatus.ACTIVE),
]
s.add_all(advisors)
s.commit()

now = datetime.now(timezone.utc)
for advisor, score, issues in [
    (advisors[0], {'rapport':80,'needs_discovery':70,'product_knowledge':75,'objection_handling':60,'compliance':85,'trial_booking':70,'closing':65,'overall':72}, [{'category':'NO_NEEDS_DISCOVERY','severity':IssueSeverity.MEDIUM}]),
    (advisors[1], {'rapport':60,'needs_discovery':50,'product_knowledge':55,'objection_handling':40,'compliance':65,'trial_booking':45,'closing':35,'overall':47}, [{'category':'MISSING_BOOKING','severity':IssueSeverity.HIGH}]),
    (advisors[2], {'rapport':90,'needs_discovery':80,'product_knowledge':85,'objection_handling':70,'compliance':90,'trial_booking':80,'closing':75,'overall':79}, []),
    (advisors[3], {'rapport':85,'needs_discovery':75,'product_knowledge':80,'objection_handling':65,'compliance':88,'trial_booking':76,'closing':70,'overall':74}, []),
]:
    call = Call(id=uuid.uuid4(), advisor_id=advisor.id, source_type='REST API', audio_file='test.wav', processed_audio_file='test.wav', audio_duration=120, language='en', processing_status=ProcessingStatus.COMPLETED, upload_time=now)
    s.add(call)
    s.flush()
    s.add(CallScore(call_id=call.id, rapport_score=score['rapport'], needs_discovery_score=score['needs_discovery'], product_knowledge_score=score['product_knowledge'], objection_handling_score=score['objection_handling'], compliance_score=score['compliance'], trial_booking_score=score['trial_booking'], closing_score=score['closing'], overall_score=score['overall']))
    for issue in issues:
        s.add(IssueTag(call_id=call.id, category=issue['category'], severity=issue['severity'], timestamp=1.0, speaker='Advisor', quote='x', reason='y', confidence=0.9))
    s.commit()

print('teams', s.query(Team).count())
print('advisors', s.query(Advisor).count())
print('calls', s.query(Call).count())
