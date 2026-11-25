from django import http
from django.apps import apps
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django.utils.deprecation import MiddlewareMixin
from django.utils.encoding import escape_uri_path, iri_to_uri

from .table import get_table, match_path


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
        table = get_table(current_site.pk)
        match = None
        for path in possible_paths:
            match = match_path(table, path)
            if match:
                break

        redirect = match["new_path"] if match else None
        status_code = match["response_code"] if match else None
        if redirect == "":
            return self.response_gone_class()
        if status_code == "302":
            return self.response_redirect_class("{}{}".format(redirect, querystring))
        elif status_code == "301":
            return self.response_permanent_redirect_class("{}{}".format(redirect, querystring))
        elif status_code == "410":
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
