=====
Usage
=====

To manage redirect rules navigate to the ``Redirect`` section of the django admin
(usually ``http://www.yoursite.com/admin/djangocms_redirect/redirect``).

For each redirect you must provide:

* **Site**: The site for which you want to add a redirect.
* **Redirect from**: The path that need to be redirected: you can type any URL or select an existing django CMS page.
* **Redirect to**: The path to which the request will be redirected: you can type any URL or select an existing django CMS page.
* **Response code**: You can select 3 types of status_code header: 301 (permanent redirect), 302 (temporary redirect) or 410 (permanent unavailable resource).

Each **redirect from** URL must be unique and start with a slash. If you leave out the
leading slash when creating a redirect, it is added automatically.

*****************
Redirect examples
*****************

From: ``/something/old-path`` (no trailing slash)
To: ``/something-else/new-path/``
``APPEND_SLASH`` setting is ``True``

* When on Django >= 4.2:

    * visiting ``/something/old-path`` will correctly redirect to ``something-else/new-path/``
    * visiting ``/something/old-path/`` will return a 404

* When on Django < 4.2:

    * visiting ``/something/old-path`` will redirect to ``something/old-path/``
    * visiting ``/something/old-path/`` will return a 404

From: ``/something/old-path/`` (trailing slash)
To: ``/something-else/new-path/``
``APPEND_SLASH`` setting is ``True``

* When on Django >= 4.2:

    * visiting ``/something/old-path`` will correctly redirect to ``something-else/new-path/``
    * visiting ``/something/old-path/`` will correctly redirect to ``something-else/new-path/``

* When on Django < 4.2:

    * visiting ``/something/old-path`` will redirect to ``something/old-path/`` and then will correctly redirect to ``something-else/new-path/``
    * visiting ``/something/old-path/`` will correctly redirect to ``something-else/new-path/``

From: ``/something/old-path`` (no trailing slash)
To: ``/something-else/new-path/``
``APPEND_SLASH`` setting is ``False``

* Every version of Django:

    * visiting ``/something/old-path`` will correctly redirect to ``something-else/new-path/``
    * visiting ``/something/old-path/`` will return a 404

From: ``/something/old-path/`` (trailing slash)
To: ``/something-else/new-path/``
``APPEND_SLASH`` setting is ``False``

* Every version of Django:

    * visiting ``/something/old-path`` will correctly redirect to ``something-else/new-path/``
    * visiting ``/something/old-path/`` will correctly redirect to ``something-else/new-path/``

****************
Subpath matching
****************

Each redirect can match the exact incoming request path (the default behavior) or a subpath.

Subpath matching comes in two behaviour:

Plain subpath matching
======================

The registered redirects will be checked against the incoming URL and the longest string matching the beginning of the request path will be selected.

The request will be then redirected by replacing the matching **Redirect from** with the **Redirect to** in the original URL.

**Example**

* Incoming request: ``/en/some/path/``
* Redirect from: ``/en/some``
* Redirect to: ``/en/other``
* Resulting redirect: ``/en/other/path/``


Catchall redirect
=================

As in **plain subpath matching** the registered redirects will be checked against the incoming URL and the longest string matching the beginning of the request path will be selected.

The request will be then redirected to the **Redirect to** without further changes.

**Example**

* Incoming request: ``/en/some/path/``
* Redirect from: ``/en/some``
* Redirect to: ``/en/other``
* Resulting redirect: ``/en/other``
