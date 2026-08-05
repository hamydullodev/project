"""
Prompt construction: turning compressed context + a question into LLM messages.

WHY THIS MODULE EXISTS
-----------------------
Every prior milestone in the question-answering pipeline produces
structured data (a query string, a list of `RerankedResult` chunks with
metadata). An LLM consumes text. This module is the boundary between the
two: it formats the compressed, reranked chunks into the "MANBALAR"
(sources) block the system prompt (`templates.py`) refers to, and
assembles the final chat messages ready to send to Ollama (Milestone 13).

WHY MESSAGES (system + user), NOT ONE FLAT STRING
--------------------------------------------------------
Ollama's chat API (and essentially every modern local instruction-tuned
model — Llama, Qwen, Mistral, Gemma, DeepSeek, all named in the spec)
expects a list of role-tagged messages, not a single blob of text. Each
model's own chat template (baked into its tokenizer config) wraps
`system`/`user`/`assistant` messages with the specific special tokens
that model was fine-tuned to expect — sending a hand-assembled flat
string instead would bypass that template and produce measurably worse
instruction-following, since the model wouldn't recognize where
instructions end and content begins. Producing `[{"role": "system", ...},
{"role": "user", ...}]` lets Ollama apply whichever model's own template
correctly, keeping this project's prompt logic independent of which
specific model is configured via `LLM_MODEL`.

WHY EACH SOURCE IS NUMBERED AND EXPLICITLY LABELED
--------------------------------------------------------
Giving each chunk a "--- Manba N ---" (Source N) header, followed by its
law name, article number, and section (when known), gives the model a
concrete anchor to both internally reason about ("Manba 2 covers
termination grounds...") and externally cite by name in its answer
(instructed in the system prompt to always name the actual law and
article, not just "Manba 2" — the source numbering is a scaffold for the
model's own reasoning, not the citation format it should ultimately
output).

WHY MISSING METADATA FIELDS ARE OMITTED, NOT SHOWN AS "None"
--------------------------------------------------------------------
A chunk from the plain-text fallback chunking path (Milestone 4, for
documents with no detected legal-article structure) has no
`article_number` or `section`; a chunk from a single-page TXT/DOCX/HTML
source has no `page_number` (Milestone 4's `PageMapper`). Printing
"Modda: None" or "Sahifa: None" into the prompt would be actively
misleading — the model might interpret "None" as itself being a piece of
information to relay, or a real value. `_format_source` builds each
source's header line-by-line, including only the fields that are
actually populated for that specific chunk.

TIME / MEMORY COMPLEXITY
-------------------------
O(k) in the number of chunks passed in (`RERANK_TOP_K` after context
compression, typically single digits) — string formatting and
concatenation, no algorithmic work. Negligible relative to every other
stage of the pipeline.

ADVANTAGES
-----------
- Model-agnostic: swapping `LLM_MODEL` in `.env` (the spec's explicit
  requirement) needs no prompt code changes, since Ollama's chat API
  handles the model-specific templating.
- Citation grounding is structural, not just instructed: because each
  source's law name and article number are placed directly next to its
  text in the prompt, the model has the correct citation readily
  available right where it needs it, rather than having to recall it
  from elsewhere in a long context.

DISADVANTAGES
--------------
- No conversation history is threaded into the prompt — this builds a
  single-turn (question + context -> answer) prompt only. Multi-turn
  chat (Milestone 16) is a documented future extension point (see
  `build_messages`'s signature), not implemented in this milestone to
  avoid scope creep before the Chat UI that would actually need it
  exists.
- Prompt length grows with the number and size of kept chunks; extremely
  large `MAX_CONTEXT_CHARS` combined with a small local model's context
  window could still exceed what the model can process — context
  compression (Milestone 11) is the primary safeguard against this, not
  this module.

ALTERNATIVES CONSIDERED
-------------------------
- A single flat prompt string instead of role-tagged messages: simpler
  code, but bypasses each model's fine-tuned chat template — rejected for
  the instruction-following quality reason explained above.
- Few-shot examples embedded in the system prompt (showing the model an
  example Q&A pair): can improve output format consistency, but adds
  prompt length and a maintenance burden (examples need to stay
  representative); the explicit, repeated rules in `templates.py` were
  judged sufficient without this added complexity — revisit if real
  usage shows a formatting problem examples would fix.

BEST PRACTICES APPLIED
------------------------
- Prompt wording (`templates.py`) and assembly logic (this module) are
  cleanly separated — tuning the instructions never requires touching
  code that manipulates data structures, and vice versa.
"""

from __future__ import annotations

from app.config import settings
from app.prompts.templates import (
    DOCUMENT_ANALYSIS_SYSTEM_PROMPT_UZ,
    DOCUMENT_ANALYSIS_USER_TEMPLATE,
    DOCUMENT_TRUNCATED_NOTICE_UZ,
    SOURCE_HEADER_TEMPLATE,
    SYSTEM_PROMPT_UZ,
    USER_PROMPT_TEMPLATE,
)
from app.reranker.cross_encoder import RerankedResult


def _format_source(index: int, chunk: RerankedResult) -> str:
    """Render one chunk as a numbered source block, omitting unknown fields.

    See module docstring for why missing metadata is omitted entirely
    rather than rendered as a placeholder like "None".
    """
    lines = [SOURCE_HEADER_TEMPLATE.format(index=index)]

    if chunk.law_name:
        lines.append(f"Qonun: {chunk.law_name}")
    if chunk.article_number:
        lines.append(f"Modda: {chunk.article_number}-modda")
    if chunk.section:
        lines.append(f"Boʻlim: {chunk.section}")
    if chunk.page_number is not None:
        lines.append(f"Sahifa: {chunk.page_number}")

    lines.append(f"Matn: {chunk.text}")
    return "\n".join(lines)


def format_context(chunks: list[RerankedResult]) -> str:
    """Render every chunk as the MANBALAR (sources) block of the prompt.

    Chunks are numbered in the order given — callers should pass them
    already sorted best-first (as `compress_context`'s `kept` list is),
    so "Manba 1" is consistently the single most relevant source.
    """
    if not chunks:
        return "(Hech qanday tegishli manba topilmadi.)"
    return "\n\n".join(_format_source(i, chunk) for i, chunk in enumerate(chunks, start=1))


def build_messages(query: str, chunks: list[RerankedResult]) -> list[dict[str, str]]:
    """Assemble the final chat messages to send to the local LLM.

    Returns a list of `{"role": ..., "content": ...}` dicts in the shape
    Ollama's chat API expects (Milestone 13) — a system message with the
    fixed instructions (`templates.SYSTEM_PROMPT_UZ`) and a user message
    with the formatted sources and the (already-preprocessed, see
    `app.rag.query_processing`) question.
    """
    context_block = format_context(chunks)
    user_content = USER_PROMPT_TEMPLATE.format(context=context_block, question=query)
    return [
        {"role": "system", "content": SYSTEM_PROMPT_UZ},
        {"role": "user", "content": user_content},
    ]


def build_analysis_messages(document_text: str, file_name: str) -> list[dict[str, str]]:
    """Assemble chat messages for the document-analysis endpoint.

    Unlike `build_messages()`, there is no retrieved-chunks context block
    here — the ENTIRE input is the uploaded document's own text (see
    `templates.DOCUMENT_ANALYSIS_SYSTEM_PROMPT_UZ` for why "related laws"
    is scoped to only what the document itself cites, not the model's
    outside knowledge). Text longer than
    `settings.max_document_analysis_chars` is truncated with a trailing
    notice so the model — and the user reading its output — both know
    the analysis only covers a prefix of the document, rather than
    silently analyzing a cut-off document as if it were complete.
    """
    limit = settings.max_document_analysis_chars
    truncated = len(document_text) > limit
    text = document_text[:limit]
    if truncated:
        text += DOCUMENT_TRUNCATED_NOTICE_UZ

    user_content = DOCUMENT_ANALYSIS_USER_TEMPLATE.format(file_name=file_name, document_text=text)
    return [
        {"role": "system", "content": DOCUMENT_ANALYSIS_SYSTEM_PROMPT_UZ},
        {"role": "user", "content": user_content},
    ]
