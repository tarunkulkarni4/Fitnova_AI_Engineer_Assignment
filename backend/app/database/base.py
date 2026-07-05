import re
from typing import Any
from sqlalchemy.orm import DeclarativeBase, declared_attr

class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Automatically generate snake_case __tablename__ from class name
    @declared_attr
    @classmethod
    def __tablename__(cls) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
