# Support Django 4.2 / 5.2, Python 3.11 / 3.13, django CMS 3.11 — design

Date: 2026-11-25
Language: English (confirmed)

## Intent
Keep `djangocms-redirect` maintained on currently supported stacks and drop EOL ones.

## Goals
- Officially support Django 4.2 and 5.2, Python 3.11 and 3.13, latest django CMS 3.11.x.
- Test every combination in tox and CI.
- Drop Django 3.2/4.1, django CMS 3.9, Python 3.9/3.10.

## Non-goals
- Version bump / release (handled via bump-my-version).
- The stale `feature/django-42` branch.
- Python 3.12 (not requested).

## Constraints
- Django 5.2 requires Python >= 3.10.
- django CMS 3.11.11 declares Django <= 5.1 and Python <= 3.12; 5.2 / 3.13 are verified empirically.

## Approaches
1. **Declare new matrix everywhere, test, fix code only if needed (chosen).**
2. Keep old versions alongside: rejected (user chose to drop them; larger CI matrix).
3. Add 5.2 to CI only without declaring support: rejected (hides support from users).

## Design
- Matrix: py{311,313} x django{42,52} x cms311 (4 jobs).
- `tox.ini`: envlist/deps; CMS from the release/3.11.x branch.
- `.github/workflows/test.yml`: new matrix, remove the `django42+cms311` exclusion (bug), bump outdated actions.
- `setup.cfg`: classifiers, `python_requires >= 3.11`, `django-cms>=3.11`.
- `pyproject.toml`: black/ruff target versions.
- Docs/README version mentions; towncrier fragment in `changes/`.
- Code in `djangocms_redirect/`: expected unchanged; minimal fix if a combination fails.
- If failure is caused by django CMS itself on Django 5.2, stop and ask.
