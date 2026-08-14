from scripts.math_fallback_seed import FALLBACKS, build_rows


def test_math_fallback_bank_covers_all_math_route_topics():
    """Stage 04 requires all 42 math route topics to have specific fallbacks."""
    from app.math_plan import MATH_TOPIC_PLAN

    expected = {row.topic_id for row in MATH_TOPIC_PLAN}
    assert set(FALLBACKS) == expected


def test_math_fallback_bank_has_checkable_single_choice_rows():
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


def test_stage03_new_high_impact_topics_are_specific_not_generic():
    upgraded = {187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 201, 202}
    assert upgraded.issubset(FALLBACKS)
    for topic_id in upgraded:
        row = build_rows(topic_id)[0]
        question_text = str(row["question_text"])
        assert "Что лучше всего описывает тему" not in question_text
        assert "первый шаг обычно" not in question_text
