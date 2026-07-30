"""Convert public instruction datasets (Dolly, ShareGPT-style, OASST1) into Alpaca format.

Usage:
    python scripts/convert_to_alpaca.py --source dolly --output data/raw/dolly_alpaca.jsonl
    python scripts/convert_to_alpaca.py --source sharegpt --hf-dataset teknium/OpenHermes-2.5 \
        --max-samples 10000 --output data/raw/openhermes_alpaca.jsonl
    python scripts/convert_to_alpaca.py --source oasst1 --output data/raw/oasst1_alpaca.jsonl
"""

import argparse
import json
from pathlib import Path


def convert_dolly(example: dict) -> dict:
    return {
        "instruction": example["instruction"],
        "input": example.get("context", ""),
        "output": example["response"],
    }


def convert_sharegpt(example: dict) -> list[dict]:
    turns = example.get("conversations") or example.get("messages") or []
    rows, history = [], ""
    for i in range(0, len(turns) - 1, 2):
        human, gpt = turns[i], turns[i + 1]
        human_role = human.get("from") or human.get("role")
        gpt_role = gpt.get("from") or gpt.get("role")
        human_text = human.get("value") or human.get("content", "")
        gpt_text = gpt.get("value") or gpt.get("content", "")
        if human_role not in ("human", "user") or gpt_role not in ("gpt", "assistant"):
            continue
        rows.append({"instruction": human_text, "input": history, "output": gpt_text})
        history += f"User: {human_text}\nAssistant: {gpt_text}\n"
    return rows


def convert_oasst1(rows: list[dict]) -> list[dict]:
    by_id = {row["message_id"]: row for row in rows}
    out = []
    for row in rows:
        if row.get("role") != "assistant" or row.get("parent_id") is None:
            continue
        parent = by_id.get(row["parent_id"])
        if parent is None or parent.get("role") != "prompter":
            continue
        out.append({"instruction": parent["text"], "input": "", "output": row["text"]})
    return out


def load_hf_dataset(name: str, split: str, max_samples: int | None):
    from datasets import load_dataset

    ds = load_dataset(name, split=split)
    if max_samples:
        ds = ds.select(range(min(max_samples, len(ds))))
    return ds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=["dolly", "sharegpt", "oasst1"])
    parser.add_argument("--hf-dataset", default=None, help="Override the default HF dataset repo for the chosen source")
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    default_repo = {
        "dolly": "databricks/databricks-dolly-15k",
        "sharegpt": "teknium/OpenHermes-2.5",
        "oasst1": "OpenAssistant/oasst1",
    }[args.source]
    repo_id = args.hf_dataset or default_repo

    ds = load_hf_dataset(repo_id, args.split, args.max_samples)

    rows: list[dict] = []
    if args.source == "dolly":
        rows = [convert_dolly(ex) for ex in ds]
    elif args.source == "sharegpt":
        for ex in ds:
            rows.extend(convert_sharegpt(ex))
    elif args.source == "oasst1":
        rows = convert_oasst1(list(ds))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for row in rows:
            if row["instruction"].strip() and row["output"].strip():
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(rows)} Alpaca-format examples to {args.output}")


if __name__ == "__main__":
    main()
