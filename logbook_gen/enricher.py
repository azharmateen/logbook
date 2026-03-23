"""Enrich entries: extract PR numbers, link to GitHub PRs, fetch PR title/description, contributors."""

from __future__ import annotations

import os
from typing import Optional

from .categorizer import CategorizedChangelog, CategorizedEntry


def enrich_with_pr_links(
    changelog: CategorizedChangelog,
    owner: str,
    repo: str,
) -> CategorizedChangelog:
    """
    Add GitHub PR links to all entries that reference PRs.

    Args:
        changelog: CategorizedChangelog to enrich.
        owner: GitHub repo owner.
        repo: GitHub repo name.

    Returns:
        Enriched changelog (mutated in place and returned).
    """
    for entries in changelog.categories.values():
        for entry in entries:
            if entry.commit.pr_numbers and not entry.pr_link:
                pr_num = entry.commit.pr_numbers[0]
                entry.pr_link = f"https://github.com/{owner}/{repo}/pull/{pr_num}"

    return changelog


def enrich_with_github_api(
    changelog: CategorizedChangelog,
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> CategorizedChangelog:
    """
    Fetch PR titles and descriptions from GitHub API.

    Requires httpx (install with `pip install logbook-gen[github]`).

    Args:
        changelog: CategorizedChangelog to enrich.
        owner: GitHub repo owner.
        repo: GitHub repo name.
        token: GitHub API token. Falls back to GITHUB_TOKEN env var.

    Returns:
        Enriched changelog.
    """
    token = token or os.environ.get("GITHUB_TOKEN", "")

    try:
        import httpx
    except ImportError:
        return changelog  # httpx not installed, skip enrichment

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    # Collect all unique PR numbers
    pr_numbers: set[int] = set()
    for entries in changelog.categories.values():
        for entry in entries:
            pr_numbers.update(entry.commit.pr_numbers)

    if not pr_numbers:
        return changelog

    # Fetch PR details
    pr_cache: dict[int, dict] = {}
    with httpx.Client(timeout=10.0) as client:
        for pr_num in pr_numbers:
            try:
                url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_num}"
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    pr_cache[pr_num] = {
                        "title": data.get("title", ""),
                        "body": data.get("body", ""),
                        "user": data.get("user", {}).get("login", ""),
                        "labels": [l["name"] for l in data.get("labels", [])],
                        "merged_at": data.get("merged_at", ""),
                    }
            except (httpx.HTTPError, Exception):
                continue

    # Enrich entries with PR data
    for entries in changelog.categories.values():
        for entry in entries:
            if entry.commit.pr_numbers:
                pr_num = entry.commit.pr_numbers[0]
                pr_data = pr_cache.get(pr_num)
                if pr_data:
                    # Use PR title if it's more descriptive than commit message
                    if pr_data["title"] and len(pr_data["title"]) > len(entry.description):
                        entry.description = pr_data["title"]

    # Add PR authors to contributors
    pr_authors = {pr["user"] for pr in pr_cache.values() if pr.get("user")}
    existing = set(changelog.contributors)
    changelog.contributors = sorted(existing | pr_authors)

    return changelog


def format_pr_reference(entry: CategorizedEntry) -> str:
    """Format PR reference for display."""
    parts = []

    if entry.commit.pr_numbers:
        refs = [f"#{n}" for n in entry.commit.pr_numbers]
        parts.append(f"({', '.join(refs)})")

    return " ".join(parts)


def format_contributor_line(name: str, email: str = "", github_user: str = "") -> str:
    """Format a contributor line."""
    if github_user:
        return f"@{github_user}"
    if email:
        return f"{name} <{email}>"
    return name


def get_unique_contributors(changelog: CategorizedChangelog) -> list[dict]:
    """Get unique contributors with commit counts."""
    contrib_counts: dict[str, int] = {}
    contrib_emails: dict[str, str] = {}

    for entries in changelog.categories.values():
        for entry in entries:
            name = entry.commit.author_name
            contrib_counts[name] = contrib_counts.get(name, 0) + 1
            if entry.commit.author_email:
                contrib_emails[name] = entry.commit.author_email

    return [
        {
            "name": name,
            "email": contrib_emails.get(name, ""),
            "commits": count,
        }
        for name, count in sorted(contrib_counts.items(), key=lambda x: -x[1])
    ]
