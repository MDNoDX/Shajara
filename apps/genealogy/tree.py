"""Family-tree layout shared by the web view (SVG) and the PDF export.

Around a focus person the chart shows:
  * ancestors above (father's line on the left, mother's on the right),
  * the focus person between their brothers and sisters, ordered by birth,
  * spouses beside each person and descendants below, grouped by the other
    parent.
A person reachable twice (e.g. cousins who married) is drawn in full once;
the second place is a small reference card.

Coordinates are in abstract units; the browser and the PDF scale them.
"""
from django.utils.translation import ngettext

from .kinship import Archive

CARD_W, CARD_H = 188, 84
SIB_GAP, COUPLE_GAP, ROW_GAP = 28, 36, 64
ROW_H = CARD_H + ROW_GAP
PAD = 40


class TreeLayout:
    def __init__(self, archive: Archive, focus_id, up=3, down=3):
        self.a = archive
        self.focus = focus_id
        self.up = up
        self.down = down
        self.seen = set()
        self.nodes = []
        self.lines = []

    # ---- output helpers ---------------------------------------------------
    def _node(self, pk, x, y, dup=False, hidden=0):
        self.nodes.append({"id": pk, "x": x, "y": y, "dup": dup, "hidden": hidden})

    def _line(self, points, kind="child"):
        self.lines.append({"points": [[round(px, 1), round(py, 1)] for px, py in points], "kind": kind})

    def _connect(self, drops, child_centers, child_y):
        """Lines from parents' drop points to the tops of their children."""
        bar_y = child_y - ROW_GAP / 2
        xs = [d[0] for d in drops] + child_centers
        for dx, dy in drops:
            self._line([(dx, dy), (dx, bar_y)])
        if len(xs) > 1 and min(xs) != max(xs):
            self._line([(min(xs), bar_y), (max(xs), bar_y)])
        for cx in child_centers:
            self._line([(cx, bar_y), (cx, child_y)])

    def _marriage(self, a, b):
        for partner, m in self.a.unions.get(a, []):
            if partner == b:
                return m
        return None

    # ---- descendants --------------------------------------------------------
    def _desc_unit(self, pk, depth):
        unit = {"pk": pk, "dup": pk in self.seen, "groups": [], "hidden": 0}
        if unit["dup"]:
            return unit
        self.seen.add(pk)
        groups = {}
        for partner, marriage in self.a.unions.get(pk, []):
            groups[partner] = {"partner": partner, "marriage": marriage, "kids": []}
        for kid in self.a.children.get(pk, []):
            child = self.a.people[kid]
            other = child.mother_id if child.father_id == pk else child.father_id
            other = other if other in self.a.people else None
            groups.setdefault(other, {"partner": other, "marriage": None, "kids": []})["kids"].append(kid)
        ordered = [g for key, g in groups.items() if key is not None]
        if None in groups:
            ordered.append(groups[None])
        for g in ordered:
            g["partner_dup"] = g["partner"] is not None and g["partner"] in self.seen
            if g["partner"] is not None:
                self.seen.add(g["partner"])
        for g in ordered:
            if depth > 0:
                g["children"] = [self._desc_unit(k, depth - 1) for k in g["kids"]]
            else:
                g["children"] = []
                unit["hidden"] += len(g["kids"])
        unit["groups"] = ordered
        unit["cards"] = 1 + sum(1 for g in ordered if g["partner"] is not None)
        return unit

    def _measure(self, unit):
        if unit["dup"]:
            unit["own"] = unit["w"] = CARD_W
            unit["child_w"] = 0
            return
        unit["own"] = unit["cards"] * CARD_W + (unit["cards"] - 1) * COUPLE_GAP
        kids = [c for g in unit["groups"] for c in g["children"]]
        for c in kids:
            self._measure(c)
        with_kids = sum(1 for g in unit["groups"] if g["children"])
        unit["child_w"] = (
            sum(c["w"] for c in kids) + SIB_GAP * (len(kids) - 1) + SIB_GAP * max(0, with_kids - 1) if kids else 0
        )
        unit["w"] = max(unit["own"], unit["child_w"])

    def _place(self, unit, x0, y):
        if unit["dup"]:
            unit["sx"] = x0
            self._node(unit["pk"], x0, y, dup=True)
            return
        bx = x0 + (unit["w"] - unit["own"]) / 2
        unit["sx"] = bx
        self._node(unit["pk"], bx, y, hidden=unit["hidden"])
        slot = 1
        for g in unit["groups"]:
            if g["partner"] is None:
                g["drop"] = (bx + CARD_W / 2, y + CARD_H)
                continue
            px = bx + slot * (CARD_W + COUPLE_GAP)
            self._node(g["partner"], px, y, dup=g["partner_dup"])
            kind = "divorced" if g["marriage"] and g["marriage"].is_divorced else (
                "couple" if g["marriage"] else "partners")
            mid_y = y + CARD_H / 2
            if slot == 1:
                self._line([(bx + CARD_W, mid_y), (px, mid_y)], kind)
                g["drop"] = ((bx + CARD_W + px) / 2, mid_y)
            else:
                top = y - 14
                self._line([(bx + CARD_W / 2, y), (bx + CARD_W / 2, top), (px + CARD_W / 2, top), (px + CARD_W / 2, y)], kind)
                g["drop"] = (px + CARD_W / 2, y + CARD_H)
            slot += 1
        if not unit["child_w"]:
            return
        cx = x0 + (unit["w"] - unit["child_w"]) / 2
        cy = y + ROW_H
        first = True
        for g in unit["groups"]:
            if not g["children"]:
                continue
            if not first:
                cx += SIB_GAP
            first = False
            centers = []
            for c in g["children"]:
                self._place(c, cx, cy)
                centers.append(c["sx"] + CARD_W / 2)
                cx += c["w"] + SIB_GAP
            self._connect([g["drop"]], centers, cy)

    # ---- ancestors ----------------------------------------------------------
    def _anc_node(self, pk, depth):
        node = {"pk": pk, "parents": [], "dup": False}
        if depth <= 0:
            return node
        for par in self.a.parents(pk):
            if par in self.seen:
                node["parents"].append({"pk": par, "parents": [], "dup": True})
            else:
                self.seen.add(par)
                node["parents"].append(self._anc_node(par, depth - 1))
        return node

    def _measure_anc(self, node):
        if not node["parents"]:
            node["w"] = CARD_W
        else:
            for p in node["parents"]:
                self._measure_anc(p)
            span = sum(p["w"] for p in node["parents"]) + SIB_GAP * (len(node["parents"]) - 1)
            node["w"] = max(CARD_W, span)

    def _place_parents(self, parents, center_x, child_centers, child_y):
        """Place a row of (at most two) parents centred over `center_x`."""
        span = sum(p["w"] for p in parents) + SIB_GAP * (len(parents) - 1)
        px = center_x - span / 2
        py = child_y - ROW_H
        for p in parents:
            self._place_anc(p, px, py)
            px += p["w"] + SIB_GAP
        if len(parents) == 2:
            left, right = parents
            mid_y = py + CARD_H / 2
            m = self._marriage(left["pk"], right["pk"])
            kind = "divorced" if m and m.is_divorced else ("couple" if m else "partners")
            self._line([(left["x"] + CARD_W, mid_y), (right["x"], mid_y)], kind)
            drop = ((left["x"] + CARD_W + right["x"]) / 2, mid_y)
        else:
            drop = (parents[0]["x"] + CARD_W / 2, py + CARD_H)
        self._connect([drop], child_centers, child_y)

    def _place_anc(self, node, x0, y):
        x = x0 + (node["w"] - CARD_W) / 2
        node["x"] = x
        self._node(node["pk"], x, y, dup=node["dup"])
        if node["parents"]:
            self._place_parents(node["parents"], x + CARD_W / 2, [x + CARD_W / 2], y)

    # ---- whole chart --------------------------------------------------------
    def _sibship(self):
        me = self.a.people[self.focus]
        if not me.father_id and not me.mother_id:
            return [self.focus]
        same = [
            pk for pk, p in self.a.people.items()
            if p.father_id == me.father_id and p.mother_id == me.mother_id
        ]
        return sorted(same, key=lambda pk: (self.a.people[pk].birth_key or (9999,), pk))

    def build(self):
        units = []
        for pk in self._sibship():
            units.append(self._desc_unit(pk, self.down if pk == self.focus else 0))
        x = 0
        for u in units:
            self._measure(u)
            self._place(u, x, 0)
            x += u["w"] + SIB_GAP
        centers = [u["sx"] + CARD_W / 2 for u in units]

        root = self._anc_node(self.focus, self.up)
        if root["parents"]:
            for p in root["parents"]:
                self._measure_anc(p)
            self._place_parents(root["parents"], (min(centers) + max(centers)) / 2, centers, 0)
        return self._finish()

    def _finish(self):
        min_x = min(n["x"] for n in self.nodes)
        min_y = min(n["y"] for n in self.nodes)
        dx, dy = PAD - min_x, PAD - min_y
        for n in self.nodes:
            n["x"] = round(n["x"] + dx, 1)
            n["y"] = round(n["y"] + dy, 1)
        for line in self.lines:
            line["points"] = [[round(px + dx, 1), round(py + dy, 1)] for px, py in line["points"]]
        width = max(n["x"] for n in self.nodes) + CARD_W + PAD
        height = max(n["y"] for n in self.nodes) + CARD_H + PAD
        return {"nodes": self.nodes, "lines": self.lines, "width": round(width), "height": round(height)}


def build_tree(archive: Archive, focus_id, up=3, down=3, photo_urls=True, viewer_is_owner=True):
    """Layout plus the text of every card, in the active language."""
    layout = TreeLayout(archive, focus_id, up=up, down=down).build()
    owner_self = archive.owner.person_id if viewer_is_owner else None
    for node in layout["nodes"]:
        person = archive.people[node["id"]]
        # "You" only when the centre is the viewer's own record.
        is_centre_not_owner = person.pk == focus_id and focus_id != owner_self
        node.update(
            name=person.short_name,
            years=person.lifespan,
            label="" if is_centre_not_owner else archive.label(focus_id, person.pk),
            gender=person.gender,
            deceased=person.is_deceased,
            focus=person.pk == focus_id,
            url=person.get_absolute_url(),
            photo=person.photo.url if photo_urls and person.photo else "",
            hidden_label=ngettext(
                "%(count)d more child", "%(count)d more children", node["hidden"]
            ) % {"count": node["hidden"]} if node["hidden"] else "",
        )
    layout["card"] = {"w": CARD_W, "h": CARD_H}
    layout["focus"] = focus_id
    return layout
