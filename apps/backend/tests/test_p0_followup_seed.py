from scripts.p0_followup_seed import build_followups


def test_build_followups_returns_three_student_actions():
    rows = build_followups("Проценты")

    assert [row["label"] for row in rows] == ["Ещё пример", "Проверь меня", "Дай задачу"]
    assert [row["order_index"] for row in rows] == [1, 2, 3]
    assert all("Проценты" in str(row["prompt"]) for row in rows)
    assert rows[2]["kind"] == "next"
