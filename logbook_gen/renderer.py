"""Render changelogs: Keep a Changelog, GitHub Releases, Slack, plain text, HTML."""

from __future__ import annotations

import html
from typing import Optional

from .categorizer import CategorizedChangelog, CategorizedEntry
from .enricher import format_pr_reference, get_unique_contributors


def _entry_line(entry: CategorizedEntry, include_scope: bool = True, include_pr: bool = True) -> str:
    """Format a single entry line."""
    parts = []

    if include_scope and entry.scope:
        parts.append(f"**{entry.scope}:**")

    parts.append(entry.description)

    if include_pr and entry.commit.pr_numbers:
        pr_refs = format_pr_reference(entry)
        parts.append(pr_refs)

    if entry.is_breaking and entry.breaking_description:
        parts.append(f"\n  > BREAKING: {entry.breaking_description}")

    return " ".join(parts)


def render_keepachangelog(
    changelog: CategorizedChangelog,
    compare_url: str = "",
) -> str:
    """
    Render in Keep a Changelog format.
    https://keepachangelog.com/

    Args:
        changelog: CategorizedChangelog to render.
        compare_url: Optional URL for version comparison.

    Returns:
        Markdown string.
    """
    lines = []

    # Version header
    version_str = changelog.version
    if changelog.date:
        version_str += f" - {changelog.date}"
    if compare_url:
        lines.append(f"## [{version_str}]({compare_url})")
    else:
        lines.append(f"## [{version_str}]")

    lines.append("")

    # Category mapping to Keep a Changelog names
    kac_map = {
        "Features": "Added",
        "Bug Fixes": "Fixed",
        "Performance": "Changed",
        "Security": "Security",
        "Breaking Changes": "Changed",
        "Documentation": "Changed",
        "Dependencies": "Changed",
        "Internal": "Changed",
    }

    # Group by Keep a Changelog categories
    kac_groups: dict[str, list[str]] = {}
    for cat, entries in changelog.categories.items():
        kac_name = kac_map.get(cat, "Changed")
        if kac_name not in kac_groups:
            kac_groups[kac_name] = []
        for entry in entries:
            kac_groups[kac_name].append(_entry_line(entry))

    # Render in standard order
    for kac_cat in ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]:
        if kac_cat in kac_groups:
            lines.append(f"### {kac_cat}")
            lines.append("")
            for item in kac_groups[kac_cat]:
                lines.append(f"- {item}")
            lines.append("")

    return "\n".join(lines)


def render_github_release(
    changelog: CategorizedChangelog,
) -> str:
    """
    Render for GitHub Releases (Markdown).

    Args:
        changelog: CategorizedChangelog to render.

    Returns:
        Markdown string.
    """
    lines = []

    # Breaking changes first
    if changelog.has_breaking:
        lines.append("## :warning: Breaking Changes")
        lines.append("")
        for entry in changelog.get_entries("Breaking Changes"):
            lines.append(f"- {_entry_line(entry)}")
        lines.append("")

    # Category order for GitHub releases
    category_icons = {
        "Features": ":rocket: Features",
        "Bug Fixes": ":bug: Bug Fixes",
        "Performance": ":zap: Performance",
        "Security": ":lock: Security",
        "Documentation": ":book: Documentation",
        "Dependencies": ":package: Dependencies",
        "Internal": ":wrench: Internal",
    }

    for cat, header in category_icons.items():
        entries = changelog.get_entries(cat)
        if entries:
            lines.append(f"## {header}")
            lines.append("")
            for entry in entries:
                lines.append(f"- {_entry_line(entry)}")
            lines.append("")

    # Contributors
    if changelog.contributors:
        lines.append("## Contributors")
        lines.append("")
        for name in changelog.contributors:
            lines.append(f"- {name}")
        lines.append("")

    lines.append(f"**Full Changelog**: {changelog.total_commits} commits")

    return "\n".join(lines)


def render_slack(
    changelog: CategorizedChangelog,
    repo_name: str = "",
) -> str:
    """
    Render condensed Slack announcement.

    Args:
        changelog: CategorizedChangelog to render.
        repo_name: Optional repository name.

    Returns:
        Slack-formatted string.
    """
    lines = []
    title = repo_name or "Release"
    lines.append(f"*{title} {changelog.version}* ({changelog.date})")
    lines.append("")

    # Only show Features, Bug Fixes, Breaking Changes, and Performance
    important_cats = ["Breaking Changes", "Features", "Bug Fixes", "Performance"]

    for cat in important_cats:
        entries = changelog.get_entries(cat)
        if entries:
            emoji = {
                "Breaking Changes": ":warning:",
                "Features": ":sparkles:",
                "Bug Fixes": ":bug:",
                "Performance": ":zap:",
            }.get(cat, ":memo:")

            lines.append(f"{emoji} *{cat}*")
            for entry in entries[:5]:  # Max 5 per category for Slack
                lines.append(f"  - {entry.description}")
            if len(entries) > 5:
                lines.append(f"  _...and {len(entries) - 5} more_")
            lines.append("")

    # Summary
    other_count = sum(
        len(entries) for cat, entries in changelog.categories.items()
        if cat not in important_cats
    )
    if other_count:
        lines.append(f"_Plus {other_count} other changes_")

    return "\n".join(lines)


def render_plain_text(changelog: CategorizedChangelog) -> str:
    """Render as plain text."""
    lines = [
        f"Release {changelog.version} ({changelog.date})",
        "=" * 50,
        "",
    ]

    for cat, entries in changelog.categories.items():
        lines.append(f"{cat}:")
        for entry in entries:
            scope = f"[{entry.scope}] " if entry.scope else ""
            lines.append(f"  - {scope}{entry.description}")
        lines.append("")

    if changelog.contributors:
        lines.append(f"Contributors: {', '.join(changelog.contributors)}")
        lines.append("")

    lines.append(f"Total commits: {changelog.total_commits}")

    return "\n".join(lines)


def render_html(changelog: CategorizedChangelog) -> str:
    """Render as self-contained HTML page."""
    h = html.escape

    lines = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8">',
        f"<title>Release {h(changelog.version)}</title>",
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }",
        "h1 { color: #111; border-bottom: 2px solid #eee; padding-bottom: 10px; }",
        "h2 { color: #444; margin-top: 24px; }",
        "ul { padding-left: 20px; }",
        "li { margin: 6px 0; line-height: 1.5; }",
        ".scope { background: #e8f0fe; padding: 1px 6px; border-radius: 3px; font-size: 0.85em; color: #1a73e8; }",
        ".pr { color: #888; font-size: 0.85em; }",
        ".breaking { color: #d32f2f; font-weight: bold; }",
        ".contributors { margin-top: 24px; padding: 16px; background: #f8f9fa; border-radius: 8px; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>Release {h(changelog.version)}</h1>",
        f"<p><strong>Date:</strong> {h(changelog.date)} | <strong>Commits:</strong> {changelog.total_commits}</p>",
    ]

    for cat, entries in changelog.categories.items():
        lines.append(f"<h2>{h(cat)}</h2>")
        lines.append("<ul>")
        for entry in entries:
            scope_html = f'<span class="scope">{h(entry.scope)}</span> ' if entry.scope else ""
            pr_html = ""
            if entry.commit.pr_numbers:
                pr_refs = ", ".join(f"#{n}" for n in entry.commit.pr_numbers)
                pr_html = f' <span class="pr">({pr_refs})</span>'
            breaking_html = ""
            if entry.is_breaking:
                breaking_html = ' <span class="breaking">BREAKING</span>'
            lines.append(f"<li>{scope_html}{h(entry.description)}{pr_html}{breaking_html}</li>")
        lines.append("</ul>")

    if changelog.contributors:
        lines.append('<div class="contributors">')
        lines.append(f"<strong>Contributors:</strong> {', '.join(h(c) for c in changelog.contributors)}")
        lines.append("</div>")

    lines.extend(["</body>", "</html>"])
    return "\n".join(lines)
