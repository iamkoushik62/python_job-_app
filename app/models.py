import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Enum, Text, ForeignKey,
    UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_id():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────

class RoleEnum(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    EMPLOYER = "EMPLOYER"
    ADMIN = "ADMIN"


class UserStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    SUSPENDED = "SUSPENDED"


class JobTypeEnum(str, enum.Enum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    REMOTE = "Remote"
    INTERNSHIP = "Internship"
    FREELANCE = "Freelance"


class ApplicationStatusEnum(str, enum.Enum):
    APPLIED = "APPLIED"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"
    HIRED = "HIRED"


# ─────────────────────────────────────────────────
# User model
# ─────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_id)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.CANDIDATE, nullable=False)
    status = Column(Enum(UserStatusEnum), default=UserStatusEnum.ACTIVE, nullable=False)
    bio = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    linked_in = Column(String(500), nullable=True)
    resume_url = Column(String(1000), nullable=True)
    profile_image = Column(String(1000), nullable=True)
    skills = Column(JSON, default=list)
    remember_token = Column(String(255), nullable=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relations
    company = relationship("Company", back_populates="users")
    applications = relationship("JobApplication", back_populates="candidate", foreign_keys="JobApplication.candidate_id")
    saved_jobs = relationship("SavedJob", back_populates="user")
    jobs = relationship("Job", back_populates="employer")


# ─────────────────────────────────────────────────
# Company model
# ─────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=gen_id)
    name = Column(String(255), nullable=False)
    logo = Column(String(10), nullable=True)  # 2-letter initials or URL
    description = Column(Text, nullable=True)
    industry = Column(String(100), nullable=False)
    location = Column(String(255), nullable=False)
    website = Column(String(500), nullable=True)
    employee_count = Column(Integer, nullable=True)
    founded_year = Column(Integer, nullable=True)
    headquarters = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relations
    users = relationship("User", back_populates="company")
    jobs = relationship("Job", back_populates="company")


# ─────────────────────────────────────────────────
# Job model
# ─────────────────────────────────────────────────

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=gen_id)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(255), nullable=False)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_display = Column(String(100), nullable=True)
    type = Column(String(50), nullable=False, default="Full-time")
    experience = Column(String(100), nullable=False)
    industry = Column(String(100), nullable=False)
    skills = Column(JSON, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    is_draft = Column(Boolean, default=False, nullable=False)
    applicants_count = Column(Integer, default=0, nullable=False)
    posted_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    employer_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)

    # Relations
    employer = relationship("User", back_populates="jobs")
    company = relationship("Company", back_populates="jobs")
    applications = relationship("JobApplication", back_populates="job")
    saved_by = relationship("SavedJob", back_populates="job")


# ─────────────────────────────────────────────────
# Job Application model
# ─────────────────────────────────────────────────

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(String(36), primary_key=True, default=gen_id)
    cover_letter = Column(Text, nullable=False)
    resume_url = Column(String(1000), nullable=False)
    status = Column(Enum(ApplicationStatusEnum), default=ApplicationStatusEnum.APPLIED)
    status_note = Column(Text, nullable=True)
    applied_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Denormalized fields for performance
    candidate_name = Column(String(255), nullable=True)
    candidate_email = Column(String(255), nullable=True)
    candidate_phone = Column(String(50), nullable=True)

    # Relations
    job = relationship("Job", back_populates="applications")
    candidate = relationship("User", back_populates="applications", foreign_keys=[candidate_id])


# ─────────────────────────────────────────────────
# Saved Job model
# ─────────────────────────────────────────────────

class SavedJob(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_saved_job"),)

    id = Column(String(36), primary_key=True, default=gen_id)
    saved_at = Column(DateTime(timezone=True), default=utcnow)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False)

    # Relations
    user = relationship("User", back_populates="saved_jobs")
    job = relationship("Job", back_populates="saved_by")


# ─────────────────────────────────────────────────
# Password Reset Token model
# ─────────────────────────────────────────────────

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=gen_id)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


# ─────────────────────────────────────────────────
# Refresh Token model
# ─────────────────────────────────────────────────

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, default=gen_id)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
