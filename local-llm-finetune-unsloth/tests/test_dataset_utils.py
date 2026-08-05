from training.dataset_utils import format_example


def test_format_example_uses_input_template_when_input_present():
    example = {"instruction": "Summarize", "input": "some text", "output": "a summary"}
    text = format_example(example, eos_token="</s>")
    assert "### Input:\nsome text" in text
    assert text.endswith("a summary</s>")


def test_format_example_uses_no_input_template_when_input_missing():
    example = {"instruction": "Say hi", "output": "Hello!"}
    text = format_example(example, eos_token="</s>")
    assert "### Input:" not in text
    assert "### Instruction:\nSay hi" in text
    assert text.endswith("Hello!</s>")


def test_format_example_strips_whitespace():
    example = {"instruction": "  Say hi  ", "input": "  ", "output": "  Hello!  "}
    text = format_example(example, eos_token="</s>")
    assert "### Input:" not in text
    assert text.endswith("Hello!</s>")
