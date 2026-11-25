import time
import uuid

from django.conf import settings
from django.core.cache import cache

from .models import Redirect

DEFAULT_CACHE_TIMEOUT = 3600
DEFAULT_MEMO_TIMEOUT = 5

ENTRY_FIELDS = ("old_path", "new_path", "response_code", "subpath_match", "catchall_redirect")


def build_table(site_id):
    """
    Load all the redirects of a site with a single query.

    :param site_id: primary key of the site
    :return: ``{"exact": {old_path: entry}, "substring": [entry, ...]}`` where ``substring`` only contains the
             subpath / catch-all entries, sorted by ``old_path`` descending (longest prefix first).
    """
    entries = list(Redirect.objects.filter(site_id=site_id).values(*ENTRY_FIELDS))
    substring = [entry for entry in entries if entry["subpath_match"] or entry["catchall_redirect"]]
    substring.sort(key=lambda entry: entry["old_path"], reverse=True)
    return {"exact": {entry["old_path"]: entry for entry in entries}, "substring": substring}


def match_path(table, path):
    """
    Find the redirect matching a path: exact matches win over subpath / catch-all ones.

    :param table: a table as returned by :py:func:`build_table`
    :param path: the requested path
    :return: a copy of the matching entry (with ``new_path`` rewritten for subpath matches) or ``None``
    """
    entry = table["exact"].get(path)
    if entry:
        return dict(entry)
    for entry in table["substring"]:
        if path.startswith(entry["old_path"]):
            match = dict(entry)
            if match["subpath_match"]:
                match["new_path"] = path.replace(match["old_path"], match["new_path"])
            return match
    return None


# Process-local memo: ``{site_id: (expires_at, table)}``. It spares a cache round trip per request; changes made in
# other processes become visible after at most ``DJANGOCMS_REDIRECT_MEMO_TIMEOUT`` seconds.
_memo = {}
_now = time.monotonic


def get_version_key(site_id):
    """Cache key of the token that versions the table of a site."""
    return "CMSREDIRECT:VERSION:{}".format(site_id)


def get_table_key(site_id, token):
    """Cache key of the table of a site for a given version token."""
    return "CMSREDIRECT:TABLE:{}:{}".format(site_id, token)


def clear_memo():
    """Drop the process-local memo for all the sites."""
    _memo.clear()


def _get_token(site_id):
    key = get_version_key(site_id)
    token = cache.get(key)
    if token is None:
        new_token = uuid.uuid4().hex
        cache.add(key, new_token, None)
        token = cache.get(key) or new_token
    return token


def get_table(site_id):
    """
    Return the redirect table of a site: process memo first, then the shared cache, then the database.

    The table is stored under a key including the version token; :py:func:`invalidate_site` rotates the token, so
    a table loaded concurrently with a change is never served after the change. A failed load caches nothing.

    :param site_id: primary key of the site
    :return: a table as returned by :py:func:`build_table`
    """
    memo_timeout = getattr(settings, "DJANGOCMS_REDIRECT_MEMO_TIMEOUT", DEFAULT_MEMO_TIMEOUT)
    memoized = _memo.get(site_id)
    if memoized and memoized[0] > _now():
        return memoized[1]
    token = _get_token(site_id)
    table_key = get_table_key(site_id, token)
    table = cache.get(table_key)
    if table is None:
        table = build_table(site_id)
        cache.set(table_key, table, getattr(settings, "DJANGOCMS_REDIRECT_CACHE_TIMEOUT", DEFAULT_CACHE_TIMEOUT))
    if memo_timeout > 0:
        _memo[site_id] = (_now() + memo_timeout, table)
    return table


def invalidate_site(site_id):
    """Make the cached table of a site obsolete (rotate its version token and drop the local memo)."""
    cache.set(get_version_key(site_id), uuid.uuid4().hex, None)
    _memo.pop(site_id, None)
