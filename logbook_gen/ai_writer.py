"""AI-assisted: send categorized changes to LLM for polished summaries (optional, works without)."""

from __future__ import annotations

import os
from typing import Optional

from .categorizer import CategorizedChangelog


def _build_changes_summary(changelog: CategorizedChangelog) -> str:
    """Build a text summary of changes for the AI prompt."""
    lines = [f"Version: {changelog.version}", f"Date: {changelog.date}", ""]

    for cat, entries in changelog.categories.items():
        lines.append(f"{cat}:")
        for entry in entries:
            scope = f"[{entry.scope}] " if entry.scope else ""
            lines.append(f"  - {scope}{entry.description}")
        lines.append("")

    lines.append(f"Contributors: {', '.join(changelog.contributors)}")
    lines.append(f"Total commits: {changelog.total_commits}")
    return "\n".join(lines)


def generate_release_highlights(
    changelog: CategorizedChangelog,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
    max_tokens: int = 1000,
) -> Optional[str]:
    """
    Generate polished release highlights using an LLM.

    Requires openai package (install with `pip install logbook-gen[ai]`).

    Args:
        changelog: CategorizedChangelog to summarize.
        api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        model: Model to use.
        max_tokens: Maximum tokens in response.

    Returns:
        Polished release summary string, or None if AI is unavailable.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    changes_summary = _build_changes_summary(changelog)

    prompt = f"""You are a technical writer creating release notes for a software project.
Given the following categorized changes, write a polished, concise release summary.

Rules:
- Start with a 1-2 sentence overview of the most impactful changes
- Highlight the top 3-5 changes that users care about
- Mention breaking changes prominently if any
- Use clear, professional language
- Keep it under 200 words
- Use markdown formatting

Changes:
{changes_summary}

Write the release summary:"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def polish_entry_description(
    description: str,
    category: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> str:
    """
    Polish a single changelog entry description.

    Args:
        description: Raw description to polish.
        category: Category (Features, Bug Fixes, etc.).
        api_key: OpenAI API key.
        model: Model to use.

    Returns:
        Polished description, or original if AI unavailable.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return description

    try:
        from openai import OpenAI
    except ImportError:
        return description

    prompt = f"""Rewrite this changelog entry to be clearer and more user-friendly.
Keep it concise (one sentence). Category: {category}

Original: {description}

Rewritten:"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.5,
        )
        result = response.choices[0].message.content.strip()
        # Remove quotes if the AI wrapped it
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        return result
    except Exception:
        return description


def generate_twitter_thread(
    changelog: CategorizedChangelog,
    project_name: str = "",
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> Optional[list[str]]:
    """
    Generate a Twitter/X announcement thread.

    Args:
        changelog: CategorizedChangelog to announce.
        project_name: Project name for the announcement.
        api_key: OpenAI API key.
        model: Model to use.

    Returns:
        List of tweet strings (3-5 tweets), or None if AI unavailable.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        return None

    changes_summary = _build_changes_summary(changelog)

    prompt = f"""Write a Twitter/X announcement thread (3-5 tweets) for this software release.

Project: {project_name or 'the project'}
{changes_summary}

Rules:
- Tweet 1: Exciting announcement with version number
- Tweets 2-4: Key features and fixes (most impactful first)
- Last tweet: Thank contributors and invite feedback
- Each tweet must be under 280 characters
- Use relevant emojis sparingly
- Include a thread indicator (1/N format)

Write each tweet on a separate line, separated by ---:"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.8,
        )
        text = response.choices[0].message.content.strip()
        tweets = [t.strip() for t in text.split("---") if t.strip()]
        return tweets
    except Exception:
        return None
