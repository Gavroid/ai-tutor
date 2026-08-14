from app.math_plan import MATH_TOPIC_PLAN, diagnostic_topic_ids, next_topic_after, tier_rank


def test_math_plan_covers_42_unique_topics_in_order():
    ids = [row.topic_id for row in MATH_TOPIC_PLAN]
    assert len(ids) == 42
    assert len(set(ids)) == 42
    assert [row.order for row in MATH_TOPIC_PLAN] == list(range(1, 43))


def test_diagnostic_sample_is_balanced_and_stable():
    ids = diagnostic_topic_ids()
    assert len(ids) == 8
    assert ids[:3] == [187, 188, 193]
    assert len(set(ids)) == len(ids)


def test_next_topic_and_tier_rank():
    assert next_topic_after(187) == 188
    assert next_topic_after(228) is None
    assert tier_rank("base") < tier_rank("medium") < tier_rank("hard")
