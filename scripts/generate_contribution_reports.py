"""
Generate Individual Contribution Reports for each team member.
Parses git log per author and creates a .docx report that reuses the
exact MSU cover page template (logo, table borders, merged cells).
Formatting: Times New Roman, 12pt, 1.5 line spacing, black font.
"""

import subprocess
import os
import sys

from docx.shared import Inches

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from report_utils import (
    build_cover_page_document,
    set_document_defaults,
    add_heading,
    add_paragraph,
    add_table,
    finalize_document_fonts,
)

OUTPUT_DIR = r"C:\Users\NgonidzasheMuzanenha\OneDrive\Masters Information Systems\Semester 1.2\MIM736 - Software Engineering"

TEAM_MEMBERS = [
    {
        "name": "Ngonidzashe Muzanenhamo",
        "reg_number": "R211790N",
        "email": "37529955+nmuzanenhamo@users.noreply.github.com",
        "role": "Tech Lead / DevOps Engineer",
        "responsibility": "CI/CD pipeline, Docker containerization, cloud deployment, project scaffolding, and documentation",
    },
    {
        "name": "Loreen Venge",
        "reg_number": "R2118621M",
        "email": "129304525+loreenvenge@users.noreply.github.com",
        "role": "Backend Developer",
        "responsibility": "Database models, Pydantic schemas, qualification CRUD API, and audit logging service",
    },
    {
        "name": "Judah T Chisare",
        "reg_number": "R267853N",
        "email": "84022158+judahtc@users.noreply.github.com",
        "role": "QA / Testing Engineer",
        "responsibility": "Unit tests, integration tests, test fixtures, and coverage reporting",
    },
    {
        "name": "Nyasha A Madziwanzira",
        "reg_number": "R2117220T",
        "email": "276561319+madziwanziran@users.noreply.github.com",
        "role": "Security & AI Engineer",
        "responsibility": "JWT authentication, RBAC, blockchain verification, AI fraud detection, and monitoring dashboard",
    },
]


def get_git_log_for_author(repo_path, email):
    """Get git log entries for a specific author email."""
    result = subprocess.run(
        ["git", "log", "--all", "--format=%H|%an|%ae|%ad|%s", "--date=short", f"--author={email}"],
        capture_output=True,
        text=True,
        cwd=repo_path,
    )
    commits = []
    for line in result.stdout.strip().split("\n"):
        if line:
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append({
                    "hash": parts[0],
                    "name": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "message": parts[4],
                })
    return commits


def get_files_changed(repo_path, commit_hash):
    """Get list of files changed in a commit."""
    result = subprocess.run(
        ["git", "show", "--name-only", "--format=", commit_hash],
        capture_output=True,
        text=True,
        cwd=repo_path,
    )
    return [f for f in result.stdout.strip().split("\n") if f]


def get_branches_for_author(repo_path, email):
    """Get branches that contain commits from the specified author."""
    result = subprocess.run(
        ["git", "log", "--all", "--format=%H", f"--author={email}"],
        capture_output=True,
        text=True,
        cwd=repo_path,
    )
    commit_hashes = result.stdout.strip().split("\n") if result.stdout.strip() else []

    branches = set()
    for ch in commit_hashes:
        if ch:
            branch_result = subprocess.run(
                ["git", "branch", "--contains", ch],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )
            for line in branch_result.stdout.strip().split("\n"):
                branch = line.strip().lstrip("* ").strip()
                if branch:
                    branches.add(branch)
    return sorted(branches)


def generate_contribution_report(repo_path, member):
    """Generate an individual contribution report for a team member."""
    doc = build_cover_page_document(
        student_name=member["name"],
        reg_number=member["reg_number"],
        question_text="Assignment 2: Individual Contribution Report",
    )
    set_document_defaults(doc)

    # 1. Member Information
    add_heading(doc, "1. Member Information", level=1)
    add_table(doc, "Table 1: Member Details",
        ["Field", "Value"],
        [
            ["Name", member["name"]],
            ["Registration Number", member["reg_number"]],
            ["Git Email", member["email"]],
            ["Role", member["role"]],
            ["Responsibility", member["responsibility"]],
        ]
    )

    # 2. Git Activity Summary
    add_heading(doc, "2. Git Activity Summary", level=1)
    commits = get_git_log_for_author(repo_path, member["email"])
    branches = get_branches_for_author(repo_path, member["email"])

    add_paragraph(doc,
        f"During the development of the Qualification Verification System, {member['name']} "
        f"made {len(commits)} commits across {len(branches)} branches. The following sections "
        f"provide a detailed breakdown of the contributions made."
    )

    add_table(doc, "Table 2: Git Activity Summary",
        ["Metric", "Value"],
        [
            ["Total Commits", str(len(commits))],
            ["Branches Involved", str(len(branches))],
            ["Role", member["role"]],
            ["Primary Responsibility", member["responsibility"]],
        ]
    )

    # 3. Branches
    add_heading(doc, "3. Branches Involved", level=1)
    add_paragraph(doc,
        "The following branches were created or contributed to during the development process:"
    )
    for branch in branches:
        add_paragraph(doc, f"- {branch}")

    # 4. Commit History
    add_heading(doc, "4. Commit History", level=1)
    add_paragraph(doc,
        "The following table lists all commits made by this member, including commit hash, date, and message:"
    )

    commit_rows = []
    for c in commits:
        short_hash = c["hash"][:8]
        commit_rows.append([short_hash, c["date"], c["message"]])

    if commit_rows:
        add_table(doc, "Table 3: Commit History",
            ["Commit Hash", "Date", "Commit Message"],
            commit_rows
        )
    else:
        add_paragraph(doc, "No commits found for this member.")

    # 5. Files Modified
    add_heading(doc, "5. Files Modified", level=1)
    add_paragraph(doc,
        "The following files were created or modified by this member across all commits:"
    )

    all_files = set()
    for c in commits:
        files = get_files_changed(repo_path, c["hash"])
        all_files.update(files)

    if all_files:
        file_rows = [[f] for f in sorted(all_files)]
        add_table(doc, "Table 4: Files Modified",
            ["File Path"],
            file_rows
        )
    else:
        add_paragraph(doc, "No files found.")

    # 6. Contribution Summary by Area
    add_heading(doc, "6. Contribution Summary by Area", level=1)
    add_paragraph(doc, member["responsibility"] + ".")

    # Categorize files
    code_files = [f for f in all_files if f.endswith(".py") and "test" not in f.lower()]
    test_files = [f for f in all_files if "test" in f.lower() or "conftest" in f.lower()]
    ci_cd_files = [f for f in all_files if ".github" in f or "Dockerfile" in f or "docker-compose" in f or "render" in f]
    doc_files = [f for f in all_files if f.endswith(".md") or "docs/" in f]
    config_files = [f for f in all_files if f.endswith(".toml") or f.endswith(".yml") or f.endswith(".yaml") or f == ".gitignore" or f == ".dockerignore" or f == ".env.example"]

    add_table(doc, "Table 5: Contribution Breakdown by Area",
        ["Area", "Number of Files", "Files"],
        [
            ["Source Code", str(len(code_files)), ", ".join(sorted(code_files)[:5]) + ("..." if len(code_files) > 5 else "")],
            ["Tests", str(len(test_files)), ", ".join(sorted(test_files)[:5]) + ("..." if len(test_files) > 5 else "")],
            ["CI/CD and Deployment", str(len(ci_cd_files)), ", ".join(sorted(ci_cd_files)[:5])],
            ["Documentation", str(len(doc_files)), ", ".join(sorted(doc_files)[:5])],
            ["Configuration", str(len(config_files)), ", ".join(sorted(config_files)[:5])],
        ]
    )

    # 7. Verification Methods Design Rationale
    add_heading(doc, "7. Verification Methods Design Rationale", level=1)
    add_paragraph(doc,
        "The system provides four verification methods. Each method serves a distinct "
        "purpose and addresses a different real-world verification scenario. The following "
        "explanation justifies the design decision to include all four methods rather than "
        "a single approach."
    )

    add_heading(doc, "7.1 Blockchain Method", level=2)
    add_paragraph(doc,
        "The Blockchain method runs six SHA-256 hash chain integrity checks: whether a "
        "credential hash has been assigned, whether the recomputed hash matches the stored "
        "hash and the chain link to the previous record is intact, whether a serial number "
        "exists, whether a registration number exists, whether the qualification has not "
        "expired, and whether the status is not revoked. All six checks must pass for the "
        "credential to be marked as Verified. This method answers the question: has this "
        "credential been tampered with since it was registered? It is the fastest and most "
        "objective check, relying purely on cryptographic hashing with no human judgement "
        "or AI inference. It serves as the baseline verification mechanism that every other "
        "method builds upon."
    )

    add_heading(doc, "7.2 Manual Review Method", level=2)
    add_paragraph(doc,
        "The Manual Review method runs the exact same six blockchain checks, but the audit "
        "trail records that a human reviewed the physical document alongside the blockchain "
        "check. The verifier can add notes such as comparing the digital record against the "
        "original transcript or confirming the holder's identity in person. Blockchain alone "
        "only proves the digital record is intact; it does not prove the person presenting "
        "the certificate is the legitimate holder. Manual Review documents that a human "
        "performed that extra step. The distinction in the audit trail matters for legal and "
        "compliance purposes because it shows how the verification was conducted, not just "
        "that it was conducted."
    )

    add_heading(doc, "7.3 AI Assisted Method", level=2)
    add_paragraph(doc,
        "The AI Assisted method runs the six blockchain checks plus the AI fraud detection "
        "engine. The AI scans for anomalies including missing serial numbers, missing "
        "registration numbers, expired qualifications, no verifiable holder contact "
        "information, suspicious institution names (such as diploma mill or fake), and "
        "unclassified qualification types. It produces a risk score from 0 to 100 with a "
        "recommendation of APPROVE, REVIEW, or REJECT. The final result combines both "
        "layers: if blockchain checks fail the result is Rejected regardless of AI; if "
        "blockchain passes and AI says APPROVE the result is Verified; if blockchain "
        "passes and AI says REVIEW the result is Inconclusive, signalling that human "
        "follow-up is needed; if blockchain passes but AI says REJECT the result is "
        "Rejected. This method is justified because blockchain only detects tampering; it "
        "cannot detect fraud at the point of registration. A university could register a "
        "fake credential with a valid serial number and blockchain verification would pass "
        "because the record was never tampered with. The AI engine catches patterns that "
        "suggest the credential itself is suspicious, providing two layers of defence in "
        "one step."
    )

    add_heading(doc, "7.4 Automated Method", level=2)
    add_paragraph(doc,
        "The Automated method uses identical logic to AI Assisted (blockchain plus AI "
        "fraud analysis), but the audit trail records it as a fully automated process with "
        "no human in the loop. This distinction matters for compliance, accountability, and "
        "audit defence. Some regulators require documentation of whether a human reviewed a "
        "verification decision. If a credential is wrongly approved, the audit trail must "
        "show whether a human or the algorithm made the call. Automated is designed for "
        "batch verification scenarios such as an employer verifying hundreds of credentials "
        "or a licensing board running periodic re-verification of all credentials, where no "
        "human reviews individual results."
    )

    add_heading(doc, "7.5 Justification for Having All Four Methods", level=2)
    add_paragraph(doc,
        "The four methods form a progressive escalation from pure cryptography to human "
        "judgement to AI augmentation to full automation. Blockchain provides a quick "
        "integrity check for low-risk credentials. Manual Review is for high-stakes "
        "verification where a human must physically inspect the document. AI Assisted is "
        "for when a verifier wants both tamper detection and fraud risk assessment in one "
        "step with human oversight. Automated is for batch processing pipelines where no "
        "human reviews individual results. Having all four allows the system to serve "
        "everything from a single credential check by a small employer to a large-scale "
        "automated verification pipeline at a licensing board. Removing any one method "
        "would leave a gap: without Blockchain there is no tamper detection; without Manual "
        "Review there is no documented human verification of physical documents; without "
        "AI Assisted there is no fraud risk assessment for individual cases; without "
        "Automated there is no way to distinguish human-initiated AI verification from "
        "fully algorithmic decisions in the audit trail."
    )

    # 8. Reflection
    add_heading(doc, "8. Reflection on Lessons Learned and Challenges", level=1)
    add_paragraph(doc,
        f"Working on the Qualification Verification System provided valuable experience in "
        f"collaborative software engineering and DevOps practices. As the {member['role']}, "
        f"I was responsible for {member['responsibility'].lower()}."
    )
    add_paragraph(doc,
        "One of the key lessons learned was the importance of following a consistent branching "
        "strategy and conventional commit format. This made the Git history readable and "
        "helped the team track progress across different features. The use of pull requests "
        "and code reviews ensured that code quality was maintained throughout the development process."
    )
    add_paragraph(doc,
        "Challenges encountered included managing dependencies between different modules, "
        "ensuring that database models were compatible with both SQLite and PostgreSQL, and "
        "configuring the CI/CD pipeline to run tests in an isolated environment. These challenges "
        "were addressed through careful design decisions, thorough testing, and iterative refinement "
        "of the CI/CD configuration."
    )
    add_paragraph(doc,
        "The experience of working with modern tools such as FastAPI, Docker, GitHub Actions, "
        "and Prometheus has strengthened my understanding of how DevOps practices can improve "
        "software quality, team collaboration, and delivery speed. I have gained practical "
        "skills in automated testing, continuous integration, containerization, and cloud "
        "deployment that will be valuable in future software engineering projects."
    )

    # Apply formatting (skips cover page which is already correct)
    finalize_document_fonts(doc)

    # Save
    safe_name = member["name"].replace(" ", "_")
    output_path = os.path.join(OUTPUT_DIR, f"Individual Contribution - {safe_name}.docx")
    doc.save(output_path)
    print(f"Generated: {output_path}")
    return output_path


def main():
    repo_path = r"C:\Users\NgonidzasheMuzanenha\CascadeProjects\qualification-verification-system"
    for member in TEAM_MEMBERS:
        generate_contribution_report(repo_path, member)
    print("\nAll individual contribution reports generated successfully.")


if __name__ == "__main__":
    main()
