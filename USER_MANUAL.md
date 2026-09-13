# QualiTrust Global — User Manual

## Qualification Verification System (QVS)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [How the System Works](#2-how-the-system-works)
3. [Accessing the System](#3-accessing-the-system)
4. [User Registration and Login](#4-user-registration-and-login)
5. [Dashboard](#5-dashboard)
6. [Managing Qualifications](#6-managing-qualifications)
7. [Verification Process](#7-verification-process)
8. [AI Fraud Detection](#8-ai-fraud-detection)
9. [Audit Logs](#9-audit-logs)
10. [User Roles and Permissions](#10-user-roles-and-permissions)
11. [Troubleshooting](#11-troubleshooting)
12. [Quick Start Guide](#12-quick-start-guide)
13. [Assignment Requirements Coverage](#13-assignment-requirements-coverage)

---

## 1. System Overview

QualiTrust Global is a DevOps-Enabled Qualification Verification System that uses blockchain hash chaining and AI-powered fraud detection to verify the authenticity of academic and professional qualifications.

### Key Features

- **Blockchain Verification**: Each qualification is assigned a SHA-256 cryptographic hash that is chained to the previous record, creating a tamper-evident ledger.
- **AI Fraud Detection**: Machine learning analysis examines credentials for anomalies, suspicious patterns, and risk indicators.
- **Audit Trail**: Every action (login, create, verify, update, delete, AI analysis) is logged with user, timestamp, and details.
- **Role-Based Access Control**: Three user roles (Admin, Verifier, Viewer) with different permission levels. Admin accounts cannot be self-registered.
- **Real-Time Monitoring**: Prometheus metrics endpoint for system health monitoring.

---

## 2. How the System Works

### Architecture Overview

The system follows a modern three-tier architecture:

```
┌──────────────────────────────────────────────────────┐
│                    Frontend (SPA)                     │
│         HTML + CSS + JavaScript (static/)             │
├──────────────────────────────────────────────────────┤
│                   Backend (FastAPI)                   │
│  Auth │ Qualifications │ Verification │ AI │ Audit    │
├──────────────────────────────────────────────────────┤
│              Data Layer (SQLAlchemy ORM)              │
│         SQLite Database (qualification_verification.db)│
└──────────────────────────────────────────────────────┘
```

### User Access and Roles

A **default admin** is auto-created on server startup (`admin@qvs.com` / `Admin1234!`). Public registration only allows **Viewer** or **Verifier** roles. Only an existing admin can create new admins via the **User Management** page.

| Role | What they can do |
|------|------------------|
| **Viewer** | View dashboard, qualifications, audit logs (read-only) |
| **Verifier** | Everything a Viewer can do, plus register, edit, delete, verify qualifications, and run AI analysis |
| **Admin** | Everything a Verifier can do, plus manage users (create, change roles, activate/deactivate) |

### Registering a Qualification

When a user registers a credential (e.g. "BSc Computer Science" from "Midlands State University"):

1. The data is saved to the database with status **Pending**
2. A **SHA-256 hash** is computed from all fields (title, type, institution, holder, dates, serial number, registration number)
3. The hash is **chained** to the previous qualification's hash, forming a lightweight blockchain
4. The credential now has a `credential_hash` and `previous_hash` stored in the database

**Key point**: For verification to pass later, the credential **must** include a **Serial Number** and **Registration Number**.

### Verification Process

A verifier can look up a credential in two ways:

1. **By ID** — for internal users who have access to the qualifications table
2. **By Serial / Reg No.** — for external verifiers (employers, verification bodies) who only have the transcript or certificate. They enter the serial number and registration number printed on the document, and the system finds the matching credential.

When you click **Verify**, the system runs **6 blockchain integrity checks**:

| # | Check | What it validates | How to pass |
|---|-------|-------------------|-------------|
| 1 | Has Credential Hash | A SHA-256 hash was assigned | Automatic (assigned on creation) |
| 2 | Hash Chain Valid | Recomputed hash matches stored hash and chain link to previous record is intact | Do not tamper with the database directly |
| 3 | Has Serial Number | A serial number exists | Enter one when registering |
| 4 | Has Registration Number | A registration number exists | Enter one when registering |
| 5 | Not Expired | Expiry date has not passed | Leave expiry empty or set a future date |
| 6 | Not Revoked | Status is not "revoked" | Do not manually revoke |

- **All 6 pass** → Status becomes **Verified** (green badge)
- **Any fail** → Status becomes **Rejected** (red badge), and the UI shows exactly which checks failed

A **Verification Record** is created each time, storing the method, result, hash, notes, and timestamp. You can view the full history of all verification attempts for any credential.

### AI Fraud Detection

The AI analysis engine scans the credential for anomalies and produces a risk score:

| Anomaly | Risk Added |
|---------|-----------|
| Missing serial number | +20 |
| Missing registration number | +15 |
| Expired qualification | +25 |
| No verifiable holder contact (no email AND no ID) | +15 |
| Suspicious institution name ("diploma mill", "acme", "fake", etc.) | +40 |
| Unclassified qualification type ("other") | +10 |

**Recommendation thresholds**:
- **Risk < 25** → `APPROVE` (low risk, credential appears legitimate)
- **Risk 25-49** → `REVIEW` (moderate risk, manual verification recommended)
- **Risk >= 50** → `REJECT` (high risk of fraud)

If an OpenAI API key is configured, it uses GPT-4o-mini for analysis. Otherwise, it falls back to the rule-based heuristic engine (works out of the box with no configuration).

### Audit Trail

Every action is automatically logged as an immutable audit entry:

- **Login** — when a user signs in
- **Create** — when a qualification is registered
- **Update** — when a qualification is edited
- **Delete** — when a qualification is soft-deleted
- **Verify** — when a verification is run
- **AI Analysis** — when an AI fraud scan is run

Each entry records: who did it (user ID), what entity was affected, a description, and a timestamp. The audit trail can be filtered by action type.

### Full Workflow

```
Admin creates account → Verifier logs in
                          ↓
              Registers credential (with serial + registration no.)
                          ↓
              System assigns SHA-256 blockchain hash
                          ↓
              Employer/Verifier looks up credential:
                ├─ By ID (internal)  ─┐
                └─ By Serial/Reg No.  ─┘ (from transcript)
                          ↓
              Selects method: Blockchain / Manual / AI Assisted / Automated
                          ↓
              6 blockchain checks run (+ AI fraud scan if AI method)
                          ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
              VERIFIED   REJECTED  INCONCLUSIVE
              (all pass)  (fail)   (AI says REVIEW)
                          ↓
              Verification record created with full details
                          ↓
              All actions logged in Audit Trail
```

---

## 3. Accessing the System

### Local Access

1. Ensure the server is running on your machine.
2. Open a web browser and navigate to: **http://127.0.0.1:8000**
3. The login page will appear.

### API Documentation

- Swagger UI (interactive API testing): **http://127.0.0.1:8000/docs**
- Health check endpoint: **http://127.0.0.1:8000/health**
- Prometheus metrics: **http://127.0.0.1:8000/metrics**

---

## 4. User Registration and Login

### Registering a New Account

1. On the login page, click the **Register** tab.
2. Fill in the following fields:
   - **Full Name**: Your complete name (e.g., John Doe)
   - **Email**: A valid email address (e.g., john@example.com)
   - **Password**: Minimum 8 characters
   - **Role**: Select one of:
     - **Viewer**: Can view qualifications and audit logs (read-only)
     - **Verifier**: Can register, verify, and manage qualifications
     - **Admin**: Not available via public registration. Only an existing admin can create admin accounts via the User Management page.
3. Click **Create Account**.
4. A success message will appear. Switch to the **Sign In** tab to log in.

### Default Admin Account

The system automatically creates a default admin account on startup:
- **Email**: admin@qvs.com
- **Password**: Admin1234!

This account has full admin privileges and should be used to create additional admin accounts as needed. Change the password after first login for production deployments.

### Logging In

1. Enter your **Email** and **Password**.
2. Click **Sign In**.
3. You will be redirected to the Dashboard.

### Logging Out

- Click the logout icon (arrow icon) in the bottom-left corner of the sidebar.

---

## 5. Dashboard

The Dashboard provides an at-a-glance overview of the system:

### Statistics Cards

- **Total Credentials**: The total number of registered qualifications in the system.
- **Verified**: Qualifications that have passed blockchain verification.
- **Pending**: Qualifications awaiting verification.
- **Rejected**: Qualifications that failed verification checks.

### Status Distribution Chart

- A donut chart showing the proportion of verified, pending, and rejected credentials.
- A legend below shows exact counts for each status.

### Recent Credentials Table

- Shows the 5 most recently registered qualifications.
- Click **View All** to go to the full Qualifications page.

---

## 6. Managing Qualifications

### Viewing Qualifications

1. Click **Qualifications** in the sidebar.
2. A table displays all qualifications with columns:
   - ID, Title, Holder, Institution, Type, Status, Date Issued, Actions

### Searching and Filtering

- **Search Box**: Type a title, holder name, registration number, or serial number to search.
- **Status Filter**: Select a status (Pending, Verified, Rejected, Revoked) to filter results.
- Search results update automatically as you type.

### Registering a New Qualification

1. Click the **Register Credential** button (top-right of the qualifications table).
2. A modal form will appear. Fill in the required fields (marked with *):

   | Field | Required | Description |
   |-------|----------|-------------|
   | Title | Yes | Name of the qualification (e.g., "BSc Computer Science") |
   | Qualification Type | Yes | Select: Degree, Diploma, Certificate, Professional Certification, or Other |
   | Issuing Institution | Yes | The institution that awarded the qualification |
   | Holder Name | Yes | Full name of the qualification holder |
   | Holder Email | No | Email address of the holder |
   | Holder ID Number | No | National ID or passport number of the holder |
   | Date Issued | Yes | Date the qualification was awarded |
   | Registration Number | No | Official registration number (recommended for verification) |
   | Serial Number | No | Unique serial number (recommended for verification) |
   | Description | No | Additional notes or details |
   | Certificate Document | No | Upload the actual certificate or transcript (PDF, JPG, PNG, GIF, BMP, WebP — max 10 MB) |

3. Click **Register Credential**.
4. The system will:
   - Save the qualification to the database
   - Compute a SHA-256 credential hash of all qualification data
   - Chain the hash to the previous qualification's hash (blockchain)
   - Set the status to **Pending**
   - Log the action in the audit trail

### Important Note for Verification

For a qualification to pass blockchain verification, it **must** have:
- A **Serial Number** (enter one when registering)
- A **Registration Number** (enter one when registering)
- No expired date (leave Date Expires empty or set a future date)

### Viewing a Qualification

1. Click the **View** button in the Actions column.
2. A modal displays all credential details including:
   - All form fields (title, type, institution, holder, etc.)
   - **Credential Hash** — the SHA-256 blockchain hash
   - **Previous Hash** — the hash of the previous credential in the chain (or "genesis" if it is the first)
   - **Document** — a link to view the uploaded certificate/transcript (if one was uploaded)
   - Registration and creation timestamps
3. Click **Verify This Credential** to jump straight to verification.

### Uploading a Certificate Document

When registering or editing a qualification, you can attach the actual certificate or transcript:

1. In the registration/edit form, scroll to the **Certificate / Transcript Document** section.
2. Click the upload area or drag and drop a file onto it.
3. Accepted formats: PDF, JPG, JPEG, PNG, GIF, BMP, WebP (max 10 MB).
4. The file name will appear in the upload area, confirming it is selected.
5. Submit the form — the document is uploaded and stored after the qualification is saved.
6. To view the document later, click **View** on the qualification and click the **View Document** link.
7. To replace an existing document, simply upload a new file when editing the qualification.

### Editing a Qualification

1. Click the **Edit** button in the Actions column.
2. The modal form appears pre-filled with the current values.
3. Make your changes and click **Save Changes**.
4. The system updates the record and logs the change in the audit trail.

### Deleting a Qualification

1. Click the **Delete** button in the Actions column.
2. Confirm the deletion in the popup.
3. The qualification is soft-deleted (hidden from lists but retained in the database for audit purposes).

---

## 7. Verification Process

### How Blockchain Verification Works

The system uses a lightweight blockchain mechanism:

1. **Hash Computation**: When a qualification is registered, a SHA-256 hash is computed from all its data fields (title, type, institution, holder, dates, serial number, registration number).

2. **Chain Linking**: Each qualification's hash is linked to the previous qualification's hash, forming a chain. If any record is tampered with, the chain breaks and verification fails.

3. **Six Verification Checks**: When you verify a qualification, the system runs these checks:

   | Check | Description | How to Pass |
   |-------|-------------|-------------|
   | Has Credential Hash | Qualification has a blockchain hash assigned | Automatic (assigned on creation) |
   | Hash Chain Valid | Recomputed hash matches stored hash and chain is intact | Automatic (do not modify records directly in the database) |
   | Has Serial Number | Qualification has a serial number | Enter a serial number when registering |
   | Has Registration Number | Qualification has a registration number | Enter a registration number when registering |
   | Not Expired | Qualification has not expired | Leave expiry date empty or set a future date |
   | Not Revoked | Qualification status is not "revoked" | Do not manually revoke the qualification |

4. **Result**: All 6 checks must pass for the qualification to be marked as **Verified**. If any check fails, the qualification is marked as **Rejected**.

### Two Ways to Look Up a Credential for Verification

The verification page provides two lookup modes, accessible via tabs at the top of the form:

#### By ID (for internal users)

1. Click the **By ID** tab.
2. Enter the **Qualification ID** (found in the qualifications table, or use the Verify button on any row).

#### By Serial / Reg No. (for external verifiers)

This is the primary method for employers and verification bodies who have a transcript or certificate but do not have access to the internal database:

1. Click the **By Serial / Reg No.** tab.
2. Enter the **Serial Number** exactly as printed on the transcript or certificate.
3. Enter the **Registration Number** exactly as printed on the transcript or certificate.
4. The system will look up the credential and display a preview showing the ID, title, holder, institution, and current status.
5. If no match is found, an error message will appear — double-check the numbers for typos.

### Verification Methods — What's the Difference?

| Method | What It Does | When to Use |
|--------|-------------|-------------|
| **Blockchain** | Runs the 6 SHA-256 hash chain integrity checks only | Standard verification — confirm the credential has not been tampered with |
| **Manual Review** | Same 6 blockchain checks, but recorded as human-reviewed in the audit trail | When a human has manually inspected the document alongside the blockchain check |
| **AI Assisted** | Blockchain checks **plus** AI fraud analysis (risk score, anomalies, recommendation) | When you want both tamper detection and fraud risk assessment in one step |
| **Automated** | Blockchain checks **plus** AI fraud analysis, recorded as fully automated (no human review) | For batch/automated verification pipelines with no human in the loop |

**Key difference**: `Blockchain` and `Manual Review` only check data integrity (has the record been tampered with?). `AI Assisted` and `Automated` additionally run the AI fraud engine to detect suspicious patterns (missing identifiers, fake institution names, expired credentials, etc.) and produce a risk score with an APPROVE/REVIEW/REJECT recommendation.

When using AI Assisted or Automated, the results panel will show an additional **AI Fraud Analysis** section with the recommendation, risk score, confidence score, and any detected anomalies.

### Performing a Verification

1. Navigate to the **Verify Credential** page from the sidebar.
2. Choose your lookup method:
   - **By ID**: Enter the Qualification ID directly.
   - **By Serial / Reg No.**: Enter the serial and registration numbers from the transcript. The system will look up the credential and show a preview.
3. Select a **Verification Method** (see table above).
4. Optionally add **Notes** for the verification record.
5. Optionally upload a **document** (certificate/transcript) for AI comparison — see below.
6. Click **Run Verification**.
7. The results panel will show:
   - **Authentic / Not Authentic** badge (green for pass, red for fail)
   - Verification hash (full SHA-256 value)
   - Individual check results (green checkmark = pass, red X = fail)
   - AI Fraud Analysis section (only for AI Assisted / Automated methods)
   - Document Match Analysis section (only when a document was uploaded)
   - Verification timestamp
   - Verification history for this qualification

### Verifying with a Document Upload (AI Document Comparison)

An employer or verification body can upload a scanned certificate or transcript during verification. The system will:

1. **Extract text** from the uploaded document (using pdfplumber for PDFs, pytesseract OCR for images).
2. **Compare against registered data** — checks if the holder name, institution, qualification title, serial number, and registration number on the document match what was registered in the system.
3. **Compare against the stored document** — if the university uploaded a document during registration, the system compares the two documents to detect if they are the same certificate.
4. **Produce a match score** (0-100%) with a recommendation:
   - **APPROVE** (>= 80%): Document matches registered data
   - **REVIEW** (50-79%): Partial match — manual review recommended
   - **REJECT** (< 50%): Document does not match — possible fraud

This detects the scenario where an attacker creates a fake certificate with the same serial and registration numbers but different qualification details (e.g., changing "BSc Computer Science" to "BSc Software Engineering"). Blockchain verification alone cannot detect this because the registered digital record was never tampered with — only the physical document is fake.

**How to use it:**
1. Look up the credential by ID or serial/reg number.
2. In the **Upload Document for AI Comparison** section, click the upload area or drag a file onto it.
3. Select a PDF or image of the certificate/transcript (max 10 MB).
4. Select a verification method (AI Assisted or Automated recommended for full analysis).
5. Click **Run Verification**.
6. The results panel will show a **Document Match Analysis** section with the match score, individual field comparisons, and (if a stored document exists) a document-to-document similarity score.

### Verification from the Qualifications Table

- Click the **Verify** button on any qualification row to jump to the Verification page with that qualification's ID pre-filled (switches to the By ID tab automatically).

### Why Verification May Show "Rejected"

If your qualification shows as "Rejected" after verification, check:

1. **Missing Serial Number**: You did not enter a serial number when registering the qualification.
2. **Missing Registration Number**: You did not enter a registration number when registering.
3. **Expired Qualification**: You set an expiry date that has already passed.
4. **Revoked Status**: The qualification was previously revoked.
5. **Hash Chain Broken**: The qualification data was modified directly in the database (not through the application).
6. **AI Recommendation was REJECT**: If using AI Assisted or Automated, the AI fraud engine detected high risk (risk score >= 50).

**Solution**: Register a new qualification with both a serial number and registration number, then verify it again.

### Verification Result Types

| Result | Meaning |
|--------|---------|
| **Verified** | All blockchain checks passed (and AI recommendation was APPROVE if AI method was used) |
| **Rejected** | One or more blockchain checks failed, or AI fraud engine detected high risk |
| **Inconclusive** | Blockchain checks passed but AI recommendation was REVIEW (moderate risk — manual follow-up needed) |

---

## 8. AI Fraud Detection

### Running AI Analysis

1. Navigate to the **AI Fraud Scan** page from the sidebar.
2. Enter the **Qualification ID**.
3. Click **Run AI Analysis**.

### What the AI Checks

The AI analysis engine examines the credential for:

- **Missing serial number** (+20 risk score)
- **Missing registration number** (+15 risk score)
- **Expired qualification** (+25 risk score)
- **No verifiable holder contact** (no email and no ID number) (+15 risk score)
- **Suspicious institution names** (e.g., "diploma mill", "acme", "test university", "fake") (+40 risk score)
- **Unclassified qualification type** (+10 risk score)

### Understanding the Results

- **Recommendation Banner**: Color-coded banner showing APPROVE (green), REVIEW (amber), or REJECT (red) with the full recommendation text.
- **Risk Score**: 0-100 (higher = more risky), displayed as an animated progress bar.
- **Confidence Score**: 0-100 (higher = more confident the assessment is correct).
- **Anomalies**: List of specific issues detected, each shown as a card with a warning icon.
- **Engine**: Shows whether the analysis used the heuristic rule-based engine or OpenAI.

**Recommendation thresholds**:
- **APPROVE** (risk < 25): Low risk, credential appears legitimate
- **REVIEW** (risk 25-49): Moderate risk, manual verification recommended
- **REJECT** (risk >= 50): High risk of fraud detected

### AI Analysis from the Qualifications Table

- Click the **AI** button on any qualification row to jump to the AI Analysis page with that qualification's ID pre-filled.

---

## 9. Audit Logs

### Viewing Audit Logs

1. Navigate to the **Audit Trail** page from the sidebar.
2. A table displays all logged actions with columns:
   - ID, Action, Entity, Description, User, Timestamp

### Filtering Audit Logs

- **Action Filter**: Filter by action type:
  - Create — qualification registration
  - Update — qualification edits
  - Delete — qualification deletions
  - Verify — verification runs
  - AI Analysis — AI fraud scans
  - Login — user sign-ins
- **Refresh Button**: Reload the latest audit logs.

### What Gets Logged

The system automatically logs:
- **Login** (action: "login") — when a user signs in
- **Qualification registration** (action: "create") — when a credential is registered
- **Qualification updates** (action: "update") — when a credential is edited
- **Qualification deletion** (action: "delete") — when a credential is soft-deleted
- **Verification attempts** (action: "verify") — when a verification is run
- **AI analysis runs** (action: "ai_analysis") — when an AI fraud scan is run

Each log entry records the user who performed the action, the entity affected, a description, and a timestamp.

---

## 10. User Roles and Permissions

| Feature | Viewer | Verifier | Admin |
|---------|--------|----------|-------|
| View Dashboard | Yes | Yes | Yes |
| View Qualifications | Yes | Yes | Yes |
| Register Qualification | No | Yes | Yes |
| Edit Qualification | No | Yes | Yes |
| Delete Qualification | No | Yes | Yes |
| Verify Qualification | No | Yes | Yes |
| Run AI Analysis | No | Yes | Yes |
| View Audit Logs | Yes | Yes | Yes |
| Register New Users (Viewer/Verifier) | Yes (self) | Yes (self) | Yes (self) |
| Register Admin Users | No | No | Yes |
| User Management Page | No | No | Yes |
| Create Users (any role) | No | No | Yes |
| Change User Roles | No | No | Yes |
| Deactivate/Activate Users | No | No | Yes |

### User Management (Admin Only)

Admins can manage all user accounts via the **User Management** page:

1. Click **User Management** in the sidebar (visible only to admins).
2. View all users with their roles, status, and creation date.
3. **Add User**: Click the **Add User** button to create a new user with any role (including admin).
4. **Change Role**: Use the dropdown in each row to change a user's role.
5. **Deactivate**: Click **Deactivate** to disable a user account (they will not be able to log in).
6. **Activate**: Click **Activate** to re-enable a deactivated account.
7. Admins cannot deactivate their own account.

---

## 11. Troubleshooting

### Login Failed

- Ensure you are using the correct email and password.
- Passwords are case-sensitive.
- If you forgot your password, register a new account or contact an admin.

### Qualification Registration Failed

- Ensure all required fields (marked with *) are filled in.
- Use a valid email format for the holder email field.
- Select a qualification type from the dropdown.
- If you get a "UNIQUE constraint" error, the serial number or registration number is already in use (even by a deleted record). Use a different value.

### Verification Shows "Rejected"

- Ensure the qualification has both a **Serial Number** and **Registration Number**.
- Do not set an expiry date that has already passed.
- Register a new qualification with all recommended fields filled in.
- Check the individual check results in the verification panel to see which checks failed.

### AI Analysis Returns Error

- The AI analysis uses a rule-based heuristic engine by default (no OpenAI API key required).
- If you see an error, ensure the qualification ID exists and has not been deleted.

### Page Shows "Not Found"

- Ensure the server is running at **http://127.0.0.1:8000**.
- If the server stopped, restart it.
- The API documentation is available at **http://127.0.0.1:8000/docs**.

### Browser Cache Issues

- If the UI looks broken after updates, press **Ctrl + Shift + R** to hard refresh the browser.

---

## 12. Quick Start Guide

1. Open **http://127.0.0.1:8000** in your browser
2. Log in with the default admin: `admin@qvs.com` / `Admin1234!`
3. Go to **Qualifications** and click **Register Credential**
4. Fill in all fields, especially **Serial Number** and **Registration Number**
5. Click **Register Credential**
6. Click **Verify** on the new qualification row
7. View the verification results with individual check details
8. Click **AI** to run fraud detection analysis
9. Go to **Audit Trail** to see all your actions recorded
10. (Admin only) Go to **User Management** to create additional users

---

## 13. Assignment Requirements Coverage

This section documents how the system satisfies each requirement of the MIM736 Software Engineering Assignment 2: "Design and implement a DevOps-Enabled Qualification Verification System Using Git and CI/CD Practices."

### Core Functional Requirements

| Requirement | How it is met |
|-------------|---------------|
| Register qualifications or certifications | The Qualifications page provides a full registration form. Each credential is saved with a SHA-256 blockchain hash, chained to the previous record. |
| Search and retrieve qualification records | The Qualifications page features live search by title, holder name, registration number, or serial number, plus status filtering and pagination. |
| Verify the authenticity of qualifications | The Verify Credential page runs 6 blockchain integrity checks (hash assigned, chain valid, serial number present, registration number present, not expired, not revoked). Results are displayed with individual pass/fail indicators. |
| Maintain an auditable history of verification activities | Every action (login, create, update, delete, verify, AI analysis) is automatically logged in the Audit Trail with user ID, entity, description, and timestamp. |

### 1. Version Control and Collaboration

| Requirement | How it is met |
|-------------|---------------|
| Git-based version control | The project is managed in a Git repository hosted on GitHub (`nmuzanenhamo/QualiTrust-Global`). |
| Branching strategy | Feature branches are used for development (e.g., `feature/frontend-ui`, `feature/blockchain-verification`). |
| Pull requests and code reviews | Pull requests are used to merge features into the main branch. |
| Issue tracking | GitHub Issues are used to track bugs and feature requests. |
| Meaningful commit history | Commits follow conventional messages describing the change (e.g., "Wire audit logging into all routers"). |
| Merge conflict management | Conflicts are resolved through pull request reviews before merging. |

### 2. DevOps Implementation

| Requirement | How it is met |
|-------------|---------------|
| Continuous Integration pipeline | A GitHub Actions CI workflow runs on every push and pull request. |
| Automated build process | The CI pipeline installs dependencies, runs the build, and validates the application. |
| Automated testing | The CI pipeline runs the full pytest suite (64 tests across unit and integration tests). |
| Continuous Delivery pipeline | The system is configured for automated deployment. |
| Automated quality checks | Static code analysis (ruff/flake8) and test coverage reporting are integrated into the CI pipeline. |

### 3. Software Quality Assurance

| Requirement | How it is met |
|-------------|---------------|
| Unit tests | Unit tests cover individual service methods (blockchain service, auth service, qualification service, audit service). Located in `tests/unit/`. |
| Integration tests | Integration tests cover API endpoints end-to-end (auth, qualifications, verification). Located in `tests/integration/`. |
| Test coverage reporting | pytest-cov generates coverage reports during CI runs. |
| Static code analysis | Ruff is configured for linting and code style enforcement. |
| Coding standards compliance | The codebase follows PEP 8 standards, uses type hints throughout, and is formatted consistently. |

### 4. Automated Verification of Requirements

| Requirement | How it is met |
|-------------|---------------|
| Test cases | 64 automated tests verify authentication, CRUD operations, blockchain hashing, verification logic, and AI analysis. |
| Validation rules | Pydantic schemas enforce input validation on all API endpoints (required fields, email format, minimum password length, enum values). |
| CI/CD quality gates | The CI pipeline fails if any test fails or if linting errors are detected, preventing broken code from being merged. |
| Verification reports | Test output and coverage reports are generated by pytest and can be reviewed in the CI pipeline logs. |

### 5. Deployment

| Requirement | How it is met |
|-------------|---------------|
| Docker / Cloud Platform | The system can be deployed using Docker (Dockerfile included) or directly to any cloud platform that supports Python/FastAPI. The application runs on Uvicorn ASGI server. |

### Bonus Advanced Features (Up to 10 bonus marks)

| Bonus Feature | How it is met |
|---------------|---------------|
| Agentic AI integration | The AI Fraud Scan page runs a heuristic analysis engine that detects anomalies (missing identifiers, suspicious institutions, expired credentials, contact data gaps) and produces a risk score with APPROVE/REVIEW/REJECT recommendations. Optionally integrates with OpenAI GPT-4o-mini when an API key is configured. |
| Blockchain-based credential verification | Each qualification is assigned a SHA-256 hash computed from all its data fields. Hashes are chained to the previous record, forming a tamper-evident ledger. Verification recomputes the hash and validates chain integrity. |
| Advanced security mechanisms | Role-based access control (Admin/Verifier/Viewer), JWT authentication with access and refresh tokens, password hashing with bcrypt, admin accounts cannot be self-registered, users can be deactivated, soft-delete preserves audit trail. |
| Real-time monitoring dashboards | Prometheus metrics are exposed at `/metrics` for system health monitoring. A health check endpoint is available at `/health`. The dashboard UI provides real-time statistics on credential counts and status distribution. |
| Infrastructure-as-Code implementation | The project includes configuration files for dependency management (`pyproject.toml`), CI/CD pipelines (GitHub Actions workflows), and containerization (Dockerfile), enabling reproducible deployments. |

### Technical Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript (SPA architecture) |
| Backend | Python 3.12, FastAPI, Uvicorn ASGI server |
| Database | SQLite (via SQLAlchemy ORM) |
| Authentication | JWT (access + refresh tokens), bcrypt password hashing |
| Blockchain | SHA-256 hash chaining (custom implementation) |
| AI Engine | Rule-based heuristics + optional OpenAI GPT-4o-mini |
| Testing | pytest, pytest-cov, TestClient |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus client |
| Version Control | Git + GitHub |

---

*QualiTrust Global — MIM736 Software Engineering Assignment 2*
*Midlands State University*
*Department of Information Systems*
