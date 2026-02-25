import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import require_role
from app.responses import success_response, error_response, paginated_response

router = APIRouter(prefix="/employer", tags=["Employer"])


def _salary_display(mn: Optional[int], mx: Optional[int]) -> Optional[str]:
    if mn and mx:
        return f"₹{mn} - ₹{mx} LPA"
    if mn:
        return f"₹{mn}+ LPA"
    return None


@router.get("/jobs")
def get_employer_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),  # active | draft | closed
    current_user: models.User = Depends(require_role("EMPLOYER")),
    db: Session = Depends(get_db),
):
    query = db.query(models.Job).filter(models.Job.employer_id == current_user.id)

    if status == "active":
        query = query.filter(models.Job.is_active == True, models.Job.is_draft == False)
    elif status == "draft":
        query = query.filter(models.Job.is_draft == True)
    elif status == "closed":
        query = query.filter(models.Job.is_active == False)

    total = query.count()
    jobs = query.order_by(models.Job.posted_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = []
    for job in jobs:
        apps = db.query(models.JobApplication).filter(models.JobApplication.job_id == job.id).all()
        shortlisted = sum(1 for a in apps if a.status == models.ApplicationStatusEnum.SHORTLISTED)
        hired = sum(1 for a in apps if a.status == models.ApplicationStatusEnum.HIRED)

        items.append({
            "id": job.id,
            "title": job.title,
            "location": job.location,
            "type": job.type,
            "salary": job.salary_display or _salary_display(job.salary_min, job.salary_max),
            "applicantsCount": job.applicants_count,
            "shortlistedCount": shortlisted,
            "hiredCount": hired,
            "isActive": job.is_active,
            "isDraft": job.is_draft,
            "postedAt": job.posted_at.isoformat() if job.posted_at else None,
            "company": {
                "id": job.company_id,
                "name": job.company.name if job.company else "",
                "logo": job.company.logo if job.company else "",
            },
        })

    return success_response(data=paginated_response(items, page, limit, total))


@router.post("/jobs", status_code=201)
def post_job(
    body: schemas.JobCreate,
    current_user: models.User = Depends(require_role("EMPLOYER")),
    db: Session = Depends(get_db),
):
    if not current_user.company_id:
        return error_response("FORBIDDEN", "You must have a company profile to post jobs. Update your profile first.", 403)

    salary_display = _salary_display(body.salaryMin, body.salaryMax)
    job = models.Job(
        id=str(uuid.uuid4()),
        title=body.title,
        description=body.description,
        location=body.location,
        salary_min=body.salaryMin,
        salary_max=body.salaryMax,
        salary_display=salary_display,
        type=body.type,
        experience=body.experience,
        industry=body.industry,
        skills=body.skills,
        is_draft=body.isDraft,
        is_active=not body.isDraft,
        employer_id=current_user.id,
        company_id=current_user.company_id,
        applicants_count=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return success_response(
        data={
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "salary": job.salary_display,
            "salaryMin": job.salary_min,
            "salaryMax": job.salary_max,
            "type": job.type,
            "experience": job.experience,
            "industry": job.industry,
            "skills": job.skills or [],
            "isActive": job.is_active,
            "isDraft": job.is_draft,
            "applicantsCount": 0,
            "postedAt": job.posted_at.isoformat() if job.posted_at else None,
        },
        message="Job posted successfully",
        status_code=201,
    )


@router.put("/jobs/{job_id}")
def update_job(
    job_id: str,
    body: schemas.JobUpdate,
    current_user: models.User = Depends(require_role("EMPLOYER")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(
        models.Job.id == job_id,
        models.Job.employer_id == current_user.id,
    ).first()
    if not job:
        return error_response("NOT_FOUND", "Job not found", 404)

    job.title = body.title
    job.description = body.description
    job.location = body.location
    job.salary_min = body.salaryMin
    job.salary_max = body.salaryMax
    job.salary_display = _salary_display(body.salaryMin, body.salaryMax)
    job.type = body.type
    job.experience = body.experience
    job.industry = body.industry
    job.skills = body.skills
    job.is_draft = body.isDraft
    if not body.isDraft:
        job.is_active = True
    db.commit()
    db.refresh(job)

    return success_response(
        data={
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "location": job.location,
            "salary": job.salary_display,
            "salaryMin": job.salary_min,
            "salaryMax": job.salary_max,
            "type": job.type,
            "experience": job.experience,
            "industry": job.industry,
            "skills": job.skills or [],
            "isActive": job.is_active,
            "isDraft": job.is_draft,
            "applicantsCount": job.applicants_count,
            "postedAt": job.posted_at.isoformat() if job.posted_at else None,
        },
        message="Job updated successfully",
    )


@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: str,
    current_user: models.User = Depends(require_role("EMPLOYER")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(
        models.Job.id == job_id,
        models.Job.employer_id == current_user.id,
    ).first()
    if not job:
        return error_response("NOT_FOUND", "Job not found", 404)

    db.delete(job)
    db.commit()
    return success_response(message="Job deleted successfully")


@router.patch("/jobs/{job_id}/close")
def close_job(
    job_id: str,
    current_user: models.User = Depends(require_role("EMPLOYER")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(
        models.Job.id == job_id,
        models.Job.employer_id == current_user.id,
    ).first()
    if not job:
        return error_response("NOT_FOUND", "Job not found", 404)

    job.is_active = False
    db.commit()
    return success_response(data={"isActive": False}, message="Job closed")


@router.get("/jobs/{job_id}/applicants")
def get_job_applicants(
    job_id: str,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(require_role("EMPLOYER")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(
        models.Job.id == job_id,
        models.Job.employer_id == current_user.id,
    ).first()
    if not job:
        return error_response("NOT_FOUND", "Job not found", 404)

    query = db.query(models.JobApplication).filter(models.JobApplication.job_id == job_id)
    if status:
        query = query.filter(models.JobApplication.status == status)

    total = query.count()
    apps = query.order_by(models.JobApplication.applied_at.desc()).offset((page - 1) * limit).limit(limit).all()

    # Counts
    all_apps = db.query(models.JobApplication).filter(models.JobApplication.job_id == job_id).all()
    counts = {
        "total": len(all_apps),
        "applied": sum(1 for a in all_apps if a.status == models.ApplicationStatusEnum.APPLIED),
        "shortlisted": sum(1 for a in all_apps if a.status == models.ApplicationStatusEnum.SHORTLISTED),
        "hired": sum(1 for a in all_apps if a.status == models.ApplicationStatusEnum.HIRED),
        "rejected": sum(1 for a in all_apps if a.status == models.ApplicationStatusEnum.REJECTED),
    }

    items = [{
        "id": a.id,
        "candidateId": a.candidate_id,
        "candidateName": a.candidate_name,
        "candidateEmail": a.candidate_email,
        "status": a.status.value,
        "appliedAt": a.applied_at.isoformat() if a.applied_at else None,
        "resumeUrl": a.resume_url,
        "coverLetter": a.cover_letter,
    } for a in apps]

    return success_response(data={
        "job": {"id": job.id, "title": job.title},
        "items": items,
        "counts": counts,
        "pagination": paginated_response(items, page, limit, total)["pagination"],
    })


@router.get("/profile")
def get_employer_profile(
    current_user: models.User = Depends(require_role("EMPLOYER")),
    db: Session = Depends(get_db),
):
    company = current_user.company

    stats = {"jobsPosted": 0, "totalHired": 0, "averageRating": 0}
    if company:
        jobs = db.query(models.Job).filter(models.Job.company_id == company.id).all()
        stats["jobsPosted"] = len(jobs)
        for job in jobs:
            apps = db.query(models.JobApplication).filter(
                models.JobApplication.job_id == job.id,
                models.JobApplication.status == models.ApplicationStatusEnum.HIRED,
            ).count()
            stats["totalHired"] += apps

    return success_response(data={
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role.value,
        },
        "company": {
            "id": company.id if company else None,
            "name": company.name if company else None,
            "logo": company.logo if company else None,
            "description": company.description if company else None,
            "industry": company.industry if company else None,
            "location": company.location if company else None,
            "website": company.website if company else None,
            "employeeCount": company.employee_count if company else None,
            "foundedYear": company.founded_year if company else None,
            "headquarters": company.headquarters if company else None,
            "isVerified": company.is_verified if company else False,
            "stats": stats,
        } if company else None,
    })


@router.put("/profile")
def update_employer_profile(
    body: schemas.EmployerProfileUpdate,
    current_user: models.User = Depends(require_role("EMPLOYER")),
    db: Session = Depends(get_db),
):
    company = current_user.company

    if not company:
        # Create a new company for the employer
        company = models.Company(
            id=str(uuid.uuid4()),
            name=body.companyName,
            description=body.description,
            industry=body.industry,
            location=body.location,
            website=body.website,
            employee_count=body.employeeCount,
            founded_year=body.foundedYear,
            headquarters=body.headquarters,
        )
        db.add(company)
        db.flush()
        current_user.company_id = company.id
    else:
        company.name = body.companyName
        company.description = body.description
        company.industry = body.industry
        company.location = body.location
        company.website = body.website
        company.employee_count = body.employeeCount
        company.founded_year = body.foundedYear
        company.headquarters = body.headquarters

    # Generate logo initials from company name
    words = body.companyName.strip().split()
    logo = "".join(w[0].upper() for w in words[:2])
    company.logo = logo

    db.commit()
    db.refresh(company)

    return success_response(data={
        "id": company.id,
        "name": company.name,
        "logo": company.logo,
        "description": company.description,
        "industry": company.industry,
        "location": company.location,
        "website": company.website,
        "employeeCount": company.employee_count,
        "foundedYear": company.founded_year,
        "headquarters": company.headquarters,
        "isVerified": company.is_verified,
    }, message="Profile updated successfully")
