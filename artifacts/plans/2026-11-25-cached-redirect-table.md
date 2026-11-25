# Cached Redirect Table Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A 404 for an unknown path costs zero DB queries once warm, by caching one redirect table per site, resolved in memory, with token-based invalidation and a short in-process memo.

**Architecture:** New module `djangocms_redirect/table.py` owns building, caching (token + memo) and resolving the per-site table. `RedirectMiddleware.do_redirect` calls it instead of per-path cache + queries. `models.py` signal handler invalidates through it.

**Tech Stack:** Django 4.2/5.2 cache framework, django CMS 3.11, django-app-helper test runner (`python cms_helper.py djangocms_redirect test`), towncrier.

**Spec:** `artifacts/specs/2026-11-25-cached-redirect-table-design.md`

## Global Constraints

- Public settings unchanged: `DJANGOCMS_REDIRECT_404_ONLY`, `DJANGOCMS_REDIRECT_USE_REQUEST`, `DJANGOCMS_REDIRECT_CACHE_TIMEOUT` (default 3600). New: `DJANGOCMS_REDIRECT_MEMO_TIMEOUT` (default 5, `0` disables).
- Cache keys: `CMSREDIRECT:VERSION:<site_id>` (timeout `None`, value = `uuid.uuid4().hex`), `CMSREDIRECT:TABLE:<site_id>:<token>` (timeout `DJANGOCMS_REDIRECT_CACHE_TIMEOUT`).
- Table = `{"exact": {old_path: entry}, "substring": [entry, ...]}`; entry = `{"old_path","new_path","response_code","subpath_match","catchall_redirect"}`; `exact` has every row of the site; `substring` has `subpath_match`/`catchall_redirect` rows sorted by `old_path` descending.
- Resolution order unchanged: per candidate in `possible_paths`, exact first, then substring; `subpath_match` rewrite on a copy (`original_path.replace(old_path, new_path)`).
- Responses unchanged: 301/302 with query string, 410, `new_path == ""` gone.
- Table keyed by `current_site.pk`. `utils.get_key_from_path_and_site` stays, unused by the middleware.
- A failed table load caches nothing (exception propagates, no retry).
- Matrix unchanged (Django 4.2/5.2, Python 3.11/3.13, CMS 3.11). Run tests: `tox -e py313-django52-cms311` (all) or inside an env `python cms_helper.py djangocms_redirect test <label>`.
- English everywhere; commits Conventional, ending with the Co-Authored-By line from the session.

## Review Focus

- Edited redirect moved to another site: old site's table must not keep serving it (Task 3 test `test_site_change_invalidates_both_sites`).
- Cache backend that never stores (DummyCache): token differs per call, table reloaded each time, still correct (Task 2 test `test_dummy_cache_still_resolves`).
- Evicted/missing token: new token created, table reloaded, no stale revival (Task 2).
- `old_path` with quotes/unicode and slash variants resolve exactly as before (Task 3, existing tests kept).
- Bulk `.update()`/`.delete()` send no signals: bounded by timeout; documented (Task 4), not tested.

---

### Task 1: Table build and in-memory resolution

**Files:**
- Create: `djangocms_redirect/table.py`
- Test: `tests/test_table.py`

**Interfaces:**
- Produces: `build_table(site_id: int) -> dict` (one query), `match_path(table: dict, path: str) -> dict | None` (returns an entry copy; for `subpath_match` entries `new_path` is already rewritten for `path`).

- [ ] **Step 1: Write failing tests** (`BaseRedirectTest`, `Redirect` rows via ORM, `self.site_1`/`self.site_2` as in existing tests): `test_build_table_one_query` (`assertNumQueries(1)`, `exact` has all rows of the site only, none of site 2); `test_substring_sorted_desc` (rows `/a/`, `/a/b/`, `/a/b/c/` all catchall → `substring` old_paths descending); `test_match_exact`; `test_match_exact_ignores_subpath_flag` (row with `subpath_match=True` matched exactly returns `new_path` unrewritten); `test_match_subpath_rewrite_does_not_mutate_table` (`/old/x` vs row `/old` → `/new/x`, table entry `new_path` still `/new`); `test_match_catchall`; `test_match_longest_prefix_first`; `test_match_none`.
- [ ] **Step 2: Run** `python cms_helper.py djangocms_redirect test tests.test_table`. Expected: FAIL (ImportError `table`).
- [ ] **Step 3: Implement** both functions in `djangocms_redirect/table.py`; build from `Redirect.objects.filter(site_id=site_id).values(...)`; `match_path` checks `exact` then iterates `substring` with `path.startswith(old_path)`; return `dict(entry)` copy.
- [ ] **Step 4: Run** the same label. Expected: PASS.
- [ ] **Step 5: Commit** `feat: add per-site redirect table build and matching`.

### Task 2: Caching layer (token, cache, memo, invalidation)

**Files:**
- Modify: `djangocms_redirect/table.py`
- Test: `tests/test_table.py`

**Interfaces:**
- Consumes: `build_table`.
- Produces: `get_table(site_id: int) -> dict`; `invalidate_site(site_id: int) -> None` (rotates token, drops memo for the site); `clear_memo() -> None`; module-level `_now = time.monotonic` (patchable clock).

- [ ] **Step 1: Write failing tests**: `test_cold_one_query_then_zero` (`assertNumQueries(1)` then `(0)`); `test_failed_load_caches_nothing` (patch `djangocms_redirect.table.build_table` to raise once → exception propagates; next call succeeds and queries once; no `CMSREDIRECT:TABLE:*` key stored); `test_invalidate_reloads` (create row after warm, `invalidate_site`, next `get_table` contains it); `test_memo_serves_without_cache_roundtrip` (patch `django.core.cache.cache.get` call count / use `assertNumQueries(0)` plus a counting wrapper: second call performs 0 cache gets with memo on); `test_memo_expires` (patch `table._now`; after timeout the cache is consulted again); `test_memo_timeout_zero_disables` (`override_settings(DJANGOCMS_REDIRECT_MEMO_TIMEOUT=0)`); `test_stale_loader_race` (start load with token T1 via patched `build_table` that calls `invalidate_site` mid-load → stored under T1, next `get_table` loads again under T2 and returns fresh data); `test_missing_token_reloads` (delete the VERSION key → new token, table rebuilt); `test_dummy_cache_still_resolves` (`override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})`, returns correct table).
- [ ] **Step 2: Run** `python cms_helper.py djangocms_redirect test tests.test_table`. Expected: new tests FAIL.
- [ ] **Step 3: Implement** `get_table`: memo hit (fresh by `_now()`) → return; else read token (`cache.get`, on miss `cache.add(key, uuid4().hex, None)` then `cache.get(key)` falling back to the new token), `cache.get(table_key)`; on miss `build_table` then `cache.set(table_key, table, timeout)`; store in memo when timeout > 0. `invalidate_site`: `cache.set(version_key, uuid4().hex, None)` and pop memo entry.
- [ ] **Step 4: Run** the label. Expected: PASS.
- [ ] **Step 5: Commit** `feat: cache the redirect table with a version token and in-process memo`.

### Task 3: Middleware, signals and existing test updates

**Files:**
- Modify: `djangocms_redirect/middleware.py`, `djangocms_redirect/models.py`, `tests/__init__.py` (call `clear_memo()` in `setUp`), `tests/test_middleware.py`
- Test: `tests/test_middleware.py`

**Interfaces:**
- Consumes: `get_table`, `match_path`, `invalidate_site`, `clear_memo` from Task 1-2.

- [ ] **Step 1: Write failing tests** in `tests/test_middleware.py` (class `TestCachedTable(BaseRedirectTest)`): `test_unknown_paths_zero_queries_when_warm` (warm with one request, then for 5 distinct unknown paths use a helper that measures only redirect queries: `CaptureQueriesContext` filtered on table `django_redirect` → 0); `test_cold_cache_single_redirect_query` (exactly 1 query on `django_redirect`, then 0 for another path); `test_no_per_path_keys` (cache key count via `cache._cache`/locmem keys unchanged after 20 distinct 404s); `test_per_site_isolation` (row on `site_2` not applied on `site_1`); `test_invalidation_create_edit_delete` (changes visible on next request with memo enabled and with `DJANGOCMS_REDIRECT_MEMO_TIMEOUT=0`); `test_site_change_invalidates_both_sites`; `test_table_load_failure_propagates_and_next_request_retries`.
- [ ] **Step 2: Run** `python cms_helper.py djangocms_redirect test tests.test_middleware`. Expected: new tests FAIL.
- [ ] **Step 3: Implement** in `middleware.py`: replace the per-path cache/`Redirect.objects.get`/`_match_substring` block of `do_redirect` with `table = get_table(current_site.pk)`, loop `possible_paths` calling `match_path`, then the unchanged response selection (`""` → gone, `"302"`, `"301"`, `"410"`); remove `_match_substring`, unused imports and the `site_id`/`cache` use. In `models.py`: `Redirect.from_db` remembers the loaded `site_id`; `clear_redirect_cache` (post_save/post_delete) calls `invalidate_site` for the current and the previously loaded site id.
- [ ] **Step 4: Update existing tests** that assert fixed query counts: for each, run, confirm the delta equals the removed redirect queries (per-path `get`/substring loads replaced by one table query), then set the new count; keep every response assertion. `tests/__init__.py`: add `clear_memo()` after `cache.clear()`.
- [ ] **Step 5: Run** full suite `python cms_helper.py djangocms_redirect test`. Expected: all PASS.
- [ ] **Step 6: Commit** `feat: resolve redirects from the cached per-site table`.

### Task 4: Docs, news fragment, lint, full matrix

**Files:**
- Modify: `docs/installation.rst` (settings list; add "How caching works" with the bulk-operation caveat, token invalidation, memo bound), `README.rst` only if it lists settings
- Create: `changes/156.feature`

- [ ] **Step 1: Docs**: document `DJANGOCMS_REDIRECT_MEMO_TIMEOUT`, the per-site table cache, invalidation on save/delete (including a redirect moved between sites), and that `.update()`/`.delete()` querysets are bounded by `DJANGOCMS_REDIRECT_CACHE_TIMEOUT` (plus memo timeout across processes).
- [ ] **Step 2: Fragment** `changes/156.feature`: "Cache the whole redirect table per site so unknown paths no longer hit the database."
- [ ] **Step 3: Verify**: `tox -e py311-django42-cms311,py313-django52-cms311`, `tox -e towncrier,docs,pypi-description,black,isort`; `pre-commit run --all-files` (ruff's 28 pre-existing findings are not to grow: compare counts, fix any new ones in touched files).
- [ ] **Step 4: Commit** `docs: document the cached redirect table`.
