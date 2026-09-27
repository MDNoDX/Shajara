"""PDF exports in the reader's interface language.

All text comes from the active gettext catalogue, so a user who works in
Кириллча receives a Cyrillic PDF. DejaVu Sans is embedded because the
standard PDF fonts have no glyphs for Ў Қ Ғ Ҳ or the Uzbek apostrophe ʻ.
"""
from collections import deque
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext, pgettext
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.core.dates import format_date

from .terminology import SECTION
from .tree import CARD_H, CARD_W

FONT = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
FONT_ITALIC = "DejaVuSans-Oblique"
FONT_BOLD_ITALIC = "DejaVuSans-BoldItalic"

INK = colors.HexColor("#1f2a26")
MUTED = colors.HexColor("#5f6b66")
ACCENT = colors.HexColor("#2f6f5e")
LINE = colors.HexColor("#c9d3ce")
MALE_BG = colors.HexColor("#e8f0f7")
FEMALE_BG = colors.HexColor("#f7ecef")
FOCUS_BG = colors.HexColor("#e3f1ea")

_registered = False


def register_fonts():
    global _registered
    if _registered:
        return
    base = settings.PDF_FONT_DIR
    pdfmetrics.registerFont(TTFont(FONT, str(base / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(base / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_ITALIC, str(base / "DejaVuSans-Oblique.ttf")))
    # No bold-oblique file is shipped; bold is used for bold italic text.
    pdfmetrics.registerFont(TTFont(FONT_BOLD_ITALIC, str(base / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD, italic=FONT_ITALIC, boldItalic=FONT_BOLD_ITALIC)
    _registered = True


def _styles():
    register_fonts()
    return {
        "title": ParagraphStyle("title", fontName=FONT_BOLD, fontSize=20, leading=25, textColor=INK, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", fontName=FONT, fontSize=11, leading=15, textColor=MUTED, spaceAfter=10),
        "h2": ParagraphStyle("h2", fontName=FONT_BOLD, fontSize=13, leading=17, textColor=ACCENT, spaceBefore=12, spaceAfter=5),
        "h3": ParagraphStyle("h3", fontName=FONT_BOLD, fontSize=11, leading=14, textColor=INK, spaceBefore=6, spaceAfter=2),
        "body": ParagraphStyle("body", fontName=FONT, fontSize=10, leading=14.5, textColor=INK),
        "small": ParagraphStyle("small", fontName=FONT, fontSize=8.5, leading=11.5, textColor=MUTED),
        "label": ParagraphStyle("label", fontName=FONT, fontSize=9, leading=12, textColor=MUTED),
        "center": ParagraphStyle("center", fontName=FONT, fontSize=9, leading=12, textColor=MUTED, alignment=TA_CENTER),
    }


def _p(text, style):
    """Paragraph from user text: escaped, line breaks kept."""
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


class _NumberedCanvas(pdf_canvas.Canvas):
    """Adds "Page 2 of 5" and the generation date to every page."""

    def __init__(self, *args, footer="", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved = []
        self._footer = footer

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total):
        w, _h = self._pagesize
        self.setFont(FONT, 8)
        self.setFillColor(MUTED)
        self.drawString(15 * mm, 10 * mm, self._footer)
        page = _("Page %(page)d of %(total)d") % {"page": self._pageNumber, "total": total}
        self.drawRightString(w - 15 * mm, 10 * mm, page)


def _footer_text():
    return _("Created on %(date)s · Family tree") % {"date": format_date(timezone.now())}


def _build(story_items, pagesize=A4, title=""):
    register_fonts()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=pagesize, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
        title=title, author=_("Family tree"),
    )
    footer = _footer_text()
    doc.build(story_items, canvasmaker=lambda *a, **k: _NumberedCanvas(*a, footer=footer, **k))
    return buf.getvalue()


def _facts(person):
    rows = []

    def add(label, value):
        if value:
            rows.append((label, value))

    add(_("Gender"), person.get_gender_display())
    add(_("Date of birth"), person.birth_date_display)
    add(_("Place of birth"), person.birth_place)
    if person.is_deceased:
        add(_("Date of death"), person.death_date_display or _("unknown"))
        add(_("Place of death"), person.death_place)
    add(_("Occupation"), person.occupation)
    add(_("Education"), person.education)
    return rows


def _facts_table(person, st, width):
    rows = [[_p(k, st["label"]), _p(v, st["body"])] for k, v in _facts(person)]
    if not rows:
        return None
    t = Table(rows, colWidths=[width * 0.32, width * 0.68])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _family_lines(archive, person):
    """[(heading, [names…])] for the person's closest family."""
    def name(pk):
        p = archive.people[pk]
        return f"{p.full_name} ({p.lifespan})" if p.lifespan else p.full_name

    out = []
    if person.father_id in archive.people:
        out.append((str(SECTION["father"]), [name(person.father_id)]))
    if person.mother_id in archive.people:
        out.append((str(SECTION["mother"]), [name(person.mother_id)]))
    spouses = archive.spouses(person.pk)
    if spouses:
        out.append((str(SECTION["spouses"]), [f"{name(s)} — {archive.label(person.pk, s)}" for s in spouses]))
    kids = archive.children.get(person.pk, [])
    if kids:
        out.append((str(SECTION["children"]), [f"{name(k)} — {archive.label(person.pk, k)}" for k in kids]))
    sibs = archive.siblings(person.pk)
    if sibs:
        out.append((str(SECTION["siblings"]), [f"{name(s)} — {archive.label(person.pk, s)}" for s in sibs]))
    return out


def _photo(person, size):
    if not person.photo:
        return None
    try:
        img = Image(person.photo.path)
    except Exception:
        return None
    ratio = img.imageWidth / float(img.imageHeight or 1)
    img.drawHeight = size
    img.drawWidth = size * ratio
    return img


def person_pdf(archive, person, focus_id=None, stories=()):
    st = _styles()
    width = A4[0] - 36 * mm
    items = []
    head = [_p(person.full_name, st["title"])]
    sub = [person.lifespan]
    if focus_id and focus_id != person.pk:
        rel = archive.label(focus_id, person.pk)
        if rel:
            sub.append(rel)
    head.append(_p(" · ".join(s for s in sub if s), st["subtitle"]))
    photo = _photo(person, 34 * mm)
    if photo:
        t = Table([[head, photo]], colWidths=[width - 40 * mm, 40 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        items.append(t)
    else:
        items.extend(head)

    facts = _facts_table(person, st, width)
    if facts:
        items.append(_p(_("Personal details"), st["h2"]))
        items.append(facts)

    family = _family_lines(archive, person)
    if family:
        items.append(_p(_("Family"), st["h2"]))
        for heading, names in family:
            items.append(KeepTogether([_p(heading, st["h3"])] + [_p(n, st["body"]) for n in names]))

    if person.biography:
        items.append(_p(_("Biography"), st["h2"]))
        items.append(_p(person.biography, st["body"]))
    if person.life_story:
        items.append(_p(_("Life story"), st["h2"]))
        items.append(_p(person.life_story, st["body"]))
    if stories:
        items.append(_p(_("Stories"), st["h2"]))
        for s in stories:
            items.append(_p(s.title, st["h3"]))
            if s.year:
                items.append(_p(pgettext("year only", "{year}").format(year=s.year), st["small"]))
            items.append(_p(s.body, st["body"]))
            items.append(Spacer(1, 4))
    return _build(items, title=person.full_name)


def generations(archive, focus_id):
    """Group everyone in the archive by generation relative to focus_id.

    Generation numbers are relative (parents −1, children +1, spouses equal);
    people not connected to the focus person are listed last.
    """
    gen = {focus_id: 0}
    queue = deque([focus_id])
    while queue:
        cur = queue.popleft()
        steps = [(p, -1) for p in archive.parents(cur)]
        steps += [(c, 1) for c in archive.children.get(cur, [])]
        steps += [(s, 0) for s in archive.spouses(cur)]
        for nxt, d in steps:
            if nxt not in gen:
                gen[nxt] = gen[cur] + d
                queue.append(nxt)
    groups = {}
    for pk, g in gen.items():
        groups.setdefault(g, []).append(pk)
    ordered = [sorted(groups[g], key=lambda pk: archive.people[pk].birth_key or (9999,)) for g in sorted(groups)]
    unconnected = sorted(
        (pk for pk in archive.people if pk not in gen), key=lambda pk: archive.people[pk].full_name
    )
    return ordered, unconnected


def family_book_pdf(archive, focus_id, owner_name, viewer_is_owner=True):
    """Whole archive: the tree chart (if given) and everyone by generation."""
    st = _styles()
    items = [
        _p(_("Family tree"), st["title"]),
        _p(owner_name, st["subtitle"]),
    ]
    people_count = len(archive.people)
    items.append(_p(ngettext("%(count)d person", "%(count)d people", people_count) % {"count": people_count}, st["small"]))
    ordered, unconnected = generations(archive, focus_id)
    width = A4[0] - 36 * mm
    for i, group in enumerate(ordered, start=1):
        items.append(_p(_("Generation %(number)d") % {"number": i}, st["h2"]))
        for pk in group:
            items.append(_person_entry(archive, archive.people[pk], focus_id, st, width, viewer_is_owner))
    if unconnected:
        items.append(_p(_("Not yet linked to the family"), st["h2"]))
        for pk in unconnected:
            items.append(_person_entry(archive, archive.people[pk], focus_id, st, width, viewer_is_owner))
    return _build(items, title=_("Family tree"))


def _person_entry(archive, person, focus_id, st, width, viewer_is_owner=True):
    parts = [_p(person.full_name, st["h3"])]
    label = "" if person.pk == focus_id and not viewer_is_owner else archive.label(focus_id, person.pk)
    sub = [s for s in (person.lifespan, label) if s]
    if sub:
        parts.append(_p(" · ".join(sub), st["small"]))
    facts = [f"{k}: {v}" for k, v in _facts(person)[1:]]
    if facts:
        parts.append(_p("; ".join(facts), st["body"]))
    for heading, names in _family_lines(archive, person)[:4]:
        parts.append(_p(f"{heading}: " + ", ".join(names), st["small"]))
    if person.biography:
        parts.append(_p(person.biography, st["body"]))
    parts.append(Spacer(1, 6))
    return KeepTogether(parts)


# ---------------------------------------------------------------------------
# Tree chart
# ---------------------------------------------------------------------------
def _wrap(text, font, size, max_w, max_lines):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if pdfmetrics.stringWidth(trial, font, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and pdfmetrics.stringWidth(lines[-1] + "…", font, size) > max_w:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    # A single word longer than the card is shortened too.
    fixed = []
    for line in lines:
        while pdfmetrics.stringWidth(line, font, size) > max_w and len(line) > 1:
            line = line[:-2] + "…"
        fixed.append(line)
    return fixed


def tree_pdf(layout, title, subtitle):
    """The chart from tree.build_tree on one landscape page (A4 or A3)."""
    register_fonts()
    lw, lh = layout["width"], layout["height"]
    pagesize = landscape(A4) if max(lw, lh) < 2200 else landscape(A3)
    pw, ph = pagesize
    margin, head_h = 12 * mm, 20 * mm
    scale = min((pw - 2 * margin) / lw, (ph - 2 * margin - head_h) / lh, 0.9)
    ox = (pw - lw * scale) / 2
    top = ph - margin - head_h

    buf = BytesIO()
    c = _NumberedCanvas(buf, pagesize=pagesize, footer=_footer_text())
    c.setTitle(title)
    c.setFont(FONT_BOLD, 16)
    c.setFillColor(INK)
    c.drawString(margin, ph - margin - 7 * mm, title)
    c.setFont(FONT, 9.5)
    c.setFillColor(MUTED)
    c.drawString(margin, ph - margin - 13 * mm, subtitle)

    def tx(x):
        return ox + x * scale

    def ty(y):
        return top - y * scale

    for line in layout["lines"]:
        c.setStrokeColor(ACCENT if line["kind"] in ("couple", "divorced") else MUTED)
        c.setLineWidth(1.1 if line["kind"] == "couple" else 0.8)
        c.setDash(3, 2) if line["kind"] in ("divorced", "partners") else c.setDash()
        path = c.beginPath()
        (x0, y0), *rest = line["points"]
        path.moveTo(tx(x0), ty(y0))
        for x, y in rest:
            path.lineTo(tx(x), ty(y))
        c.drawPath(path, stroke=1, fill=0)
    c.setDash()

    pad = 8 * scale
    inner = (CARD_W - 16) * scale
    for n in layout["nodes"]:
        x, y = tx(n["x"]), ty(n["y"] + CARD_H)
        w, h = CARD_W * scale, CARD_H * scale
        bg = FOCUS_BG if n["focus"] else (MALE_BG if n["gender"] == "male" else FEMALE_BG)
        c.setFillColor(colors.white if n["dup"] else bg)
        c.setStrokeColor(ACCENT if n["focus"] else LINE)
        c.setLineWidth(1.4 if n["focus"] else 0.6)
        if n["dup"]:
            c.setDash(3, 2)
        c.roundRect(x, y, w, h, 6 * scale, stroke=1, fill=1)
        c.setDash()
        name_size = 11 * scale
        lines = _wrap(n["name"], FONT_BOLD, name_size, inner, 2)
        cy = ty(n["y"]) - pad - name_size
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, name_size)
        for ln in lines:
            c.drawString(x + pad, cy, ln)
            cy -= name_size * 1.2
        small = 9 * scale
        c.setFont(FONT, small)
        c.setFillColor(MUTED)
        if n["years"]:
            c.drawString(x + pad, cy - 1 * scale, n["years"])
            cy -= small * 1.3
        if n["label"]:
            c.setFillColor(ACCENT)
            label = _wrap(n["label"], FONT, small, inner, 1)[0]
            c.drawString(x + pad, ty(n["y"] + CARD_H) + pad, label)
        if n["hidden_label"]:
            c.setFillColor(MUTED)
            c.setFont(FONT, 8 * scale)
            c.drawCentredString(x + w / 2, ty(n["y"] + CARD_H + 16), n["hidden_label"])
    c.showPage()
    c.save()
    return buf.getvalue()
