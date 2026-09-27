"""Central vocabulary for Uzbek kinship terms.

Every relationship word used anywhere in the product (pages, tree, PDF) comes
from here, so the Latin and Cyrillic catalogues hold one agreed form of each.

Uzbek kinship is more specific than English: siblings are named by age
(aka / uka, opa / singil), aunts and uncles by side of the family
(amaki, amma — father's side; togʻa, xola — mother's side), and in-laws by the
linking person (kelin, kuyov, yanga, pochcha, qaynota, qaynona). The English
msgids below say which exact relationship each term means; the context
"kinship" keeps them apart from other uses of the same English words.
"""
from django.utils.translation import pgettext_lazy

# A term for a person as seen from the focus person ("this is my …").
KIN = {
    "self": pgettext_lazy("kinship", "You"),
    "father": pgettext_lazy("kinship", "Father"),
    "mother": pgettext_lazy("kinship", "Mother"),
    "son": pgettext_lazy("kinship", "Son"),
    "daughter": pgettext_lazy("kinship", "Daughter"),
    "grandfather": pgettext_lazy("kinship", "Grandfather"),
    "grandmother": pgettext_lazy("kinship", "Grandmother"),
    "great_grandfather": pgettext_lazy("kinship", "Great-grandfather"),
    "great_grandmother": pgettext_lazy("kinship", "Great-grandmother"),
    "forefather": pgettext_lazy("kinship", "Distant male ancestor"),
    "foremother": pgettext_lazy("kinship", "Distant female ancestor"),
    "grandchild": pgettext_lazy("kinship", "Grandchild"),
    "great_grandchild": pgettext_lazy("kinship", "Great-grandchild"),
    "great_great_grandchild": pgettext_lazy("kinship", "Great-great-grandchild"),
    "descendant": pgettext_lazy("kinship", "Descendant"),
    "older_brother": pgettext_lazy("kinship", "Older brother"),
    "younger_brother": pgettext_lazy("kinship", "Younger brother"),
    "brother": pgettext_lazy("kinship", "Brother (age unknown)"),
    "older_sister": pgettext_lazy("kinship", "Older sister"),
    "younger_sister": pgettext_lazy("kinship", "Younger sister"),
    "sister": pgettext_lazy("kinship", "Sister (age unknown)"),
    "paternal_uncle": pgettext_lazy("kinship", "Father's brother"),
    "paternal_aunt": pgettext_lazy("kinship", "Father's sister"),
    "maternal_uncle": pgettext_lazy("kinship", "Mother's brother"),
    "maternal_aunt": pgettext_lazy("kinship", "Mother's sister"),
    "paternal_uncle_child": pgettext_lazy("kinship", "Child of father's brother"),
    "paternal_aunt_child": pgettext_lazy("kinship", "Child of father's sister"),
    "maternal_uncle_child": pgettext_lazy("kinship", "Child of mother's brother"),
    "maternal_aunt_child": pgettext_lazy("kinship", "Child of mother's sister"),
    "nephew_niece": pgettext_lazy("kinship", "Nephew or niece"),
    "husband": pgettext_lazy("kinship", "Husband"),
    "wife": pgettext_lazy("kinship", "Wife"),
    "former_husband": pgettext_lazy("kinship", "Former husband"),
    "former_wife": pgettext_lazy("kinship", "Former wife"),
    "son_in_law": pgettext_lazy("kinship", "Son-in-law"),
    "daughter_in_law": pgettext_lazy("kinship", "Daughter-in-law"),
    "grandson_in_law": pgettext_lazy("kinship", "Granddaughter's husband"),
    "granddaughter_in_law": pgettext_lazy("kinship", "Grandson's wife"),
    "father_in_law": pgettext_lazy("kinship", "Father-in-law"),
    "mother_in_law": pgettext_lazy("kinship", "Mother-in-law"),
    "brothers_wife": pgettext_lazy("kinship", "Brother's wife"),
    "sisters_husband": pgettext_lazy("kinship", "Sister's husband"),
    "stepfather": pgettext_lazy("kinship", "Stepfather"),
    "stepmother": pgettext_lazy("kinship", "Stepmother"),
    "stepson": pgettext_lazy("kinship", "Stepson"),
    "stepdaughter": pgettext_lazy("kinship", "Stepdaughter"),
    "relative": pgettext_lazy("kinship", "Relative"),
}

# Generic nouns used in headings, forms and summaries.
TERMS = {
    "child": pgettext_lazy("kinship", "Child"),
    "spouse": pgettext_lazy("kinship", "Spouse"),
    "friend": pgettext_lazy("kinship", "Friend"),
    "family_tree": pgettext_lazy("kinship", "Family tree"),
    "family_member": pgettext_lazy("kinship", "Family member"),
}

# Section headings on a person's page: "his/her father" → "Otasi".
SECTION = {
    "father": pgettext_lazy("person section", "Father"),
    "mother": pgettext_lazy("person section", "Mother"),
    "spouses": pgettext_lazy("person section", "Spouse"),
    "children": pgettext_lazy("person section", "Children"),
    "siblings": pgettext_lazy("person section", "Brothers and sisters"),
}

# Relations that can be chosen when adding a relative to someone.
ADD_RELATION = {
    "father": pgettext_lazy("add relation", "Father"),
    "mother": pgettext_lazy("add relation", "Mother"),
    "spouse": pgettext_lazy("add relation", "Spouse"),
    "child": pgettext_lazy("add relation", "Child"),
    "sibling": pgettext_lazy("add relation", "Brother or sister"),
}


def kin(code):
    return str(KIN.get(code, KIN["relative"]))
