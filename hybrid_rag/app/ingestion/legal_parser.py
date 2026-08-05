"""
Structure-aware parser for Uzbek legal codes (lex.uz-style plain text).

WHY THIS MODULE EXISTS
-----------------------
A generic text splitter (e.g. LangChain's `RecursiveCharacterTextSplitter`
run directly on the raw document) would cut chunks at arbitrary character
boundaries, frequently splitting a single legal article across two chunks
or merging the tail of one article with the head of the next. That
directly undermines the spec's citation requirement ("always cite article
numbers") — a chunk that's half of Article 12 and half of Article 13 has
no single correct citation.

This module parses the *actual legal structure* of the source documents —
qism (part) / boʻlim (section) / bob (chapter) / modda (article) — so the
chunker (chunker.py) can split along article boundaries first, and only
fall back to character-based splitting *within* an article that's still
too long. It also strips lex.uz-specific boilerplate (revision-history
footnotes, "see previous edition" links, commentary blocks) that is pure
navigation/administrative noise for a QA system, not legal content.

HOW THE PATTERNS WERE DERIVED
---------------------------------
Every pattern here was validated against all 5 real source files (not
guessed from general knowledge of Uzbek legal formatting), specifically:

- Article markers (`N-modda.`) are 100% consistent across all 5 files
  (2,910 matches total) and ALWAYS anchor a line — confirmed no article
  marker ever appears mid-sentence. Article numbers can look unusual
  (e.g. "41929-modda" in fuqorolik_protsessual.txt) because inserted
  articles use a superscript suffix (e.g. article "419²⁹") that collapses
  to a plain digit string when the superscript is flattened during
  extraction — we store the number verbatim rather than guessing where
  the "real" article number ends and the insertion suffix begins, since
  that boundary can't be recovered reliably from the flattened text.
- Chapter markers (`bob`) appear in two formats across the corpus:
  `"1-BOB."` (title on the following line) and `"I bob. Title"` (title
  inline) — both are handled.
- Section markers (`BOʻLIM`) similarly appear both with and without an
  inline title.
- Revision-history footnotes: EVERY standalone parenthetical line (a full
  line that starts with "(" and ends with ")") across all 5 files (2,556
  of them) is an amendment/citation footnote — confirmed by checking that
  none are shorter than 70 characters, i.e. there are zero short,
  substantive parenthetical asides that a blanket removal rule would
  wrongly delete. This is why noise-stripping uses one general structural
  rule instead of a fragile keyword allowlist (an earlier attempt using a
  "contains 'tahririda' or the database name" keyword filter missed ~14%
  of footnotes because the citation-source phrasing changed across
  decades of amendments, e.g. "Qonunchilik maʼlumotlari milliy bazasi" vs.
  older "Oliy Majlis Axborotnomasi").
- Commentary blocks ("LexUZ sharhi" followed by a "Qarang: ..." reference
  line) are removed as a pair; the follow-up line's exact wording varies
  ("Qarang:", "Qoʻshimcha maʼlumot uchun qarang:", even typos like
  "qarng:"), so rather than matching its content we unconditionally strip
  whatever single line immediately follows a "LexUZ sharhi" marker —
  verified this is always exactly one line, never a multi-line block.

HOW IT WORKS INTERNALLY
------------------------
1. `strip_legal_noise()` removes the three boilerplate patterns above with
   three regex passes over the full text (each O(n)), then re-collapses
   any blank lines the removals left behind.
2. `parse_legal_structure()` walks the remaining text one line at a time
   (a single-pass state machine, O(n) in total line count), tracking two
   breadcrumb slots — `major_section` (the most recent qism/boʻlim/kichik
   boʻlim heading) and `chapter` (the most recent bob heading) — and
   accumulating lines into the current article's body until the next
   `N-modda.` marker starts a new one. Each finished article becomes one
   `ParsedArticle`.

WHY A HAND-WRITTEN STATE MACHINE INSTEAD OF ONE BIG REGEX
--------------------------------------------------------------
A single regex could match the marker patterns, but recovering the body
text *between* markers, handling the "title is on the next line" case,
and maintaining the section/chapter breadcrumb as you go are inherently
stateful, sequential operations — natural to express as a loop over lines
and awkward (unreadable) to express as one regex with lookaheads. The
Zen-of-Python instinct "flat is better than nested, but explicit is
better than implicit" applies directly here.

TIME / MEMORY COMPLEXITY
-------------------------
O(n) time and O(n) memory in document length for both functions — each
line is visited a constant number of times, and the output (list of
`ParsedArticle`, each holding a slice of the original text) is bounded by
the input size.

ADVANTAGES
-----------
- Chunks align with real legal units (articles), so citations are always
  correct and complete — a chunk never spans two articles.
- Noise removal materially improves signal-to-noise ratio for both
  embeddings and BM25: roughly 15-20% of raw character count in these
  documents is revision-history/commentary boilerplate (see the ~2,556
  stripped footnote lines), none of which helps answer a legal question.

DISADVANTAGES
--------------
- Patterns are tuned to this corpus's specific formatting conventions
  (lex.uz-style Uzbek legal text). A differently-formatted legal source
  (e.g. a PDF scan with different heading conventions) may not be
  detected as structured at all — see `chunker.py`'s fallback to
  plain character-based splitting when zero articles are found.
- The section/chapter breadcrumb is a best-effort two-level summary, not
  a full qism > boʻlim > kichik boʻlim > bob hierarchy — sufficient for
  citation/debug display, not a substitute for a real legal taxonomy.

ALTERNATIVES CONSIDERED
-------------------------
- A dedicated legal-document parsing library: none exist with real Uzbek
  support; would still need corpus-specific tuning.
- An LLM-based structure extractor: far more expensive (one inference per
  document) and non-deterministic, for a problem regular expressions
  solve exactly and instantly given how consistent the source formatting
  turned out to be.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from app.ingestion.cleaning import collapse_whitespace
from app.utils.logger import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------
# Noise patterns (see module docstring for how each was empirically derived)
# --------------------------------------------------------------------------

# "See previous edition" — a lex.uz navigation link, never legal content.
_OLDINGI_TAHRIRGA_PATTERN = re.compile(r"(?m)^Oldingi tahrirga qarang\.[ \t]*\n?")

# Any full standalone line wrapped in parentheses: 100% amendment/citation
# footnotes in this corpus (verified: none under 70 chars, i.e. no short
# substantive parenthetical asides exist as their own line).
_STANDALONE_PAREN_LINE_PATTERN = re.compile(r"(?m)^\(.*\)[ \t]*\n?")

# "LexUZ sharhi" (commentary marker) + the single reference line that
# always immediately follows it.
_LEXUZ_SHARHI_BLOCK_PATTERN = re.compile(r"(?m)^[ \t]*LexUZ sharhi[ \t]*\n.*\n?")

# --------------------------------------------------------------------------
# Structural markers
# --------------------------------------------------------------------------

# "1-modda. Title" / "41929-modda. Title" (article) — the primary split
# point. Article numbers are kept verbatim (see module docstring).
MODDA_PATTERN = re.compile(r"^(\d[\d\-]*)-modda\.\s*(.*)$")

# "1-BOB." (title on next line) or "I bob. Title" (title inline).
BOB_PATTERN = re.compile(r"^(\d+|[IVXLCDM]+)[-\s]*[Bb][Oo][Bb]\.?[ \t]*(.*)$")

# "I BOʻLIM" / "I BOʻLIM. Title" / "BIRINCHI BOʻLIM".
_ORDINAL_WORDS = (
    "Birinchi|Ikkinchi|Uchinchi|Toʻrtinchi|Beshinchi|Oltinchi|" "Yettinchi|Sakkizinchi|Toʻqqizinchi|Oʻninchi"
)
BOLIM_PATTERN = re.compile(rf"^([IVXLCDM]+|{_ORDINAL_WORDS})\s+BO[ʻ]LIM\.?[ \t]*(.*)$", re.IGNORECASE)

# "1-Kichik boʻlim" (sub-section).
KICHIK_BOLIM_PATTERN = re.compile(r"^(\d+)-Kichik bo[ʻ]lim\.?[ \t]*(.*)$", re.IGNORECASE)

# "Birinchi qism" / "UMUMIY QISM" / "MAXSUS QISM" — short standalone lines
# only (length guard prevents matching a body sentence that happens to end
# in the word "qism").
QISM_PATTERN = re.compile(rf"^({_ORDINAL_WORDS}|UMUMIY|MAXSUS)\s+[Qq][Ii][Ss][Mm]\.?$")

# Maximum length for a line to be considered as an inline "title" that
# follows an empty-inline-title structural marker (e.g. the line after a
# bare "1-BOB." line). Real titles are short; this guards against
# accidentally swallowing the start of an unrelated body paragraph.
_MAX_INLINE_TITLE_LENGTH = 120


def strip_legal_noise(text: str) -> str:
    """Remove lex.uz boilerplate: nav links, revision footnotes, commentary.

    Must run before `parse_legal_structure()` — noise lines can appear
    *inside* an article's body (between two of its sentences), not just
    between articles, so structure parsing has to see the already-cleaned
    text to reconstruct a contiguous article body.
    """
    result = _OLDINGI_TAHRIRGA_PATTERN.sub("", text)
    result = _STANDALONE_PAREN_LINE_PATTERN.sub("", result)
    result = _LEXUZ_SHARHI_BLOCK_PATTERN.sub("", result)
    return collapse_whitespace(result)


class ParsedArticle(BaseModel):
    """One legal article (modda), with its section/chapter breadcrumb.

    `text` includes the "N-modda. Title" header line itself, so the chunk
    text is self-identifying even without relying solely on metadata —
    useful both for the embedding model's context and for a human reading
    a retrieved chunk directly.

    `start_offset` is this article's character position within the text
    passed to `parse_legal_structure()` — used by the chunker to look up
    which source page the article started on for paginated formats (PDF).
    """

    article_number: str | None
    section: str | None
    text: str
    start_offset: int = 0


def _section_breadcrumb(major_section: str | None, chapter: str | None) -> str | None:
    parts = [p for p in (major_section, chapter) if p]
    return " > ".join(parts) if parts else None


def _looks_like_title_continuation(line: str) -> bool:
    """Is `line` short and structurally plain enough to be a heading's
    inline title, rather than the start of unrelated body content?"""
    if not line or len(line) > _MAX_INLINE_TITLE_LENGTH:
        return False
    if MODDA_PATTERN.match(line) or BOB_PATTERN.match(line) or BOLIM_PATTERN.match(line):
        return False
    return True


def parse_legal_structure(text: str) -> list[ParsedArticle]:
    """Split noise-stripped legal text into per-article chunks with breadcrumbs.

    Returns an empty list if no `N-modda.` markers are found at all — the
    caller (chunker.py) treats that as "not a structured legal document"
    and falls back to plain character-based splitting.
    """
    lines = text.split("\n")
    n = len(lines)

    # Cumulative character offset of the start of each line within `text`.
    # Valid because `text.split("\n")` and `"\n".join(lines)` are exact
    # inverses, so summing `len(line) + 1` reconstructs true offsets.
    line_offsets = [0] * (n + 1)
    for idx in range(n):
        line_offsets[idx + 1] = line_offsets[idx] + len(lines[idx]) + 1

    articles: list[ParsedArticle] = []
    major_section: str | None = None
    chapter: str | None = None

    current_number: str | None = None
    current_section: str | None = None
    current_lines: list[str] = []
    current_start_offset = 0

    def flush() -> None:
        if current_lines:
            body = "\n".join(current_lines).strip()
            if body:
                articles.append(
                    ParsedArticle(
                        article_number=current_number,
                        section=current_section,
                        text=body,
                        start_offset=current_start_offset,
                    )
                )

    i = 0
    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        m_modda = MODDA_PATTERN.match(line)
        if m_modda:
            flush()
            current_number = m_modda.group(1)
            current_section = _section_breadcrumb(major_section, chapter)
            current_lines = [line]
            current_start_offset = line_offsets[i]
            i += 1
            continue

        m_bob = BOB_PATTERN.match(line)
        if m_bob:
            num, inline_title = m_bob.group(1), m_bob.group(2).strip()
            consumed = 1
            if not inline_title and i + 1 < n and _looks_like_title_continuation(lines[i + 1].strip()):
                inline_title = lines[i + 1].strip()
                consumed = 2
            chapter = f"{num}-bob. {inline_title}".strip() if inline_title else f"{num}-bob"
            i += consumed
            continue

        m_bolim = BOLIM_PATTERN.match(line)
        if m_bolim:
            num, inline_title = m_bolim.group(1), m_bolim.group(2).strip()
            consumed = 1
            if not inline_title and i + 1 < n and _looks_like_title_continuation(lines[i + 1].strip()):
                inline_title = lines[i + 1].strip()
                consumed = 2
            major_section = f"{num} boʻlim. {inline_title}".strip() if inline_title else f"{num} boʻlim"
            i += consumed
            continue

        m_kichik = KICHIK_BOLIM_PATTERN.match(line)
        if m_kichik:
            num, inline_title = m_kichik.group(1), m_kichik.group(2).strip()
            consumed = 1
            if not inline_title and i + 1 < n and _looks_like_title_continuation(lines[i + 1].strip()):
                inline_title = lines[i + 1].strip()
                consumed = 2
            major_section = (
                f"{num}-kichik boʻlim. {inline_title}".strip() if inline_title else f"{num}-kichik boʻlim"
            )
            i += consumed
            continue

        if QISM_PATTERN.match(line):
            major_section = line
            chapter = None  # a new qism resets the chapter breadcrumb
            i += 1
            continue

        # Plain content line: part of the current article's body if we're
        # inside one, otherwise it's preamble before the first article
        # (title-page-style headers) and is discarded.
        if current_number is not None or current_lines:
            current_lines.append(line)
        i += 1

    flush()

    logger.info(
        "Parsed legal structure: %d article(s) found (0 means this document "
        "will fall back to plain character-based chunking)",
        len(articles),
    )
    return articles


def deduplicate_articles(articles: list[ParsedArticle]) -> list[ParsedArticle]:
    """Drop articles that are exact repeats of an already-seen one.

    WHY THIS EXISTS
    -----------------
    Inspecting the actual corpus turned up a genuine data-quality issue,
    not a parsing bug: `fuqorolik.txt` (Civil Code) and `jinoyat.txt`
    (Criminal Code) each contain large stretches of content duplicated
    verbatim within the same file (confirmed by locating a second
    "1-modda." occurrence partway through `fuqorolik.txt` at which point
    the document restarts from its own beginning). Left unhandled, this
    would silently double-count and double-index a large fraction of the
    corpus, degrading both retrieval relevance (duplicate hits crowding
    out other results) and index size.

    The dedup key is `(article_number, exact text)`, not article number
    alone. This matters because the corpus ALSO contains genuine article-
    number collisions: inserted articles use a superscript suffix in the
    source (e.g. article "26¹") that flattens to a plain digit string
    ("261") when extracted as plain text, colliding with the real,
    unrelated article 261. Deduping on number alone would wrongly discard
    one of two genuinely different articles that happen to share a
    flattened number; requiring the text to match exactly as well ensures
    only true duplicates (same number AND identical content) are removed.

    Order is preserved (first occurrence wins) via a `seen` set checked
    while building the result list — O(n) time, O(n) memory for the set
    of seen keys.
    """
    seen: set[tuple[str | None, str]] = set()
    deduped: list[ParsedArticle] = []
    dropped = 0

    for article in articles:
        key = (article.article_number, article.text)
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        deduped.append(article)

    if dropped:
        logger.warning(
            "Dropped %d duplicate article(s) (identical article number + text) " "out of %d parsed",
            dropped,
            len(articles),
        )
    return deduped
