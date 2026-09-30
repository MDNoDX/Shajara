"""Moving data in and out: GEDCOM export and import, the archive file (JSON)."""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.utils.translation import gettext as _
from django.utils.translation import pgettext
from django.views.decorators.http import require_POST

from .. import archive_io, duplicates, gedcom, history
from ..access import require_edit
from ..kinship import Archive
from ..models import Change


@login_required
def gedcom_export(request):
    archive = Archive(request.archive)
    data = gedcom.export(archive, request.archive.display_name)
    response = HttpResponse(data.encode("utf-8"), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = content_disposition_header(True, pgettext("file name", "family-tree") + ".ged")
    return response


@require_POST
@login_required
def gedcom_import(request):
    """Add the people of a GEDCOM file (from another genealogy program) to the archive."""
    owner = require_edit(request)
    upload = request.FILES.get("file")
    if upload is None or upload.size > 8 * 1024 * 1024:
        messages.error(request, _("Choose a GEDCOM file (up to 8 MB)."))
        return redirect(reverse("accounts:data") + "#gedcom")
    raw = upload.read()
    try:
        counts = gedcom.import_file(owner, raw)
    except gedcom.GedcomError:
        messages.error(request, _("This file could not be read as GEDCOM."))
        return redirect(reverse("accounts:data") + "#gedcom")
    history.record(owner, request.user, Change.Action.CREATED, subject=upload.name[:200], what="gedcom",
                   details=counts)
    messages.success(request, _("Imported from GEDCOM: %(people)d people, %(families)d families.") % counts)
    return redirect("genealogy:duplicates" if duplicates.pairs(owner) else "genealogy:tree")


@login_required
def archive_export(request):
    """The signed-in user's own archive as one JSON file (with photos)."""
    data = archive_io.export_archive(request.user)
    response = HttpResponse(json.dumps(data, ensure_ascii=False, indent=1), content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = content_disposition_header(True, archive_io.export_filename())
    return response
