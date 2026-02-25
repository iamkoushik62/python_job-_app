import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user, get_optional_user, require_role
from app.responses import success_response, error_response, paginated_response

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _time_ago(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    if diff.days >= 30:
        return f"{diff.days // 30}mo ago"
    if diff.days >= 1:
        return f"{diff.days}d ago"
    hours = diff.seconds // 3600
    if hours >= 1:
        return f"{hours}h ago"
    return "Just now"


def _salary_display(mn: Optional[int], mx: Optional[int]) -> Optional[str]:
    if mn and mx:
        return f"₹{mn} - ₹{mx} LPA"
    if mn:
        return f"₹{mn}+ LPA"
    return None


def _job_list_item(job: models.Job, user: Optional[models.User], db: Session) -> dict:
    is_saved = False
    is_applied = False
    if user:
        is_saved = db.query(models.SavedJob).filter_by(user_id=user.id, job_id=job.id).first() is not None
        is_applied = db.query(models.JobApplication).filter_by(candidate_id=user.id, job_id=job.id).first() is not None

    return {
        "id": job.id,
        "title": job.title,
        "company": job.company.name if job.company else "",
        "companyLogo": job.company.logo if job.company else "",
        "location": job.location,
        "salary": job.salary_display or _salary_display(job.salary_min, job.salary_max),
        "salaryMin": job.salary_min,
        "salaryMax": job.salary_max,
        "experience": job.experience,
        "type": job.type,
        "industry": job.industry,
        "skills": job.skills or [],
        "description": job.description,
        "applicantsCount": job.applicants_count,
        "isSaved": is_saved,
        "isApplied": is_applied,
        "postedAt": job.posted_at.isoformat() if job.posted_at else None,
        "timeAgo": _time_ago(job.posted_at) if job.posted_at else "",
        "isActive": job.is_active,
        "employer": {"id": job.employer_id, "name": job.employer.name if job.employer else ""},
        "companyDetails": {
            "id": job.company_id,
            "name": job.company.name if job.company else "",
            "isVerified": job.company.is_verified if job.company else False,
            "industry": job.company.industry if job.company else "",
        },
    }


@router.get("")
def list_jobs(
    q: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    experience: Optional[str] = Query(None),
    salaryMin: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user),
):
    query = db.query(models.Job).filter(models.Job.is_active == True, models.Job.is_draft == False)

    if q:
        query = query.filter(
            or_(
                models.Job.title.ilike(f"%{q}%"),
                models.Job.description.ilike(f"%{q}%"),
            )
        )
    if type:
        query = query.filter(models.Job.type == type)
    if location:
        query = query.filter(models.Job.location.ilike(f"%{location}%"))
    if industry:
        query = query.filter(models.Job.industry == industry)
    if experience:
        query = query.filter(models.Job.experience == experience)
    if salaryMin is not None:
        query = query.filter(models.Job.salary_min >= salaryMin)

    total = query.count()
    jobs = query.order_by(models.Job.posted_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = [_job_list_item(j, current_user, db) for j in jobs]
    return success_response(data=paginated_response(items, page, limit, total))


@router.get("/saved")
def get_saved_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db),
):
    saved_query = (
        db.query(models.Job)
        .join(models.SavedJob, models.SavedJob.job_id == models.Job.id)
        .filter(models.SavedJob.user_id == current_user.id)
    )
    total = saved_query.count()
    jobs = saved_query.offset((page - 1) * limit).limit(limit).all()
    items = [_job_list_item(j, current_user, db) for j in jobs]
    return success_response(data=paginated_response(items, page, limit, total))


@router.get("/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_optional_user),
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return error_response("NOT_FOUND", "Job not found", 404)

    data = _job_list_item(job, current_user, db)
    # Add full company details
    if job.company:
        data["companyDetails"] = {
            "id": job.company.id,
            "name": job.company.name,
            "description": job.company.description,
            "industry": job.company.industry,
            "location": job.company.location,
            "website": job.company.website,
            "employeeCount": job.company.employee_count,
            "isVerified": job.company.is_verified,
        }
    return success_response(data=data)


@router.post("/{job_id}/save")
def toggle_save_job(
    job_id: str,
    current_user: models.User = Depends(require_role("CANDIDATE")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return error_response("NOT_FOUND", "Job not found", 404)

    saved = db.query(models.SavedJob).filter_by(user_id=current_user.id, job_id=job_id).first()
    if saved:
        db.delete(saved)
        db.commit()
        return success_response(data={"isSaved": False}, message="Job unsaved")
    else:
        new_saved = models.SavedJob(id=str(uuid.uuid4()), user_id=current_user.id, job_id=job_id)
        db.add(new_saved)
        db.commit()
        return success_response(data={"isSaved": True}, message="Job saved")
