"""
eval_action_items.py

Precision/recall of action_items.find_action_items against the hand-labelled
lines in eval/action_items_labeled.json (see its "_about" note: 'dev' was
used while tuning the rules, 'heldout' only scored afterwards).

    python eval_action_items.py
"""

import json
from pathlib import Path

from action_items import find_action_items

LABELS_PATH = Path(__file__).parent / "eval" / "action_items_labeled.json"


def score(rows: list[list]) -> dict:
    flagged = {text for _, text in find_action_items([("X", text) for text, _ in rows])}
    tp = sum(1 for text, label in rows if label and text in flagged)
    fp = sum(1 for text, label in rows if not label and text in flagged)
    fn = sum(1 for text, label in rows if label and text not in flagged)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "false_positives": [t for t, label in rows if not label and t in flagged],
        "missed": [t for t, label in rows if label and t not in flagged],
    }


def main() -> None:
    data = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    for split in ("dev", "heldout"):
        result = score(data[split])
        print(f"{split:8s} n={len(data[split]):3d}  precision={result['precision']:.2f}  "
              f"recall={result['recall']:.2f}  F1={result['f1']:.2f}")
        for text in result["false_positives"]:
            print(f"    false positive: {text}")
        for text in result["missed"]:
            print(f"    missed:         {text}")


if __name__ == "__main__":
    main()
