from datetime import date, datetime
from sqlalchemy import Boolean, Column, Date, DateTime, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    employee_id = Column(String, nullable=False, unique=True)
    display_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    department = Column(String)
    job_title = Column(String)
    manager_id = Column(String)
    location = Column(String)
    employment_status = Column(String, nullable=False, default="active")
    hire_date = Column(Date)
    termination_date = Column(Date)
    is_on_pip = Column(Boolean, default=False)
    is_pending_transfer = Column(Boolean, default=False)
    is_pending_resign = Column(Boolean, default=False)
    hr_risk_flag = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    data_source = Column(String, default="hr_csv")
