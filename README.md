# hcrulepy

[![CI](https://github.com/miichoow/hcrulepy/actions/workflows/ci.yml/badge.svg)](https://github.com/miichoow/hcrulepy/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/miichoow/hcrulepy/branch/main/graph/badge.svg)](https://codecov.io/gh/miichoow/hcrulepy)
[![PyPI](https://img.shields.io/pypi/v/hcrulepy.svg)](https://pypi.org/project/hcrulepy/)
[![Python versions](https://img.shields.io/pypi/pyversions/hcrulepy.svg)](https://pypi.org/project/hcrulepy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

hcrulepy applies hashcat's rule-based mangling rules to words, in pure
Python. Same rule syntax as hashcat, same output, no compiled dependencies.
Use it as a library or from the command line.

## Installation

```bash
pip install hcrulepy
```

## Library usage

The main entry point is `RuleEngine`. It parses one or more rule files (or
rule lines) once, then applies them to as many words as you like.

```python
from hcrulepy import RuleEngine

engine = RuleEngine.from_files(["best64.rule"])
# one file is fine too:
engine = RuleEngine.from_file("best64.rule")
# or pass rule lines directly:
engine = RuleEngine(["u", "$1", ":"])

for candidate in engine.apply("password"):
    print(candidate)

# word-major: for each word, yield every candidate it produces
for candidate in engine.apply_many(["password", "letmein"]):
    print(candidate)
```

Words can be `str` or `bytes`. A `str` is encoded as latin-1 on the way in,
and candidates always come back as `str`, so passing bytes is a way to keep
words that aren't valid text from tripping over an encode step.

For one rule against one word, `apply_rule` is a shortcut:

```python
from hcrulepy import apply_rule

apply_rule("password", "u")     # -> "PASSWORD"
apply_rule("password", "$1")    # -> "password1"
apply_rule("password", ")z")    # -> None (rejected)
```

The package also exports `parse_rule` and `apply_ops` if you want to parse a
rule line once and reuse the resulting op list yourself.

A rule that can't be parsed (unknown command, bad arguments) raises
`hcrulepy.errors.InvalidRule`. The message carries the file name where one
applies, the line number, and the offending line, so a bad rule buried in a
large file is easy to find. A rule that rejects a candidate, like a length
check that fails, produces no output for that word: `apply` skips it, and
`apply_rule` returns `None`.

If you would rather keep going past bad lines than stop at the first one,
pass `skip_invalid=True` to the constructor, to `from_file`, or to
`from_files`. Each rejected line gets a warning on stderr and is dropped,
and the rest of the file still loads.

To validate rule files without building an engine at all, use
`RuleEngine.check_files`. It returns one `(path, line_number, line_text,
message)` tuple per line that fails to parse, and an empty list when
everything is clean:

```python
from hcrulepy import RuleEngine

for path, lineno, line, message in RuleEngine.check_files(["best64.rule"]):
    print(f"{path}:{lineno}: {message}")
```

## CLI usage

Installing the package adds a `hcrulepy` console script (you can also run
`python -m hcrulepy`). It mirrors `hashcat --stdout -r rules.rule
wordlist.txt`. Output is word-major, meaning all candidates for one word
come out before the next word starts, one candidate per line, written as
latin-1 bytes to stdout. Rejected candidates are left out.

`-r`/`--rules` is repeatable and required. Rule files are concatenated in
the order you pass them.

You can supply input words three ways:

```bash
# 1. A single word via --word
hcrulepy -r best64.rule --word password

# 2. A wordlist file (positional argument)
hcrulepy -r best64.rule wordlist.txt

# 3. Stdin, either explicitly with '-' or by omitting the positional argument
cat wordlist.txt | hcrulepy -r best64.rule -
cat wordlist.txt | hcrulepy -r best64.rule
```

A missing rule file, or a rule that fails to parse, prints a message to
stderr and exits with status 2.

### Checking rule files

`--check` parses the rule files and stops there, without reading a wordlist
or producing candidates. Every line that fails to parse is reported on
stderr with its file, its line number, and the text of the line itself, and
the run ends with a count of how many were bad. A clean set of files prints
`hcrulepy: OK` and exits 0, a set with bad lines exits 1, and a rule file
that can't be read at all exits 2.

```bash
hcrulepy -r best64.rule -r custom.rule --check
```

### Skipping bad rule lines

By default one unparseable line aborts the whole run. With `-k` (or
`--skip-invalid`) each bad line is instead reported as a warning on stderr
and left out, and the remaining rules are applied as usual. That is handy
for large rule collections gathered from various places, where a handful of
lines use syntax hcrulepy doesn't accept and you would rather have the
output from everything else.

```bash
hcrulepy -r huge-collection.rule -k wordlist.txt
```

## Supported rules

hcrulepy implements hashcat's rule syntax as documented on the
[hashcat wiki](https://hashcat.net/wiki/doku.php?id=rule_based_attack): the
standard single-character commands, positional and character arguments, and
the `~`-prefixed character-class commands.

## Limitations

### The `p`-position register is not implemented

Rules that use `p` as a *position* argument (for example `Tp`, which reuses
the value most recently stored by a position-recording command) are not
supported, and parsing one raises `InvalidRule`. Other uses of memory, like
the `M`/`Q` rules and the `~`-prefixed memory-relative commands, work fine.

### Hashcat parity: what's actually been confirmed

Two tests check byte-for-byte parity against real hashcat.

`tests/test_hashcat_golden.py` replays a committed hashcat capture
(`tests/data/hashcat_v6.2.6_all.rules`, captured on hashcat v6.2.6 and
byte-for-byte identical again on v7.1.2) and checks hcrulepy against it: 42
of 56 transform functions, about 48,457 candidates, zero mismatches. It
runs on its own, with no hashcat binary needed.

`tests/test_hashcat_diff.py` runs the same comparison live against whatever
hashcat binary you point it at (`HASHCAT_BIN`, or `hashcat` on `PATH`; the
`~?C` class rules need hashcat 7.0.0 or newer). It skips if it can't find
one.

The other 14 functions (`M 4 6 Q X` and `< > _ ! / ( ) = %`) never appear
as actual commands in that reference file, only as literal operands, so the
golden test doesn't reach them. Each was tested directly against hashcat
v7.1.2 on 2026-08-12 instead. `tests/test_hashcat_verified_functions.py` has
the method and the results:

- hashcat's `--stdout -r` engine ran and matched: `M` `4` `6` `Q` (all the
  memory functions) and `<` `>` `_` `!` `/` (five of the nine reject
  functions).
- hashcat's `--stdout -r` engine did not process, on that build: `X`
  (extract-from-memory) and `(` `)` `=` `%` (the other four reject
  functions). They produced no output and no warning. That matches the
  "Cannot convert rule for use on OpenCL device" and "unsupported rule"
  warnings hashcat prints for memory-extract combos and the `~?C` class
  rules. hashcat's `-r` rule engine handles only a subset of the documented
  functions, whatever OpenCL or CUDA device is behind it.

So 47 of 56 functions are confirmed against real hashcat: 42 from the golden
test, plus 5 from the probes. The remaining 9 (`X`, `(`, `)`, `=`, `%`, and
the `~?C` class rules) are implemented to the wiki's documented behavior and
covered by unit tests, but not confirmed against real hashcat, because
hashcat's own rule engine won't run them through `--stdout -r`. There is no
known way to get a real-hashcat oracle for them.

One thing to know if you want to reproduce this. A small rule file holding
only these functions makes hashcat bail out with "No valid rules left" and
print nothing, even for rules it supports on their own. hashcat's `-r`
engine treats small rule files differently from large ones. The working
functions above only showed up once I appended marker-tagged probe rules to
the end of the large `all.rules` file. The header of
`tests/data/coverage_supplement.rule` explains the technique.

### Out-of-range positions aren't reconciled yet

For a few position-based ops, notably Extract range (`x`) and Omit range
(`O`), I haven't settled what hashcat does when a position or length runs
past the end of the word: clamp to a shorter range, no-op, or drop the
candidate. On very short words hcrulepy's results may not match hashcat. If
that matters to you, run `tests/test_hashcat_diff.py` against a real hashcat
binary to pin the behavior down before relying on it.
