# Demo Video Script - Qualification Verification System

**Duration:** 10-15 minutes
**Module:** MIM736 - Software Engineering
**Team:** Ngonidzashe Muzanenhamo, Loreen Venge, Judah T Chisare, Nyasha A Madziwanzira

---

## Video Outline

### Part 1: Introduction (1-2 minutes)

**[Slide 1: Title Slide]**
- Presenter introduces the team and the project title
- "Welcome to our demonstration of the Qualification Verification System, a DevOps-enabled solution for credential verification developed as part of MIM736 Software Engineering"

**[Slide 2: Project Overview]**
- Brief explanation of the problem: credential fraud and the need for reliable verification
- Overview of the system: FastAPI, blockchain verification, AI fraud detection, JWT auth, monitoring
- Mention the four team members and their roles

### Part 2: System Functionality Walkthrough (3-4 minutes)

**[Screen Recording: Swagger UI at /docs]**

1. **Authentication Demo (1 minute)**
   - Show the POST /api/v1/auth/register endpoint
   - Register a new user with verifier role
   - Show the POST /api/v1/auth/login endpoint
   - Login and receive JWT access and refresh tokens
   - Show the GET /api/v1/auth/me endpoint with the token

2. **Qualification Registration Demo (1 minute)**
   - Show the POST /api/v1/qualifications/ endpoint
   - Register a new qualification (e.g., "Bachelor of Science in Computer Science")
   - Fill in all required fields: title, type, institution, holder, date, serial number
   - Show the response with status "pending"

3. **Search and Retrieve Demo (1 minute)**
   - Show the GET /api/v1/qualifications/ endpoint with search parameters
   - Search by title, filter by type, paginate results
   - Show the GET /api/v1/qualifications/{id} endpoint for a specific record

4. **Verification Demo (1 minute)**
   - Show the POST /api/v1/qualifications/{id}/verify endpoint
   - Explain the blockchain hash verification process
   - Show the verification result with checks and hash
   - Show the GET /api/v1/qualifications/{id}/verifications endpoint for history

### Part 3: Git Workflow Demonstration (2-3 minutes)

**[Screen Recording: Git terminal and GitHub]**

1. **Branching Strategy (1 minute)**
   - Open terminal and show `git branch -a` to display all branches
   - Explain GitHub Flow: feature branches, pull requests, merge to main
   - Show the branch naming convention (feature/database-models, feature/jwt-auth-rbac, etc.)

2. **Commit History (1 minute)**
   - Run `git log --oneline --graph` to show the commit history
   - Highlight conventional commit messages (feat, test, ci, docs)
   - Show how different team members contributed commits
   - Run `git shortlog -sne` to show commit count per author

3. **Pull Requests (1 minute)**
   - Show GitHub repository pull requests tab (if available)
   - Explain the code review process
   - Show merge commits with `git log --merges --oneline`

### Part 4: CI/CD Pipeline Showcase (2-3 minutes)

**[Screen Recording: GitHub Actions tab]**

1. **CI Pipeline (1.5 minutes)**
   - Navigate to GitHub Actions tab
   - Show the CI workflow running: lint (Ruff), security scan (Bandit), tests, coverage
   - Explain each quality gate: tests must pass, coverage >= 80%, no critical security issues
   - Show a successful pipeline run with green checkmarks

2. **CD Pipeline (1 minute)**
   - Show the CD workflow: Docker build, push to Docker Hub, deploy to Render
   - Explain the automated deployment process
   - Show the live deployment URL if available

### Part 5: Automated Testing Demo (1-2 minutes)

**[Screen Recording: Terminal]**

1. **Unit Tests (30 seconds)**
   - Run `pytest tests/unit/ -v`
   - Show test results with passed/failed counts
   - Highlight key tests: password hashing, JWT tokens, blockchain integrity

2. **Integration Tests (30 seconds)**
   - Run `pytest tests/integration/ -v`
   - Show API endpoint tests passing
   - Highlight auth, qualification CRUD, and verification tests

3. **Coverage Report (30 seconds)**
   - Run `pytest --cov=app --cov-report=term`
   - Show coverage percentage and per-module breakdown
   - Explain the 80% coverage threshold enforcement

### Part 6: Qualification Verification Process Demo (1-2 minutes)

**[Screen Recording: Swagger UI and terminal]**

1. **Full Verification Flow (1 minute)**
   - Register a qualification
   - Verify it using the blockchain endpoint
   - Show the verification record created
   - Query the audit logs to show the full trail

2. **AI Analysis Demo (30 seconds)**
   - Show the POST /api/v1/ai/analyze/{id} endpoint
   - Run AI analysis on a qualification
   - Show the risk score, confidence score, anomalies, and recommendation

3. **Monitoring Demo (30 seconds)**
   - Show the /metrics endpoint with Prometheus metrics
   - If Grafana is running, show the dashboard
   - Explain the metrics: request count, latency, verification stats

### Part 7: Conclusion (1 minute)

**[Slide 3: Summary]**
- Recap the key features demonstrated
- Highlight the DevOps practices: Git workflow, CI/CD, testing, Docker, cloud deployment
- Mention the bonus features: blockchain, AI, security, monitoring
- Thank the audience and invite questions

---

## Speaker Notes

### Part 1 Notes
- Keep introduction concise and engaging
- Mention the real-world relevance of credential verification
- Introduce all team members by name and role

### Part 2 Notes
- Use Swagger UI for a clean, professional API demo
- Explain each field when filling in forms
- Show both successful and error responses (e.g., 403 for unauthorized access)

### Part 3 Notes
- Emphasize the conventional commit format
- Show that different team members have distinct commit histories
- Explain how branches map to features and pull requests

### Part 4 Notes
- If GitHub Actions has not been run yet, explain the workflow files
- Show the YAML configuration files and explain each step
- Emphasize the quality gates and automated deployment

### Part 5 Notes
- Run tests live to show they pass
- If any test fails, explain how it would be caught by CI
- Show coverage report and explain the threshold

### Part 6 Notes
- This is the culmination of the demo, showing the full verification flow
- Emphasize the blockchain integrity check
- Show how audit logs capture all activities

### Part 7 Notes
- Keep conclusion brief and confident
- Mention that all deliverables are complete
- Invite questions from the audience

---

## Recording Tips

1. **Screen Resolution:** Use 1920x1080 for clear screen recording
2. **Font Size:** Increase terminal font size for readability
3. **Browser:** Use full-screen mode for Swagger UI
4. **Pacing:** Speak slowly and clearly, pause between sections
5. **Transitions:** Use simple slide transitions, avoid distracting effects
6. **Backup:** Have a pre-seeded database ready to avoid waiting during demo
7. **Timing:** Practice beforehand to stay within 10-15 minutes
