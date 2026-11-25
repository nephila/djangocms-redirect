from django.contrib.sites.models import Site

from djangocms_redirect.models import Redirect
from djangocms_redirect.table import build_table, match_path

from . import BaseRedirectTest


class TestBuildAndMatch(BaseRedirectTest):
    def setUp(self):
        super().setUp()
        self.site_2 = Site.objects.create(domain="other.example.com", name="other")

    def _redirect(self, old_path, new_path="/new/", site=None, **kwargs):
        return Redirect.objects.create(site=site or self.site_1, old_path=old_path, new_path=new_path, **kwargs)

    def test_build_table_one_query(self):
        self._redirect("/a/")
        self._redirect("/b/", subpath_match=True)
        self._redirect("/c/", site=self.site_2)

        with self.assertNumQueries(1):
            table = build_table(self.site_1.pk)

        self.assertEqual(set(table["exact"]), {"/a/", "/b/"})
        self.assertEqual([entry["old_path"] for entry in table["substring"]], ["/b/"])

    def test_substring_sorted_desc(self):
        for path in ("/a/", "/a/b/c/", "/a/b/"):
            self._redirect(path, catchall_redirect=True)

        table = build_table(self.site_1.pk)

        self.assertEqual([entry["old_path"] for entry in table["substring"]], ["/a/b/c/", "/a/b/", "/a/"])

    def test_match_exact(self):
        self._redirect("/a/", "/target/", response_code="302")

        entry = match_path(build_table(self.site_1.pk), "/a/")

        self.assertEqual(entry["new_path"], "/target/")
        self.assertEqual(entry["response_code"], "302")

    def test_match_exact_ignores_subpath_flag(self):
        self._redirect("/a/", "/target/", subpath_match=True)

        entry = match_path(build_table(self.site_1.pk), "/a/")

        self.assertEqual(entry["new_path"], "/target/")

    def test_match_subpath_rewrite_does_not_mutate_table(self):
        self._redirect("/old/", "/new/", subpath_match=True)
        table = build_table(self.site_1.pk)

        entry = match_path(table, "/old/x/")

        self.assertEqual(entry["new_path"], "/new/x/")
        self.assertEqual(table["exact"]["/old/"]["new_path"], "/new/")
        self.assertEqual(table["substring"][0]["new_path"], "/new/")

    def test_match_catchall(self):
        self._redirect("/old/", "/new/", catchall_redirect=True)

        entry = match_path(build_table(self.site_1.pk), "/old/some/page/")

        self.assertEqual(entry["new_path"], "/new/")

    def test_match_longest_prefix_first(self):
        self._redirect("/a/", "/short/", catchall_redirect=True)
        self._redirect("/a/b/", "/long/", catchall_redirect=True)

        entry = match_path(build_table(self.site_1.pk), "/a/b/c/")

        self.assertEqual(entry["new_path"], "/long/")

    def test_match_none(self):
        self._redirect("/a/", catchall_redirect=True)

        self.assertIsNone(match_path(build_table(self.site_1.pk), "/other/"))
