## 2026-11-25 — Cache the full redirect table per site
**What:** The middleware now loads all redirects of a site with one query, caches that table, and resolves paths in memory; unknown paths cost zero queries once warm.
**Why:** A scanner flood of distinct 404 paths never hit the per-path cache, ran several queries per path and exhausted database connections in a production incident (reported from a consuming project).
**Decisions:** Invalidation uses an opaque version token (not an integer counter) so a loader racing a save can never publish a stale table, plus a short per-process memo (`DJANGOCMS_REDIRECT_MEMO_TIMEOUT`, default 5 s). After review the token is rotated again via `transaction.on_commit`, because loaders can read pre-commit data. A redirect moved between sites invalidates both sites (`from_db` remembers the loaded site). Table keyed by `current_site.pk`; subpath/catch-all matching is now per site (was global) and noted in a bugfix fragment.
**Agent usage:**

| Stage | Agent/skill | Tokens | Time |
|---|---|---|---|
| Design | superpowers:brainstorming + writing-plans | ≈30k | ≈12m |
| Implementation | superpowers:executing-plans (inline) | ≈70k | ≈25m |
| Review | opus subagent whole-branch review | ≈90k | ≈2m |
| Review | nephila code-eval | ≈8k | ≈2m |

**Considered & dropped:** Caching only the substring list plus one `old_path__in` query (still queries every path); integer version counter (missing-key and eviction corner cases); skipping the memo (rejected by maintainer).
**Follow-ups:** Verify on a real memcached/redis; exact matching is case-sensitive now (old DB lookup followed MySQL collation); `utils.get_key_from_path_and_site` is unused; two test helpers read `cache._cache` (locmem only); consumers must bump the pin and release is separate.
**Refs:** issue 156; Eval: 80% — artifacts/evaluations/2026-11-25-cached-redirect-table.md
