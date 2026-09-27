from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from apps.core import views as core_views

urlpatterns = [
    path("", core_views.home, name="home"),
    path("til/", core_views.set_language, name="set_language"),
    # Translations for static/js, from locale/*/LC_MESSAGES/djangojs.po.
    path("jsi18n/", JavaScriptCatalog.as_view(packages=["apps.core"]), name="javascript-catalog"),
    path("", include("apps.accounts.urls")),
    path("", include("apps.genealogy.urls")),
    path("dostlar/", include("apps.friends.urls")),
    path("admin/", admin.site.urls),
]

handler400 = "apps.core.views.bad_request"
handler403 = "apps.core.views.permission_denied"
handler404 = "apps.core.views.page_not_found"
handler500 = "apps.core.views.server_error"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
