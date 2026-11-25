from .models import Redirect

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
