"""Categorize changes: Features, Bug Fixes, Performance, Security, etc."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .git_reader import GitCommit

# ─── Category definitions ───────────────────────────────────────────

CATEGORIES = [
    "Breaking Changes",
    "Features",
    "Bug Fixes",
    "Performance",
    "Security",
    "Documentation",
    "Dependencies",
    "Internal",
]

# Map conventional commit types to categories
CC_TYPE_MAP = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "perf": "Performance",
    "security": "Security",
    "docs": "Documentation",
    "deps": "Dependencies",
    "style": "Internal",
    "refactor": "Internal",
    "test": "Internal",
    "build": "Internal",
    "ci": "Internal",
    "chore": "Internal",
    "revert": "Bug Fixes",
}

# Keyword-based categorization for non-conventional commits
KEYWORD_CATEGORIES = {
    "Features": [
        "add", "new", "feature", "implement", "introduce", "create",
        "support", "enable", "allow",
    ],
    "Bug Fixes": [
        "fix", "bug", "patch", "resolve", "correct", "repair", "hotfix",
        "issue", "error", "crash", "broken",
    ],
    "Performance": [
        "perf", "optimize", "speed", "fast", "slow", "cache", "lazy",
        "memory", "reduce", "improve performance",
    ],
    "Security": [
        "security", "vulnerability", "cve", "xss", "csrf", "injection",
        "auth", "permission", "sanitize",
    ],
    "Documentation": [
        "docs", "readme", "documentation", "comment", "jsdoc", "docstring",
        "changelog", "guide", "tutorial",
    ],
    "Dependencies": [
        "bump", "upgrade", "update dependency", "update deps",
        "dependabot", "renovate", "npm update", "pip install",
    ],
}


@dataclass
class CategorizedEntry:
    """A changelog entry with category."""

    commit: GitCommit
    category: str
    description: str
    scope: str = ""
    is_breaking: bool = False
    breaking_description: str = ""
    pr_link: str = ""


@dataclass
class CategorizedChangelog:
    """A complete categorized changelog."""

    version: str
    date: str
    categories: dict[str, list[CategorizedEntry]] = field(default_factory=dict)
    contributors: list[str] = field(default_factory=list)
    total_commits: int = 0

    def get_entries(self, category: str) -> list[CategorizedEntry]:
        return self.categories.get(category, [])

    @property
    def has_breaking(self) -> bool:
        return bool(self.categories.get("Breaking Changes"))


def _categorize_by_keywords(subject: str) -> str:
    """Categorize a commit by keyword matching."""
    lower = subject.lower()

    for category, keywords in KEYWORD_CATEGORIES.items():
        for kw in keywords:
            if kw in lower:
                return category

    return "Internal"


def categorize_commit(commit: GitCommit, repo_info: Optional[dict] = None) -> CategorizedEntry:
    """
    Categorize a single commit.

    Args:
        commit: GitCommit to categorize.
        repo_info: Optional dict with 'owner' and 'repo' for PR links.

    Returns:
        CategorizedEntry.
    """
    # Determine category
    if commit.cc_breaking:
        category = "Breaking Changes"
    elif commit.is_conventional and commit.cc_type in CC_TYPE_MAP:
        category = CC_TYPE_MAP[commit.cc_type]
    else:
        category = _categorize_by_keywords(commit.subject)

    # Build description
    if commit.is_conventional:
        description = commit.cc_description
    else:
        description = commit.subject

    # Build PR link
    pr_link = ""
    if commit.pr_numbers and repo_info:
        owner = repo_info.get("owner", "")
        repo = repo_info.get("repo", "")
        if owner and repo:
            pr_num = commit.pr_numbers[0]
            pr_link = f"https://github.com/{owner}/{repo}/pull/{pr_num}"

    return CategorizedEntry(
        commit=commit,
        category=category,
        description=description,
        scope=commit.cc_scope,
        is_breaking=commit.cc_breaking,
        breaking_description=commit.cc_breaking_description,
        pr_link=pr_link,
    )


def categorize_commits(
    commits: list[GitCommit],
    version: str = "Unreleased",
    date: str = "",
    repo_info: Optional[dict] = None,
) -> CategorizedChangelog:
    """
    Categorize a list of commits into a structured changelog.

    Args:
        commits: List of GitCommit objects.
        version: Version string for this changelog.
        date: Release date string.
        repo_info: Optional repo info for PR links.

    Returns:
        CategorizedChangelog with entries grouped by category.
    """
    categories: dict[str, list[CategorizedEntry]] = {cat: [] for cat in CATEGORIES}
    contributors = set()

    for commit in commits:
        entry = categorize_commit(commit, repo_info)
        categories[entry.category].append(entry)
        contributors.add(commit.author_name)

    # Remove empty categories
    categories = {k: v for k, v in categories.items() if v}

    if not date and commits:
        date = commits[0].date[:10]  # Use newest commit date

    return CategorizedChangelog(
        version=version,
        date=date,
        categories=categories,
        contributors=sorted(contributors),
        total_commits=len(commits),
    )
