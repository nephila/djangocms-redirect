from unittest import mock

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.test.utils import override_settings

from djangocms_redirect import table as table_module
from djangocms_redirect.models import Redirect
from djangocms_redirect.table import build_table, clear_memo, get_table, get_version_key, invalidate_site, match_path

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


class TestTableCache(BaseRedirectTest):
    def setUp(self):
        super().setUp()
        clear_memo()
        self.redirect = Redirect.objects.create(site=self.site_1, old_path="/a/", new_path="/new/")

    def _table_keys(self):
        return [key for key in cache._cache if "CMSREDIRECT:TABLE" in key]

    def test_cold_one_query_then_zero(self):
        with self.assertNumQueries(1):
            table = get_table(self.site_1.pk)
        self.assertIn("/a/", table["exact"])

        with self.assertNumQueries(0):
            get_table(self.site_1.pk)

    def test_failed_load_caches_nothing(self):
        with (
            mock.patch("djangocms_redirect.table.build_table", side_effect=RuntimeError("db down")),
            self.assertRaises(RuntimeError),
        ):
            get_table(self.site_1.pk)
        self.assertEqual(self._table_keys(), [])

        with self.assertNumQueries(1):
            table = get_table(self.site_1.pk)
        self.assertIn("/a/", table["exact"])

    def test_invalidate_reloads(self):
        get_table(self.site_1.pk)
        Redirect.objects.filter(pk=self.redirect.pk).update(new_path="/changed/")

        self.assertEqual(get_table(self.site_1.pk)["exact"]["/a/"]["new_path"], "/new/")

        invalidate_site(self.site_1.pk)

        self.assertEqual(get_table(self.site_1.pk)["exact"]["/a/"]["new_path"], "/changed/")

    def test_memo_serves_without_cache_roundtrip(self):
        get_table(self.site_1.pk)

        with mock.patch.object(cache, "get", side_effect=AssertionError("cache hit")):
            get_table(self.site_1.pk)

    def test_memo_expires(self):
        clock = [1000.0]
        with mock.patch("djangocms_redirect.table._now", side_effect=lambda: clock[0]):
            get_table(self.site_1.pk)
            clock[0] += 4
            with mock.patch.object(cache, "get", side_effect=AssertionError("cache hit")):
                get_table(self.site_1.pk)
            clock[0] += 2
            with mock.patch.object(cache, "get", wraps=cache.get) as cache_get:
                get_table(self.site_1.pk)
            self.assertTrue(cache_get.called)

    @override_settings(DJANGOCMS_REDIRECT_MEMO_TIMEOUT=0)
    def test_memo_timeout_zero_disables(self):
        get_table(self.site_1.pk)

        with mock.patch.object(cache, "get", wraps=cache.get) as cache_get:
            get_table(self.site_1.pk)
        self.assertTrue(cache_get.called)

    @override_settings(DJANGOCMS_REDIRECT_MEMO_TIMEOUT=0)
    def test_stale_loader_race(self):
        real_build = table_module.build_table

        def build_and_invalidate(site_id):
            result = real_build(site_id)
            Redirect.objects.filter(pk=self.redirect.pk).update(new_path="/changed/")
            invalidate_site(site_id)
            return result

        with mock.patch("djangocms_redirect.table.build_table", side_effect=build_and_invalidate):
            stale = get_table(self.site_1.pk)
        self.assertEqual(stale["exact"]["/a/"]["new_path"], "/new/")

        self.assertEqual(get_table(self.site_1.pk)["exact"]["/a/"]["new_path"], "/changed/")

    @override_settings(DJANGOCMS_REDIRECT_MEMO_TIMEOUT=0)
    def test_missing_token_reloads(self):
        get_table(self.site_1.pk)
        cache.delete(get_version_key(self.site_1.pk))

        with self.assertNumQueries(1):
            get_table(self.site_1.pk)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}})
    def test_dummy_cache_still_resolves(self):
        table = get_table(self.site_1.pk)

        self.assertEqual(match_path(table, "/a/")["new_path"], "/new/")
