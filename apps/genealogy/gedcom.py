"""GEDCOM 5.5.1 export — the standard exchange format of genealogy programs
(MyHeritage, Ancestry, FamilySearch, Gramps …). Names and places are written
exactly as stored, in UTF-8."""
import datetime

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def gedcom_date(year, month=None, day=None):
    if not year:
        return ""
    parts = []
    if month and day:
        parts.append(str(day))
    if month:
        parts.append(MONTHS[month - 1])
    parts.append(str(year))
    return " ".join(parts)


def _text(level, tag, value):
    """A line, with long or multi-line text split into CONT/CONC lines."""
    lines = []
    for i, chunk in enumerate(str(value).splitlines() or [""]):
        pieces = [chunk[j:j + 200] for j in range(0, len(chunk), 200)] or [""]
        first_tag = tag if i == 0 else "CONT"
        first_level = level if i == 0 else level + 1
        lines.append(f"{first_level} {first_tag} {pieces[0]}".rstrip())
        lines += [f"{level + 1} CONC {p}" for p in pieces[1:]]
    return lines


def export(archive, owner_name=""):
    people = archive.people
    fams = {}  # (husband, wife) -> family record
    for m in archive.marriages:
        fams[(m.husband_id, m.wife_id)] = {"husb": m.husband_id, "wife": m.wife_id, "marriage": m, "kids": []}
    for p in people.values():
        if p.father_id or p.mother_id:
            key = (p.father_id if p.father_id in people else None, p.mother_id if p.mother_id in people else None)
            fams.setdefault(key, {"husb": key[0], "wife": key[1], "marriage": None, "kids": []})["kids"].append(p.pk)
    fam_ids = {key: f"@F{i}@" for i, key in enumerate(fams, start=1)}

    out = ["0 HEAD", "1 SOUR SHAJARA", "2 NAME Shajara", "1 GEDC", "2 VERS 5.5.1", "2 FORM LINEAGE-LINKED",
           "1 CHAR UTF-8", f"1 DATE {gedcom_date(*_today())}"]
    if owner_name:
        out += ["1 SUBM @U1@", "0 @U1@ SUBM", f"1 NAME {owner_name}"]
    for p in sorted(people.values(), key=lambda x: x.pk):
        out.append(f"0 @I{p.pk}@ INDI")
        out.append(f"1 NAME {p.first_name} /{p.last_name}/".rstrip())
        out.append(f"2 GIVN {p.first_name}")
        if p.last_name:
            out.append(f"2 SURN {p.last_name}")
        out.append(f"1 SEX {'M' if p.gender == 'male' else 'F'}")
        if p.birth_year or p.birth_place:
            out.append("1 BIRT")
            if p.birth_year:
                out.append(f"2 DATE {gedcom_date(p.birth_year, p.birth_month, p.birth_day)}")
            if p.birth_place:
                out.append(f"2 PLAC {p.birth_place}")
        if p.is_deceased:
            out.append("1 DEAT Y" if not (p.death_year or p.death_place) else "1 DEAT")
            if p.death_year:
                out.append(f"2 DATE {gedcom_date(p.death_year, p.death_month, p.death_day)}")
            if p.death_place:
                out.append(f"2 PLAC {p.death_place}")
        if p.burial_place:
            out += ["1 BURI", f"2 PLAC {p.burial_place}"]
        if p.occupation:
            out.append(f"1 OCCU {p.occupation}")
        if p.education:
            out.append(f"1 EDUC {p.education}")
        for note in (p.biography, p.life_story):
            if note:
                out += _text(1, "NOTE", note)
        for key, fid in fam_ids.items():
            if p.pk in fams[key]["kids"]:
                out.append(f"1 FAMC {fid}")
            if p.pk in (fams[key]["husb"], fams[key]["wife"]):
                out.append(f"1 FAMS {fid}")
    for key, fid in fam_ids.items():
        fam = fams[key]
        out.append(f"0 {fid} FAM")
        if fam["husb"]:
            out.append(f"1 HUSB @I{fam['husb']}@")
        if fam["wife"]:
            out.append(f"1 WIFE @I{fam['wife']}@")
        m = fam["marriage"]
        if m:
            out.append("1 MARR" + ("" if m.year else " Y"))
            if m.year:
                out.append(f"2 DATE {gedcom_date(m.year, m.month, m.day)}")
            if m.is_divorced:
                out.append("1 DIV Y")
        for kid in sorted(fam["kids"], key=lambda k: (people[k].birth_key or (9999,), k)):
            out.append(f"1 CHIL @I{kid}@")
    out.append("0 TRLR")
    return "\r\n".join(out) + "\r\n"


def _today():
    d = datetime.date.today()
    return d.year, d.month, d.day
