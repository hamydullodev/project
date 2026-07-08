from pathlib import Path

import pypdfium2 as pdfium
from docling_core.types.doc import ImageRefMode

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    EasyOcrOptions,
)
from docling.datamodel.accelerator_options import (
    AcceleratorDevice,
    AcceleratorOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

# =========================
# Fayl yo'llari
# =========================

pdf_path = Path("public.pdf")
output_md_path = Path("public.md")

images_output_dir = Path("public")
images_output_dir.mkdir(exist_ok=True)

# Har safar nechta sahifa parse qilinsin
CHUNK_SIZE = 20

# =========================
# Pipeline
# =========================

pipeline_options = PdfPipelineOptions()

# Mac uchun CPU
pipeline_options.accelerator_options = AcceleratorOptions(
    num_threads=4,
    device=AcceleratorDevice.CPU,
)

# OCR
pipeline_options.do_ocr = True

pipeline_options.ocr_options = EasyOcrOptions(
    force_full_page_ocr=True
)

# Table recognition
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

# MPS qo'llamaydigan VLM modellarini o'chiramiz
pipeline_options.do_formula_enrichment = False
pipeline_options.do_code_enrichment = False

# Rasmlar
pipeline_options.images_scale = 1.5
pipeline_options.generate_page_images = False
pipeline_options.generate_picture_images = True

# =========================
# Converter
# =========================

converter = DocumentConverter(
    allowed_formats=[InputFormat.PDF],
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pipeline_options
        )
    },
)

# =========================
# Sahifalar soni
# =========================

pdf_doc = pdfium.PdfDocument(str(pdf_path))
total_pages = len(pdf_doc)
pdf_doc.close()

print(f"Jami sahifalar: {total_pages}")
print(f"Chunk size: {CHUNK_SIZE}")

# =========================
# Parse qilish
# =========================

markdown_parts = []

for start in range(1, total_pages + 1, CHUNK_SIZE):

    end = min(start + CHUNK_SIZE - 1, total_pages)

    print(f"Processing pages {start}-{end}")

    result = converter.convert(
        pdf_path,
        page_range=(start, end),
    )

    chunk_path = Path(f"_chunk_{start:04d}_{end:04d}.md")

    result.document.save_as_markdown(
        chunk_path,
        artifacts_dir=images_output_dir,
        image_mode=ImageRefMode.REFERENCED,
    )

    markdown_parts.append(
        chunk_path.read_text(encoding="utf-8")
    )

    chunk_path.unlink()

    del result

# =========================
# Bitta markdown faylga birlashtirish
# =========================

with open(output_md_path, "w", encoding="utf-8") as f:
    f.write("\n\n---\n\n".join(markdown_parts))

print("\n✅ Tayyor!")
print(f"Markdown: {output_md_path}")
print(f"Rasmlar: {images_output_dir}")