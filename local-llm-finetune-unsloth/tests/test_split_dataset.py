import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _write_jsonl(path, rows):
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _read_jsonl(path):
    with path.open() as f:
        return [json.loads(line) for line in f]


def test_split_dataset_respects_ratio_and_covers_all_rows(tmp_path):
    input_path = tmp_path / "clean.jsonl"
    train_path = tmp_path / "train.jsonl"
    val_path = tmp_path / "val.jsonl"

    rows = [{"instruction": f"q{i}", "input": "", "output": f"a{i}"} for i in range(20)]
    _write_jsonl(input_path, rows)

    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "split_dataset.py"),
         "--input", str(input_path), "--train-output", str(train_path),
         "--val-output", str(val_path), "--val-ratio", "0.2", "--seed", "42"],
        check=True, capture_output=True, text=True,
    )

    train_rows = _read_jsonl(train_path)
    val_rows = _read_jsonl(val_path)

    assert len(train_rows) == 16
    assert len(val_rows) == 4
    assert {r["instruction"] for r in train_rows} | {r["instruction"] for r in val_rows} == {r["instruction"] for r in rows}
    assert {r["instruction"] for r in train_rows}.isdisjoint({r["instruction"] for r in val_rows})


def test_split_dataset_val_size_is_at_least_one(tmp_path):
    input_path = tmp_path / "clean.jsonl"
    train_path = tmp_path / "train.jsonl"
    val_path = tmp_path / "val.jsonl"

    rows = [{"instruction": f"q{i}", "input": "", "output": f"a{i}"} for i in range(5)]
    _write_jsonl(input_path, rows)

    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "split_dataset.py"),
         "--input", str(input_path), "--train-output", str(train_path),
         "--val-output", str(val_path), "--val-ratio", "0.01", "--seed", "1"],
        check=True, capture_output=True, text=True,
    )

    assert len(_read_jsonl(val_path)) == 1
    assert len(_read_jsonl(train_path)) == 4


def test_split_dataset_is_deterministic_with_seed(tmp_path):
    input_path = tmp_path / "clean.jsonl"
    rows = [{"instruction": f"q{i}", "input": "", "output": f"a{i}"} for i in range(10)]
    _write_jsonl(input_path, rows)

    outputs = []
    for run in range(2):
        train_path = tmp_path / f"train_{run}.jsonl"
        val_path = tmp_path / f"val_{run}.jsonl"
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "split_dataset.py"),
             "--input", str(input_path), "--train-output", str(train_path),
             "--val-output", str(val_path), "--val-ratio", "0.3", "--seed", "7"],
            check=True, capture_output=True, text=True,
        )
        outputs.append((_read_jsonl(train_path), _read_jsonl(val_path)))

    assert outputs[0] == outputs[1]
