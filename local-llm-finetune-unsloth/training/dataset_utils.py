"""Load Alpaca-format JSONL files and format them into the model's training prompt."""

from datasets import Dataset, load_dataset

ALPACA_PROMPT = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

ALPACA_PROMPT_NO_INPUT = """Below is an instruction that describes a task. Write a response that appropriately completes the request.

### Instruction:
{}

### Response:
{}"""


def format_example(example: dict, eos_token: str) -> str:
    instruction = example["instruction"].strip()
    input_ = example.get("input", "").strip()
    output = example["output"].strip()

    if input_:
        text = ALPACA_PROMPT.format(instruction, input_, output)
    else:
        text = ALPACA_PROMPT_NO_INPUT.format(instruction, output)

    return text + eos_token


def load_alpaca_dataset(path: str, tokenizer) -> Dataset:
    ds = load_dataset("json", data_files=path, split="train")

    def _map(example):
        return {"text": format_example(example, tokenizer.eos_token)}

    return ds.map(_map, remove_columns=ds.column_names)
