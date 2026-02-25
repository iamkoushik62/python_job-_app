from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models, schemas
from app.dependencies import require_role
from app.responses import success_response, error_response, paginated_response

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
def get_dashboard(
    current_user: models.User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    total_users = db.query(models.User).count()
    total_candidates = db.query(models.User).filter(models.User.role == models.RoleEnum.CANDIDATE).count()
    total_employers = db.query(models.User).filter(models.User.role == models.RoleEnum.EMPLOYER).count()
    total_jobs = db.query(models.Job).count()
    active_jobs = db.query(models.Job).filter(models.Job.is_active == True, models.Job.is_draft == False).count()
    total_applications = db.query(models.JobApplication).count()

    today = datetime.now(timezone.utc).date()
    new_users_today = db.query(models.User).filter(
        func.date(models.User.created_at) == today
    ).count()
    new_apps_today = db.query(models.JobApplication).filter(
        func.date(models.JobApplication.applied_at) == today
    ).count()

    # Recent activity: last 10 applications + jobs + users
    recent_apps = db.query(models.JobApplication).order_by(
        models.JobApplication.applied_at.desc()
    ).limit(5).all()
    recent_jobs = db.query(models.Job).order_by(models.Job.posted_at.desc()).limit(3).all()
    recent_users = db.query(models.User).order_by(models.User.created_at.desc()).limit(3).all()

    recent_activity = []
    for a in recent_apps:
        job = a.job
        recent_activity.append({
            "type": "new_application",
            "message": f"{a.candidate_name or 'Someone'} applied to {job.title if job else 'a job'}",
            "timestamp": a.applied_at.isoformat() if a.applied_at else None,
        })
    for j in recent_jobs:
        recent_activity.append({
            "type": "new_job",
            "message": f"{j.company.name if j.company else ''} posted {j.title}",
            "timestamp": j.posted_at.isoformat() if j.posted_at else None,
        })
    for u in recent_users:
        recent_activity.append({
            "type": "new_user",
            "message": f"{u.name} registered as {u.role.value.capitalize()}",
            "timestamp": u.created_at.isoformat() if u.created_at else None,
        })

    # Weekly trend (last 7 days)
    weekly_trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = db.query(models.JobApplication).filter(
            func.date(models.JobApplication.applied_at) == day
        ).count()
        weekly_trend.append(count)

    # Jobs by industry
    industry_rows = db.query(
        models.Job.industry, func.count(models.Job.id)
    ).group_by(models.Job.industry).all()
    jobs_by_industry = {row[0]: row[1] for row in industry_rows}

    return success_response(data={
        "stats": {
            "totalUsers": total_users,
            "totalCandidates": total_candidates,
            "totalEmployers": total_employers,
            "totalJobs": total_jobs,
            "activeJobs": active_jobs,
            "totalApplications": total_applications,
            "newUsersToday": new_users_today,
            "newApplicationsToday": new_apps_today,
        },
        "recentActivity": sorted(recent_activity, key=lambda x: x["timestamp"] or "", reverse=True)[:10],
        "weeklyApplicationsTrend": weekly_trend,
        "jobsByIndustry": jobs_by_industry,
    })


@router.get("/users")
def list_users(
    q: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    query = db.query(models.User)
    if q:
        query = query.filter(
            models.User.name.ilike(f"%{q}%") | models.User.email.ilike(f"%{q}%")
        )
    if role:
        query = query.filter(models.User.role == role)
    if status:
        query = query.filter(models.User.status == status)

    total = query.count()
    users = query.offset((page - 1) * limit).limit(limit).all()

    items = []
    for u in users:
        initials = "".join(w[0].upper() for w in u.name.split()[:2]) if u.name else "??"
        if u.role == models.RoleEnum.CANDIDATE:
            app_count = db.query(models.JobApplication).filter(
                models.JobApplication.candidate_id == u.id
            ).count()
            stats = {"applicationsCount": app_count}
        else:
            job_count = db.query(models.Job).filter(models.Job.employer_id == u.id).count()
            stats = {"jobsPostedCount": job_count}

        items.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value,
            "status": u.status.value,
            "avatar": initials,
            "createdAt": u.created_at.isoformat() if u.created_at else None,
            "stats": stats,
        })

    return success_response(data=paginated_response(items, page, limit, total))


@router.patch("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    body: schemas.UserStatusUpdate,
    current_user: models.User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return error_response("NOT_FOUND", "User not found", 404)
    if user.id == current_user.id:
        return error_response("FORBIDDEN", "Cannot change your own status", 403)

    user.status = models.UserStatusEnum(body.status)
    db.commit()
    return success_response(message=f"User status updated to {body.status}")


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: models.User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return error_response("NOT_FOUND", "User not found", 404)
    if user.id == current_user.id:
        return error_response("FORBIDDEN", "Cannot delete yourself", 403)

    db.delete(user)
    db.commit()
    return success_response(message="User deleted successfully")


@router.get("/jobs")
def list_all_jobs(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    query = db.query(models.Job)
    if q:
        query = query.filter(models.Job.title.ilike(f"%{q}%"))
    if status == "active":
        query = query.filter(models.Job.is_active == True, models.Job.is_draft == False)
    elif status == "draft":
        query = query.filter(models.Job.is_draft == True)
    elif status == "closed":
        query = query.filter(models.Job.is_active == False)

    total = query.count()
    jobs = query.order_by(models.Job.posted_at.desc()).offset((page - 1) * limit).limit(limit).all()

    items = [{
        "id": j.id,
        "title": j.title,
        "company": j.company.name if j.company else "",
        "location": j.location,
        "type": j.type,
        "isActive": j.is_active,
        "isDraft": j.is_draft,
        "applicantsCount": j.applicants_count,
        "postedAt": j.posted_at.isoformat() if j.posted_at else None,
        "employer": {
            "id": j.employer_id,
            "name": j.employer.name if j.employer else "",
            "email": j.employer.email if j.employer else "",
        },
    } for j in jobs]

    return success_response(data=paginated_response(items, page, limit, total))


@router.delete("/jobs/{job_id}")
def admin_delete_job(
    job_id: str,
    current_user: models.User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return error_response("NOT_FOUND", "Job not found", 404)

    db.delete(job)
    db.commit()
    return success_response(message="Job deleted by admin")


@router.patch("/jobs/{job_id}/toggle")
def toggle_job_status(
    job_id: str,
    current_user: models.User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return error_response("NOT_FOUND", "Job not found", 404)

    job.is_active = not job.is_active
    db.commit()
    return success_response(data={"isActive": job.is_active})


@router.get("/reports")
def get_reports(
    period: str = Query("30d"),
    current_user: models.User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(period, 30)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Applications by status
    apps_by_status = {}
    for st in models.ApplicationStatusEnum:
        count = db.query(models.JobApplication).filter(
            models.JobApplication.status == st,
            models.JobApplication.applied_at >= since,
        ).count()
        apps_by_status[st.value] = count

    # Top industries
    industry_rows = db.query(
        models.Job.industry, func.count(models.Job.id)
    ).filter(models.Job.posted_at >= since).group_by(models.Job.industry).order_by(
        func.count(models.Job.id).desc()
    ).limit(5).all()
    top_industries = [{"industry": r[0], "count": r[1]} for r in industry_rows]

    # Top jobs by applicants
    top_jobs_rows = db.query(models.Job).order_by(models.Job.applicants_count.desc()).limit(5).all()
    top_jobs = [{"title": j.title, "applicants": j.applicants_count} for j in top_jobs_rows]

    # New users per day
    new_users = []
    new_apps = []
    today = datetime.now(timezone.utc).date()
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        uc = db.query(models.User).filter(func.date(models.User.created_at) == day).count()
        ac = db.query(models.JobApplication).filter(func.date(models.JobApplication.applied_at) == day).count()
        new_users.append({"date": str(day), "count": uc})
        new_apps.append({"date": str(day), "count": ac})

    return success_response(data={
        "period": period,
        "applicationsByStatus": apps_by_status,
        "topIndustries": top_industries,
        "topJobs": top_jobs,
        "newUsersPerDay": new_users,
        "applicationsPerDay": new_apps,
    })
