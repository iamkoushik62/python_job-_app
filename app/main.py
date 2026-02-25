import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.config import settings
from app.routers import auth, jobs, applications, candidates, employer, admin

# ─── Create DB tables ────────────────────────────
Base.metadata.create_all(bind=engine)

# ─── Create upload directory ─────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# ─── App instance ────────────────────────────────
app = FastAPI(
    title="KougoTech Jobs API",
    description="Backend REST API for the KougoTech Job Application Flutter app.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to your Flutter app domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static files (uploaded resumes) ─────────────
app.mount("/files", StaticFiles(directory=settings.UPLOAD_DIR), name="files")

# ─── API v1 prefix ───────────────────────────────
API_PREFIX = "/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(jobs.router, prefix=API_PREFIX)
app.include_router(applications.router, prefix=API_PREFIX)
app.include_router(candidates.router, prefix=API_PREFIX)
app.include_router(employer.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


# ─── Global Exception Handler ────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
            },
        },
    )


# ─── Health check ────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", tags=["Health"])
def root():
    return {
        "name": "KougoTech Jobs API",
        "version": "1.0.0",
        "docs": "/docs",
    }
