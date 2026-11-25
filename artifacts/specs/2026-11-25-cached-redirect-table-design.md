# Cache the full redirect table per site — design

Date: 2026-11-25
Language: English (confirmed)
Origin: production incident of 2026-11-24, where a scanner 404 flood exhausted database connections on a site using this package.

## Intent
A 404 for an unknown path must cost zero database queries in the steady state, however many distinct paths are requested, with unchanged redirect semantics.

## Goals
- One redirect query per site (cold cache), then zero queries for any path.
- Same responses: 301/302 with the original query string, 410, `new_path == ""` gone.
- Safe invalidation (no stale table surviving a save/delete race) and a short in-process memo to avoid a cache round trip per 404 during a flood.

## Non-goals
- Changing public settings `DJANGOCMS_REDIRECT_404_ONLY`, `DJANGOCMS_REDIRECT_USE_REQUEST`, `DJANGOCMS_REDIRECT_CACHE_TIMEOUT`.
- Large-table fallback (cache only substring list): not needed, tables are <= ~500 rows (maintainer).
- Release/version bump; the consumer-side pin bump; WAF, rate limiting and connection pooling work in consuming projects.

## Constraints
- Supported Django/CMS/Python matrix unchanged (Django 4.2/5.2, Python 3.11/3.13, CMS 3.11).
- `unique_together (site, old_path)` exists: no duplicate rows, a dict is safe.
- A failed table load must raise before anything is cached and fail fast (no retry, no negative entry): during the incident, uncached failures created a query feedback loop.
- Bulk `QuerySet.update()`/`.delete()` send no per-row signals: bounded only by the cache timeout (documented).

## Approaches
1. **Full table per site + version token + memo (chosen by maintainer).**
2. Substring list cached + one `old_path__in` query for exact matches: still queries on every unknown path; rejected.
3. Full table without memo/version: simpler, but leaves a stale-table race and a cache round trip per 404; rejected by maintainer.

## Design
- **Table:** `{"exact": {old_path: entry}, "substring": [entry, ...]}`; entry = `{old_path, new_path, response_code, subpath_match, catchall_redirect}`; `exact` holds every row of the site (as today's `get()`), `substring` holds `subpath_match`/`catchall_redirect` rows sorted by `old_path` descending. An empty site caches an empty table.
- **Resolution (unchanged algorithm):** for each candidate in `possible_paths` (path, quoted, slash, slash quoted): exact hit wins, else first substring entry whose `old_path` prefixes the candidate; `subpath_match` rewrites `new_path` via `replace` on a copy, never persisted.
- **Keys:** `CMSREDIRECT:VERSION:<site_id>` (timeout None) holds an opaque token; table key `CMSREDIRECT:TABLE:<site_id>:<token>` with `DJANGOCMS_REDIRECT_CACHE_TIMEOUT`. Loader reads the token (creating one with `cache.add` if missing), loads the table, stores it under that token. Invalidation sets a fresh token, so a loader that raced with a save writes under an obsolete token that is never read again.
  - My call: an opaque unique token (uuid) instead of an integer counter. `cache.incr` raises on a missing key and an evicted counter could restart at a previously used number and revive a stale table; a token has neither problem. Behaves as a "version".
- **Memo:** in-process dict `site_id -> (expires_at, table)`, validity `DJANGOCMS_REDIRECT_MEMO_TIMEOUT` seconds (new setting; my call: default 5, `0` disables). `post_save`/`post_delete` handlers clear the local memo for the site and rotate the token, so same-process changes are visible immediately; other processes see a change after at most the memo timeout.
- **Site key:** the table is keyed by `current_site.pk` (my call; previously the path key used `int(settings.SITE_ID)` while the query used `current_site`).
- **Removed:** per-path cache read/write in `do_redirect`; `_match_substring` DB query. `utils.get_key_from_path_and_site` stays (public helper) but is no longer used by the middleware.
- **Signals:** `clear_redirect_cache` in `models.py` now rotates the site token and clears the memo.
- **Docs:** `docs/installation.rst` settings list (new setting, bulk-operation caveat, how caching works); towncrier fragment.

## Tests (TDD, written first)
Warm cache: `assertNumQueries(0)` for several distinct unknown paths; cold: exactly one redirect query, then zero for the next distinct path; 301/302/410/empty `new_path` responses with query string preserved; `subpath_match` rewrite and `catchall_redirect` incl. ordering of several matching prefixes; trailing slash and quoted/unquoted candidates; per-site isolation; invalidation on create/edit/delete (next request sees it, memo on and off); failed load caches nothing and the next request retries; no per-path cache key is written for N distinct 404s (key count constant); memo expiry (patched clock); stale-table race (loader stores under an obsolete token → not served). Existing tests with fixed query counts are rewritten to the new counts.

## Left to the builder
Exact token/memo helper placement (new module vs `utils.py`), memo clock function, test helper names.
