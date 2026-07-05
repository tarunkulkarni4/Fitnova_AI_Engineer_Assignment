import os
os.environ['DATABASE_URL'] = 'sqlite:///fitnova.db'
from app.database.database import SessionLocal
from app.models.team import Team
from app.models.advisor import Advisor
from app.models.call import Call
from sqlalchemy import func
s = SessionLocal()
print('teams')
for t in s.query(Team).all():
    print(t.id, t.name)
print('advisors')
for a in s.query(Advisor).all():
    print(a.id, a.name, a.team_id)
print('calls', s.query(func.count(Call.id)).scalar())
