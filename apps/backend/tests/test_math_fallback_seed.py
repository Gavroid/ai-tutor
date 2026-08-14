from scripts.math_fallback_seed import FALLBACKS, build_rows


def test_failed_smoke_topics_have_checkable_single_choice_fallbacks():
    expected = {200, 213, 214, 220, 221, 222, 224, 226, 227, 228}

    assert set(FALLBACKS) == expected
    for topic_id in expected:
        rows = build_rows(topic_id)
        assert len(rows) == 1
        row = rows[0]
        assert row["type"] == "single"
        assert isinstance(row["options"], list)
        assert row["correct_answer"] in row["options"]
        assert row["question_text"]
        assert row["explanation"]
