"""
Shared tokenizer for BM25 indexing and querying.

WHY THIS MODULE EXISTS
-----------------------
BM25 (Milestone 7) works by exact token matching — it counts how often
each token in a query appears in each document. If the tokenizer used
when *building* the index differs even slightly from the one used when
*querying* it (different lowercasing, different word-boundary rules), a
term that should match silently doesn't, and BM25 degrades without any
error. Putting tokenization in one shared function that both the index
build path and the query path import guarantees they can never drift
apart.

WHY \\w+ WORKS CORRECTLY FOR UZBEK LATIN SCRIPT
----------------------------------------------------
Uzbek Latin script uses two "modifier letter" characters that are not
plain Latin letters: ⟨ʻ⟩ (U+02BB, the oʻ/gʻ digraph marker) and ⟨ʼ⟩
(U+02BC, the glottal-stop marker, e.g. "maʼno"). Empirically verified
(see tests) that Python's `\\w` (in Unicode mode, the default for `str`
patterns) matches both of these correctly, because `\\w` matches any
Unicode "letter" category — which includes `Lm` (Letter, modifier), not
just `Ll`/`Lu` (lowercase/uppercase letters). Concretely,
`re.findall(r"\\w+", "Oʻzbekiston")` returns `["Oʻzbekiston"]` as ONE
token, not incorrectly split into `["O", "zbekiston"]` — this is the
single most important correctness property this tokenizer needs, since
splitting the digraph marker off would silently break matching on very
common words like "oʻzbek", "huquqi" (via "gʻ" elsewhere), etc.

WHAT THIS TOKENIZER DELIBERATELY DOES NOT DO
--------------------------------------------------
- **No stopword removal**: no well-established, freely available Uzbek
  stopword list exists (unlike English/Russian, which most NLP libraries
  ship built in). BM25's own IDF term-weighting already naturally
  down-weights very common words (they appear in most documents, so their
  IDF approaches zero) — a partial, automatic substitute for explicit
  stopword removal, though not a full one.
- **No stemming/lemmatization**: Uzbek is agglutinative (like Turkish or
  Finnish) — a single root combines with many suffixes ("mehnat",
  "mehnatga", "mehnatning", "mehnatlar" are all morphologically related
  but are 4 different tokens to this tokenizer). No mature, freely
  available Uzbek stemmer exists (unlike the Snowball stemmers available
  for many other languages). This is a real, known limitation: a query
  using "mehnatga" will not BM25-match a document that only contains
  "mehnat". Dense retrieval (FAISS, Milestone 6) partially compensates
  for this, since embedding models generalize across morphological
  variants far better than exact token matching does — one of the
  concrete reasons this project uses *hybrid* search rather than BM25
  alone.

ALTERNATIVES CONSIDERED
-------------------------
- A proper morphological analyzer for Uzbek: would meaningfully improve
  BM25 recall, but no mature open-source library exists; building one is
  a research-scale project on its own, well beyond this project's scope.
- `nltk`/`spaCy` tokenizers: general-purpose multilingual tokenizers don't
  have Uzbek-specific rules either, and would add a dependency for
  behavior a two-line regex already handles correctly for this script.
"""

from __future__ import annotations

import re

_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Lowercase and split `text` into word tokens.

    Used identically at BM25 index-build time and query time — see
    module docstring for why that consistency matters.
    """
    return _TOKEN_PATTERN.findall(text.lower())
