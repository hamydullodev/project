"""Clean an Alpaca-format JSONL dataset: dedup, length-filter, encoding-sanitize, validate.

Usage:
    python scripts/clean_dataset.py --input data/raw/custom_raw.jsonl --output data/raw/custom_clean.jsonl
"""

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = CONTROL_CHARS_RE.sub("", text)
    return text.strip()


def normalized_hash(instruction: str, input_: str) -> str:
    key = (instruction.strip().lower() + "||" + input_.strip().lower())
    key = re.sub(r"\s+", " ", key)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--min-output-chars", type=int, default=3)
    parser.add_argument("--max-output-tokens", type=int, default=512, help="approximate, via whitespace split")
    args = parser.parse_args()

    seen_hashes: set[str] = set()
    kept, dropped_dup, dropped_invalid, dropped_length = 0, 0, 0, 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.input.open("r", encoding="utf-8") as fin, args.output.open("w", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                dropped_invalid += 1
                continue

            instruction = sanitize_text(row.get("instruction", ""))
            input_ = sanitize_text(row.get("input", ""))
            output = sanitize_text(row.get("output", ""))

            if not instruction or not output:
                dropped_invalid += 1
                continue

            if len(output) < args.min_output_chars:
                dropped_length += 1
                continue

            if len(output.split()) > args.max_output_tokens:
                dropped_length += 1
                continue

            h = normalized_hash(instruction, input_)
            if h in seen_hashes:
                dropped_dup += 1
                continue
            seen_hashes.add(h)

            fout.write(json.dumps({"instruction": instruction, "input": input_, "output": output}, ensure_ascii=False) + "\n")
            kept += 1

    print(f"Kept {kept} examples")
    print(f"Dropped {dropped_dup} duplicates, {dropped_invalid} invalid rows, {dropped_length} length-filtered rows")


if __name__ == "__main__":
    main()
