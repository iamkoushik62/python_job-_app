# KougoTech Jobs — API Endpoints Reference

> **Base URL:** `http://localhost:8000/v1`
> **Docs UI:** `http://localhost:8000/docs`
> **Content-Type:** `application/json` (except file upload routes)
> **Auth Header:** `Authorization: Bearer <access_token>`

---

## Table of Contents

1. [Standard Response Shapes](#standard-response-shapes)
2. [Auth APIs](#1-auth-apis)
3. [Jobs APIs](#2-jobs-apis)
4. [Applications APIs](#3-applications-apis)
5. [Candidate APIs](#4-candidate-apis)
6. [Employer APIs](#5-employer-apis)
7. [Admin APIs](#6-admin-apis)
8. [Error Codes Reference](#error-codes-reference)
9. [Quick Endpoint Summary](#quick-endpoint-summary)

---

## Standard Response Shapes

### ✅ Success
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { }
}
```

### 📋 Paginated List
```json
{
  "success": true,
  "data": {
    "items": [ ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 134,
      "totalPages": 7,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

### ❌ Error
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      { "field": "email", "message": "Invalid email format" }
    ]
  }
}
```

---

## 1. Auth APIs

### `POST /auth/register`
Register a new Candidate or Employer account.

**Request Body:**
```json
{
  "name": "Rahul Sharma",
  "email": "rahul@example.com",
  "phone": "+91 9876543210",
  "password": "MyStr0ng!Pass",
  "confirmPassword": "MyStr0ng!Pass",
  "role": "CANDIDATE",
  "agreeToTerms": true
}
```

> `role` must be `"CANDIDATE"` or `"EMPLOYER"` — never `"ADMIN"`.

**Response `201`:**
```json
{
  "success": true,
  "message": "Account created successfully",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Rahul Sharma",
      "email": "rahul@example.com",
      "role": "CANDIDATE",
      "status": "ACTIVE",
      "createdAt": "2026-02-25T10:00:00.000000+00:00"
    },
    "tokens": {
      "accessToken": "eyJhbGci...",
      "refreshToken": "eyJhbGci...",
      "expiresIn": 900
    }
  }
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `409` | `DUPLICATE_EMAIL` — email already registered |
| `400` | `VALIDATION_ERROR` — passwords don't match / weak password / invalid role |

---

### `POST /auth/login`
Login with email and password.

**Request Body:**
```json
{
  "email": "rahul@example.com",
  "password": "MyStr0ng!Pass",
  "rememberMe": true
}
```

**Response `200`:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Rahul Sharma",
      "email": "rahul@example.com",
      "role": "CANDIDATE",
      "status": "ACTIVE",
      "profileImage": null,
      "companyId": null
    },
    "tokens": {
      "accessToken": "eyJhbGci...",
      "refreshToken": "eyJhbGci...",
      "expiresIn": 900
    }
  }
}
```

> Flutter uses `role` to navigate: `CANDIDATE → /candidate/home`, `EMPLOYER → /employer/home`, `ADMIN → /admin/home`

**Error Responses:**

| Code | Scenario |
|------|----------|
| `401` | `INVALID_CREDENTIALS` — wrong email or password |
| `403` | `FORBIDDEN` — account suspended |

---

### `POST /auth/refresh`
Exchange a refresh token for a new access token.

**Request Body:**
```json
{
  "refreshToken": "eyJhbGci..."
}
```

**Response `200`:**
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "accessToken": "eyJhbGci...",
    "expiresIn": 900
  }
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `401` | `TOKEN_INVALID` — token expired, revoked, or malformed |

---

### `POST /auth/forgot-password`
Send a password reset link to the given email.

**Request Body:**
```json
{
  "email": "rahul@example.com"
}
```

**Response `200`:**
```json
{
  "success": true,
  "message": "Password reset link sent to rahul@example.com"
}
```

> Always returns `200` even if the email doesn't exist (prevents email enumeration).

---

### `POST /auth/reset-password`
Reset password using the token from the email link.

**Request Body:**
```json
{
  "token": "abc123def456...",
  "password": "NewStr0ng!Pass",
  "confirmPassword": "NewStr0ng!Pass"
}
```

**Response `200`:**
```json
{
  "success": true,
  "message": "Password reset successfully"
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `400` | `TOKEN_INVALID` — token expired or already used |
| `404` | `NOT_FOUND` — user not found |

---

### `POST /auth/logout`
🔒 **Protected.** Revoke the refresh token.

**Request Body:**
```json
{
  "refreshToken": "eyJhbGci..."
}
```

**Response `200`:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 2. Jobs APIs

### `GET /jobs`
Public — browse and search all active jobs.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Full-text search on title / description |
| `type` | string | `Full-time` \| `Part-time` \| `Contract` \| `Remote` \| `Internship` \| `Freelance` |
| `location` | string | e.g. `Bangalore` |
| `industry` | string | e.g. `Technology` |
| `experience` | string | e.g. `Senior (5-8 years)` |
| `salaryMin` | number | Minimum salary in LPA |
| `page` | number | Page number (default: `1`) |
| `limit` | number | Items per page (default: `20`, max: `100`) |

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "job-uuid",
        "title": "Senior Flutter Developer",
        "company": "TechNova Solutions",
        "companyLogo": "TN",
        "location": "Bangalore, India",
        "salary": "₹18 - ₹28 LPA",
        "salaryMin": 18,
        "salaryMax": 28,
        "experience": "Senior (5-8 years)",
        "type": "Full-time",
        "industry": "Technology",
        "skills": ["Flutter", "Dart", "Firebase", "REST APIs"],
        "description": "We are looking for an experienced Flutter developer...",
        "applicantsCount": 47,
        "isSaved": false,
        "isApplied": false,
        "postedAt": "2026-02-23T09:00:00.000000+00:00",
        "timeAgo": "2d ago",
        "isActive": true,
        "employer": { "id": "emp-uuid", "name": "Priya Patel" },
        "companyDetails": {
          "id": "comp-uuid",
          "name": "TechNova Solutions",
          "isVerified": true,
          "industry": "Technology"
        }
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 134,
      "totalPages": 7,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

> `isSaved` and `isApplied` are `false` for unauthenticated requests.

---

### `GET /jobs/saved`
🔒 **Candidate only.** Get the logged-in candidate's saved jobs.

**Query Parameters:** `page`, `limit`

**Response `200`:** Same shape as `GET /jobs`.

---

### `GET /jobs/{job_id}`
Public — get full details of a single job.

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "job-uuid",
    "title": "Senior Flutter Developer",
    "company": "TechNova Solutions",
    "companyLogo": "TN",
    "location": "Bangalore, India",
    "salary": "₹18 - ₹28 LPA",
    "salaryMin": 18,
    "salaryMax": 28,
    "experience": "Senior (5-8 years)",
    "type": "Full-time",
    "industry": "Technology",
    "skills": ["Flutter", "Dart", "Firebase"],
    "description": "We are looking for an experienced Flutter developer...",
    "applicantsCount": 47,
    "isSaved": false,
    "isApplied": false,
    "postedAt": "2026-02-23T09:00:00.000000+00:00",
    "timeAgo": "2d ago",
    "isActive": true,
    "employer": { "id": "emp-uuid", "name": "Priya Patel" },
    "companyDetails": {
      "id": "comp-uuid",
      "name": "TechNova Solutions",
      "description": "A leading software company specialising in fintech.",
      "industry": "Technology",
      "location": "Bangalore, India",
      "website": "www.technova.com",
      "employeeCount": 750,
      "isVerified": true
    }
  }
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `404` | `NOT_FOUND` — job does not exist |

---

### `POST /jobs/{job_id}/save`
🔒 **Candidate only.** Toggle save / unsave a job.

**Response `200` — saved:**
```json
{
  "success": true,
  "message": "Job saved",
  "data": { "isSaved": true }
}
```

**Response `200` — unsaved:**
```json
{
  "success": true,
  "message": "Job unsaved",
  "data": { "isSaved": false }
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `404` | `NOT_FOUND` — job does not exist |

---

## 3. Applications APIs

### `POST /applications`
🔒 **Candidate only.** Submit a job application.

**Request:** `multipart/form-data`

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `jobId` | string | ✅ | Target job ID |
| `coverLetter` | string | ✅ | Min 50 characters |
| `name` | string | ✅ | Candidate full name |
| `email` | string | ✅ | Candidate email |
| `phone` | string | ✅ | Candidate phone |
| `resume` | file | ✅ | PDF/DOC/DOCX — max 5 MB |

**Response `201`:**
```json
{
  "success": true,
  "message": "Application submitted successfully",
  "data": {
    "id": "app-uuid",
    "jobId": "job-uuid",
    "jobTitle": "Senior Flutter Developer",
    "company": "TechNova Solutions",
    "companyLogo": "TN",
    "candidateId": "user-uuid",
    "candidateName": "Rahul Sharma",
    "candidateEmail": "rahul@example.com",
    "resumeUrl": "/files/resumes/user-uuid/abc123.pdf",
    "coverLetter": "I am excited to apply...",
    "status": "APPLIED",
    "appliedAt": "2026-02-25T09:00:00.000000+00:00",
    "location": "Bangalore, India",
    "salary": "₹18 - ₹28 LPA"
  }
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `400` | `INVALID_FILE_TYPE` — not PDF/DOC/DOCX |
| `400` | `VALIDATION_ERROR` — cover letter too short |
| `404` | `NOT_FOUND` — job not found or closed |
| `409` | `ALREADY_APPLIED` — already applied to this job |
| `413` | `FILE_TOO_LARGE` — file exceeds 5 MB |

---

### `GET /applications/my`
🔒 **Candidate only.** Get all applications submitted by the logged-in candidate.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter: `APPLIED` \| `SHORTLISTED` \| `HIRED` \| `REJECTED` |
| `page` | number | Default: `1` |
| `limit` | number | Default: `20` |

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "app-uuid",
        "jobId": "job-uuid",
        "jobTitle": "Backend Engineer (Python)",
        "company": "DataDriven Corp",
        "companyLogo": "DD",
        "status": "APPLIED",
        "appliedAt": "2026-02-24T09:00:00.000000+00:00",
        "location": "Hyderabad, India",
        "salary": "₹15 - ₹25 LPA",
        "resumeUrl": "/files/resumes/user-uuid/resume.pdf",
        "coverLetter": "I am excited to apply..."
      }
    ],
    "pagination": { "page": 1, "limit": 20, "total": 4, "totalPages": 1, "hasNext": false, "hasPrev": false }
  }
}
```

---

### `GET /applications/{app_id}`
🔒 **Candidate / Employer / Admin.** Get full details of one application.

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "app-uuid",
    "jobId": "job-uuid",
    "jobTitle": "Backend Engineer (Python)",
    "company": "DataDriven Corp",
    "companyLogo": "DD",
    "candidateId": "user-uuid",
    "candidateName": "Rahul Sharma",
    "candidateEmail": "rahul@example.com",
    "resumeUrl": "/files/resumes/user-uuid/resume.pdf",
    "coverLetter": "I am excited to apply for the Backend Engineer role...",
    "status": "APPLIED",
    "statusNote": null,
    "appliedAt": "2026-02-24T09:00:00.000000+00:00",
    "location": "Hyderabad, India",
    "salary": "₹15 - ₹25 LPA"
  }
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `403` | `FORBIDDEN` — not your application and not the job's employer |
| `404` | `NOT_FOUND` — application not found |

---

### `PATCH /applications/{app_id}/status`
🔒 **Employer / Admin.** Update an applicant's status.

**Request Body:**
```json
{
  "status": "SHORTLISTED",
  "statusNote": "Great profile, scheduling interview"
}
```

> `status` values: `APPLIED` | `SHORTLISTED` | `REJECTED` | `HIRED`

**Response `200`:**
```json
{
  "success": true,
  "message": "Status updated to Shortlisted",
  "data": {
    "id": "app-uuid",
    "status": "SHORTLISTED",
    "statusNote": "Great profile, scheduling interview",
    "updatedAt": "2026-02-25T10:30:00.000000+00:00"
  }
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `400` | `VALIDATION_ERROR` — invalid status value |
| `403` | `FORBIDDEN` — employer trying to update another employer's applicant |
| `404` | `NOT_FOUND` — application not found |

---

## 4. Candidate APIs

### `GET /candidates/profile`
🔒 **Candidate only.** Get the current candidate's full profile and stats.

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "user-uuid",
    "name": "Rahul Sharma",
    "email": "rahul@example.com",
    "phone": "+91 9876543210",
    "role": "CANDIDATE",
    "bio": "Passionate Flutter developer with 6 years of experience...",
    "location": "Bangalore, India",
    "website": "https://rahulsharma.dev",
    "linkedIn": "https://linkedin.com/in/rahulsharma",
    "skills": ["Flutter", "Dart", "Firebase", "REST APIs"],
    "resumeUrl": "/files/resumes/user-uuid/resume.pdf",
    "profileImage": null,
    "stats": {
      "totalApplied": 4,
      "shortlisted": 1,
      "hired": 1,
      "rejected": 1
    },
    "createdAt": "2024-01-12T00:00:00.000000+00:00"
  }
}
```

---

### `PUT /candidates/profile`
🔒 **Candidate only.** Update profile details.

**Request Body:**
```json
{
  "name": "Rahul Sharma",
  "phone": "+91 9876543210",
  "bio": "Passionate Flutter developer with 6 years of experience...",
  "location": "Bangalore, India",
  "website": "https://rahulsharma.dev",
  "linkedIn": "https://linkedin.com/in/rahulsharma",
  "skills": ["Flutter", "Dart", "Firebase", "REST APIs", "GetX", "BLoC"]
}
```

**Response `200`:**
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "data": {
    "id": "user-uuid",
    "name": "Rahul Sharma",
    "email": "rahul@example.com",
    "phone": "+91 9876543210",
    "bio": "Passionate Flutter developer...",
    "location": "Bangalore, India",
    "website": "https://rahulsharma.dev",
    "linkedIn": "https://linkedin.com/in/rahulsharma",
    "skills": ["Flutter", "Dart", "Firebase", "REST APIs", "GetX", "BLoC"],
    "updatedAt": "2026-02-25T10:00:00.000000+00:00"
  }
}
```

---

### `POST /candidates/profile/resume`
🔒 **Candidate only.** Upload or replace resume file.

**Request:** `multipart/form-data`

| Field | Type | Required | Notes |
|-------|------|:--------:|-------|
| `resume` | file | ✅ | PDF/DOC/DOCX — max 5 MB |

**Response `200`:**
```json
{
  "success": true,
  "message": "Resume uploaded successfully",
  "data": {
    "resumeUrl": "/files/resumes/user-uuid/abc456.pdf"
  }
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `400` | `INVALID_FILE_TYPE` — not PDF/DOC/DOCX |
| `413` | `FILE_TOO_LARGE` — exceeds 5 MB |

---

## 5. Employer APIs

### `GET /employer/jobs`
🔒 **Employer only.** List all jobs posted by this employer.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | `active` \| `draft` \| `closed` |
| `page` | number | Default: `1` |
| `limit` | number | Default: `20` |

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "job-uuid",
        "title": "Senior Flutter Developer",
        "location": "Bangalore, India",
        "type": "Full-time",
        "salary": "₹18 - ₹28 LPA",
        "applicantsCount": 47,
        "shortlistedCount": 12,
        "hiredCount": 3,
        "isActive": true,
        "isDraft": false,
        "postedAt": "2026-02-23T09:00:00.000000+00:00",
        "company": {
          "id": "comp-uuid",
          "name": "TechNova Solutions",
          "logo": "TN"
        }
      }
    ],
    "pagination": { "page": 1, "limit": 20, "total": 6, "totalPages": 1, "hasNext": false, "hasPrev": false }
  }
}
```

---

### `POST /employer/jobs`
🔒 **Employer only.** Post a new job.

**Request Body:**
```json
{
  "title": "Senior Flutter Developer",
  "description": "We are looking for an experienced Flutter developer...",
  "location": "Bangalore, India",
  "salaryMin": 18,
  "salaryMax": 28,
  "type": "Full-time",
  "experience": "Senior (5-8 years)",
  "industry": "Technology",
  "skills": ["Flutter", "Dart", "Firebase", "REST APIs"],
  "isDraft": false,
  "isRemote": false
}
```

> If `isDraft: true` — job is saved but **not publicly visible**.

**Response `201`:**
```json
{
  "success": true,
  "message": "Job posted successfully",
  "data": {
    "id": "new-job-uuid",
    "title": "Senior Flutter Developer",
    "description": "We are looking for an experienced Flutter developer...",
    "location": "Bangalore, India",
    "salary": "₹18 - ₹28 LPA",
    "salaryMin": 18,
    "salaryMax": 28,
    "type": "Full-time",
    "experience": "Senior (5-8 years)",
    "industry": "Technology",
    "skills": ["Flutter", "Dart", "Firebase", "REST APIs"],
    "isActive": true,
    "isDraft": false,
    "applicantsCount": 0,
    "postedAt": "2026-02-25T09:00:00.000000+00:00"
  }
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `403` | `FORBIDDEN` — employer has no company profile yet |

---

### `PUT /employer/jobs/{job_id}`
🔒 **Employer only.** Edit an existing job (own jobs only).

**Request Body:** Same as `POST /employer/jobs`

**Response `200`:** Same shape as create response with `message: "Job updated successfully"`.

**Error Responses:**

| Code | Scenario |
|------|----------|
| `404` | `NOT_FOUND` — job not found or not yours |

---

### `DELETE /employer/jobs/{job_id}`
🔒 **Employer only.** Delete a job posting.

**Response `200`:**
```json
{
  "success": true,
  "message": "Job deleted successfully"
}
```

---

### `PATCH /employer/jobs/{job_id}/close`
🔒 **Employer only.** Close a job (marks `isActive: false`).

**Response `200`:**
```json
{
  "success": true,
  "message": "Job closed",
  "data": { "isActive": false }
}
```

---

### `GET /employer/jobs/{job_id}/applicants`
🔒 **Employer only.** Get all applicants for a specific job.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | `APPLIED` \| `SHORTLISTED` \| `HIRED` \| `REJECTED` |
| `page` | number | Default: `1` |
| `limit` | number | Default: `20` |

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "job": { "id": "job-uuid", "title": "Senior Flutter Developer" },
    "items": [
      {
        "id": "app-uuid",
        "candidateId": "user-uuid",
        "candidateName": "Rahul Sharma",
        "candidateEmail": "rahul@example.com",
        "status": "APPLIED",
        "appliedAt": "2026-02-24T09:00:00.000000+00:00",
        "resumeUrl": "/files/resumes/user-uuid/resume.pdf",
        "coverLetter": "I am excited to apply..."
      }
    ],
    "counts": {
      "total": 47,
      "applied": 30,
      "shortlisted": 12,
      "hired": 3,
      "rejected": 2
    },
    "pagination": { "page": 1, "limit": 20, "total": 47, "totalPages": 3, "hasNext": true, "hasPrev": false }
  }
}
```

---

### `GET /employer/profile`
🔒 **Employer only.** Get employer user + company profile.

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "emp-uuid",
      "name": "Priya Patel",
      "email": "priya@technova.com",
      "role": "EMPLOYER"
    },
    "company": {
      "id": "comp-uuid",
      "name": "TechNova Solutions",
      "logo": "TN",
      "description": "A leading software company specialising in fintech...",
      "industry": "Technology",
      "location": "Bangalore, India",
      "website": "www.technova.com",
      "employeeCount": 750,
      "foundedYear": 2015,
      "headquarters": "Bangalore, India",
      "isVerified": true,
      "stats": {
        "jobsPosted": 18,
        "totalHired": 47,
        "averageRating": 0
      }
    }
  }
}
```

---

### `PUT /employer/profile`
🔒 **Employer only.** Create or update company profile.

**Request Body:**
```json
{
  "companyName": "TechNova Solutions",
  "description": "A leading software company specialising in fintech...",
  "industry": "Technology",
  "location": "Bangalore, India",
  "website": "www.technova.com",
  "employeeCount": 750,
  "foundedYear": 2015,
  "headquarters": "Bangalore, India"
}
```

> If the employer has **no company yet**, this creates one automatically and links it to the account.

**Response `200`:**
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "data": {
    "id": "comp-uuid",
    "name": "TechNova Solutions",
    "logo": "TN",
    "description": "A leading software company specialising in fintech...",
    "industry": "Technology",
    "location": "Bangalore, India",
    "website": "www.technova.com",
    "employeeCount": 750,
    "foundedYear": 2015,
    "headquarters": "Bangalore, India",
    "isVerified": false
  }
}
```

---

## 6. Admin APIs

### `GET /admin/dashboard`
🔒 **Admin only.** Platform-wide statistics and recent activity.

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "stats": {
      "totalUsers": 2840,
      "totalCandidates": 2200,
      "totalEmployers": 630,
      "totalJobs": 412,
      "activeJobs": 287,
      "totalApplications": 8934,
      "newUsersToday": 24,
      "newApplicationsToday": 156
    },
    "recentActivity": [
      {
        "type": "new_application",
        "message": "Rahul Sharma applied to Senior Flutter Developer",
        "timestamp": "2026-02-25T09:05:00.000000+00:00"
      },
      {
        "type": "new_job",
        "message": "TechNova Solutions posted DevOps Engineer",
        "timestamp": "2026-02-25T08:45:00.000000+00:00"
      },
      {
        "type": "new_user",
        "message": "Priya Patel registered as Employer",
        "timestamp": "2026-02-25T08:30:00.000000+00:00"
      }
    ],
    "weeklyApplicationsTrend": [45, 62, 78, 91, 54, 38, 156],
    "jobsByIndustry": {
      "Technology": 145,
      "Finance": 67,
      "Design": 38
    }
  }
}
```

---

### `GET /admin/users`
🔒 **Admin only.** List all users with filtering.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Search by name or email |
| `role` | string | `CANDIDATE` \| `EMPLOYER` \| `ADMIN` |
| `status` | string | `ACTIVE` \| `PENDING` \| `SUSPENDED` |
| `page` | number | Default: `1` |
| `limit` | number | Default: `20` |

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "user-uuid",
        "name": "Rahul Sharma",
        "email": "rahul@example.com",
        "role": "CANDIDATE",
        "status": "ACTIVE",
        "avatar": "RS",
        "createdAt": "2024-01-12T00:00:00.000000+00:00",
        "stats": { "applicationsCount": 4 }
      },
      {
        "id": "emp-uuid",
        "name": "Priya Patel",
        "email": "priya@technova.com",
        "role": "EMPLOYER",
        "status": "ACTIVE",
        "avatar": "PP",
        "createdAt": "2024-02-05T00:00:00.000000+00:00",
        "stats": { "jobsPostedCount": 18 }
      }
    ],
    "pagination": { "page": 1, "limit": 20, "total": 2840, "totalPages": 142, "hasNext": true, "hasPrev": false }
  }
}
```

---

### `PATCH /admin/users/{user_id}/status`
🔒 **Admin only.** Change a user's status.

**Request Body:**
```json
{
  "status": "SUSPENDED",
  "reason": "Violation of terms of service"
}
```

> `status` values: `ACTIVE` | `PENDING` | `SUSPENDED`

**Response `200`:**
```json
{
  "success": true,
  "message": "User status updated to SUSPENDED"
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `403` | `FORBIDDEN` — admin cannot change their own status |
| `404` | `NOT_FOUND` — user not found |

---

### `DELETE /admin/users/{user_id}`
🔒 **Admin only.** Permanently delete a user and all their data.

**Response `200`:**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

**Error Responses:**

| Code | Scenario |
|------|----------|
| `403` | `FORBIDDEN` — admin cannot delete themselves |
| `404` | `NOT_FOUND` — user not found |

---

### `GET /admin/jobs`
🔒 **Admin only.** List all jobs on the platform.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Search by title |
| `status` | string | `active` \| `draft` \| `closed` |
| `page` | number | Default: `1` |
| `limit` | number | Default: `20` |

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "job-uuid",
        "title": "Senior Flutter Developer",
        "company": "TechNova Solutions",
        "location": "Bangalore, India",
        "type": "Full-time",
        "isActive": true,
        "isDraft": false,
        "applicantsCount": 47,
        "postedAt": "2026-02-23T09:00:00.000000+00:00",
        "employer": {
          "id": "emp-uuid",
          "name": "Priya Patel",
          "email": "priya@technova.com"
        }
      }
    ],
    "pagination": { "page": 1, "limit": 20, "total": 412, "totalPages": 21, "hasNext": true, "hasPrev": false }
  }
}
```

---

### `DELETE /admin/jobs/{job_id}`
🔒 **Admin only.** Force-delete any job.

**Response `200`:**
```json
{
  "success": true,
  "message": "Job deleted by admin"
}
```

---

### `PATCH /admin/jobs/{job_id}/toggle`
🔒 **Admin only.** Toggle a job's `isActive` status.

**Response `200`:**
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { "isActive": false }
}
```

---

### `GET /admin/reports`
🔒 **Admin only.** Get platform analytics for a given period.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `period` | string | `7d` \| `30d` \| `90d` (default: `30d`) |

**Response `200`:**
```json
{
  "success": true,
  "data": {
    "period": "30d",
    "applicationsByStatus": {
      "APPLIED": 4200,
      "SHORTLISTED": 1800,
      "HIRED": 600,
      "REJECTED": 2334
    },
    "topIndustries": [
      { "industry": "Technology", "count": 145 },
      { "industry": "Finance", "count": 67 }
    ],
    "topJobs": [
      { "title": "UI/UX Designer", "applicants": 134 },
      { "title": "Product Manager", "applicants": 89 }
    ],
    "newUsersPerDay": [
      { "date": "2026-02-01", "count": 18 },
      { "date": "2026-02-02", "count": 24 }
    ],
    "applicationsPerDay": [
      { "date": "2026-02-01", "count": 120 },
      { "date": "2026-02-02", "count": 156 }
    ]
  }
}
```

---

## Error Codes Reference

| HTTP | Code | Description |
|------|------|-------------|
| `400` | `VALIDATION_ERROR` | Request body/query validation failed |
| `400` | `TOKEN_INVALID` | Reset/refresh token invalid or expired |
| `401` | `UNAUTHORIZED` | No token provided |
| `401` | `INVALID_CREDENTIALS` | Wrong email or password |
| `401` | `TOKEN_EXPIRED` | JWT access token expired |
| `403` | `FORBIDDEN` | Authenticated but insufficient role/permissions |
| `404` | `NOT_FOUND` | Resource does not exist |
| `409` | `DUPLICATE_EMAIL` | Email already registered |
| `409` | `ALREADY_APPLIED` | Candidate already applied to this job |
| `413` | `FILE_TOO_LARGE` | Upload exceeds 5 MB |
| `400` | `INVALID_FILE_TYPE` | Only PDF/DOC/DOCX allowed |
| `500` | `INTERNAL_SERVER_ERROR` | Unexpected server error |

---

## Quick Endpoint Summary

| Method | Endpoint | 🔒 Auth | Role |
|--------|----------|:-------:|------|
| `POST` | `/auth/register` | ❌ | — |
| `POST` | `/auth/login` | ❌ | — |
| `POST` | `/auth/refresh` | ❌ | — |
| `POST` | `/auth/forgot-password` | ❌ | — |
| `POST` | `/auth/reset-password` | ❌ | — |
| `POST` | `/auth/logout` | ✅ | Any |
| `GET` | `/jobs` | Optional | Any |
| `GET` | `/jobs/saved` | ✅ | Candidate |
| `GET` | `/jobs/{job_id}` | Optional | Any |
| `POST` | `/jobs/{job_id}/save` | ✅ | Candidate |
| `POST` | `/applications` | ✅ | Candidate |
| `GET` | `/applications/my` | ✅ | Candidate |
| `GET` | `/applications/{app_id}` | ✅ | Candidate / Employer / Admin |
| `PATCH` | `/applications/{app_id}/status` | ✅ | Employer / Admin |
| `GET` | `/candidates/profile` | ✅ | Candidate |
| `PUT` | `/candidates/profile` | ✅ | Candidate |
| `POST` | `/candidates/profile/resume` | ✅ | Candidate |
| `GET` | `/employer/jobs` | ✅ | Employer |
| `POST` | `/employer/jobs` | ✅ | Employer |
| `PUT` | `/employer/jobs/{job_id}` | ✅ | Employer |
| `DELETE` | `/employer/jobs/{job_id}` | ✅ | Employer |
| `PATCH` | `/employer/jobs/{job_id}/close` | ✅ | Employer |
| `GET` | `/employer/jobs/{job_id}/applicants` | ✅ | Employer |
| `GET` | `/employer/profile` | ✅ | Employer |
| `PUT` | `/employer/profile` | ✅ | Employer |
| `GET` | `/admin/dashboard` | ✅ | Admin |
| `GET` | `/admin/users` | ✅ | Admin |
| `PATCH` | `/admin/users/{user_id}/status` | ✅ | Admin |
| `DELETE` | `/admin/users/{user_id}` | ✅ | Admin |
| `GET` | `/admin/jobs` | ✅ | Admin |
| `DELETE` | `/admin/jobs/{job_id}` | ✅ | Admin |
| `PATCH` | `/admin/jobs/{job_id}/toggle` | ✅ | Admin |
| `GET` | `/admin/reports` | ✅ | Admin |

---

*Generated: 2026-02-25 · KougoTech Jobs Backend v1.0.0*
