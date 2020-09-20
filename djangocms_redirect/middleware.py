from operator import itemgetter

from django import http
from django.apps import apps
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils.deprecation import MiddlewareMixin
from django.utils.encoding import escape_uri_path, iri_to_uri

from .models import Redirect
from .utils import get_key_from_path_and_site


class RedirectMiddleware(MiddlewareMixin):
    # Defined as class-level attributes to be subclassing-friendly.
    response_gone_class = http.HttpResponseGone
    response_redirect_class = http.HttpResponseRedirect
    response_permanent_redirect_class = http.HttpResponsePermanentRedirect

    no_site_message = "RedirectFallbackMiddleware requires django.contrib.sites to work."

    def __init__(self, *args, **kwargs):
        if not apps.is_installed("django.contrib.sites"):
            raise ImproperlyConfigured(self.no_site_message)
        super().__init__(*args, **kwargs)

    def do_redirect(self, request, response=None):
        site_id = int(settings.SITE_ID)
        if getattr(settings, "DJANGOCMS_REDIRECT_404_ONLY", True) and response and response.status_code != 404:
            return response

        req_path = request.path
        # get the query string
        querystring = request.META.get("QUERY_STRING", "")
        if querystring:
            querystring = "?%s" % iri_to_uri(querystring)
        # start with the path as is
        possible_paths = [req_path]
        # add the unquoted path if it differs
        req_path_quoted = escape_uri_path(req_path)
        if req_path_quoted != req_path:
            possible_paths.append(req_path_quoted)
        # if a slash is missing, try to append it
        if not req_path.endswith("/"):
            req_path_slash = req_path + "/"
            possible_paths.append(req_path_slash)
            req_path_slash_quoted = escape_uri_path(req_path_slash)
            if req_path_slash_quoted != req_path_slash:
                possible_paths.append(req_path_slash_quoted)

        current_site = get_current_site(request)
        r = None
        key = get_key_from_path_and_site(req_path, site_id)
        cached_redirect = cache.get(key)

        if not cached_redirect:
            print("possible_paths", possible_paths)
            for path in possible_paths:
                filters = dict(site=current_site, old_path=path)
                try:
                    r = Redirect.objects.get(**filters)
                    break
                except Redirect.DoesNotExist:
                    r = self._match_substring(path)
                    if r:
                        break

            cached_redirect = {
                "site": site_id,
                "redirect": r.new_path if r else None,
                "status_code": r.response_code if r else None,
            }
            cache.set(key, cached_redirect, timeout=getattr(settings, "DJANGOCMS_REDIRECT_CACHE_TIMEOUT", 3600))
        print("cached_redirect", cached_redirect)
        if cached_redirect["redirect"] == "":
            return self.response_gone_class()
        if cached_redirect["status_code"] == "302":
            return self.response_redirect_class("{}{}".format(cached_redirect["redirect"], querystring))
        elif cached_redirect["status_code"] == "301":
            return self.response_permanent_redirect_class("{}{}".format(cached_redirect["redirect"], querystring))
        elif cached_redirect["status_code"] == "410":
            return self.response_gone_class()

    def process_request(self, request):
        if getattr(settings, "DJANGOCMS_REDIRECT_USE_REQUEST", True):
            return self.do_redirect(request)

    def process_response(self, request, response):
        redirect = None
        if not getattr(settings, "DJANGOCMS_REDIRECT_USE_REQUEST", True):
            redirect = self.do_redirect(request, response)
        if redirect:
            return redirect
        return response

    def _match_substring(self, original_path):
        redirects = [
            (r.old_path, r) for r in Redirect.objects.filter(Q(subpath_match=True) | Q(catchall_redirect=True))
        ]
        redirects = sorted(redirects, key=itemgetter(0), reverse=True)
        for url in redirects:
            if original_path.startswith(url[0]):
                redirect = url[1]
                if redirect.subpath_match:
                    # we change this in memory only to return the proper redirect object
                    # without persisting the change
                    redirect.new_path = original_path.replace(redirect.old_path, redirect.new_path)
                return redirect
