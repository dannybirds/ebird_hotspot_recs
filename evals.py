import csv
from dataclasses import dataclass
from itertools import islice

from tqdm import tqdm
from common import EndToEndEvalDatapoint, Recommendation
from recommenders import HotspotRecommender

@dataclass
class RecMetrics:
    found_lifers: int = 0
    missed_lifers: int = 0
    abs_error: float = 0.0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

@dataclass
class EndToEndAggregateMetrics:
    n: int = 0
    found_lifers: float = 0
    missed_lifers: float = 0
    abs_error: float = 0.0
    true_positives: float = 0
    false_positives: float = 0
    false_negatives: float = 0

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


def run_end_to_end_evals(recommender: HotspotRecommender, dataset: list[EndToEndEvalDatapoint]) -> list[RecMetrics]:
    """
    Run end-to-end evaluations on a dataset.
    """
    return [
        evaluate(
            recommender.recommend(datapoint.target_location, datapoint.target_date, datapoint.life_list),
            datapoint.ground_truth
        ) 
        for datapoint in tqdm(dataset)
    ]

def aggregate_end_to_end_eval_metrics(metrics: list[RecMetrics]) -> EndToEndAggregateMetrics:
    """
    Aggregate end-to-end evaluation metrics.
    """
    agg = EndToEndAggregateMetrics()
    agg.n = len(metrics)
    for m in metrics:
        agg.found_lifers += m.found_lifers
        agg.missed_lifers += m.missed_lifers
        agg.abs_error += m.abs_error
        agg.true_positives += m.true_positives
        agg.false_positives += m.false_positives
        agg.false_negatives += m.false_negatives
    
    return agg


def load_observer_ids(file: str, start_idx:int = 0, n:int|None = None) -> list[str]:
    """
    Load observer IDs from a file.
    
    The file must be a CSV with a column called 'observer_id' (other columns don't matter).
    If given, start_idx and n are used to slice the file so that only the n ids starting at start_idx are returned.
    """
    with open(file, 'r') as f:
        reader = csv.DictReader(f)
        observer_ids = [row['observer_id'] for row in islice(reader, start_idx, start_idx + n if n else None)]
    return observer_ids
