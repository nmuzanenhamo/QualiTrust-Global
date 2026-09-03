#!/usr/bin/env python3
"""
Commit simulation script for multi-member Git workflow.

This script allows attributing commits to different team members
by switching git user.name and user.email before each commit.
"""

import subprocess
import sys

TEAM_MEMBERS = {
    "ngonidzashe": {
        "name": "Ngonidzashe Muzanenhamo",
        "email": "37529955+nmuzanenhamo@users.noreply.github.com",
    },
    "loreen": {
        "name": "Loreen Venge",
        "email": "129304525+loreenvenge@users.noreply.github.com",
    },
    "judah": {
        "name": "Judah T Chisare",
        "email": "84022158+judahtc@users.noreply.github.com",
    },
    "nyasha": {
        "name": "Nyasha A Madziwanzira",
        "email": "276561319+madziwanziran@users.noreply.github.com",
    },
}


def set_git_user(member_key: str) -> dict:
    """Set git user.name and user.email for the given team member."""
    member = TEAM_MEMBERS[member_key]
    subprocess.run(
        ["git", "config", "user.name", member["name"]], check=True
    )
    subprocess.run(
        ["git", "config", "user.email", member["email"]], check=True
    )
    return member


def commit_as(member_key: str, message: str) -> None:
    """Stage all changes and commit as the specified team member."""
    member = set_git_user(member_key)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        check=True,
    )
    print(f"Committed as: {member['name']} <{member['email']}>")
    print(f"Message: {message}")


def list_members() -> None:
    """List all available team member keys."""
    print("Available team members:")
    for key, info in TEAM_MEMBERS.items():
        print(f"  {key}: {info['name']} <{info['email']}>")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python commit_as.py <member_key> <commit_message>")
        print("       python commit_as.py --list")
        print("\nMembers:")
        list_members()
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_members()
        sys.exit(0)

    member_key = sys.argv[1]
    if member_key not in TEAM_MEMBERS:
        print(f"Error: Unknown member '{member_key}'")
        list_members()
        sys.exit(1)

    if len(sys.argv) < 3:
        print("Error: Commit message required")
        sys.exit(1)

    commit_message = " ".join(sys.argv[2:])
    commit_as(member_key, commit_message)
