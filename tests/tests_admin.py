from unittest import skipIf

from cms.forms.widgets import PageSmartLinkWidget
from django.contrib import admin
from django.urls import reverse
from django.utils.translation import activate

from djangocms_redirect.compat import CMS_LT_4
from djangocms_redirect.models import Redirect

from . import BaseRedirectTest

redirect_admin = admin.site._registry[Redirect]


class AdminPageTest(BaseRedirectTest):
    @skipIf(not CMS_LT_4, "Test relevant only for CMS<4.0")
    def test_get_form_widgets(self):
        """
        Admin form has proper widgets.
        """
        activate("it")
        request = self.request("/", lang="it", user=self.user)
        form_class = redirect_admin.get_form(request)
        form = form_class()
        self.assertTrue(form.fields["old_path"].widget, PageSmartLinkWidget)
        self.assertTrue(form.fields["new_path"].widget, PageSmartLinkWidget)
        self.assertEqual(form.fields["old_path"].widget.language, "it")
        self.assertEqual(form.fields["new_path"].widget.language, "it")
        self.assertEqual(form.fields["old_path"].widget.ajax_url, reverse("admin:cms_page_get_published_pagelist"))
        self.assertEqual(form.fields["new_path"].widget.ajax_url, reverse("admin:cms_page_get_published_pagelist"))
        activate("en")

    @skipIf(CMS_LT_4, "Test relevant only for CMS>=4.0")
    def test_get_form_widgets_djangocms_4_plus(self):
        """
        Admin form has proper widgets.
        """
        activate("it")
        request = self.request("/", lang="it", user=self.user)
        form_class = redirect_admin.get_form(request)
        form = form_class()
        self.assertTrue(form.fields["old_path"].widget, PageSmartLinkWidget)
        self.assertTrue(form.fields["new_path"].widget, PageSmartLinkWidget)
        self.assertEqual(form.fields["old_path"].widget.language, "it")
        self.assertEqual(form.fields["new_path"].widget.language, "it")
        self.assertEqual(form.fields["old_path"].widget.ajax_url, reverse("admin:cms_page_get_list"))
        self.assertEqual(form.fields["new_path"].widget.ajax_url, reverse("admin:cms_page_get_list"))
        activate("en")
