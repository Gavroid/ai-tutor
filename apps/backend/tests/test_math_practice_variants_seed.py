from scripts.math_practice_variants_seed import build_rows


def test_build_rows_returns_three_checkable_single_choice_variants():
    rows = build_rows(200, "Распределительное свойство умножения")

    assert len(rows) == 3
    assert [row["order_index"] for row in rows] == [1, 2, 3]
    assert all(row["type"] == "single" for row in rows)
    assert all(row["correct_answer"] in row["options"] for row in rows)
    assert all(row["question_text"] for row in rows)
    assert rows[0]["correct_answer"] == "27"
