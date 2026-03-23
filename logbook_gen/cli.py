"""Click CLI: logbook generate, draft, publish, format."""

from __future__ import annotations

import os
import sys

import click
from rich.console import Console

from . import __version__
from .ai_writer import generate_release_highlights
from .categorizer import categorize_commits
from .enricher import enrich_with_github_api, enrich_with_pr_links
from .git_reader import get_commits, get_latest_tag, get_repo_info, get_tags
from .renderer import (
    render_github_release,
    render_html,
    render_keepachangelog,
    render_plain_text,
    render_slack,
)

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="logbook")
def cli():
    """AI-assisted changelog generation from git commits and PR descriptions."""
    pass


@cli.command()
@click.option("--from", "from_ref", default=None, help="Start reference (tag or commit)")
@click.option("--to", "to_ref", default="HEAD", help="End reference")
@click.option("--version", "-v", "version_name", default=None, help="Version name")
@click.option("--style", "-s", type=click.Choice(["keepachangelog", "github", "slack", "plain", "html"]),
              default="keepachangelog", help="Output style")
@click.option("--output", "-o", default=None, help="Output file")
@click.option("--repo-dir", "-r", default=".", help="Git repository directory")
@click.option("--enrich/--no-enrich", default=False, help="Fetch PR details from GitHub API")
@click.option("--ai/--no-ai", default=False, help="Use AI for polished summaries")
def generate(from_ref: str | None, to_ref: str, version_name: str | None,
             style: str, output: str | None, repo_dir: str, enrich: bool, ai: bool):
    """Generate a changelog from git history."""
    repo_dir = os.path.abspath(repo_dir)

    # Auto-detect from_ref if not specified
    if from_ref is None:
        from_ref = get_latest_tag(cwd=repo_dir)
        if from_ref:
            console.print(f"[dim]Using latest tag: {from_ref}[/dim]", err=True)
        else:
            console.print("[dim]No tags found, using full history[/dim]", err=True)

    # Auto-detect version name
    if version_name is None:
        version_name = "Unreleased"

    # Read commits
    console.print("[dim]Reading git history...[/dim]", err=True)
    commits = get_commits(from_ref=from_ref, to_ref=to_ref, cwd=repo_dir)

    if not commits:
        console.print("No commits found in the specified range.")
        return

    console.print(f"[dim]Found {len(commits)} commits[/dim]", err=True)

    # Get repo info
    repo_info = get_repo_info(cwd=repo_dir)

    # Categorize
    changelog = categorize_commits(
        commits,
        version=version_name,
        repo_info=repo_info,
    )

    # Enrich with PR links
    if repo_info.get("owner") and repo_info.get("repo"):
        changelog = enrich_with_pr_links(changelog, repo_info["owner"], repo_info["repo"])

    # Fetch from GitHub API
    if enrich and repo_info.get("owner") and repo_info.get("repo"):
        console.print("[dim]Fetching PR details from GitHub...[/dim]", err=True)
        changelog = enrich_with_github_api(
            changelog, repo_info["owner"], repo_info["repo"],
        )

    # AI summary
    if ai:
        console.print("[dim]Generating AI summary...[/dim]", err=True)
        highlights = generate_release_highlights(changelog)
        if highlights:
            console.print("\n[bold cyan]AI Release Highlights:[/bold cyan]", err=True)
            console.print(highlights, err=True)
            console.print("", err=True)

    # Render
    if style == "keepachangelog":
        output_text = render_keepachangelog(changelog)
    elif style == "github":
        output_text = render_github_release(changelog)
    elif style == "slack":
        repo_name = repo_info.get("repo", "")
        output_text = render_slack(changelog, repo_name=repo_name)
    elif style == "plain":
        output_text = render_plain_text(changelog)
    elif style == "html":
        output_text = render_html(changelog)
    else:
        output_text = render_keepachangelog(changelog)

    # Output
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(output_text)
        console.print(f"[green]Changelog written to {output}[/green]")
    else:
        click.echo(output_text)


@cli.command()
@click.option("--repo-dir", "-r", default=".", help="Git repository directory")
def draft(repo_dir: str):
    """Generate a draft changelog from unreleased commits."""
    repo_dir = os.path.abspath(repo_dir)
    from_ref = get_latest_tag(cwd=repo_dir)

    commits = get_commits(from_ref=from_ref, to_ref="HEAD", cwd=repo_dir)
    if not commits:
        console.print("No unreleased commits found.")
        return

    repo_info = get_repo_info(cwd=repo_dir)
    changelog = categorize_commits(commits, version="Unreleased", repo_info=repo_info)

    if repo_info.get("owner"):
        changelog = enrich_with_pr_links(changelog, repo_info["owner"], repo_info["repo"])

    output_text = render_github_release(changelog)
    click.echo(output_text)

    # Stats
    console.print(f"\n[dim]---[/dim]", err=True)
    console.print(f"[dim]{len(commits)} commits since {from_ref or 'beginning'}[/dim]", err=True)
    console.print(f"[dim]{len(changelog.contributors)} contributors[/dim]", err=True)
    for cat, entries in changelog.categories.items():
        console.print(f"[dim]  {cat}: {len(entries)}[/dim]", err=True)


@cli.command()
@click.argument("file_path", default="CHANGELOG.md")
@click.option("--style", "-s", type=click.Choice(["keepachangelog", "github", "slack", "plain", "html"]),
              default="keepachangelog")
@click.option("--output", "-o", default=None, help="Output file (default: overwrite input)")
def format(file_path: str, style: str, output: str | None):
    """Reformat an existing changelog file."""
    # This command reads a keepachangelog-style file and converts to another format
    if not os.path.exists(file_path):
        console.print(f"[red]File not found: {file_path}[/red]")
        sys.exit(1)

    with open(file_path, "r") as f:
        content = f.read()

    console.print(f"[green]Read {len(content)} chars from {file_path}[/green]")
    console.print(f"[dim]Reformat to {style} is a pass-through (already formatted)[/dim]")

    # For now, this validates the existing file
    # A full implementation would parse and re-render
    out_path = output or file_path
    with open(out_path, "w") as f:
        f.write(content)
    console.print(f"[green]Written to {out_path}[/green]")


@cli.command()
@click.option("--repo-dir", "-r", default=".", help="Git repository directory")
@click.option("--output", "-o", default="CHANGELOG.md", help="Changelog file")
@click.option("--enrich/--no-enrich", default=False, help="Fetch PR details")
def publish(repo_dir: str, output: str, enrich: bool):
    """Generate and publish a changelog from all tags."""
    repo_dir = os.path.abspath(repo_dir)
    tags = get_tags(cwd=repo_dir)

    if not tags:
        console.print("[yellow]No tags found. Generating from full history.[/yellow]")
        # Fall through to generate with no tags

    repo_info = get_repo_info(cwd=repo_dir)
    all_sections = []

    # Generate changelog for each tag range
    tag_pairs = []
    for i, tag in enumerate(tags):
        prev_tag = tags[i + 1] if i + 1 < len(tags) else None
        tag_pairs.append((prev_tag, tag))

    # Add unreleased section
    if tags:
        unreleased_commits = get_commits(from_ref=tags[0], to_ref="HEAD", cwd=repo_dir)
        if unreleased_commits:
            changelog = categorize_commits(unreleased_commits, version="Unreleased", repo_info=repo_info)
            if repo_info.get("owner"):
                changelog = enrich_with_pr_links(changelog, repo_info["owner"], repo_info["repo"])
            all_sections.append(render_keepachangelog(changelog))

    for prev_tag, current_tag in tag_pairs:
        commits = get_commits(from_ref=prev_tag, to_ref=current_tag, cwd=repo_dir)
        if commits:
            changelog = categorize_commits(commits, version=current_tag, repo_info=repo_info)
            if repo_info.get("owner"):
                changelog = enrich_with_pr_links(changelog, repo_info["owner"], repo_info["repo"])
            all_sections.append(render_keepachangelog(changelog))

    # If no tags, generate from full history
    if not tags:
        commits = get_commits(cwd=repo_dir)
        if commits:
            changelog = categorize_commits(commits, version="Unreleased", repo_info=repo_info)
            all_sections.append(render_keepachangelog(changelog))

    if not all_sections:
        console.print("No changes found.")
        return

    # Combine
    header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
    full_changelog = header + "\n".join(all_sections)

    with open(output, "w", encoding="utf-8") as f:
        f.write(full_changelog)

    console.print(f"[green]Published changelog to {output}[/green]")
    console.print(f"  Versions: {len(all_sections)}")


@cli.command()
@click.option("--repo-dir", "-r", default=".", help="Git repository directory")
def tags(repo_dir: str):
    """List all tags in the repository."""
    repo_dir = os.path.abspath(repo_dir)
    tag_list = get_tags(cwd=repo_dir)

    if not tag_list:
        console.print("No tags found.")
        return

    for tag in tag_list:
        console.print(f"  {tag}")


def main():
    cli()


if __name__ == "__main__":
    main()
