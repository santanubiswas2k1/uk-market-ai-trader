import pandas as pd

from src.models.walkforward import walk_forward_evaluate


def test_walk_forward_only_predicts_after_training_window():
    rows = 90
    idx = pd.date_range("2025-01-01", periods=rows, freq="B", tz="UTC")
    frame = pd.DataFrame(
        {
            "x1": [i / rows for i in range(rows)],
            "x2": [((i % 7) - 3) / 10 for i in range(rows)],
            "target_up_1d": [i % 2 for i in range(rows)],
        },
        index=idx,
    )

    result = walk_forward_evaluate(
        frame,
        ["x1", "x2"],
        min_train_rows=50,
        test_rows=10,
        step_rows=10,
    )

    assert result.folds == 4
    assert result.predictions.index.min() == idx[50]
    assert len(result.predictions) == 40
