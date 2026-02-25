-- ============================================================
--  KougoTech Jobs — Full MariaDB Schema
--  Run once:  mysql -u root -p < init_db.sql
-- ============================================================

-- ── 1. Create & select database ──────────────────────────────
CREATE DATABASE IF NOT EXISTS kougotech_jobs
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE kougotech_jobs;

-- ── 2. Drop tables in safe order (FK aware) ──────────────────
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS refresh_tokens;
DROP TABLE IF EXISTS password_reset_tokens;
DROP TABLE IF EXISTS saved_jobs;
DROP TABLE IF EXISTS job_applications;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS companies;
SET FOREIGN_KEY_CHECKS = 1;

-- ── 3. companies ─────────────────────────────────────────────
CREATE TABLE companies (
    id              VARCHAR(36)     NOT NULL PRIMARY KEY,
    name            VARCHAR(255)    NOT NULL,
    logo            VARCHAR(10)     NULL COMMENT '2-letter initials e.g. TN',
    description     TEXT            NULL,
    industry        VARCHAR(100)    NOT NULL,
    location        VARCHAR(255)    NOT NULL,
    website         VARCHAR(500)    NULL,
    employee_count  INT             NULL,
    founded_year    INT             NULL,
    headquarters    VARCHAR(255)    NULL,
    is_verified     TINYINT(1)      NOT NULL DEFAULT 0,
    created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                                             ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 4. users ─────────────────────────────────────────────────
CREATE TABLE users (
    id              VARCHAR(36)     NOT NULL PRIMARY KEY,
    name            VARCHAR(255)    NOT NULL,
    email           VARCHAR(255)    NOT NULL,
    phone           VARCHAR(50)     NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    role            ENUM('CANDIDATE','EMPLOYER','ADMIN')
                                    NOT NULL DEFAULT 'CANDIDATE',
    status          ENUM('ACTIVE','PENDING','SUSPENDED')
                                    NOT NULL DEFAULT 'ACTIVE',
    bio             TEXT            NULL,
    location        VARCHAR(255)    NULL,
    website         VARCHAR(500)    NULL,
    linked_in       VARCHAR(500)    NULL,
    resume_url      VARCHAR(1000)   NULL,
    profile_image   VARCHAR(1000)   NULL,
    skills          JSON            NULL COMMENT 'Array of skill strings',
    remember_token  VARCHAR(255)    NULL,
    company_id      VARCHAR(36)     NULL,
    created_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at      DATETIME(6)     NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                                             ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uq_users_email (email),
    INDEX      idx_users_role   (role),
    INDEX      idx_users_status (status),
    INDEX      idx_users_company (company_id),

    CONSTRAINT fk_users_company
        FOREIGN KEY (company_id) REFERENCES companies (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 5. jobs ──────────────────────────────────────────────────
CREATE TABLE jobs (
    id               VARCHAR(36)    NOT NULL PRIMARY KEY,
    title            VARCHAR(255)   NOT NULL,
    description      TEXT           NOT NULL,
    location         VARCHAR(255)   NOT NULL,
    salary_min       INT            NULL COMMENT 'In LPA',
    salary_max       INT            NULL COMMENT 'In LPA',
    salary_display   VARCHAR(100)   NULL COMMENT 'e.g. ₹18 - ₹28 LPA',
    type             VARCHAR(50)    NOT NULL DEFAULT 'Full-time'
                                    COMMENT 'Full-time|Part-time|Contract|Remote|Internship|Freelance',
    experience       VARCHAR(100)   NOT NULL
                                    COMMENT 'e.g. Senior (5-8 years)',
    industry         VARCHAR(100)   NOT NULL,
    skills           JSON           NULL COMMENT 'Array of skill strings',
    is_active        TINYINT(1)     NOT NULL DEFAULT 1,
    is_draft         TINYINT(1)     NOT NULL DEFAULT 0,
    applicants_count INT            NOT NULL DEFAULT 0,
    employer_id      VARCHAR(36)    NOT NULL,
    company_id       VARCHAR(36)    NOT NULL,
    posted_at        DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at       DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                                             ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_jobs_employer  (employer_id),
    INDEX idx_jobs_company   (company_id),
    INDEX idx_jobs_is_active (is_active),
    INDEX idx_jobs_is_draft  (is_draft),
    INDEX idx_jobs_industry  (industry),
    INDEX idx_jobs_posted_at (posted_at),
    FULLTEXT INDEX ft_jobs_search (title, description),

    CONSTRAINT fk_jobs_employer
        FOREIGN KEY (employer_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 6. job_applications ──────────────────────────────────────
CREATE TABLE job_applications (
    id               VARCHAR(36)    NOT NULL PRIMARY KEY,
    job_id           VARCHAR(36)    NOT NULL,
    candidate_id     VARCHAR(36)    NOT NULL,
    cover_letter     TEXT           NOT NULL,
    resume_url       VARCHAR(1000)  NOT NULL,
    status           ENUM('APPLIED','SHORTLISTED','REJECTED','HIRED')
                                    NOT NULL DEFAULT 'APPLIED',
    status_note      TEXT           NULL,
    -- Denormalised candidate snapshot (at time of apply)
    candidate_name   VARCHAR(255)   NULL,
    candidate_email  VARCHAR(255)   NULL,
    candidate_phone  VARCHAR(50)    NULL,
    applied_at       DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at       DATETIME(6)    NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                                             ON UPDATE CURRENT_TIMESTAMP(6),

    INDEX idx_apps_job       (job_id),
    INDEX idx_apps_candidate (candidate_id),
    INDEX idx_apps_status    (status),
    INDEX idx_apps_applied   (applied_at),

    CONSTRAINT fk_apps_job
        FOREIGN KEY (job_id) REFERENCES jobs (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_apps_candidate
        FOREIGN KEY (candidate_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 7. saved_jobs ────────────────────────────────────────────
CREATE TABLE saved_jobs (
    id       VARCHAR(36)  NOT NULL PRIMARY KEY,
    user_id  VARCHAR(36)  NOT NULL,
    job_id   VARCHAR(36)  NOT NULL,
    saved_at DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    UNIQUE KEY uq_saved_job (user_id, job_id),
    INDEX      idx_saved_user (user_id),
    INDEX      idx_saved_job  (job_id),

    CONSTRAINT fk_saved_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_saved_job
        FOREIGN KEY (job_id) REFERENCES jobs (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 8. password_reset_tokens ─────────────────────────────────
CREATE TABLE password_reset_tokens (
    id         VARCHAR(36)   NOT NULL PRIMARY KEY,
    email      VARCHAR(255)  NOT NULL,
    token      VARCHAR(255)  NOT NULL,
    expires_at DATETIME(6)   NOT NULL,
    used       TINYINT(1)    NOT NULL DEFAULT 0,
    created_at DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    UNIQUE KEY uq_prt_token (token),
    INDEX      idx_prt_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 9. refresh_tokens ────────────────────────────────────────
CREATE TABLE refresh_tokens (
    id         VARCHAR(36)   NOT NULL PRIMARY KEY,
    user_id    VARCHAR(36)   NOT NULL,
    token      VARCHAR(500)  NOT NULL,
    expires_at DATETIME(6)   NOT NULL,
    revoked    TINYINT(1)    NOT NULL DEFAULT 0,
    created_at DATETIME(6)   NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    UNIQUE KEY uq_rt_token  (token(255)),
    INDEX      idx_rt_user  (user_id),
    INDEX      idx_rt_revoked (revoked),

    CONSTRAINT fk_rt_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── 10. Seed: default Admin account ──────────────────────────
-- Password = Admin@1234  (bcrypt hash below — change in production!)
INSERT INTO users (
    id, name, email, password_hash, role, status, skills, created_at, updated_at
) VALUES (
    UUID(),
    'Admin',
    'admin@kougotech.com',
    '$2b$12$Wn.vdM8pM4A5mTqxsL9dGeYJRsJD9w3.eZ8d6n4yBHGi6GECXEm6G',
    'ADMIN',
    'ACTIVE',
    '[]',
    NOW(),
    NOW()
);

-- ── Done ─────────────────────────────────────────────────────
SELECT 'KougoTech Jobs schema created successfully.' AS status;

