# Evaluation — cached-redirect-table

- **Date:** 2026-11-25
- **Branch:** feature/156-cached-redirect-table (origin/develop..cb10952, 5 commits)
- **Task:** GitHub issue 156
- **Coverage:** full (table.py, middleware.py, models.py, tests, docs)

## Scores
| Dimension | Score | Weight | Key evidence |
|---|---|---|---|
| Functionality | 4 | 20 | `TestCachedTable`: 0 redirect queries for 5 distinct unknown paths when warm, 1 when cold; 57 tests green on py311-dj42 and py313-dj52; not run against a real memcached/redis |
| Testing | 4 | 15 | Tests written first and seen failing (ImportError, then 8/8 assertion failures); race, memo expiry, failed load, DummyCache, on-commit and site-move covered; two helpers read `cache._cache` (locmem-only) |
| Security | N/A | 15 | No input handling or trust-boundary change |
| Code quality | 4 | 15 | black/isort pass, ruff findings 28 -> 27 (none new); `utils.get_key_from_path_and_site` left as now-unused public helper |
| Maintainability | 4 | 15 | Cache logic isolated in `table.py` (`get_table`/`invalidate_site`), middleware reduced to ~15 lines; module-level memo is process-global state |
| Error handling | 4 | 10 | Failed load raises before `cache.set` (`test_failed_load_caches_nothing`); missing token and DummyCache degrade to a reload |
| Documentation | 4 | 10 | `docs/installation.rst` new setting + "How caching works" (bulk caveat, size limit, per-site matching); news fragments `156.feature`, `156.bugfix` |

## Recommendations
None required (all dimensions >= 4).

## Total
**80%** — Behavior verified by tests on two matrix corners and reviewed once by a fresh reviewer (commit-ordering race found and fixed); remaining gaps are real-backend verification and MySQL case-insensitive exact matching.
