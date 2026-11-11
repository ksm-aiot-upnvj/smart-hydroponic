# Contributing Guide

This project uses Conventional Commits and separate release automation for backend and frontend.
Following the rules below keeps changelogs and releases accurate.

## Branching Rules

1. Create feature branches from `main`.
2. Use short branch names that explain intent, for example:
	- `feat/backend-auth-refresh`
	- `fix/frontend-dashboard-chart`
3. Keep one topic per branch.

## Commit Message Rules

Use this format:

`<type>(<scope>): <summary>`

Allowed types:

- `feat`
- `fix`
- `perf`
- `refactor`
- `docs`
- `ci`
- `chore`
- `test`
- `build`

Recommended scopes for this repository:

- `backend`
- `frontend`
- `frontend-ui`
- `frontend-web`
- `shared`
- `infra`

Examples:

- `feat(backend): add token rotation endpoint`
- `fix(frontend): handle websocket reconnect`
- `refactor(frontend-ui): simplify topbar state handling`
- `docs(shared): update deployment steps`

## Release-Aware Rules

1. Backend-impacting changes should use `scope=backend`.
2. Frontend-impacting changes should use `scope=frontend`, `frontend-ui`, or `frontend-web`.
3. Avoid mixed backend and frontend changes in one commit.
4. If one PR must include both areas, split into separate commits with correct scopes.

## Pull Request Rules

1. Rebase or merge latest `main` before opening PR.
2. Keep PR title aligned with Conventional Commits.
3. Describe:
	- What changed
	- Why it changed
	- How it was tested
4. Link related issues when applicable.

## Local Backend Runs and `.env`

The repository root `.env` is the single source of configuration. `backend/config/config.py`
loads the `.env` file found in the current working directory, so:

1. Keep only the root `.env`. Do not create a second, conflicting `backend/.env`.
2. Prefer running the backend from the repository root so the root `.env` is loaded:

   ```bash
   uv run --project backend uvicorn --app-dir backend main:app --reload
   ```

3. If you must run from `backend/`, point the tool at the root file explicitly:

   ```bash
   uv run uvicorn main:app --reload --env-file ../.env
   ```

Docker Compose injects the same variables as process environment variables, which
take precedence over any `.env` file, so container behaviour is unaffected.

## Validation Before Push

1. For backend changes, run backend checks/tests.
2. For frontend changes, run frontend checks/tests.
3. Ensure CI workflows pass before requesting final review.

## Collaboration Rules

1. Do not force-push shared branches unless agreed by the team.
2. Prefer small, reviewable PRs.
3. Resolve review comments with follow-up commits, then squash only if the team prefers squash merge.
4. Keep commit history readable and focused on user-facing impact.
