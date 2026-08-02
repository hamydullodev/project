"""
Prompt text constants: the system instructions and formatting templates.

WHY THIS MODULE EXISTS
-----------------------
Separating the actual prompt WORDING from the code that assembles it
(`builder.py`) means the prompt can be read, reviewed, and tweaked as
plain text — the thing that actually needs iteration when tuning an LLM's
behavior — without touching any Python logic. This mirrors
`legal_parser.py`'s separation of regex patterns from the parsing
algorithm: constants that are "content to get right" live apart from
"logic to get right."

WHY THE SYSTEM PROMPT IS WRITTEN IN UZBEK
------------------------------------------------
This project's users ask legal questions in Uzbek about Uzbek law; having
the model think and respond in Uzbek throughout — not receive English
instructions and switch languages mid-response — produces more natural,
consistent output. It also sidesteps a real failure mode: an
instruction-following model given English meta-instructions but Uzbek
content sometimes answers in English or mixes languages. Writing the
instructions themselves in Uzbek keeps the model in one linguistic
register end to end.

HOW EACH SPEC REQUIREMENT MAPS TO A SPECIFIC INSTRUCTION
------------------------------------------------------------
The spec's prompt requirements are each turned into an explicit,
unambiguous rule rather than a vague "be careful" instruction — LLMs
follow concrete, repeated instructions far more reliably than implied
ones:

  - "Answer ONLY using retrieved documents" -> an explicit rule stating
    the model must not use outside knowledge, stated twice (once as a
    rule, once again in the closing reminder) since repetition measurably
    improves instruction-following in smaller local models, which are
    more prone to instruction drift over a long context than large
    hosted models.
  - "If information is missing, say [X]" -> `NOT_FOUND_MESSAGE_UZ` is
    given to the model VERBATIM as the exact string to output — an exact
    string match is far more reliable for the calling code to check for
    (Milestone 14) than asking the model to "explain that it doesn't
    know" in its own words each time.
  - "Never hallucinate" -> operationalized as "if a fact isn't in the
    provided sources, don't state it," which is something a model can
    actually act on, unlike the abstract instruction "don't hallucinate"
    alone.
  - "Always cite article numbers" / "Always mention document names" ->
    an explicit citation FORMAT is specified (which law, which article),
    not just "cite your sources" — vague citation instructions reliably
    produce vague citations.

WHY THE NOT-FOUND MESSAGE IS GIVEN VERBATIM RATHER THAN DESCRIBED
------------------------------------------------------------------------
`NOT_FOUND_MESSAGE_UZ` is deliberately the Uzbek-language equivalent of
the spec's exact required text ("I could not find this information in
the provided laws"), not a paraphrase — this satisfies the letter of the
spec (that exact fallback message must appear) while keeping the whole
interaction in Uzbek. Because it's specified as a literal, fixed string
the model is told to reproduce exactly, Milestone 14's pipeline can
detect a "no answer found" response with a simple substring check rather
than needing to interpret free-form text.
"""

from __future__ import annotations

# Given VERBATIM to the model as the exact text to output when no
# relevant information is found — see module docstring for why an exact,
# fixed string (rather than "explain you don't know") is used.
NOT_FOUND_MESSAGE_UZ = "Men taqdim etilgan qonun hujjatlarida bu haqida maʼlumot topa olmadim."

SYSTEM_PROMPT_UZ = f"""Siz Oʻzbekiston Respublikasi qonunchiligi boʻyicha ishonchli yuridik yordamchisiz.

Qat'iy qoidalar:
1. Faqat quyida taqdim etilgan manbalardagi maʼlumotlardan foydalaning. Sizning oʻz bilimingizni yoki manbalarda yoʻq hech qanday maʼlumotni ishlatmang.
2. Agar taqdim etilgan manbalarda savolga javob topilmasa, aynan shu jumlani yozing: "{NOT_FOUND_MESSAGE_UZ}" Hech qachon taxmin qilmang yoki oʻylab topmang.
3. Har bir dalil yoki qoidani keltirganingizda, qaysi qonun va qaysi moddadan olinganini aniq koʻrsating (masalan: "Mehnat kodeksining 155-moddasiga koʻra...").
4. Faqat manbalarda aniq yozilgan modda raqamlari va qonun nomlaridan foydalaning. Hech qachon modda raqamini yoki qonun nomini oʻzingizdan oʻylab topmang.
5. Javobingizni aniq, tushunarli oʻzbek tilida, professional uslubda yozing.
6. Agar bir nechta manba tegishli boʻlsa, ularning barchasidan foydalaning va ziddiyat boʻlsa, buni aytib oʻting.

Yodda tuting: siz faqat pastda "MANBALAR" boʻlimida keltirilgan matnlarga asoslanib javob berishingiz shart. Manbalardan tashqari hech narsa qoʻshmang."""

USER_PROMPT_TEMPLATE = """MANBALAR:

{context}

SAVOL: {question}

Yuqoridagi manbalarga asoslanib, savolga javob bering. Har bir faktni qaysi qonun va moddadan olinganini koʻrsating."""

# One retrieved chunk's formatting within the MANBALAR (sources) block.
# Fields that don't apply to a given chunk (e.g. article_number for a
# non-legal-code document, page_number for a non-paginated format) are
# omitted entirely by the builder rather than shown as "None" - see
# builder.py's _format_source.
SOURCE_HEADER_TEMPLATE = "--- Manba {index} ---"


# --------------------------------------------------------------------------
# Document analysis ("+" upload button) — a SEPARATE prompt from the
# corpus Q&A one above. This one has no retrieved MANBALAR block at all;
# the only input is the uploaded document's own text, so the grounding
# rule is different in kind: not "only use the retrieved chunks" but
# "only use what this document itself says or cites" — an ungrounded
# "related laws" section here would be exactly the kind of fabrication
# the rest of this project refuses to produce.
# --------------------------------------------------------------------------

DOCUMENT_ANALYSIS_SYSTEM_PROMPT_UZ = """Siz Oʻzbekiston Respublikasi qonunchiligi boʻyicha ishonchli yuridik yordamchisiz. Foydalanuvchi bitta hujjatni yukladi — sizning vazifangiz shu hujjatni tahlil qilish.

Qat'iy qoidalar:
1. Faqat quyida taqdim etilgan hujjat matnidagi maʼlumotlardan foydalaning. Hujjatda yoʻq hech qanday faktni oʻylab topmang.
2. "Hujjatda tilga olingan qonun va moddalar" boʻlimida FAQAT hujjat matnining oʻzida aniq zikr etilgan qonun/modda nomlarini keltiring. Agar hujjat biror qonunga havola qilmagan boʻlsa, bu boʻlimni boʻsh qoldiring yoki "Hujjatda aniq qonunga havola yoʻq" deb yozing — oʻzingizning umumiy bilimingizdan tegishli qonunlarni oʻylab topib qoʻshmang.
3. Agar hujjat matni to'liq o'qib bo'lmagan yoki juda qisqa/tushunarsiz boʻlsa, buni ochiq ayting, mavjud boʻlmagan tafsilotlarni to'ldirmang.
4. Javobingizni aniq, tushunarli oʻzbek tilida, professional uslubda, quyidagi boʻlimlar bilan tuzing (Markdown sarlavhalari bilan):

## Qisqacha xulosa
## Huquqlar
## Majburiyatlar
## Muddatlar
## Zarur harakatlar
## Hujjatda tilga olingan qonun va moddalar
## Ehtimoliy huquqiy oqibatlar
## Yetishmayotgan yoki noaniq maʼlumotlar

Har bir boʻlimda hujjatga tegishli boʻlmagan narsa uchun "Hujjatda topilmadi" deb yozing — boʻlimni oʻylab topilgan matn bilan toʻldirmang."""

DOCUMENT_ANALYSIS_USER_TEMPLATE = """HUJJAT ({file_name}):

{document_text}

Yuqoridagi hujjatni tahlil qiling."""

DOCUMENT_TRUNCATED_NOTICE_UZ = (
    "\n\n[Eslatma: hujjat juda uzun boʻlgani uchun matn qisqartirildi; "
    "tahlil faqat yuqoridagi qismga asoslangan.]"
)
