# logbook

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-blue?logo=anthropic&logoColor=white)](https://claude.ai/code)


**Your git history already has a changelog. Extract it.**

Generate beautiful changelogs from git commits. Understands conventional commits, groups by category, enriches with PR links, and optionally polishes with AI.

```
$ logbook generate --from v1.0.0

## [Unreleased - 2026-03-24]

### Added

- **auth:** Add OAuth2 PKCE flow for mobile clients (#142)
- **api:** Support batch operations in REST endpoints (#138)
- Add WebSocket real-time notifications (#135)

### Fixed

- **cache:** Fix race condition in Redis cache invalidation (#141)
- Fix memory leak in long-running workers (#139)

### Changed

- **perf:** Reduce cold start time by 60% with lazy loading (#140)

### Security

- Upgrade jsonwebtoken to patch CVE-2026-1234 (#143)
```

## Why?

- Writing changelogs by hand is **tedious** and always falls behind
- Your **git history already contains** all the information
- Conventional commits make it **automatic** -- this tool does the rest
- Need a Slack announcement? GitHub Release? HTML page? **One command**

## Install

```bash
pip install logbook-gen

# Optional: AI polishing
pip install logbook-gen[ai]

# Optional: GitHub PR enrichment
pip install logbook-gen[github]
```

## Usage

### Generate changelog

```bash
# From latest tag to HEAD
logbook generate

# Between specific tags
logbook generate --from v1.0.0 --to v2.0.0

# Set version name
logbook generate --version v2.1.0

# Different output styles
logbook generate --style keepachangelog
logbook generate --style github
logbook generate --style slack
logbook generate --style html
logbook generate --style plain

# Save to file
logbook generate -o CHANGELOG.md
```

### Draft unreleased changes

```bash
logbook draft
```

### Publish full changelog

```bash
# Generate changelog from all tags
logbook publish -o CHANGELOG.md

# With GitHub PR enrichment
logbook publish --enrich
```

### AI-powered summaries

```bash
# Requires OPENAI_API_KEY
logbook generate --ai
```

## Commit Format

Works best with [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(auth): add SSO support
fix(api): handle null response from upstream
perf: reduce bundle size by 40%
docs: update API reference
BREAKING CHANGE: remove deprecated v1 endpoints
```

Also works with regular commits using keyword detection (fix, add, update, etc.).

## Output Styles

| Style | Use Case |
|-------|----------|
| `keepachangelog` | CHANGELOG.md (Added/Changed/Fixed/Security) |
| `github` | GitHub Releases with emoji headers |
| `slack` | Condensed Slack announcement |
| `plain` | Plain text |
| `html` | Self-contained HTML page |

## License

MIT
