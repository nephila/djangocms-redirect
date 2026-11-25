============
Installation
============

* Install djangocms-redirect::

    pip install djangocms-redirect

* Add to INSTALLED_APPS::

    INSTALLED_APPS = [
        ...
        djangocms_redirect
        ...
    ]

* Add to MIDDLEWARE_CLASSES:

  If you intend to use ``process_request`` the add it near the top (after
  ``django.middleware.cache.UpdateCacheMiddleware``); if using ``process_response`` add at the
  bottom (before ``django.middleware.cache.FetchFromCacheMiddleware``)::

    MIDDLEWARE_CLASSES = [
        ...
        djangocms_redirect.middleware.RedirectMiddleware
        ...
    ]


* Choose if you want to process the redirect during the request (default) or response by setting:

    * ``DJANGOCMS_REDIRECT_USE_REQUEST = True``: during request
    * ``DJANGOCMS_REDIRECT_USE_REQUEST = False``: during response

* Migrate::

    python manage.py migrate

The go to ``http://mysite.com/admin/djangocms_redirect/`` and create redirect instances.


Settings
========

* ``DJANGOCMS_REDIRECT_USE_REQUEST``: If ``True`` the redirect check will be done in the request phase,
  to allow preempting any other logic. **Beware**: this will result in extra queries on **each**
  request because the redirects will be checked before the view logic triggers.
  If ``False`` the redirect will be checked in the response phase.
* ``DJANGOCMS_REDIRECT_CACHE_TIMEOUT``: You can provide a custom timeout for the cached redirect table
  (Default: 3600 sec)
* ``DJANGOCMS_REDIRECT_MEMO_TIMEOUT``: Seconds the redirect table is kept in the memory of each process, on top
  of the shared cache, to spare a cache round trip on each request (Default: 5 sec, ``0`` disables it)
* ``DJANGOCMS_REDIRECT_404_ONLY``: If ``True`` (the default) and ``DJANGOCMS_REDIRECT_USE_REQUEST=False``
  the redirect will be checked only for responses that return 404 (the default ``django.contrib.redirect``
  behavior). This is the lowest impact option in terms of performance and the advised configuration.

How caching works
=================

The whole redirect table of a site is loaded with a single query and stored in the Django cache, so
requests for paths that do not match any redirect do not hit the database once the table is cached. Make sure
the configured cache is shared between processes (e.g. memcached or redis) in multi-process deployments.

* Saving or deleting a redirect (e.g. from the admin) invalidates the table of its site immediately: the new
  table is loaded on the next request.
* A process that already holds the table in memory keeps serving it for at most
  ``DJANGOCMS_REDIRECT_MEMO_TIMEOUT`` seconds; the process that made the change sees it immediately.
* Bulk operations that do not send signals (``QuerySet.update()``, ``QuerySet.delete()``) do **not** invalidate
  the cache: the change is visible once ``DJANGOCMS_REDIRECT_CACHE_TIMEOUT`` expires. Clear the cache to apply
  it sooner.
