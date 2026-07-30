import json

from scripts.clean_dataset import normalized_hash, sanitize_text


def test_sanitize_text_strips_control_chars_and_normalizes():
    assert sanitize_text("hello\x00world") == "helloworld"
    assert sanitize_text("  padded  ") == "padded"


def test_normalized_hash_is_case_and_whitespace_insensitive():
    a = normalized_hash("Summarize   this", "some input")
    b = normalized_hash("summarize this", "  Some Input ")
    assert a == b


def test_normalized_hash_differs_for_different_content():
    a = normalized_hash("Summarize this", "")
    b = normalized_hash("Translate this", "")
    assert a != b


def test_clean_dataset_drops_duplicates_and_invalid_rows(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    input_path = tmp_path / "in.jsonl"
    output_path = tmp_path / "out.jsonl"

    rows = [
        {"instruction": "Say hi", "input": "", "output": "Hi there"},
        {"instruction": "Say hi", "input": "", "output": "Hi there"},  # exact duplicate
        {"instruction": "  Say Hi  ", "input": "", "output": "hi there"},  # normalized duplicate (diff case/whitespace)
        {"instruction": "", "output": "no instruction"},  # invalid: missing instruction
        {"instruction": "Missing output"},  # invalid: missing output
        {"instruction": "Too short", "input": "", "output": "ok"},  # below min-output-chars default (3)
        {"instruction": "Fine", "input": "", "output": "This is fine"},
    ]
    with input_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    result = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "clean_dataset.py"),
         "--input", str(input_path), "--output", str(output_path)],
        check=True, capture_output=True, text=True,
    )

    with output_path.open() as f:
        kept = [json.loads(line) for line in f]

    assert len(kept) == 2
    assert {row["instruction"] for row in kept} == {"Say hi", "Fine"}
    assert "Kept 2 examples" in result.stdout


def test_clean_dataset_filters_by_max_output_tokens(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    input_path = tmp_path / "in.jsonl"
    output_path = tmp_path / "out.jsonl"

    rows = [
        {"instruction": "Long", "input": "", "output": " ".join(["word"] * 10)},
        {"instruction": "Short", "input": "", "output": "short answer"},
    ]
    with input_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    subprocess.run(
        [sys.executable, str(project_root / "scripts" / "clean_dataset.py"),
         "--input", str(input_path), "--output", str(output_path), "--max-output-tokens", "5"],
        check=True, capture_output=True, text=True,
    )

    with output_path.open() as f:
        kept = [json.loads(line) for line in f]

    assert len(kept) == 1
    assert kept[0]["instruction"] == "Short"
