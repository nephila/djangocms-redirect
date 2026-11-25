## 2026-11-25 — Support Django 4.2/5.2, Python 3.11/3.13, django CMS 3.11
**What:** Replaced the support matrix with py{311,313} x django{42,52} x cms311 in tox, CI, package metadata, tooling targets and RTD; no package code changed.
**Why:** Django 3.2/4.1, django CMS 3.9 and Python 3.9/3.10 are EOL; Django 5.2 and Python 3.13 were untested, and CI excluded django42+cms311 entirely.
**Decisions:** Branch cut from `origin/develop` (local `develop` was 112 commits behind). CI uses `py-django<d>-cms<c>` so tox picks each job's interpreter (GitHub expressions have no `replace()`). `django-cms>=3.11,<4` capped after review; docs tox env pinned the same way because the `django<6` docs extra otherwise pulled django CMS 5. Dropped the "Django < 4.2" blocks in docs/usage.rst.
**Agent usage:**

| Stage | Agent/skill | Tokens | Time |
|---|---|---|---|
| Design | superpowers:brainstorming + writing-plans | ≈25k | ≈10m |
| Implementation | superpowers:executing-plans (inline) | ≈60k | ≈20m |
| Review | general subagent (opus) whole-branch review | ≈80k | ≈1m |
| Review | nephila code-eval | ≈8k | ≈2m |

**Considered & dropped:** Keeping old versions alongside (user chose to drop); CI-only Django 5.2 without declaring it.
**Follow-ups:** Check first GitHub Actions run is green on all 4 jobs; rename `changes/+django52-py313.feature` to the PR number (repo `towncrier-check` needs a numbered branch/fragment); pre-existing migration drift (`id` AutoField vs BigAutoField, also on Django 4.2) and 28 ruff errors left alone; py313+django42 is not officially supported upstream; `publish.yml` still uses old actions.
**Refs:** Eval: 76% — artifacts/evaluations/2026-11-25-django-52-py313-support.md
