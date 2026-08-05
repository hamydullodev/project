from scripts.convert_to_alpaca import convert_dolly, convert_oasst1, convert_sharegpt


def test_convert_dolly_maps_context_to_input():
    example = {"instruction": "Summarize", "context": "Some context", "response": "A summary"}
    assert convert_dolly(example) == {"instruction": "Summarize", "input": "Some context", "output": "A summary"}


def test_convert_dolly_defaults_missing_context_to_empty_string():
    example = {"instruction": "Summarize", "response": "A summary"}
    assert convert_dolly(example)["input"] == ""


def test_convert_sharegpt_pairs_human_and_gpt_turns():
    example = {
        "conversations": [
            {"from": "human", "value": "Hi"},
            {"from": "gpt", "value": "Hello!"},
            {"from": "human", "value": "How are you?"},
            {"from": "gpt", "value": "Doing well."},
        ]
    }
    rows = convert_sharegpt(example)
    assert len(rows) == 2
    assert rows[0] == {"instruction": "Hi", "input": "", "output": "Hello!"}
    assert rows[1]["instruction"] == "How are you?"
    assert "User: Hi\nAssistant: Hello!" in rows[1]["input"]


def test_convert_sharegpt_skips_turns_with_wrong_roles():
    example = {"conversations": [{"from": "system", "value": "setup"}, {"from": "gpt", "value": "ok"}]}
    assert convert_sharegpt(example) == []


def test_convert_sharegpt_supports_messages_role_content_schema():
    example = {
        "messages": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
    }
    assert convert_sharegpt(example) == [{"instruction": "Hi", "input": "", "output": "Hello!"}]


def test_convert_oasst1_pairs_prompter_and_assistant_messages():
    rows = [
        {"message_id": "1", "parent_id": None, "role": "prompter", "text": "What is LoRA?"},
        {"message_id": "2", "parent_id": "1", "role": "assistant", "text": "LoRA is..."},
        {"message_id": "3", "parent_id": "2", "role": "prompter", "text": "follow-up, ignored"},
    ]
    out = convert_oasst1(rows)
    assert out == [{"instruction": "What is LoRA?", "input": "", "output": "LoRA is..."}]


def test_convert_oasst1_ignores_orphaned_assistant_messages():
    rows = [{"message_id": "2", "parent_id": "missing", "role": "assistant", "text": "orphan"}]
    assert convert_oasst1(rows) == []
