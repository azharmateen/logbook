"""Read git history: parse commits between tags/ranges, extract conventional commit components."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GitCommit:
    """A parsed git commit."""

    hash: str
    short_hash: str
    subject: str
    body: str
    author_name: str
    author_email: str
    date: str  # ISO format
    # Conventional commit fields
    cc_type: str = ""  # feat, fix, perf, docs, etc.
    cc_scope: str = ""  # optional scope in parentheses
    cc_description: str = ""  # the actual description
    cc_breaking: bool = False  # BREAKING CHANGE
    cc_breaking_description: str = ""
    pr_numbers: list[int] = field(default_factory=list)
    is_conventional: bool = False

    @property
    def display_type(self) -> str:
        """Human-readable type name."""
        type_map = {
            "feat": "Feature",
            "fix": "Bug Fix",
            "perf": "Performance",
            "docs": "Documentation",
            "style": "Style",
            "refactor": "Refactor",
            "test": "Test",
            "build": "Build",
            "ci": "CI",
            "chore": "Chore",
            "revert": "Revert",
            "security": "Security",
            "deps": "Dependencies",
        }
        return type_map.get(self.cc_type, self.cc_type.capitalize() if self.cc_type else "Other")


# Conventional commit regex
# Matches: type(scope)!: description
CC_PATTERN = re.compile(
    r"^(?P<type>[a-z]+)"
    r"(?:\((?P<scope>[^)]+)\))?"
    r"(?P<breaking>!)?"
    r":\s*"
    r"(?P<description>.+)$",
    re.IGNORECASE,
)

# PR reference patterns
PR_PATTERN = re.compile(r"#(\d+)")
PR_URL_PATTERN = re.compile(r"github\.com/[^/]+/[^/]+/pull/(\d+)")


def _run_git(args: list[str], cwd: Optional[str] = None) -> str:
    """Run a git command and return stdout."""
    cmd = ["git"] + args
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def _parse_conventional_commit(subject: str, body: str) -> dict:
    """Parse conventional commit format from subject and body."""
    match = CC_PATTERN.match(subject)
    if not match:
        return {"is_conventional": False}

    cc_type = match.group("type").lower()
    cc_scope = match.group("scope") or ""
    cc_breaking = bool(match.group("breaking"))
    cc_description = match.group("description").strip()

    # Check body for BREAKING CHANGE
    breaking_desc = ""
    if body:
        for line in body.splitlines():
            if line.startswith("BREAKING CHANGE:") or line.startswith("BREAKING-CHANGE:"):
                breaking_desc = line.split(":", 1)[1].strip()
                cc_breaking = True
                break

    return {
        "is_conventional": True,
        "cc_type": cc_type,
        "cc_scope": cc_scope,
        "cc_description": cc_description,
        "cc_breaking": cc_breaking,
        "cc_breaking_description": breaking_desc,
    }


def _extract_pr_numbers(subject: str, body: str) -> list[int]:
    """Extract PR numbers from commit message."""
    text = subject + "\n" + body
    numbers = set()

    for match in PR_PATTERN.finditer(text):
        numbers.add(int(match.group(1)))

    for match in PR_URL_PATTERN.finditer(text):
        numbers.add(int(match.group(1)))

    return sorted(numbers)


def get_tags(cwd: Optional[str] = None) -> list[str]:
    """Get all tags sorted by date (newest first)."""
    try:
        output = _run_git(["tag", "--sort=-creatordate"], cwd=cwd)
        return [t.strip() for t in output.splitlines() if t.strip()]
    except RuntimeError:
        return []


def get_latest_tag(cwd: Optional[str] = None) -> Optional[str]:
    """Get the most recent tag."""
    tags = get_tags(cwd=cwd)
    return tags[0] if tags else None


def get_commits(
    from_ref: Optional[str] = None,
    to_ref: str = "HEAD",
    cwd: Optional[str] = None,
) -> list[GitCommit]:
    """
    Read git commits between two references.

    Args:
        from_ref: Start reference (tag, commit, branch). If None, reads all commits.
        to_ref: End reference. Defaults to HEAD.
        cwd: Working directory (git repo root).

    Returns:
        List of GitCommit objects, newest first.
    """
    # Format: hash|short_hash|subject|author_name|author_email|date
    fmt = "%H|%h|%s|%an|%ae|%aI"
    separator = "---COMMIT_END---"

    args = ["log", f"--pretty=format:{fmt}{separator}%n%b{separator}"]

    if from_ref:
        args.append(f"{from_ref}..{to_ref}")
    else:
        args.append(to_ref)

    try:
        output = _run_git(args, cwd=cwd)
    except RuntimeError:
        return []

    if not output:
        return []

    commits = []

    # Split into commit blocks
    blocks = output.split(separator + "\n")
    i = 0
    while i < len(blocks):
        header_line = blocks[i].strip()
        if not header_line:
            i += 1
            continue

        # Parse header
        parts = header_line.split("|", 5)
        if len(parts) < 6:
            i += 1
            continue

        hash_full, short_hash, subject, author_name, author_email, date = parts

        # Get body (next block)
        body = ""
        if i + 1 < len(blocks):
            body = blocks[i + 1].strip()
            i += 1

        # Parse conventional commit
        cc = _parse_conventional_commit(subject, body)

        # Extract PR numbers
        pr_numbers = _extract_pr_numbers(subject, body)

        commit = GitCommit(
            hash=hash_full,
            short_hash=short_hash,
            subject=subject,
            body=body,
            author_name=author_name,
            author_email=author_email,
            date=date,
            pr_numbers=pr_numbers,
            **cc,
        )
        commits.append(commit)
        i += 1

    return commits


def get_commits_between_tags(
    tag_from: Optional[str] = None,
    tag_to: Optional[str] = None,
    cwd: Optional[str] = None,
) -> list[GitCommit]:
    """Get commits between two tags."""
    return get_commits(from_ref=tag_from, to_ref=tag_to or "HEAD", cwd=cwd)


def get_repo_info(cwd: Optional[str] = None) -> dict:
    """Get repository info (name, remote URL)."""
    try:
        remote_url = _run_git(["config", "--get", "remote.origin.url"], cwd=cwd)
    except RuntimeError:
        remote_url = ""

    # Extract owner/repo from URL
    owner = ""
    repo = ""
    if remote_url:
        # Handle git@github.com:owner/repo.git and https://github.com/owner/repo.git
        match = re.search(r"[:/]([^/]+)/([^/]+?)(?:\.git)?$", remote_url)
        if match:
            owner = match.group(1)
            repo = match.group(2)

    return {
        "remote_url": remote_url,
        "owner": owner,
        "repo": repo,
    }
