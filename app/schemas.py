from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator, model_validator


# ─── Auth Schemas ────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    confirmPassword: str
    role: str = "CANDIDATE"   # CANDIDATE | EMPLOYER only
    agreeToTerms: bool = True

    @field_validator("role")
    @classmethod
    def role_not_admin(cls, v: str):
        if v not in ("CANDIDATE", "EMPLOYER"):
            raise ValueError("role must be CANDIDATE or EMPLOYER")
        return v

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirmPassword:
            raise ValueError("Passwords do not match")
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    rememberMe: bool = False


class RefreshRequest(BaseModel):
    refreshToken: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    confirmPassword: str

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.password != self.confirmPassword:
            raise ValueError("Passwords do not match")
        return self


class LogoutRequest(BaseModel):
    refreshToken: str


# ─── Job Schemas ─────────────────────────────────

class JobCreate(BaseModel):
    title: str
    description: str
    location: str
    salaryMin: Optional[int] = None
    salaryMax: Optional[int] = None
    type: str = "Full-time"
    experience: str
    industry: str
    skills: List[str] = []
    isDraft: bool = False
    isRemote: bool = False


class JobUpdate(JobCreate):
    pass


# ─── Application Schemas ──────────────────────────

class ApplicationStatusUpdate(BaseModel):
    status: str
    statusNote: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str):
        if v not in ("APPLIED", "SHORTLISTED", "REJECTED", "HIRED"):
            raise ValueError("Invalid status value")
        return v


# ─── Candidate Profile Schemas ────────────────────

class CandidateProfileUpdate(BaseModel):
    name: str
    phone: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    linkedIn: Optional[str] = None
    skills: List[str] = []


# ─── Employer Profile Schemas ─────────────────────

class EmployerProfileUpdate(BaseModel):
    companyName: str
    description: Optional[str] = None
    industry: str
    location: str
    website: Optional[str] = None
    employeeCount: Optional[int] = None
    foundedYear: Optional[int] = None
    headquarters: Optional[str] = None


# ─── Admin Schemas ────────────────────────────────

class UserStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str):
        if v not in ("ACTIVE", "PENDING", "SUSPENDED"):
            raise ValueError("Invalid status value")
        return v
