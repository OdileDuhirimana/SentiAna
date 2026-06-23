from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from app.db import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String(64), index=True, nullable=True)
    source = Column(String(64), nullable=True)

    text_original = Column(Text, nullable=False)
    text_en = Column(Text, nullable=False)
    language = Column(String(8), nullable=False)

    emotions_json = Column(JSON, nullable=False)
    toxicity_json = Column(JSON, nullable=False)
    sarcasm_json = Column(JSON, nullable=False)
    aspects_json = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
