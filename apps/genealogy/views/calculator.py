""""Who is who to whom?": the relationship between two people."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..access import viewer_person
from ..kinship import Archive


@login_required
def calculator(request):
    archive = Archive(request.archive)
    a = b = None
    result = None
    try:
        a = int(request.GET.get("a") or viewer_person(request, archive) or 0)
        b = int(request.GET.get("b") or 0)
    except ValueError:
        a = b = None
    if a in archive.people and b in archive.people and a != b:
        chain = archive.path(a, b)
        steps = []
        if chain:
            for prev, cur in zip(chain, chain[1:]):
                steps.append((archive.people[cur], archive.label(prev, cur)))
        result = {
            "a": archive.people[a], "b": archive.people[b],
            "b_to_a": archive.label(a, b), "a_to_b": archive.label(b, a),
            "chain_start": archive.people[a], "steps": steps, "connected": chain is not None,
        }
    return render(request, "genealogy/calculator.html", {
        "a": a, "b": b, "result": result,
        "person_a": archive.people.get(a), "person_b": archive.people.get(b),
    })
