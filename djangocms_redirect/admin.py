from cms.forms.widgets import PageSmartLinkWidget
from django.contrib import admin
from django.forms import ModelForm
from django.utils.translation import get_language

from .compat import CMS_LT_4
from .models import Redirect
from .utils import normalize_url


class RedirectForm(ModelForm):
    class Meta:
        model = Redirect
        fields = ["site", "old_path", "new_path", "response_code", "subpath_match", "catchall_redirect"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        pagelist_endpoint = "admin:cms_page_get_published_pagelist"
        # django-cms 4+ support
        if not CMS_LT_4:
            pagelist_endpoint = "admin:cms_page_get_list"

        widget = PageSmartLinkWidget(ajax_view=pagelist_endpoint)
        widget.language = get_language()
        self.fields["old_path"].widget = widget
        self.fields["new_path"].widget = widget

    def clean_old_path(self):
        return normalize_url(self.cleaned_data.get("old_path"))


@admin.register(Redirect)
class RedirectAdmin(admin.ModelAdmin):
    list_display = ("old_path", "new_path", "response_code", "subpath_match", "catchall_redirect")
    list_filter = ("site",)
    search_fields = ("old_path", "new_path")
    radio_fields = {"site": admin.VERTICAL}
    form = RedirectForm
