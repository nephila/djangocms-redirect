.. :changelog:

*******
History
*******

.. towncrier release notes start

0.7.2 (2023-09-26)
==================

Features
--------

- Migrate to bump-my-version (#56)


0.7.1 (2023-08-11)
==================

Features
--------

- Add missing subpath_match and catchall_redirect fields in admin (#44)


Bugfixes
--------

- Fix django-multisite compatibility issue (#47)


0.7.0 (2023-08-09)
==================

Features
--------

- Add django 4.2 compatibility, drop python<3.9, djangocms<3.9 and django<3.2 (#42)


0.6.0 (2020-11-15)
==================

Features
--------

- Drop Python 2, Django < 2.2 - Update toolchain (#39)
- Fix Handling of trailing slashes in redirects (#31)


Unreleased
==================

* Nothing yet

0.5.0 (2019-12-27)
==================

* Add compatibility with Django 2.2
* Drop compatibility with Django < 1.11
* Drop compatibility with django CMS < 3.6
* Move to django-app-helper
* Add support to match unquoted strings as redirect old path

0.4.0 (2019-08-22)
==================

* Add subpath matching

0.3.1 (2019-07-13)
==================

* Ignore querystring when matching redirect objects

0.3.0 (2019-03-11)
==================

* Added compatibility to Django 2.0, 2.1

0.2.3 (unreleased)
==================

* Add support to match unquoted strings as redirect old path

0.2.2 (2019-06-02)
==================

* Ignore querystring when matching redirect objects

0.2.1 (2019-04-22)
==================

* Fixed compatibility issue with Django 1.8

0.2.0 (2018-11-03)
==================

* Updated for Django 1.11
* Added configurable cache timeout
* Added configuration option to check redirect on 404 only

0.1.1 (2017-11-19)
==================

* Added missing migration.
* Fixed compatibility issue with Django 1.8

0.1.0 (2016-02-01)
==================

* First release on PyPI.
