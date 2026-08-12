"""Individually hashcat-verified rule functions.

`all.rules` (the golden oracle in `tests/test_hashcat_golden.py`) exercises
42 of hcrulepy's 56 transform functions, but never uses the memory functions
(``M 4 6 Q X``) or the plain rejection functions (``< > _ ! / ( ) = %``) as
actual rule commands (only as literal operands elsewhere).

To close that gap, on 2026-08-12 each of those 13 functions was tested
directly against real hashcat v7.1.2 (``--stdout``, input word ``p@ssW0rd``)
by appending 13 tagged probe rules to a copy of `all.rules` and running
hashcat once. Each probe rule ends in a unique literal marker (``$1``..``$D``)
so its output can't be confused with anything already produced elsewhere in
the 48,000+ line file, and its presence/absence in hashcat's stdout was
checked with an exact-line match.

Result: hashcat's ``-r``-file rule engine (used for `--stdout`) executed 8 of
these 13 as real functions; the other 5 produced no output line and no
warning of any kind. Notably, a *standalone* few-line rule file for the same
probes made hashcat abort entirely with "No valid rules left" instead of
processing the ones it does support — i.e. hashcat's `-r` engine behaves
differently for small rule files than for large ones, so probes like this
must be embedded in (or appended to) a large existing ruleset to get a
meaningful per-rule result.

CONFIRMED supported by hashcat's --stdout -r rule engine:
  M (memorize), 4 (append memory), 6 (prepend memory),
  Q (reject if memory == word), < > _ ! / (5 of the 9 reject functions)

CONFIRMED NOT processed by hashcat's --stdout -r rule engine on this build
(silently produces no candidate, no warning — not merely "unsupported here",
consistent with the earlier explicit "Cannot convert"/"unsupported" warnings
seen for X-combos and the ~?C class rules):
  X (extract from memory), ( ) = % (the remaining 4 reject functions)

hcrulepy still implements the "not processed by hashcat -r" functions per
the wiki's documented semantics (`X`, `(`, `)`, `=`, `%`, and the `~?C` class
rules) — see `tests/test_rules_edit.py`, `tests/test_rules_reject.py`, and
`tests/test_rules_charclass.py` for their wiki-derived unit tests. Those
five plus the `~?C` class rules are the only functions whose correctness
cannot currently be checked against a real hashcat run; everything else
(47 of 56 functions) now has real-hashcat confirmation, either via the
byte-for-byte `all.rules` golden test or the probes here.
"""

from hcrulepy import apply_rule

# (rule, expected output) — each confirmed present, verbatim, in a real
# hashcat v7.1.2 --stdout capture on 2026-08-12.
HASHCAT_CONFIRMED = [
    ("M4$1", "p@ssW0rdp@ssW0rd1"),
    ("M6$2", "p@ssW0rdp@ssW0rd2"),
    ("MlQ$3", "p@ssw0rd3"),
    ("l<9$5", "p@ssw0rd5"),
    ("l>7$6", "p@ssw0rd6"),
    ("l_8$7", "p@ssw0rd7"),
    ("l!z$8", "p@ssw0rd8"),
    ("l/s$9", "p@ssw0rd9"),
]


def test_hashcat_confirmed_probes():
    for rule, expected in HASHCAT_CONFIRMED:
        assert apply_rule("p@ssW0rd", rule) == expected


# The complementary probes that hashcat's -r engine did NOT process (no
# output line, no warning) in the same run. hcrulepy still implements them
# per the wiki; these are NOT claims of hashcat parity, just a record of
# what remains unverified against a real hashcat run, and why.
NOT_PROCESSED_BY_HASHCAT_R_ENGINE = [
    ("MX088$4", "p@ssW0rdp@ssW0rd4"),  # X: extract from memory
    ("l(p$A", "p@ssw0rdA"),  # (: reject unless starts with
    ("l)d$B", "p@ssw0rdB"),  # ): reject unless ends with
    ("l=0p$C", "p@ssw0rdC"),  # =: reject unless char at position
    ("l%1s$D", "p@ssw0rdD"),  # %: reject if count below threshold
]


def test_unverified_probes_still_match_wiki_semantics():
    # These match hcrulepy's own (wiki-derived) semantics; they are NOT
    # confirmed against hashcat, since hashcat's -r engine dropped them.
    for rule, expected in NOT_PROCESSED_BY_HASHCAT_R_ENGINE:
        assert apply_rule("p@ssW0rd", rule) == expected
