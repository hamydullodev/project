"""
Collection identity: deriving a stable law/collection id from a file's location.

WHY THIS MODULE EXISTS
-----------------------
The multi-collection upgrade (spec: "add a new law simply by placing files
inside a folder") needs a `collection_id` that is stable, human-readable,
and requires ZERO code changes when a new law is added. The document's
own text can't be that identifier — `_extract_law_name()`
(`app/ingestion/chunker.py`) already derives a free-text `law_name` from
content for display, but it's not a controlled slug and two documents
could plausibly extract the same or a slightly different string.

The one thing that IS already a stable, unique, human-chosen identifier
is the folder a document lives in: `txt/kodekslar/jinoyat_kodeksi/document.txt`.
This module's `derive_collection()` reads that folder structure — nothing
else — so dropping a new `txt/<category>/<new_slug>/document.txt` in
immediately becomes a new, correctly-labeled collection with no code
change, satisfying the "no hardcoded logic" requirement.

WHY A CURATED TITLE REGISTRY, NOT PURE PRETTIFICATION
------------------------------------------------------------
A prettified slug (`jinoyat_kodeksi` -> "Jinoyat kodeksi") is a
serviceable fallback but reads awkwardly for some slugs. `KNOWN_TITLES`
lets specific collections get a properly-cased, natural display title;
any slug NOT in the registry still gets a readable fallback rather than
failing or requiring a registry update before it can be indexed.

WHY `SOURCE_URLS` IS SEPARATE AND OPTIONAL
------------------------------------------------
Citing the original lex.uz document lets users verify an answer against
the authoritative source. This is a pure citation convenience (a link),
NOT a live data source — the indexed text is always the local corpus.
Collections with no confirmed lex.uz URL simply have no outbound link;
nothing else depends on this dict being complete.
"""

from __future__ import annotations

from pathlib import Path

# collection_id -> human-readable Uzbek title.
KNOWN_TITLES: dict[str, str] = {
    # -- konstitutsiya --
    "konstitutsiya": "O'zbekiston Respublikasi Konstitutsiyasi",
    # -- kodekslar --
    "bojxona_kodeksi": "Bojxona kodeksi",
    "byudjet_kodeksi": "Byudjet kodeksi",
    "fuqarolik_kodeksi": "Fuqarolik kodeksi",
    "fuqarolik_protsessual_kodeksi": "Fuqarolik protsessual kodeksi",
    "havo_kodeksi": "Havo kodeksi",
    "iqtisodiy_protsessual_kodeksi": "Iqtisodiy protsessual kodeks",
    "jinoyat_kodeksi": "Jinoyat kodeksi",
    "jinoyat_protsessual_kodeksi": "Jinoyat-protsessual kodeksi",
    "mamuriy_javobgarlik_kodeksi": "Ma'muriy javobgarlik to'g'risida kodeks",
    "mamuriy_sud_ishlarini_yuritish_kodeksi": "Ma'muriy sud ishlarini yuritish kodeksi",
    "mehnat_kodeksi": "Mehnat kodeksi",
    "oila_kodeksi": "Oila kodeksi",
    "saylov_kodeksi": "Saylov kodeksi",
    "shaharsozlik_kodeksi": "Shaharsozlik kodeksi",
    "soliq_kodeksi": "Soliq kodeksi",
    "suv_kodeksi": "Suv kodeksi",
    "uy_joy_kodeksi": "Uy-joy kodeksi",
    "yer_kodeksi": "Yer kodeksi",
    # -- qonunlar (a representative subset; unlisted slugs fall back to prettify) --
    "vasiylik_va_homiylik": "Vasiylik va homiylik to'g'risida(gi qonun)",
    "xotin_qizlar": "Xotin-qizlarni har qanday tazyiq va zo'ravonlikdan himoya qilish to'g'risida(gi qonun)",
    "bola_huquqlari_kafolatlari": "Bola huquqlarining kafolatlari to'g'risida(gi qonun)",
    "nogironligi_bolgan_shaxslar_huquqlari": "Nogironligi bo'lgan shaxslarning huquqlarini himoya qilish to'g'risida(gi qonun)",
    "fuqarolarning_murojaatlari": "Jismoniy va yuridik shaxslarning murojaatlari to'g'risida(gi qonun)",
    "bandlik_togrisida": "Aholi bandligi to'g'risida(gi qonun)",
    "mehnatni_muhofaza_qilish": "Mehnatni muhofaza qilish to'g'risida(gi qonun)",
    "talim_togrisida": "Ta'lim to'g'risida(gi qonun)",
}

# collection_id -> lex.uz document URL, for "view original" citation links.
# Deliberately sparse: only confirmed URLs go here. No live scraping of
# lex.uz is performed anywhere in this project.
SOURCE_URLS: dict[str, str] = {}

# Folder categories that group collections, mirroring txt/'s top-level layout.
_KNOWN_CATEGORIES = {"kodekslar", "qonunlar", "konstitutsiya"}


def _prettify(slug: str) -> str:
    """Fallback display title for a slug with no `KNOWN_TITLES` entry."""
    words = slug.replace("_", " ").split()
    return " ".join(w.capitalize() for w in words)


def derive_collection(file_path: Path, root: Path) -> tuple[str, str, str]:
    """Derive (category, collection_id, title) for a file from its location under `root`.

    Expected layout: `<root>/<category>/<collection_id>/<file>` (e.g.
    `txt/kodekslar/jinoyat_kodeksi/document.txt`). Any file that doesn't
    fit this shape (fewer than two path segments below `root`) falls back
    to using its immediate parent folder name as `collection_id` with
    `category="other"` — still stable and unique, just not grouped under
    one of the three known top-level categories.
    """
    try:
        relative_parts = file_path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        relative_parts = file_path.parts

    if len(relative_parts) >= 3:
        category, collection_id = relative_parts[0], relative_parts[1]
    elif len(relative_parts) == 2:
        category, collection_id = "other", relative_parts[0]
    else:
        category, collection_id = "other", file_path.stem

    title = KNOWN_TITLES.get(collection_id, _prettify(collection_id))
    return category, collection_id, title
