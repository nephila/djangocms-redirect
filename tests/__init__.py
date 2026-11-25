from app_helper.base_test import BaseTestCase
from django.core.cache import cache

from djangocms_redirect.table import clear_memo


class BaseRedirectTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        clear_memo()
