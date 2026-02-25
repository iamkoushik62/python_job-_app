import uuid
import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import require_role
from app.responses import success_response, error_response
from app.config import settings

router = APIRouter(prefix="/candidates", tags=["Candidates"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.get("/profile")
def get_candidate_profile(
    current_user: models.User = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db),
):
    # Stats
    apps = db.query(models.JobApplication).filter(
        models.JobApplication.candidate_id == current_user.id
    ).all()
    total_applied = len(apps)
    shortlisted = sum(1 for a in apps if a.status == models.ApplicationStatusEnum.SHORTLISTED)
    hired = sum(1 for a in apps if a.status == models.ApplicationStatusEnum.HIRED)
    rejected = sum(1 for a in apps if a.status == models.ApplicationStatusEnum.REJECTED)

    return success_response(data={
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role.value,
        "bio": current_user.bio,
        "location": current_user.location,
        "website": current_user.website,
        "linkedIn": current_user.linked_in,
        "skills": current_user.skills or [],
        "resumeUrl": current_user.resume_url,
        "profileImage": current_user.profile_image,
        "stats": {
            "totalApplied": total_applied,
            "shortlisted": shortlisted,
            "hired": hired,
            "rejected": rejected,
        },
        "createdAt": current_user.created_at.isoformat() if current_user.created_at else None,
    })


@router.put("/profile")
def update_candidate_profile(
    body: schemas.CandidateProfileUpdate,
    current_user: models.User = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db),
):
    current_user.name = body.name
    current_user.phone = body.phone
    current_user.bio = body.bio
    current_user.location = body.location
    current_user.website = body.website
    current_user.linked_in = body.linkedIn
    current_user.skills = body.skills
    db.commit()
    db.refresh(current_user)

    return success_response(
        data={
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "phone": current_user.phone,
            "bio": current_user.bio,
            "location": current_user.location,
            "website": current_user.website,
            "linkedIn": current_user.linked_in,
            "skills": current_user.skills or [],
            "updatedAt": current_user.updated_at.isoformat() if current_user.updated_at else None,
        },
        message="Profile updated successfully",
    )


@router.post("/profile/resume")
async def upload_resume(
    resume: UploadFile = File(...),
    current_user: models.User = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db),
):
    if resume.content_type not in ALLOWED_MIME_TYPES:
        return error_response("INVALID_FILE_TYPE", "Only PDF, DOC, DOCX files are allowed", 400)

    content = await resume.read()
    if len(content) > MAX_FILE_SIZE:
        return error_response("FILE_TOO_LARGE", "File exceeds 5MB limit", 413)
    await resume.seek(0)

    os.makedirs(f"{settings.UPLOAD_DIR}/resumes/{current_user.id}", exist_ok=True)
    ext = os.path.splitext(resume.filename)[1] if resume.filename else ".pdf"
    filename = f"{uuid.uuid4()}{ext}"
    path = f"{settings.UPLOAD_DIR}/resumes/{current_user.id}/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    resume_url = f"/files/resumes/{current_user.id}/{filename}"
    current_user.resume_url = resume_url
    db.commit()

    return success_response(
        data={"resumeUrl": resume_url},
        message="Resume uploaded successfully",
    )
