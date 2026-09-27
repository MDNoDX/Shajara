"""Relationship names between two people in one family archive.

`Archive` loads a user's people and marriages once; `Archive.relation(focus,
other)` returns a code from terminology.KIN such as "older_brother" or
"maternal_aunt". The rules follow Uzbek usage: siblings by relative age,
aunts/uncles/cousins by the side of the family, in-laws by the linking person.
"""
from collections import deque

from apps.accounts.models import Gender

from .models import Marriage, Person
from .terminology import kin


class Archive:
    def __init__(self, owner):
        self.owner = owner
        self.people = {p.pk: p for p in Person.objects.filter(owner=owner)}
        self.marriages = list(Marriage.objects.filter(owner=owner))
        self.children = {pk: [] for pk in self.people}
        for p in self.people.values():
            for parent_id in (p.father_id, p.mother_id):
                if parent_id in self.children:
                    self.children[parent_id].append(p.pk)
        for kids in self.children.values():
            kids.sort(key=lambda pk: self.people[pk].birth_key or (9999,))
        self.unions = {pk: [] for pk in self.people}
        for m in self.marriages:
            if m.husband_id in self.unions and m.wife_id in self.unions:
                self.unions[m.husband_id].append((m.wife_id, m))
                self.unions[m.wife_id].append((m.husband_id, m))
        self._anc = {}

    # ---- structure -------------------------------------------------------
    def get(self, pk):
        return self.people.get(pk)

    def parents(self, pk):
        p = self.people[pk]
        return [x for x in (p.father_id, p.mother_id) if x in self.people]

    def spouses(self, pk):
        return [sid for sid, _m in self.unions.get(pk, [])]

    def siblings(self, pk):
        p = self.people[pk]
        found = []
        for parent_id in (p.father_id, p.mother_id):
            if parent_id in self.children:
                found.extend(c for c in self.children[parent_id] if c != pk and c not in found)
        found.sort(key=lambda s: self.people[s].birth_key or (9999,))
        return found

    def ancestors(self, pk):
        """{ancestor_id: generations up}, including pk itself at 0."""
        if pk not in self._anc:
            dist = {pk: 0}
            queue = deque([pk])
            while queue:
                cur = queue.popleft()
                for par in self.parents(cur):
                    if par not in dist:
                        dist[par] = dist[cur] + 1
                        queue.append(par)
            self._anc[pk] = dist
        return self._anc[pk]

    def is_ancestor(self, candidate, pk):
        return candidate != pk and candidate in self.ancestors(pk)

    def descendants(self, pk):
        seen, queue = set(), deque([pk])
        while queue:
            for c in self.children.get(queue.popleft(), []):
                if c not in seen:
                    seen.add(c)
                    queue.append(c)
        return seen

    # ---- relationship names ---------------------------------------------
    def relation(self, focus, other):
        """Kinship code of `other` as seen from `focus`, or None if unrelated."""
        if focus == other:
            return "self"
        code = self._blood(focus, other)
        if code:
            return code
        return self._by_marriage(focus, other)

    def label(self, focus, other):
        code = self.relation(focus, other)
        return kin(code) if code else ""

    def _male(self, pk):
        return self.people[pk].gender == Gender.MALE

    def _older(self, a, b):
        """True if a was born before b, False if after, None if unknown."""
        ka, kb = self.people[a].birth_key, self.people[b].birth_key
        if ka is None or kb is None or ka == kb:
            return None
        return ka < kb

    def _common_ancestor(self, focus, other):
        up_f, up_o = self.ancestors(focus), self.ancestors(other)
        best = None
        for anc, a in up_f.items():
            if anc in up_o:
                b = up_o[anc]
                if best is None or a + b < best[0] + best[1]:
                    best = (a, b, anc)
        return best

    def _parent_towards(self, pk, ancestor, dist):
        """The parent of pk that lies on the line to `ancestor`."""
        for par in self.parents(pk):
            if self.ancestors(par).get(ancestor) == dist - 1:
                return par
        return None

    def _blood(self, focus, other):
        best = self._common_ancestor(focus, other)
        if not best:
            return None
        up, down, anc = best
        male = self._male(other)
        if down == 0:  # other is an ancestor of focus
            return {
                1: ("father", "mother"),
                2: ("grandfather", "grandmother"),
                3: ("great_grandfather", "great_grandmother"),
            }.get(up, ("forefather", "foremother"))[0 if male else 1]
        if up == 0:  # other is a descendant of focus
            if down == 1:
                return "son" if male else "daughter"
            return {2: "grandchild", 3: "great_grandchild", 4: "great_great_grandchild"}.get(down, "descendant")
        if up == 1 and down == 1:
            older = self._older(other, focus)
            if male:
                return {True: "older_brother", False: "younger_brother"}.get(older, "brother")
            return {True: "older_sister", False: "younger_sister"}.get(older, "sister")
        if up == 2 and down == 1:
            via = self._parent_towards(focus, anc, up)
            if via is None:
                return "relative"
            if self._male(via):
                return "paternal_uncle" if male else "paternal_aunt"
            return "maternal_uncle" if male else "maternal_aunt"
        if up == 1 and down == 2:
            return "nephew_niece"
        if up == 2 and down == 2:
            via_f = self._parent_towards(focus, anc, up)
            via_o = self._parent_towards(other, anc, down)
            if via_f is None or via_o is None:
                return "relative"
            side = "paternal" if self._male(via_f) else "maternal"
            kind = "uncle" if self._male(via_o) else "aunt"
            return f"{side}_{kind}_child"
        return "relative"

    def _by_marriage(self, focus, other):
        male = self._male(other)
        for partner, m in self.unions.get(focus, []):
            if partner == other:
                if m.is_divorced:
                    return "former_husband" if male else "former_wife"
                return "husband" if male else "wife"
        # Spouse of one of focus's blood relatives.
        for partner, _m in self.unions.get(other, []):
            code = self._blood(focus, partner)
            if code in ("son", "daughter"):
                return "son_in_law" if male else "daughter_in_law"
            if code == "grandchild":
                return "grandson_in_law" if male else "granddaughter_in_law"
            if code in ("older_brother", "younger_brother", "brother") and not male:
                return "brothers_wife"
            if code in ("older_sister", "younger_sister", "sister") and male:
                return "sisters_husband"
            if code in ("father", "mother"):
                return "stepfather" if male else "stepmother"
            if code:
                return "relative"
        for partner, _m in self.unions.get(focus, []):
            # Parents of focus's spouse.
            if self.ancestors(partner).get(other) == 1:
                return "father_in_law" if male else "mother_in_law"
            # Children of focus's spouse from another marriage.
            if other in self.children.get(partner, []):
                return "stepson" if male else "stepdaughter"
            if self._blood(partner, other):
                return "relative"
        return None
