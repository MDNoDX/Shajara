"""What several pages share: the person in the centre, the state of the tree, PDF replies, search."""
from django.http import HttpResponse
from django.utils.http import content_disposition_header

from apps.core.text import search_tokens

from ..access import viewer_person


def _focus_for(request, archive, requested=None):
    """The person in the centre: the one asked for, else the viewer's own
    record, else the archive owner's, else anyone."""
    if requested:
        try:
            pk = int(requested)
        except (TypeError, ValueError):
            pk = None
        if pk in archive.people:
            return pk
    me = viewer_person(request, archive)
    return me if me is not None else next(iter(archive.people), None)


def _ids(value):
    out = set()
    for part in (value or "").split(","):
        if part.strip().isdigit() and len(out) < 500:
            out.add(int(part))
    return out


def _tree_state(request):
    """Which branches are open: ?all=1&open=…&closed=…&folded=…&kids=… (comma-separated ids)."""
    return {
        "open_all": request.GET.get("all") == "1",
        "opened": _ids(request.GET.get("open")),
        "closed": _ids(request.GET.get("closed")),
        "folded": _ids(request.GET.get("folded")),
        "unfolded": _ids(request.GET.get("kids")),
    }


def _pdf_response(data, filename):
    response = HttpResponse(data, content_type="application/pdf")
    response["Content-Disposition"] = content_disposition_header(True, filename)
    return response


def _search(queryset, query):
    for token in search_tokens(query):
        queryset = queryset.filter(search_key__contains=token)
    return queryset
