# KougoTech Jobs — Backend API Documentation

> **Purpose:** This document is the single source of truth for building the backend server that powers the KougoTech Job Application Flutter app. Every API endpoint, JSON request/response shape, database schema, and business rule is derived directly from the Flutter app's screen code and data models.

---

## Table of Contents

1. [Tech Stack Recommendation](#1-tech-stack-recommendation)
2. [Project Structure](#2-project-structure)
3. [Database Schema](#3-database-schema)
4. [Authentication & Authorization](#4-authentication--authorization)
5. [API Base URL & Common Conventions](#5-api-base-url--common-conventions)
6. [Auth APIs](#6-auth-apis)
7. [Jobs APIs](#7-jobs-apis)
8. [Applications APIs](#8-applications-apis)
9. [Candidate Profile APIs](#9-candidate-profile-apis)
10. [Employer APIs](#10-employer-apis)
11. [Admin APIs](#11-admin-apis)
12. [File Upload](#12-file-upload)
13. [Role & Permission Matrix](#13-role--permission-matrix)
14. [Error Response Format](#14-error-response-format)
15. [Enums & Constants Reference](#15-enums--constants-reference)
16. [Flutter Integration Notes](#16-flutter-integration-notes)

---

## 1. Tech Stack Recommendation

| Layer | Recommended | Alternatives |
|-------|------------|--------------|
| Runtime | **Node.js 20 LTS** | Python (FastAPI/Django), Laravel |
| Framework | **Express.js** | NestJS, Fastify |
| Database | **PostgreSQL 16** | MySQL 8, MongoDB |
| ORM | **Prisma** | Sequelize, TypeORM |
| Auth | **JWT (access + refresh tokens)** | Supabase Auth, Firebase Auth |
| File Storage | **AWS S3 / Cloudflare R2** | Firebase Storage |
| Caching | **Redis** | — |
| Email | **Nodemailer + SMTP / Resend** | SendGrid |
| Deployment | **Railway / Render / AWS EC2** | — |

---

## 2. Project Structure

```
backend/
├── src/
│   ├── config/
│   │   ├── database.js         # DB connection (Prisma)
│   │   ├── jwt.js              # JWT helpers
│   │   └── s3.js               # File storage config
│   ├── middleware/
│   │   ├── auth.js             # JWT verification middleware
│   │   ├── roleGuard.js        # Role-based access control
│   │   └── errorHandler.js     # Global error handler
│   ├── routes/
│   │   ├── auth.routes.js
│   │   ├── jobs.routes.js
│   │   ├── applications.routes.js
│   │   ├── candidates.routes.js
│   │   ├── employers.routes.js
│   │   └── admin.routes.js
│   ├── controllers/
│   │   ├── auth.controller.js
│   │   ├── jobs.controller.js
│   │   ├── applications.controller.js
│   │   ├── candidates.controller.js
│   │   ├── employers.controller.js
│   │   └── admin.controller.js
│   ├── services/
│   │   ├── email.service.js
│   │   ├── upload.service.js
│   │   └── notification.service.js
│   └── app.js
├── prisma/
│   └── schema.prisma
├── .env
└── package.json
```

---

## 3. Database Schema

### Prisma Schema (`prisma/schema.prisma`)

```prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// ────────────────────────────────────────────────
// Users — covers Candidates, Employers, and Admins
// ────────────────────────────────────────────────
model User {
  id           String   @id @default(cuid())
  name         String
  email        String   @unique
  phone        String?
  passwordHash String
  role         Role     @default(CANDIDATE)
  status       UserStatus @default(ACTIVE)
  bio          String?
  location     String?
  website      String?
  linkedIn     String?
  resumeUrl    String?
  profileImage String?
  skills       String[] @default([])
  rememberToken String?
  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt

  // Relations
  company      Company?          @relation(fields: [companyId], references: [id])
  companyId    String?
  applications JobApplication[]
  savedJobs    SavedJob[]
  jobs         Job[]             // Jobs posted (Employer role)
}

enum Role {
  CANDIDATE
  EMPLOYER
  ADMIN
}

enum UserStatus {
  ACTIVE
  PENDING
  SUSPENDED
}

// ────────────────────────────────────────────────
// Company — linked to an Employer user
// ────────────────────────────────────────────────
model Company {
  id            String  @id @default(cuid())
  name          String
  logo          String?           // Initials or URL
  description   String?
  industry      String
  location      String
  website       String?
  employeeCount Int?
  foundedYear   Int?
  headquarters  String?
  isVerified    Boolean @default(false)
  createdAt     DateTime @default(now())
  updatedAt     DateTime @updatedAt

  // Relations
  users         User[]
  jobs          Job[]
}

// ────────────────────────────────────────────────
// Job — posted by an Employer
// ────────────────────────────────────────────────
model Job {
  id              String   @id @default(cuid())
  title           String
  description     String
  location        String
  salaryMin       Int?
  salaryMax       Int?
  salaryDisplay   String?            // e.g. "₹18 - ₹28 LPA"
  type            JobType  @default(FULL_TIME)
  experience      String             // e.g. "Senior (5-8 years)"
  industry        String
  skills          String[] @default([])
  isActive        Boolean  @default(true)
  isDraft         Boolean  @default(false)
  applicantsCount Int      @default(0)
  postedAt        DateTime @default(now())
  updatedAt       DateTime @updatedAt

  // Relations
  employer        User    @relation(fields: [employerId], references: [id])
  employerId      String
  company         Company @relation(fields: [companyId], references: [id])
  companyId       String
  applications    JobApplication[]
  savedBy         SavedJob[]
}

enum JobType {
  FULL_TIME
  PART_TIME
  CONTRACT
  REMOTE
  INTERNSHIP
  FREELANCE
}

// ────────────────────────────────────────────────
// Job Application — submitted by a Candidate
// ────────────────────────────────────────────────
model JobApplication {
  id            String            @id @default(cuid())
  coverLetter   String
  resumeUrl     String
  status        ApplicationStatus @default(APPLIED)
  statusNote    String?           // Optional employer note on status change
  appliedAt     DateTime          @default(now())
  updatedAt     DateTime          @updatedAt

  // Relations
  job           Job    @relation(fields: [jobId], references: [id])
  jobId         String
  candidate     User   @relation(fields: [candidateId], references: [id])
  candidateId   String
}

enum ApplicationStatus {
  APPLIED
  SHORTLISTED
  REJECTED
  HIRED
}

// ────────────────────────────────────────────────
// Saved Jobs — Candidate bookmarks
// ────────────────────────────────────────────────
model SavedJob {
  id        String   @id @default(cuid())
  savedAt   DateTime @default(now())

  user      User @relation(fields: [userId], references: [id])
  userId    String
  job       Job  @relation(fields: [jobId], references: [id])
  jobId     String

  @@unique([userId, jobId])
}

// ────────────────────────────────────────────────
// Password Reset Tokens
// ────────────────────────────────────────────────
model PasswordResetToken {
  id        String   @id @default(cuid())
  email     String
  token     String   @unique
  expiresAt DateTime
  used      Boolean  @default(false)
  createdAt DateTime @default(now())
}
```

---

## 4. Authentication & Authorization

### JWT Strategy

- **Access Token** — expires in `15 minutes`
- **Refresh Token** — expires in `30 days`
- Both are returned on login/register
- Every protected API requires: `Authorization: Bearer <access_token>`

### Token Payload (JWT Claim)

```json
{
  "sub": "user_cuid",
  "email": "user@example.com",
  "role": "CANDIDATE",
  "iat": 1700000000,
  "exp": 1700000900
}
```

### Role Guard Logic

- `CANDIDATE` — can view/save/apply to jobs, manage own profile & applications
- `EMPLOYER` — can post/manage own jobs, view and update their applicants
- `ADMIN` — can manage all users, all jobs, view platform analytics

---

## 5. API Base URL & Common Conventions

```
Base URL:  https://api.kougotech.com/v1
```

### Common Headers

```
Content-Type: application/json
Authorization: Bearer <token>       ← required for all protected routes
```

### Standard Success Response

```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

### Paginated List Response

```json
{
  "success": true,
  "data": {
    "items": [ ... ],
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

---

## 6. Auth APIs

### POST `/auth/register`

Registers a new user (Candidate or Employer). Admin accounts are created directly in DB.

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

> **role** must be `"CANDIDATE"` or `"EMPLOYER"`. Never `"ADMIN"`.

**Success Response `201`:**
```json
{
  "success": true,
  "message": "Account created successfully",
  "data": {
    "user": {
      "id": "clxyz123",
      "name": "Rahul Sharma",
      "email": "rahul@example.com",
      "role": "CANDIDATE",
      "status": "ACTIVE",
      "createdAt": "2025-02-25T09:00:00.000Z"
    },
    "tokens": {
      "accessToken": "eyJhbGci...",
      "refreshToken": "eyJhbGci...",
      "expiresIn": 900
    }
  }
}
```

---

### POST `/auth/login`

**Request Body:**
```json
{
  "email": "rahul@example.com",
  "password": "MyStr0ng!Pass",
  "rememberMe": true
}
```

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": {
      "id": "clxyz123",
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

> Flutter uses the `role` field to decide which home screen to navigate to:
> - `CANDIDATE` → `/candidate/home`
> - `EMPLOYER` → `/employer/home`
> - `ADMIN` → `/admin/home`

---

### POST `/auth/refresh`

Get a new access token using the refresh token.

**Request Body:**
```json
{
  "refreshToken": "eyJhbGci..."
}
```

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGci...",
    "expiresIn": 900
  }
}
```

---

### POST `/auth/forgot-password`

Sends a password reset link to the given email.

**Request Body:**
```json
{
  "email": "rahul@example.com"
}
```

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Password reset link sent to rahul@example.com"
}
```

> Always return `200` (even if email doesn't exist) to prevent email enumeration.

---

### POST `/auth/reset-password`

**Request Body:**
```json
{
  "token": "reset_token_from_email_link",
  "password": "NewStr0ng!Pass",
  "confirmPassword": "NewStr0ng!Pass"
}
```

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Password reset successfully"
}
```

---

### POST `/auth/logout`

🔒 Protected.

**Request Body:**
```json
{
  "refreshToken": "eyJhbGci..."
}
```

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 7. Jobs APIs

### GET `/jobs`

Public — anyone can browse jobs. Supports filtering and search.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Full-text search on title, company, skills |
| `type` | string | `Full-time`, `Part-time`, `Remote`, `Contract`, `Internship` |
| `location` | string | e.g. `Bangalore` |
| `industry` | string | e.g. `Technology` |
| `experience` | string | e.g. `Senior (5-8 years)` |
| `salaryMin` | number | Minimum salary (in LPA) |
| `page` | number | Page number (default: 1) |
| `limit` | number | Items per page (default: 20) |

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "clxyz123",
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
        "skills": ["Flutter", "Dart", "Firebase", "REST APIs", "GetX", "BLoC"],
        "description": "We are looking for an experienced Flutter developer...",
        "applicantsCount": 47,
        "isSaved": false,
        "isApplied": false,
        "postedAt": "2025-02-23T09:00:00.000Z",
        "timeAgo": "2d ago",
        "isActive": true,
        "employer": {
          "id": "emp1",
          "name": "Priya Patel"
        },
        "companyDetails": {
          "id": "comp1",
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

> **Note:** `isSaved` and `isApplied` are only accurate when token is provided. Without token, both are `false`.

---

### GET `/jobs/:id`

Get full details of a single job.

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "clxyz123",
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
    "skills": ["Flutter", "Dart", "Firebase", "REST APIs", "GetX", "BLoC"],
    "description": "We are looking for an experienced Flutter developer to join our dynamic team...",
    "applicantsCount": 47,
    "postedAt": "2025-02-23T09:00:00.000Z",
    "timeAgo": "2d ago",
    "isSaved": false,
    "isApplied": false,
    "isActive": true,
    "companyDetails": {
      "id": "comp1",
      "name": "TechNova Solutions",
      "description": "A leading software company specialising in fintech and enterprise solutions.",
      "industry": "Technology",
      "location": "Bangalore, India",
      "website": "www.technova.com",
      "employeeCount": 750,
      "isVerified": true
    }
  }
}
```

---

### POST `/jobs/:id/save`

🔒 Candidate only. Toggle save/unsave a job.

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Job saved",
  "data": {
    "isSaved": true
  }
}
```

---

### GET `/jobs/saved`

🔒 Candidate only. Get all saved jobs.

**Response:** Same paginated list as `GET /jobs`.

---

## 8. Applications APIs

### POST `/applications`

🔒 Candidate only. Submit a job application.

**Request:** `multipart/form-data` (because resume is a file)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `jobId` | string | ✅ | ID of the job being applied to |
| `coverLetter` | string | ✅ | Cover letter text (min 50 chars) |
| `name` | string | ✅ | Candidate full name |
| `email` | string | ✅ | Candidate email |
| `phone` | string | ✅ | Candidate phone |
| `resume` | file | ✅ | PDF/DOC/DOCX, max 5MB |

**Success Response `201`:**
```json
{
  "success": true,
  "message": "Application submitted successfully",
  "data": {
    "id": "app_clxyz",
    "jobId": "clxyz123",
    "jobTitle": "Senior Flutter Developer",
    "company": "TechNova Solutions",
    "companyLogo": "TN",
    "candidateId": "c1",
    "candidateName": "Rahul Sharma",
    "candidateEmail": "rahul@example.com",
    "resumeUrl": "https://s3.amazonaws.com/kougotech/resumes/rahul_resume.pdf",
    "coverLetter": "I am excited to apply...",
    "status": "APPLIED",
    "appliedAt": "2025-02-25T09:00:00.000Z",
    "location": "Bangalore, India",
    "salary": "₹18 - ₹28 LPA"
  }
}
```

> After submission, the server should:
> 1. Upload resume to S3 and store the URL
> 2. Increment the job's `applicantsCount` by 1
> 3. Send a confirmation email to the candidate

---

### GET `/applications/my`

🔒 Candidate only. Get the logged-in candidate's own applications.

**Query Parameters:** `page`, `limit`, `status` (APPLIED|SHORTLISTED|HIRED|REJECTED)

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "app1",
        "jobId": "4",
        "jobTitle": "Backend Engineer (Python)",
        "company": "DataDriven Corp",
        "companyLogo": "DD",
        "status": "APPLIED",
        "appliedAt": "2025-02-24T09:00:00.000Z",
        "location": "Hyderabad, India",
        "salary": "₹15 - ₹25 LPA",
        "resumeUrl": "https://s3...",
        "coverLetter": "I am excited to apply..."
      },
      {
        "id": "app2",
        "jobId": "1",
        "jobTitle": "Senior Flutter Developer",
        "company": "TechNova Solutions",
        "companyLogo": "TN",
        "status": "SHORTLISTED",
        "appliedAt": "2025-02-18T09:00:00.000Z",
        "location": "Bangalore, India",
        "salary": "₹18 - ₹28 LPA",
        "resumeUrl": "https://s3...",
        "coverLetter": "With 6 years of Flutter experience..."
      }
    ],
    "pagination": { "page": 1, "limit": 20, "total": 4, "totalPages": 1, "hasNext": false, "hasPrev": false }
  }
}
```

---

### GET `/applications/:id`

🔒 Candidate or Employer or Admin. Get a single application's details.

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "app1",
    "jobId": "4",
    "jobTitle": "Backend Engineer (Python)",
    "company": "DataDriven Corp",
    "companyLogo": "DD",
    "candidateId": "c1",
    "candidateName": "Rahul Sharma",
    "candidateEmail": "rahul@example.com",
    "resumeUrl": "https://s3.amazonaws.com/kougotech/resumes/rahul_resume.pdf",
    "coverLetter": "I am excited to apply for the Backend Engineer role...",
    "status": "APPLIED",
    "statusNote": null,
    "appliedAt": "2025-02-24T09:00:00.000Z",
    "location": "Hyderabad, India",
    "salary": "₹15 - ₹25 LPA"
  }
}
```

---

### PATCH `/applications/:id/status`

🔒 Employer only (for their job applicants).

Update an applicant's status. This is used from the Employer's "Applicant Detail" screen.

**Request Body:**
```json
{
  "status": "SHORTLISTED",
  "statusNote": "Great profile, scheduling interview"
}
```

> **Allowed values for `status`:** `APPLIED`, `SHORTLISTED`, `REJECTED`, `HIRED`

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Status updated to Shortlisted",
  "data": {
    "id": "app1",
    "status": "SHORTLISTED",
    "statusNote": "Great profile, scheduling interview",
    "updatedAt": "2025-02-25T10:30:00.000Z"
  }
}
```

> After updating status, send an email notification to the candidate.

---

## 9. Candidate Profile APIs

### GET `/candidates/profile`

🔒 Candidate only. Get the currently logged-in candidate's profile.

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "id": "c1",
    "name": "Rahul Sharma",
    "email": "rahul@example.com",
    "phone": "+91 9876543210",
    "role": "CANDIDATE",
    "bio": "Passionate Flutter developer with 6 years of experience...",
    "location": "Bangalore, India",
    "website": "https://rahulsharma.dev",
    "linkedIn": "https://linkedin.com/in/rahulsharma",
    "skills": ["Flutter", "Dart", "Firebase", "REST APIs"],
    "resumeUrl": "https://s3.amazonaws.com/kougotech/resumes/rahul_resume.pdf",
    "profileImage": null,
    "stats": {
      "totalApplied": 4,
      "shortlisted": 1,
      "hired": 1,
      "rejected": 1
    },
    "createdAt": "2024-01-12T00:00:00.000Z"
  }
}
```

---

### PUT `/candidates/profile`

🔒 Candidate only. Update profile details.

**Request Body:**
```json
{
  "name": "Rahul Sharma",
  "phone": "+91 9876543210",
  "bio": "Passionate Flutter developer with 6 years of experience building production apps for iOS and Android.",
  "location": "Bangalore, India",
  "website": "https://rahulsharma.dev",
  "linkedIn": "https://linkedin.com/in/rahulsharma",
  "skills": ["Flutter", "Dart", "Firebase", "REST APIs", "GetX", "BLoC"]
}
```

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Profile updated successfully",
  "data": {
    "id": "c1",
    "name": "Rahul Sharma",
    "email": "rahul@example.com",
    "phone": "+91 9876543210",
    "bio": "Passionate Flutter developer...",
    "location": "Bangalore, India",
    "website": "https://rahulsharma.dev",
    "linkedIn": "https://linkedin.com/in/rahulsharma",
    "skills": ["Flutter", "Dart", "Firebase", "REST APIs", "GetX", "BLoC"],
    "updatedAt": "2025-02-25T10:00:00.000Z"
  }
}
```

---

### POST `/candidates/profile/resume`

🔒 Candidate only. Upload/replace resume file.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `resume` | file | ✅ | PDF/DOC/DOCX, max 5MB |

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Resume uploaded successfully",
  "data": {
    "resumeUrl": "https://s3.amazonaws.com/kougotech/resumes/rahul_resume_v2.pdf"
  }
}
```

---

## 10. Employer APIs

### GET `/employer/jobs`

🔒 Employer only. Get all jobs posted by this employer.

**Query Parameters:** `page`, `limit`, `status` (`active` | `draft` | `closed`)

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "clxyz123",
        "title": "Senior Flutter Developer",
        "location": "Bangalore, India",
        "type": "Full-time",
        "salary": "₹18 - ₹28 LPA",
        "applicantsCount": 47,
        "shortlistedCount": 12,
        "hiredCount": 3,
        "isActive": true,
        "isDraft": false,
        "postedAt": "2025-02-23T09:00:00.000Z",
        "company": {
          "id": "comp1",
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

### POST `/employer/jobs`

🔒 Employer only. Post a new job.

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

> **isDraft:** If `true`, job is saved but not publicly visible. If `false`, job is live immediately.

**Success Response `201`:**
```json
{
  "success": true,
  "message": "Job posted successfully",
  "data": {
    "id": "new_job_id",
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
    "postedAt": "2025-02-25T09:00:00.000Z"
  }
}
```

---

### PUT `/employer/jobs/:id`

🔒 Employer only. Edit an existing job (only employer's own jobs).

**Request Body:** Same as `POST /employer/jobs`.

**Success Response `200`:** Same shape as create response.

---

### DELETE `/employer/jobs/:id`

🔒 Employer only. Delete a job posting.

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Job deleted successfully"
}
```

---

### PATCH `/employer/jobs/:id/close`

🔒 Employer only. Close a job (mark `isActive: false`).

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Job closed",
  "data": { "isActive": false }
}
```

---

### GET `/employer/jobs/:jobId/applicants`

🔒 Employer only. Get all applicants for a specific job.

**Query Parameters:** `status` (APPLIED|SHORTLISTED|HIRED|REJECTED), `page`, `limit`

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "job": {
      "id": "clxyz123",
      "title": "Senior Flutter Developer"
    },
    "items": [
      {
        "id": "app1",
        "candidateId": "c1",
        "candidateName": "Rahul Sharma",
        "candidateEmail": "rahul@example.com",
        "status": "APPLIED",
        "appliedAt": "2025-02-24T09:00:00.000Z",
        "resumeUrl": "https://s3.amazonaws.com/...",
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

### GET `/employer/profile`

🔒 Employer only. Get company + employer profile.

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "emp1",
      "name": "Priya Patel",
      "email": "priya@technova.com",
      "role": "EMPLOYER"
    },
    "company": {
      "id": "comp1",
      "name": "TechNova Solutions",
      "logo": "TN",
      "description": "TechNova Solutions is a leading software company specialising in fintech...",
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
        "averageRating": 4.8
      }
    }
  }
}
```

---

### PUT `/employer/profile`

🔒 Employer only. Update company profile.

**Request Body:**
```json
{
  "companyName": "TechNova Solutions",
  "description": "TechNova Solutions is a leading...",
  "industry": "Technology",
  "location": "Bangalore, India",
  "website": "www.technova.com",
  "employeeCount": 750,
  "foundedYear": 2015,
  "headquarters": "Bangalore, India"
}
```

**Success Response `200`:** Returns updated company object.

---

## 11. Admin APIs

### GET `/admin/dashboard`

🔒 Admin only. Platform-wide statistics.

**Success Response `200`:**
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
        "timestamp": "2025-02-25T09:05:00.000Z"
      },
      {
        "type": "new_job",
        "message": "TechNova Solutions posted DevOps Engineer",
        "timestamp": "2025-02-25T08:45:00.000Z"
      },
      {
        "type": "new_user",
        "message": "Priya Patel registered as Employer",
        "timestamp": "2025-02-25T08:30:00.000Z"
      }
    ],
    "weeklyApplicationsTrend": [45, 62, 78, 91, 54, 38, 156],
    "jobsByIndustry": {
      "Technology": 145,
      "Finance": 67,
      "Design": 38,
      "HR": 22,
      "Marketing": 15
    }
  }
}
```

---

### GET `/admin/users`

🔒 Admin only. Get all users with filtering.

**Query Parameters:** `q` (search by name/email), `role` (CANDIDATE|EMPLOYER|ADMIN), `status` (ACTIVE|PENDING|SUSPENDED), `page`, `limit`

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "1",
        "name": "Rahul Sharma",
        "email": "rahul@example.com",
        "role": "CANDIDATE",
        "status": "ACTIVE",
        "avatar": "RS",
        "createdAt": "2024-01-12T00:00:00.000Z",
        "stats": {
          "applicationsCount": 4
        }
      },
      {
        "id": "2",
        "name": "Priya Patel",
        "email": "priya@technova.com",
        "role": "EMPLOYER",
        "status": "ACTIVE",
        "avatar": "PP",
        "createdAt": "2024-02-05T00:00:00.000Z",
        "stats": {
          "jobsPostedCount": 18
        }
      },
      {
        "id": "3",
        "name": "Amit Kumar",
        "email": "amit@financeflow.com",
        "role": "EMPLOYER",
        "status": "PENDING",
        "avatar": "AK",
        "createdAt": "2024-03-20T00:00:00.000Z",
        "stats": {
          "jobsPostedCount": 0
        }
      }
    ],
    "pagination": { "page": 1, "limit": 20, "total": 2840, "totalPages": 142, "hasNext": true, "hasPrev": false }
  }
}
```

---

### PATCH `/admin/users/:id/status`

🔒 Admin only. Change a user's status.

**Request Body:**
```json
{
  "status": "SUSPENDED",
  "reason": "Violation of terms of service"
}
```

> **Allowed status values:** `ACTIVE`, `PENDING`, `SUSPENDED`

**Success Response `200`:**
```json
{
  "success": true,
  "message": "User status updated to SUSPENDED"
}
```

---

### DELETE `/admin/users/:id`

🔒 Admin only. Permanently delete a user.

**Success Response `200`:**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

---

### GET `/admin/jobs`

🔒 Admin only. Get all jobs on the platform.

**Query Parameters:** `q`, `status` (active|draft|closed), `page`, `limit`

**Success Response `200`:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "clxyz123",
        "title": "Senior Flutter Developer",
        "company": "TechNova Solutions",
        "location": "Bangalore, India",
        "type": "Full-time",
        "isActive": true,
        "isDraft": false,
        "applicantsCount": 47,
        "postedAt": "2025-02-23T09:00:00.000Z",
        "employer": {
          "id": "emp1",
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

### DELETE `/admin/jobs/:id`

🔒 Admin only. Force-delete any job.

**Success Response `200`:**
```json
{
  "success": true,
  "message": "Job deleted by admin"
}
```

---

### PATCH `/admin/jobs/:id/toggle`

🔒 Admin only. Toggle a job's active status.

**Success Response `200`:**
```json
{
  "success": true,
  "data": { "isActive": false }
}
```

---

### GET `/admin/reports`

🔒 Admin only. Get analytics data.

**Query Parameters:** `period` (`7d`, `30d`, `90d`)

**Success Response `200`:**
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
      { "date": "2025-02-01", "count": 18 },
      { "date": "2025-02-02", "count": 24 }
    ],
    "applicationsPerDay": [
      { "date": "2025-02-01", "count": 120 },
      { "date": "2025-02-02", "count": 156 }
    ]
  }
}
```

---

## 12. File Upload

All file uploads use `multipart/form-data`. Files are stored on **AWS S3** (or Cloudflare R2).

### Resume Upload Rules
- **Accepted types:** `application/pdf`, `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- **Max size:** 5 MB
- **Storage path:** `s3://kougotech-bucket/resumes/{userId}/{timestamp}_{filename}`

### S3 Upload Flow (Backend)

```js
// Using @aws-sdk/client-s3
const uploadResume = async (file, userId) => {
  const filename = `${userId}/${Date.now()}_${file.originalname}`;
  const command = new PutObjectCommand({
    Bucket: process.env.S3_BUCKET,
    Key: `resumes/${filename}`,
    Body: file.buffer,
    ContentType: file.mimetype,
  });
  await s3Client.send(command);
  return `https://${process.env.S3_BUCKET}.s3.amazonaws.com/resumes/${filename}`;
};
```

---

## 13. Role & Permission Matrix

| Action | Candidate | Employer | Admin |
|--------|:---------:|:--------:|:-----:|
| Browse/Search jobs | ✅ | ✅ | ✅ |
| View job detail | ✅ | ✅ | ✅ |
| Save a job | ✅ | ❌ | ❌ |
| Apply to a job | ✅ | ❌ | ❌ |
| View own applications | ✅ | ❌ | ❌ |
| Post a job | ❌ | ✅ | ❌ |
| Edit own jobs | ❌ | ✅ | ❌ |
| View job applicants | ❌ | ✅ (own jobs) | ✅ (all) |
| Update applicant status | ❌ | ✅ (own jobs) | ✅ (all) |
| Edit own profile | ✅ | ✅ | ❌ |
| Manage all users | ❌ | ❌ | ✅ |
| Delete any job | ❌ | ❌ | ✅ |
| View admin dashboard | ❌ | ❌ | ✅ |
| View platform reports | ❌ | ❌ | ✅ |

---

## 14. Error Response Format

All errors follow this consistent JSON format:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      { "field": "email", "message": "Invalid email format" },
      { "field": "password", "message": "Password must be at least 8 characters" }
    ]
  }
}
```

### HTTP Status Codes Used

| Code | Meaning |
|------|---------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request / Validation Error |
| `401` | Unauthorized (token missing/invalid) |
| `403` | Forbidden (wrong role) |
| `404` | Resource Not Found |
| `409` | Conflict (e.g. email already registered) |
| `413` | File too large |
| `500` | Internal Server Error |

### Common Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `INVALID_CREDENTIALS` | Wrong email or password |
| `TOKEN_EXPIRED` | JWT access token expired |
| `TOKEN_INVALID` | JWT is malformed or tampered |
| `UNAUTHORIZED` | Login required |
| `FORBIDDEN` | Insufficient role permissions |
| `NOT_FOUND` | Resource does not exist |
| `DUPLICATE_EMAIL` | Email already registered |
| `ALREADY_APPLIED` | Candidate already applied to this job |
| `FILE_TOO_LARGE` | Upload exceeds 5MB |
| `INVALID_FILE_TYPE` | Only PDF/DOC/DOCX allowed |

---

## 15. Enums & Constants Reference

These values are directly from the Flutter `AppConstants` class and must match exactly in the backend:

### Job Types (JobType enum)
```
Full-time
Part-time
Contract
Remote
Internship
Freelance
```

### Experience Levels
```
Fresher (0-1 year)
Junior (1-3 years)
Mid-level (3-5 years)
Senior (5-8 years)
Lead (8-12 years)
Principal (12+ years)
```

### Industries
```
Technology
Finance
Healthcare
Education
Marketing
Design
HR
Operations
Sales
Legal
```

### Application Statuses (ApplicationStatus enum)
```
APPLIED      → label: "Applied"
SHORTLISTED  → label: "Shortlisted"
REJECTED     → label: "Rejected"
HIRED        → label: "Hired"
```

### User Roles (Role enum)
```
CANDIDATE  → const: "candidate"
EMPLOYER   → const: "employer"
ADMIN      → const: "admin"
```

### User Statuses (UserStatus enum)
```
ACTIVE
PENDING
SUSPENDED
```

---

## 16. Flutter Integration Notes

These notes describe how the Flutter app expects to call each API so the integration is seamless.

### Base URL Setup (Flutter)
```dart
// lib/core/constants/app_constants.dart — add this:
static const String baseUrl = 'https://api.kougotech.com/v1';
```

### HTTP Client (Recommended: `dio` package)
```yaml
# pubspec.yaml
dependencies:
  dio: ^5.4.0
  shared_preferences: ^2.2.0     # For storing tokens locally
```

### Authentication Flow (Flutter)

1. On login success → store `accessToken` + `refreshToken` in `SharedPreferences`
2. Add `dio` interceptor to attach `Authorization: Bearer <token>` to every request
3. On `401` response → call `/auth/refresh`, retry original request
4. On refresh failure → navigate to login screen

### Route Navigation After Login

```dart
// Flutter main.dart login callback logic:
switch (response['data']['user']['role']) {
  case 'CANDIDATE': Navigator.pushReplacementNamed(context, AppRoutes.candidateHome);
  case 'EMPLOYER':  Navigator.pushReplacementNamed(context, AppRoutes.employerHome);
  case 'ADMIN':     Navigator.pushReplacementNamed(context, AppRoutes.adminHome);
}
```

### Job Model Mapping (Flutter ↔ API)

| Flutter Field | API JSON Key | Notes |
|--------------|--------------|-------|
| `id` | `id` | — |
| `title` | `title` | — |
| `company` | `company` | — |
| `companyLogo` | `companyLogo` | 2-letter initials string |
| `location` | `location` | — |
| `salary` | `salary` | Display string e.g. `₹18 - ₹28 LPA` |
| `experience` | `experience` | Full string form |
| `type` | `type` | Full string form (`Full-time`) |
| `description` | `description` | Multiline text |
| `skills` | `skills` | `List<String>` |
| `industry` | `industry` | — |
| `postedAt` | `postedAt` | ISO 8601 `DateTime` |
| `isSaved` | `isSaved` | boolean |
| `isApplied` | `isApplied` | boolean |
| `applicantsCount` | `applicantsCount` | integer |

### Application Model Mapping

| Flutter Field | API JSON Key | Notes |
|--------------|--------------|-------|
| `id` | `id` | — |
| `jobId` | `jobId` | — |
| `jobTitle` | `jobTitle` | — |
| `company` | `company` | — |
| `companyLogo` | `companyLogo` | 2-letter initials |
| `candidateId` | `candidateId` | — |
| `candidateName` | `candidateName` | — |
| `candidateEmail` | `candidateEmail` | — |
| `resumeUrl` | `resumeUrl` | Full S3 URL |
| `coverLetter` | `coverLetter` | — |
| `status` | `status` | `APPLIED` / `SHORTLISTED` / `REJECTED` / `HIRED` |
| `appliedAt` | `appliedAt` | ISO 8601 `DateTime` |
| `location` | `location` | nullable |
| `salary` | `salary` | nullable |

---

## Quick API Summary

| Method | Endpoint | Auth | Role |
|--------|----------|------|------|
| POST | `/auth/register` | ❌ | — |
| POST | `/auth/login` | ❌ | — |
| POST | `/auth/refresh` | ❌ | — |
| POST | `/auth/forgot-password` | ❌ | — |
| POST | `/auth/reset-password` | ❌ | — |
| POST | `/auth/logout` | ✅ | Any |
| GET | `/jobs` | Optional | Any |
| GET | `/jobs/:id` | Optional | Any |
| POST | `/jobs/:id/save` | ✅ | Candidate |
| GET | `/jobs/saved` | ✅ | Candidate |
| POST | `/applications` | ✅ | Candidate |
| GET | `/applications/my` | ✅ | Candidate |
| GET | `/applications/:id` | ✅ | Any |
| PATCH | `/applications/:id/status` | ✅ | Employer |
| GET | `/candidates/profile` | ✅ | Candidate |
| PUT | `/candidates/profile` | ✅ | Candidate |
| POST | `/candidates/profile/resume` | ✅ | Candidate |
| GET | `/employer/jobs` | ✅ | Employer |
| POST | `/employer/jobs` | ✅ | Employer |
| PUT | `/employer/jobs/:id` | ✅ | Employer |
| DELETE | `/employer/jobs/:id` | ✅ | Employer |
| PATCH | `/employer/jobs/:id/close` | ✅ | Employer |
| GET | `/employer/jobs/:id/applicants` | ✅ | Employer |
| GET | `/employer/profile` | ✅ | Employer |
| PUT | `/employer/profile` | ✅ | Employer |
| GET | `/admin/dashboard` | ✅ | Admin |
| GET | `/admin/users` | ✅ | Admin |
| PATCH | `/admin/users/:id/status` | ✅ | Admin |
| DELETE | `/admin/users/:id` | ✅ | Admin |
| GET | `/admin/jobs` | ✅ | Admin |
| DELETE | `/admin/jobs/:id` | ✅ | Admin |
| PATCH | `/admin/jobs/:id/toggle` | ✅ | Admin |
| GET | `/admin/reports` | ✅ | Admin |

---

*Generated on 2026-02-25 from the KougoTech Flutter app source code.*
