"""Split a cleaned Alpaca-format JSONL dataset into train/validation sets.

Usage:
    python scripts/split_dataset.py --input data/raw/custom_clean.jsonl \
        --train-output data/processed/train.jsonl \
        --val-output data/processed/val.jsonl \
        --val-ratio 0.1 --seed 3407
"""

import argparse
import json
import random
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--train-output", required=True, type=Path)
    parser.add_argument("--val-output", required=True, type=Path)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=3407)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    random.Random(args.seed).shuffle(rows)

    val_size = max(1, int(len(rows) * args.val_ratio))
    val_rows = rows[:val_size]
    train_rows = rows[val_size:]

    for path, split_rows in [(args.train_output, train_rows), (args.val_output, val_rows)]:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for row in split_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Train: {len(train_rows)} examples -> {args.train_output}")
    print(f"Val:   {len(val_rows)} examples -> {args.val_output}")


if __name__ == "__main__":
    main()
