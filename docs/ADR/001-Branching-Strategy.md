---
title: '001: Trunk-Based Development for Recify'
---

## Status

Accepted

## Context

Recify is a recipe management system built with event-driven architecture:

- **Team Size**: 3 developers
- **Architecture**: Event-driven with RabbitMQ message broker
- **Components**: Instagram Crawler, Recipe Schema Converter, MongoDB, Web UI

### Why We Need a Strategy

1. **Clean History**: We want to easily track what changed when, and quickly identify bugs
2. **Simple Collaboration**: With 3 developers, we need a straightforward workflow without overhead
3. **Easy Rollbacks**: If a feature breaks, we should be able to revert it cleanly

### Alternatives Considered

- **GitFlow**: Too complex for a 3-person team
- **Merge Commits**: Creates messy history
- **Direct Commits to Main**: No code review safety net

## Decision

We will use **Trunk-Based Development with Rebase and Squash**:

### Branch Naming

1. **Main Branch (`main`)**:
   - Always deployable
   - Protected (requires pull request + approval)

2. **Feature Branches**:
   - Format: `feature/<component>-<brief-description>`
   - Examples:
     - `feature/crawler-instagram-auth`
     - `feature/ui-recipe-search`
   - Keep them short-lived (1-2 days max)

3. **Hotfix Branches**:
   - Format: `hotfix/<brief-description>`
   - Merge and deploy immediately

### Workflow

1. **Create branch** from latest `main`
   ```bash
   git checkout main && git pull
   git checkout -b feature/ui-recipe-filters
   ```

2. **Work and commit** freely on your branch

3. **Before creating PR, rebase** on `main`:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

4. **Create pull request** and get 1 approval from another team member

5. **Squash and merge** - all commits become one clean commit on `main`

### Commit Message Format

When squashing, use this format:
```
[Component] Brief description

What changed:
- Key point 1
- Key point 2

Breaking changes: (if any)
```

Example:
```
[Crawler] Add Instagram authentication

What changed:
- Implement OAuth2 flow
- Add credential storage
- Handle token refresh
```

## Consequences

### Benefits

1. **Clean linear history** - easy to understand and debug
2. **Simple rollbacks** - each feature is one commit
3. **Fast integration** - no long-lived branches
4. **Better reviews** - small, focused PRs

### Trade-offs

1. **Learning rebase** - needs practice (but we're only 3 people)
2. **Lost commit details** - branch commits are squashed (keep good squash messages)

### Guidelines

- Keep PRs small and focused
- Rebase daily if your branch lives more than a day
- Communicate before working on the same component
- If unsure about rebasing, ask for help!