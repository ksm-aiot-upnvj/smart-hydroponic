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

The repository installs Git hooks that run the same quality gates as CI, so a
normal `git commit` / `git push` is enough to catch problems early. See
[Git Hooks](#git-hooks) below.

1. For backend changes, run backend checks/tests.
2. For frontend changes, run frontend checks/tests.
3. Ensure CI workflows pass before requesting final review.

## Git Hooks

Hooks are managed with the [`pre-commit`](https://pre-commit.com) framework.
A single `.pre-commit-config.yaml` covers both toolchains through
`language: system` hooks, so the repository does not need a second, overlapping
manager (for example Husky) and does not need a POSIX shell script on Windows.

### Required tooling

1. `uv` — the hooks call the backend tools through `uv`.
2. `npm` with `frontend-vue/node_modules` installed (`npm --prefix frontend-vue install`).

### Installation

Run once from the repository root:

```bash
uv run --project backend pre-commit install
```

`default_install_hook_types` in `.pre-commit-config.yaml` installs both the
`pre-commit` and the `pre-push` hook. The command is idempotent and does not
change unrelated Git configuration. CI does not depend on this step; the hooks
only guard local commits and pushes.

### What runs before commit (fast, staged files only)

1. `ruff check` on staged backend Python files.
2. `ruff format --check` on staged backend Python files.
3. `vue-tsc -b` type check when frontend files are staged.

### What runs before push (full gates, mirrors CI)

1. `uv run --directory backend ruff check .`
2. `uv run --directory backend ruff format --check .`
3. `uv run --directory backend pytest -q`
4. `npm --prefix frontend-vue run build` (`vue-tsc -b && vite build`)

### Running the checks manually

```bash
uv run --project backend pre-commit run --hook-stage pre-commit
uv run --project backend pre-commit run --hook-stage pre-push --all-files
```

### Troubleshooting

1. `pre-commit` not found — run `uv sync --project backend`, the tool is a dev dependency.
2. Hook does not run — reinstall with `uv run --project backend pre-commit install`.
3. Frontend hooks fail with a missing `node_modules` — run `npm --prefix frontend-vue install`.
4. Bypassing hooks with `--no-verify` is discouraged and should only be used in an emergency.

## Collaboration Rules

1. Do not force-push shared branches unless agreed by the team.
2. Prefer small, reviewable PRs.
3. Resolve review comments with follow-up commits, then squash only if the team prefers squash merge.
4. Keep commit history readable and focused on user-facing impact.
