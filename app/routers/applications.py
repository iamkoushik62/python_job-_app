import uuid
import os
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, require_role
from app.responses import success_response, error_response, paginated_response
from app.config import settings

router = APIRouter(prefix="/applications", tags=["Applications"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def _save_resume(file: UploadFile, user_id: str) -> str:
    """Save uploaded resume locally and return URL path."""
    os.makedirs(f"{settings.UPLOAD_DIR}/resumes/{user_id}", exist_ok=True)
    ext = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
    filename = f"{uuid.uuid4()}{ext}"
    path = f"{settings.UPLOAD_DIR}/resumes/{user_id}/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    # Return a URL-style path (in production replace with S3 URL)
    return f"/files/resumes/{user_id}/{filename}"


def _app_list_item(app: models.JobApplication) -> dict:
    job = app.job
    company = job.company if job else None
    return {
        "id": app.id,
        "jobId": app.job_id,
        "jobTitle": job.title if job else "",
        "company": company.name if company else "",
        "companyLogo": company.logo if company else "",
        "status": app.status.value if app.status else "APPLIED",
        "appliedAt": app.applied_at.isoformat() if app.applied_at else None,
        "location": job.location if job else None,
        "salary": job.salary_display if job else None,
        "resumeUrl": app.resume_url,
        "coverLetter": app.cover_letter,
    }


@router.post("", status_code=201)
async def submit_application(
    jobId: str = Form(...),
    coverLetter: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    resume: UploadFile = File(...),
    current_user: models.User = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db),
):
    # Validate file type
    if resume.content_type not in ALLOWED_MIME_TYPES:
        return error_response("INVALID_FILE_TYPE", "Only PDF, DOC, DOCX files are allowed", 400)

    # Read to check size
    content = await resume.read()
    if len(content) > MAX_FILE_SIZE:
        return error_response("FILE_TOO_LARGE", "File exceeds 5MB limit", 413)
    await resume.seek(0)

    if len(coverLetter.strip()) < 50:
        return error_response("VALIDATION_ERROR", "Cover letter must be at least 50 characters", 400)

    # Check job exists
    job = db.query(models.Job).filter(models.Job.id == jobId, models.Job.is_active == True).first()
    if not job:
        return error_response("NOT_FOUND", "Job not found or no longer active", 404)

    # Check duplicate
    existing = db.query(models.JobApplication).filter_by(candidate_id=current_user.id, job_id=jobId).first()
    if existing:
        return error_response("ALREADY_APPLIED", "You have already applied to this job", 409)

    resume_url = _save_resume(resume, current_user.id)

    application = models.JobApplication(
        id=str(uuid.uuid4()),
        job_id=jobId,
        candidate_id=current_user.id,
        cover_letter=coverLetter,
        resume_url=resume_url,
        status=models.ApplicationStatusEnum.APPLIED,
        candidate_name=name,
        candidate_email=email,
        candidate_phone=phone,
    )
    db.add(application)

    # Increment applicants count
    job.applicants_count = (job.applicants_count or 0) + 1
    db.commit()
    db.refresh(application)

    company = job.company
    return success_response(
        data={
            "id": application.id,
            "jobId": job.id,
            "jobTitle": job.title,
            "company": company.name if company else "",
            "companyLogo": company.logo if company else "",
            "candidateId": current_user.id,
            "candidateName": name,
            "candidateEmail": email,
            "resumeUrl": resume_url,
            "coverLetter": coverLetter,
            "status": "APPLIED",
            "appliedAt": application.applied_at.isoformat(),
            "location": job.location,
            "salary": job.salary_display,
        },
        message="Application submitted successfully",
        status_code=201,
    )


@router.get("/my")
def get_my_applications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: models.User = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db),
):
    query = db.query(models.JobApplication).filter(
        models.JobApplication.candidate_id == current_user.id
    )
    if status:
        query = query.filter(models.JobApplication.status == status)

    total = query.count()
    apps = query.order_by(models.JobApplication.applied_at.desc()).offset((page - 1) * limit).limit(limit).all()
    items = [_app_list_item(a) for a in apps]
    return success_response(data=paginated_response(items, page, limit, total))


@router.get("/{app_id}")
def get_application(
    app_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = db.query(models.JobApplication).filter(models.JobApplication.id == app_id).first()
    if not app:
        return error_response("NOT_FOUND", "Application not found", 404)

    # Access control
    is_candidate = app.candidate_id == current_user.id
    is_employer = (current_user.role.value == "EMPLOYER" and
                   app.job and app.job.employer_id == current_user.id)
    is_admin = current_user.role.value == "ADMIN"

    if not (is_candidate or is_employer or is_admin):
        return error_response("FORBIDDEN", "Access denied", 403)

    job = app.job
    company = job.company if job else None
    return success_response(data={
        "id": app.id,
        "jobId": app.job_id,
        "jobTitle": job.title if job else "",
        "company": company.name if company else "",
        "companyLogo": company.logo if company else "",
        "candidateId": app.candidate_id,
        "candidateName": app.candidate_name,
        "candidateEmail": app.candidate_email,
        "resumeUrl": app.resume_url,
        "coverLetter": app.cover_letter,
        "status": app.status.value,
        "statusNote": app.status_note,
        "appliedAt": app.applied_at.isoformat() if app.applied_at else None,
        "location": job.location if job else None,
        "salary": job.salary_display if job else None,
    })


@router.patch("/{app_id}/status")
def update_application_status(
    app_id: str,
    body: schemas.ApplicationStatusUpdate,
    current_user: models.User = Depends(require_role("EMPLOYER", "ADMIN")),
    db: Session = Depends(get_db),
):
    app = db.query(models.JobApplication).filter(models.JobApplication.id == app_id).first()
    if not app:
        return error_response("NOT_FOUND", "Application not found", 404)

    # Employer can only update their own job's applicants
    if current_user.role.value == "EMPLOYER":
        if not app.job or app.job.employer_id != current_user.id:
            return error_response("FORBIDDEN", "Access denied", 403)

    app.status = models.ApplicationStatusEnum(body.status)
    app.status_note = body.statusNote
    db.commit()
    db.refresh(app)

    return success_response(
        data={
            "id": app.id,
            "status": app.status.value,
            "statusNote": app.status_note,
            "updatedAt": app.updated_at.isoformat() if app.updated_at else None,
        },
        message=f"Status updated to {body.status.capitalize()}",
    )
