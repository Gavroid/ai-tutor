from app.algebra_plan import ALGEBRA_TOPIC_PLAN

from scripts.algebra_fallback_seed import FALLBACKS, build_rows


def test_algebra_fallback_bank_covers_all_preview_route_topics():
    expected = {row.topic_id for row in ALGEBRA_TOPIC_PLAN}
    assert set(FALLBACKS) == expected


def test_algebra_fallback_rows_are_checkable_single_choice_tasks():
    for topic_id in FALLBACKS:
        rows = build_rows(topic_id)
        assert len(rows) == 1
        row = rows[0]
        assert row["type"] == "single"
        assert isinstance(row["options"], list)
        assert len(row["options"]) >= 4
        assert row["correct_answer"] in row["options"]
        assert row["question_text"]
        assert row["explanation"]
        assert row["typical_mistakes"]
        assert row["difficulty"] == 1
        assert row["order_index"] == 1
        assert row["is_active"] is True


def test_algebra_fallbacks_are_specific_not_generic():
    for topic_id in FALLBACKS:
        question_text = str(build_rows(topic_id)[0]["question_text"])
        assert "Что лучше всего описывает тему" not in question_text
        assert "первый шаг обычно" not in question_text
