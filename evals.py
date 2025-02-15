from dataclasses import dataclass
from recommenders import Recommendation

@dataclass
class RecMetrics:
    found_lifers: int = 0
    missed_lifers: int = 0
    abs_error: float = 0.0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

def evaluate(recs: list[Recommendation], ground_truth: list[Recommendation]) -> RecMetrics:
    """
    Evaluate the recommendations against the ground truth.

    Parameters:
    recs (list[Recommendation]): The recommendations to evaluate.
    ground_truth (list[Recommendation]): The ground truth recommendations.

    Returns:
    dict: A dictionary of evaluation metrics.
    """

    gt_dict = {r.location: r for r in ground_truth}
    hits: set[str] = set()
    metrics: RecMetrics = RecMetrics()
    for rec in recs:
        if rec.location in gt_dict:
            hits.add(rec.location)
            metrics.found_lifers += int(gt_dict[rec.location].score) # give credit for all of them, whether predicted or not
            metrics.abs_error += abs(rec.score - gt_dict[rec.location].score)
            metrics.true_positives += 1
        else:
            metrics.abs_error += rec.score
            metrics.false_positives += 1
    for gt in gt_dict.values():
        if gt.location not in hits:
            metrics.missed_lifers += int(gt.score)
            metrics.abs_error += gt.score
            metrics.false_negatives += 1
    return metrics