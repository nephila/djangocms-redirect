# Django 5.2 / Python 3.13 Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Declare and test support for Django 4.2/5.2, Python 3.11/3.13 and django CMS 3.11.x, dropping Django 3.2/4.1, CMS 3.9 and Python 3.9/3.10.

**Architecture:** Metadata/config-only change (tox, CI, setup.cfg, pyproject, RTD, news fragment). Package code is touched only if a matrix combination fails the existing test suite.

**Tech Stack:** Python, Django, django CMS 3.11, tox (>4), django-app-helper, GitHub Actions, towncrier.

**Spec:** `artifacts/specs/2026-11-25-django-52-py313-support-design.md`

**Base branch:** `origin/develop` (local `develop` was 112 commits behind; work branch `feature/django-52-py313-support` is cut from `origin/develop`).

## Global Constraints

- Matrix: py{311,313} x django{42,52} x cms311 (4 jobs); nothing else.
- Dropped: Django 3.2/4.1, django CMS 3.9, Python 3.9/3.10 (and 3.6-era `python_requires`).
- `python_requires >= 3.11`; `django-cms>=3.11`.
- django CMS installed from the `release/3.11.x` branch zip (as today).
- No version bump or release; no changes to `feature/django-42`.
- If a failure is caused by django CMS itself on Django 5.2, stop and ask the user.
- All text in English.

## Review Focus

- Django 5.2 + CMS 3.11.x import/startup failure (CMS declares Django <= 5.1): covered by Task 1 test run.
- Python 3.13 failure from removed stdlib modules in dependencies (e.g. `python-memcached`, `mock`): Task 1.
- CI matrix silently excluding the target combo (old `django42+cms311` exclusion): Task 2 verification greps the matrix.
- Migrations check under Django 5.2 (`makemigrations --check`): Task 1.
- Stale `target-version`/RTD python leaving old floors in tooling: Task 3.

---

### Task 1: tox matrix and green test run

**Files:**
- Modify: `tox.ini` (envlist, `[testenv] deps`)
- Modify: `requirements-test.txt` only if a dependency breaks on 3.13
- Modify (only if a combination fails): `djangocms_redirect/*.py`, `tests/*.py`

**Interfaces:**
- Produces: tox env names `py{311,313}-django{42,52}-cms311`, used by Task 2's CI matrix.

- [ ] **Step 1: Edit `tox.ini`**: replace both `py{...}` envlist lines with `py{313,311}-django{52,42}-cms{311}`; in `deps` remove `django32`, `django41`, `cms39` lines and add `django52: Django~=5.2.0`.
- [ ] **Step 2: Run each env**: `tox -e py311-django42-cms311,py311-django52-cms311,py313-django42-cms311,py313-django52-cms311`. Expected: all pass (existing `tests/test_middleware.py`, `tests/tests_admin.py`).
- [ ] **Step 3: For any failure**, diagnose root cause (systematic-debugging). Package-side fix: minimal change, plus a regression test if behavior changed. CMS-side failure on Django 5.2: STOP and surface to the user. Dependency-side failure (e.g. 3.13): pin/replace in `requirements-test.txt`.
- [ ] **Step 4: Check migrations**: `python cms_helper.py djangocms_redirect makemigrations --check --dry-run` inside the `py313-django52-cms311` env. Expected: "No changes detected". If changes are detected, stop and surface (do not add migrations without approval).
- [ ] **Step 5: Re-run all four envs**; expected all green.

### Task 2: CI workflow

**Files:**
- Modify: `.github/workflows/test.yml`
- Modify: `.github/workflows/lint.yml` (bump action versions only if outdated)

**Interfaces:**
- Consumes: tox env naming from Task 1.

- [ ] **Step 1: Edit matrix** in `test.yml`: `python-version: ["3.13", "3.11"]`, `django: [52, 42]`, `cms: [311]`, delete the whole `exclude:` block (it blocks `django42+cms311`).
- [ ] **Step 2: Fix the tox env name**: `TOX_ENV` currently omits the Python version (`py-django..`); make it `py<ver without dot>-django<d>-cms<c>` (e.g. via `format('py{0}-django{1}-cms{2}', replace(matrix.python-version, '.', ''), ...)`) so each job runs its own interpreter. Apply the same to the tox cache key.
- [ ] **Step 3: Bump outdated actions** (`checkout`, `setup-python`, `cache`, `codecov-action`) to current majors.
- [ ] **Step 4: Verify**: `python -c "import yaml;print(yaml.safe_load(open('.github/workflows/test.yml'))['jobs']['test']['strategy']['matrix'])"` shows exactly 2x2x1 with no `exclude`; also run `actionlint` if available.

### Task 3: Package metadata, tooling targets, docs, news fragment

**Files:**
- Modify: `setup.cfg` (classifiers, `python_requires`, `install_requires`, docs extra)
- Modify: `pyproject.toml` (`[tool.black] target-version`, `[tool.ruff] target-version`)
- Modify: `.readthedocs.yml` (python version)
- Modify: `docs/` / `README.rst` only if they state supported versions (current grep: none)
- Create: `changes/<n>.feature` (towncrier; follow existing HISTORY.rst style: one sentence, no ticket-less number conflicts — use the next free number, or `+django52.feature` orphan form if no issue exists)

- [ ] **Step 1: `setup.cfg`**: classifiers = Django 4.2 and 5.2; Python 3.11, 3.12 omitted, 3.13 added; `python_requires = >=3.11`; `django-cms>=3.11`; docs extra `django<6`.
- [ ] **Step 2: `pyproject.toml`**: black `target-version = ["py311"]`, ruff `target-version = "py311"`.
- [ ] **Step 3: `.readthedocs.yml`**: `python: "3.13"`.
- [ ] **Step 4: Add news fragment** "Add support for Django 5.2 and Python 3.13; drop Django < 4.2, django CMS 3.9 and Python < 3.11."
- [ ] **Step 5: Verify**: `towncrier build --draft` renders the fragment; `tox -e pypi-description,towncrier` pass; `pre-commit run --all-files` clean.
