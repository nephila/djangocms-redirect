from unittest import mock
from urllib.parse import unquote_plus

import django
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test.utils import CaptureQueriesContext, override_settings
from django.utils.encoding import force_str
from setuptools._distutils.version import LooseVersion

from djangocms_redirect.admin import RedirectForm
from djangocms_redirect.middleware import RedirectMiddleware
from djangocms_redirect.models import Redirect
from djangocms_redirect.table import get_table, get_version_key

from . import BaseRedirectTest

DJANGO_4_2 = LooseVersion(django.__version__) >= LooseVersion("4.2")


class TestRedirect(BaseRedirectTest):
    _pages_data = (
        {"en": {"title": "home page", "template": "page.html", "publish": True}},
        {"en": {"title": "test page", "template": "page.html", "publish": True}},
        {"en": {"title": "b", "template": "page.html", "publish": True}},
        {"en": {"title": "internal page", "template": "page.html", "publish": True, "parent": "test-page"}},
    )

    def test_str(self):
        pages = self.get_pages()

        redirect = Redirect.objects.create(
            site=self.site_1,
            old_path=pages[1].get_absolute_url(),
            new_path=pages[0].get_absolute_url(),
            response_code="301",
        )
        self.assertIn(pages[1].get_absolute_url(), force_str(redirect))
        self.assertIn(pages[0].get_absolute_url(), force_str(redirect))

    def test_301_redirect(self):
        pages = self.get_pages()

        redirect = Redirect.objects.create(
            site=self.site_1,
            old_path=pages[1].get_absolute_url(),
            new_path=pages[0].get_absolute_url(),
            response_code="301",
        )

        with self.assertNumQueries(1):
            response = self.client.get(pages[1].get_absolute_url())
        self.assertEqual(response.status_code, 301)
        self.assertRedirects(response, redirect.new_path, status_code=301)

    def test_cached_redirect(self):
        pages = self.get_pages()

        redirect = Redirect.objects.create(
            site=self.site_1,
            old_path=pages[1].get_absolute_url(),
            new_path=pages[0].get_absolute_url(),
            response_code="301",
        )

        with self.assertNumQueries(1):
            response = self.client.get(pages[1].get_absolute_url())
        self.assertEqual(response.status_code, 301)
        self.assertRedirects(response, redirect.new_path, status_code=301)

        with self.assertNumQueries(0):
            response = self.client.get(pages[1].get_absolute_url())
        self.assertEqual(response.status_code, 301)

    def test_302_redirect(self):
        pages = self.get_pages()

        redirect = Redirect.objects.create(
            site=self.site_1,
            old_path=pages[1].get_absolute_url(),
            new_path=pages[0].get_absolute_url(),
            response_code="302",
        )

        with self.assertNumQueries(1):
            response = self.client.get(pages[1].get_absolute_url())
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, redirect.new_path, status_code=302)

    def test_querystring_redirect(self):
        pages = self.get_pages()

        redirect = Redirect.objects.create(
            site=self.site_1,
            old_path=pages[1].get_absolute_url(),
            new_path=pages[0].get_absolute_url(),
            response_code="302",
        )

        with self.assertNumQueries(1):
            response = self.client.get(pages[1].get_absolute_url() + "?Some_query_param")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, redirect.new_path + "?Some_query_param", status_code=302)

    def test_quoted_path_redirect(self):
        pages = self.get_pages()

        escaped_path = "/path%20%28escaped%29/"
        redirect = Redirect.objects.create(
            site=self.site_1,
            old_path=escaped_path,
            new_path=pages[0].get_absolute_url(),
            response_code="302",
        )

        response = self.client.get(escaped_path)
        self.assertEqual(response.status_code, 404)

        redirect.old_path = "/path%20(escaped)/"
        redirect.save()
        response = self.client.get(escaped_path)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, redirect.new_path, status_code=302)

        unescaped_path = unquote_plus(escaped_path)
        redirect.old_path = unescaped_path
        redirect.save()

        response = self.client.get(escaped_path)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, redirect.new_path, status_code=302)

    def test_410_redirect(self):
        pages = self.get_pages()

        Redirect.objects.create(
            site=self.site_1,
            old_path=pages[1].get_absolute_url(),
            new_path=pages[0].get_absolute_url(),
            response_code="410",
        )

        with self.assertNumQueries(1):
            response = self.client.get(pages[1].get_absolute_url())
        self.assertEqual(response.status_code, 410)

        Redirect.objects.create(site=self.site_1, old_path="/some-path/", response_code="302")

        with self.assertNumQueries(1):
            response2 = self.client.get("/some-path/")
        self.assertEqual(response2.status_code, 410)

    def test_use_response_404_only(self):
        pages = self.get_pages()

        with self.settings(DJANGOCMS_REDIRECT_USE_REQUEST=False):
            Redirect.objects.create(
                site=self.site_1,
                old_path=pages[1].get_absolute_url(),
                new_path=pages[0].get_absolute_url(),
                response_code="302",
            )

            with self.assertNumQueries(8):
                response = self.client.get(pages[1].get_absolute_url())
            self.assertEqual(response.status_code, 200)

    def test_use_response_no404(self):
        pages = self.get_pages()

        with self.settings(DJANGOCMS_REDIRECT_USE_REQUEST=False, DJANGOCMS_REDIRECT_404_ONLY=False):
            redirect = Redirect.objects.create(
                site=self.site_1,
                old_path=pages[1].get_absolute_url(),
                new_path=pages[0].get_absolute_url(),
                response_code="302",
            )

            with self.assertNumQueries(9):
                response = self.client.get(pages[1].get_absolute_url())
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, redirect.new_path, status_code=302)

    def test_delete_redirect(self):
        pages = self.get_pages()

        redirect = Redirect.objects.create(
            site=self.site_1,
            old_path=pages[1].get_absolute_url(),
            new_path=pages[0].get_absolute_url(),
            response_code="301",
        )

        with self.assertNumQueries(1):
            response = self.client.get(pages[1].get_absolute_url())
        self.assertRedirects(response, redirect.new_path, status_code=301)
        redirect.delete()

        with self.assertNumQueries(6):
            response2 = self.client.get(pages[1].get_absolute_url())
        self.assertEqual(response2.status_code, 200)

    def test_redirect_no_append_slash(self):
        pages = self.get_pages()

        with override_settings(APPEND_SLASH=False):
            redirect = Redirect.objects.create(
                site=self.site_1,
                old_path=pages[1].get_absolute_url(),
                new_path=pages[0].get_absolute_url(),
                response_code="301",
            )

            with self.assertNumQueries(1):
                response = self.client.get(pages[1].get_absolute_url().rstrip("/"))
            self.assertRedirects(response, redirect.new_path, status_code=301)

    def test_redirect_no_append_slash_unquoted(self):
        pages = self.get_pages()

        original_path = "/path (escaped)/"
        with override_settings(APPEND_SLASH=False):
            redirect = Redirect.objects.create(
                site=self.site_1,
                old_path=original_path,
                new_path=pages[0].get_absolute_url(),
                response_code="301",
            )

            with self.assertNumQueries(1):
                response = self.client.get(original_path.rstrip("/"))
            self.assertRedirects(response, redirect.new_path, status_code=301)

    def test_redirect_no_append_slash_quoted(self):
        pages = self.get_pages()

        original_path = "/path%20(escaped)/"
        with override_settings(APPEND_SLASH=False):
            redirect = Redirect.objects.create(
                site=self.site_1,
                old_path=original_path,
                new_path=pages[0].get_absolute_url(),
                response_code="301",
            )

            with self.assertNumQueries(1):
                response = self.client.get(original_path.rstrip("/"))
            self.assertRedirects(response, redirect.new_path, status_code=301)

    def test_redirect_no_append_slash_no_match(self):
        pages = self.get_pages()

        with override_settings(APPEND_SLASH=False):
            Redirect.objects.create(
                site=self.site_1,
                old_path="/no-match",
                new_path=pages[0].get_absolute_url(),
                response_code="301",
            )

            with self.assertNumQueries(1):
                response = self.client.get(pages[1].get_absolute_url().rstrip("/"))
            self.assertEqual(404, response.status_code)

    def test_no_slash_no_append_slash(self):
        self.get_pages()

        with override_settings(APPEND_SLASH=False):
            Redirect.objects.create(
                site=self.site_1,
                old_path="/en/a",
                new_path="/en/b/",
                response_code="301",
            )
            # redirect match
            response = self.client.get("/en/a")
            self.assertRedirects(response, "/en/b/", status_code=301)

            # no redirect match
            response = self.client.get("/en/a/")
            self.assertEqual(404, response.status_code)

    def test_no_slash_append_slash(self):
        self.get_pages()

        with override_settings(APPEND_SLASH=True):
            Redirect.objects.create(
                site=self.site_1,
                old_path="/en/a",
                new_path="/en/b/",
                response_code="301",
            )

            # django append slash settings kicks in before djangocms-redirect, redirecting to /a/
            response = self.client.get("/en/a")
            # django 4.2 skips APPEND_SLASH for successful requests
            # see https://github.com/django/django/pull/15689
            if DJANGO_4_2:
                self.assertRedirects(response, "/en/b/", status_code=301, fetch_redirect_response=False)
            else:
                self.assertRedirects(response, "/en/a/", status_code=301, fetch_redirect_response=False)
                response = self.client.get(response["Location"])
                self.assertEqual(404, response.status_code)

            # no redirect match
            response = self.client.get("/en/a/")
            self.assertEqual(404, response.status_code)

    def test_slash_no_append_slash(self):
        self.get_pages()

        with override_settings(APPEND_SLASH=False):
            Redirect.objects.create(
                site=self.site_1,
                old_path="/en/a/",
                new_path="/en/b/",
                response_code="301",
            )
            # redirect match
            response = self.client.get("/en/a")
            self.assertRedirects(response, "/en/b/", status_code=301)

            # redirect match
            response = self.client.get("/en/a/")
            self.assertRedirects(response, "/en/b/", status_code=301)

    def test_slash_append_slash(self):
        self.get_pages()

        with override_settings(APPEND_SLASH=True):
            Redirect.objects.create(
                site=self.site_1,
                old_path="/en/a/",
                new_path="/en/b/",
                response_code="301",
            )

            # django append slash settings kicks in before djangocms-redirect, redirecting to /a/
            # then redirect match
            response = self.client.get("/en/a")
            # django 4.2 skips APPEND_SLASH for successful requests
            # see https://github.com/django/django/pull/15689
            if DJANGO_4_2:
                self.assertRedirects(response, "/en/b/", status_code=301)
            else:
                self.assertRedirects(response, "/en/a/", status_code=301, fetch_redirect_response=False)
                response = self.client.get(response["Location"])
                self.assertRedirects(response, "/en/b/", status_code=301)

            # redirect match
            response = self.client.get("/en/a/")
            self.assertRedirects(response, "/en/b/", status_code=301)


class TestClean(BaseRedirectTest):
    _pages_data = ({"en": {"title": "home page", "template": "page.html", "publish": True}},)

    def _make_form(self, old_path):
        pages = self.get_pages()
        return RedirectForm(
            {
                "site": self.site_1.pk,
                "old_path": old_path,
                "new_path": pages[0].get_absolute_url(),
                "response_code": "301",
            }
        )

    def _assert_clean(self, old_path, old_path_cleaned):
        redirect_form = self._make_form(old_path)
        redirect = redirect_form.save()
        self.assertEqual(redirect.old_path, old_path_cleaned)

    def test_clean_keep_slash(self):
        self._assert_clean("/slash-bar/", "/slash-bar/")

    def test_clean_prepend_slash(self):
        self._assert_clean("slash-test/", "/slash-test/")

    def test_clean_single_slash_root(self):
        self._assert_clean("/", "/")

    def test_clean_append_slash(self):
        with override_settings(APPEND_SLASH=True):
            self._assert_clean("/slash-foo", "/slash-foo/")

    def test_clean_no_append_slash(self):
        with override_settings(APPEND_SLASH=False):
            self._assert_clean("/slash-baz", "/slash-baz")


class TestPartialMatch(BaseRedirectTest):
    _pages_data = (
        {"en": {"title": "home page", "template": "page.html", "publish": True}},
        {"en": {"title": "test page", "template": "page.html", "publish": True}},
        {"en": {"title": "internal page", "template": "page.html", "publish": True, "parent": "test-page"}},
    )

    def setUp(self):
        super().setUp()
        Redirect.objects.create(
            site=self.site_1,
            old_path="/en/test",
            new_path="/baz",
            response_code="301",
        )
        Redirect.objects.create(
            site=self.site_1,
            old_path="/en/test-page/in",
            new_path="/bar",
            response_code="301",
        )
        Redirect.objects.create(
            site=self.site_1,
            old_path="/en/test-page/internal",
            new_path="/not-match",
            response_code="302",
        )
        Redirect.objects.create(
            site=self.site_1,
            old_path="/en/test-page/other/path",
            new_path="/foo",
            response_code="301",
        )
        Redirect.objects.create(
            site=self.site_1,
            old_path="/en/fobz/",
            new_path="/fabz",
            response_code="301",
        )

    def _patch_catchall_redirect(self, redirect):
        redirect.catchall_redirect = True
        redirect.save()
        return redirect

    def _patch_subpath_match(self, redirect):
        redirect.subpath_match = True
        redirect.save()
        return redirect

    def test_no_substring(self):
        pages = self.get_pages()
        with self.assertNumQueries(12):
            response = self.client.get(pages[2].get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_partial_success(self):
        pages = self.get_pages()
        redirect = self._patch_catchall_redirect(Redirect.objects.get(old_path="/en/test-page/in"))
        with self.assertNumQueries(1):
            response = self.client.get(pages[2].get_absolute_url())
        self.assertRedirects(response, redirect.new_path, status_code=301, fetch_redirect_response=False)

    def test_partial_subpath_replace(self):
        pages = self.get_pages()
        self._patch_subpath_match(Redirect.objects.get(old_path="/en/test-page/in"))
        with self.assertNumQueries(1):
            response = self.client.get(pages[2].get_absolute_url())
        new_path = pages[2].get_absolute_url().replace("/en/test-page/in", "/bar")
        self.assertRedirects(response, new_path, status_code=301, fetch_redirect_response=False)

    def test_all_partials(self):
        pages = self.get_pages()
        redirect = Redirect.objects.get(old_path="/en/test-page/internal")
        for patched in Redirect.objects.all():
            self._patch_catchall_redirect(patched)
        with self.assertNumQueries(1):
            response = self.client.get(pages[2].get_absolute_url())
        self.assertRedirects(response, redirect.new_path, status_code=302, fetch_redirect_response=False)


class TestCachedTable(BaseRedirectTest):
    _pages_data = (
        {"en": {"title": "home page", "template": "page.html", "publish": True}},
        {"en": {"title": "test page", "template": "page.html", "publish": True}},
    )

    def setUp(self):
        super().setUp()
        self.site_2 = Site.objects.create(domain="other.example.com", name="other")

    def _get(self, path):
        """Request a path and return the response with the number of queries on the redirect table."""
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(path)
        redirect_queries = [query for query in queries if "django_redirect" in query["sql"]]
        return response, len(redirect_queries)

    def _redirect_cache_keys(self):
        return [key for key in cache._cache if "CMSREDIRECT" in key]

    def test_unknown_paths_zero_queries_when_warm(self):
        Redirect.objects.create(site=self.site_1, old_path="/en/known/", new_path="/target/")
        self._get("/en/warm-up/")

        for index in range(5):
            response, redirect_queries = self._get(f"/en/unknown-{index}/")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(redirect_queries, 0)

    def test_cold_cache_single_redirect_query(self):
        Redirect.objects.create(site=self.site_1, old_path="/en/known/", new_path="/target/")

        _, first = self._get("/en/unknown-1/")
        _, second = self._get("/en/unknown-2/")

        self.assertEqual((first, second), (1, 0))

    def test_no_per_path_keys(self):
        self._get("/en/warm-up/")
        keys_before = len(self._redirect_cache_keys())

        for index in range(20):
            self._get(f"/en/unknown-{index}/")

        self.assertEqual(len(self._redirect_cache_keys()), keys_before)

    def test_per_site_isolation(self):
        Redirect.objects.create(site=self.site_2, old_path="/en/only-site-2/", new_path="/target/")

        response, _ = self._get("/en/only-site-2/")

        self.assertEqual(response.status_code, 404)

    def _check_invalidation(self):
        redirect = Redirect.objects.create(site=self.site_1, old_path="/en/a/", new_path="/first/")
        self.assertRedirects(self.client.get("/en/a/"), "/first/", status_code=301, fetch_redirect_response=False)

        redirect.new_path = "/second/"
        redirect.save()
        self.assertRedirects(self.client.get("/en/a/"), "/second/", status_code=301, fetch_redirect_response=False)

        redirect.delete()
        self.assertEqual(self.client.get("/en/a/").status_code, 404)

        Redirect.objects.create(site=self.site_1, old_path="/en/b/", new_path="/created/")
        self.assertRedirects(self.client.get("/en/b/"), "/created/", status_code=301, fetch_redirect_response=False)

    def test_invalidation_create_edit_delete(self):
        self._check_invalidation()

    @override_settings(DJANGOCMS_REDIRECT_MEMO_TIMEOUT=0)
    def test_invalidation_create_edit_delete_no_memo(self):
        self._check_invalidation()

    def test_site_change_invalidates_both_sites(self):
        redirect = Redirect.objects.create(site=self.site_1, old_path="/en/moving/", new_path="/target/")
        self.assertEqual(self.client.get("/en/moving/").status_code, 301)

        redirect = Redirect.objects.get(pk=redirect.pk)
        redirect.site = self.site_2
        redirect.save()

        self.assertEqual(self.client.get("/en/moving/").status_code, 404)

    def test_site_moved_twice_invalidates_every_site_it_was_on(self):
        site_3 = Site.objects.create(domain="third.example.com", name="third")
        redirect = Redirect.objects.create(site=self.site_1, old_path="/en/moving/", new_path="/target/")
        redirect = Redirect.objects.get(pk=redirect.pk)
        redirect.site = self.site_2
        redirect.save()
        self.assertEqual(get_table(self.site_2.pk)["exact"]["/en/moving/"]["new_path"], "/target/")

        redirect.site = site_3
        redirect.save()

        self.assertNotIn("/en/moving/", get_table(self.site_2.pk)["exact"])

    def test_invalidation_is_repeated_on_commit(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            Redirect.objects.create(site=self.site_1, old_path="/en/a/", new_path="/target/")
        token_after_save = cache.get(get_version_key(self.site_1.pk))

        for callback in callbacks:
            callback()

        self.assertNotEqual(cache.get(get_version_key(self.site_1.pk)), token_after_save)

    def test_table_load_failure_propagates_and_next_request_retries(self):
        Redirect.objects.create(site=self.site_1, old_path="/en/a/", new_path="/target/")

        with (
            mock.patch("djangocms_redirect.table.build_table", side_effect=RuntimeError("db down")),
            self.assertRaises(RuntimeError),
        ):
            self.client.get("/en/a/")

        self.assertEqual(self.client.get("/en/a/").status_code, 301)


class TestNoSitesMatch(BaseRedirectTest):
    _pages_data = (
        {"en": {"title": "home page", "template": "page.html", "publish": True}},
        {"en": {"title": "test page", "template": "page.html", "publish": True}},
        {"en": {"title": "internal page", "template": "page.html", "publish": True, "parent": "test-page"}},
    )
    PATCHED_INSTALLED_APPS = [app for app in settings.INSTALLED_APPS if app != "django.contrib.sites"]

    @override_settings(INSTALLED_APPS=PATCHED_INSTALLED_APPS)
    def test_no_sites(self):
        pages = self.get_pages()

        Redirect.objects.create(
            site=self.site_1,
            old_path=pages[1].get_absolute_url(),
            new_path=pages[0].get_absolute_url(),
            response_code="301",
        )

        with self.assertRaises(ImproperlyConfigured) as context:
            self.client.get(pages[1].get_absolute_url())
        self.assertEqual(RedirectMiddleware.no_site_message, force_str(context.exception))


try:
    import memcache
except ImportError:
    pass
else:

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
                "LOCATION": "127.0.0.1:11211",
            }
        }
    )
    class TestMemcacheRedirect(BaseRedirectTest):
        _pages_data = (
            {"en": {"title": "home page", "template": "page.html", "publish": True}},
            {"en": {"title": "test page", "template": "page.html", "publish": True}},
            {"en": {"title": "internal page", "template": "page.html", "publish": True, "parent": "test-page"}},
        )

        def test_fix_memcache_memcachedkeylengtherror(self):
            """
            Fixes https://github.com/nephila/djangocms-redirect/issues/8
            Using an url > 250 chars with memcache active, a memcache.Client.MemcachedKeyLengthError is raised
            """
            pages = self.get_pages()
            url_suffix = "x" * 250  # url > 250 chars

            url = "{}?{}".format(pages[1].get_absolute_url(), url_suffix)
            expected_url = "{}?{}".format(pages[0].get_absolute_url(), url_suffix)

            Redirect.objects.create(
                site=self.site_1,
                old_path=pages[1].get_absolute_url(),
                new_path=pages[0].get_absolute_url(),
                response_code="302",
            )
            try:
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertRedirects(response, expected_url, status_code=302)
            except memcache.Client.MemcachedKeyLengthError:
                self.fail("memcache.Client.MemcachedKeyLengthError raised")
