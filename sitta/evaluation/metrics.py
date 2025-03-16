"""
Evaluation metrics for recommender systems.
"""

import csv
from dataclasses import dataclass
from itertools import islice

from tqdm import tqdm

from sitta.common.base import EndToEndEvalDatapoint, Recommendation, TargetArea, TargetAreaType
from sitta.recommenders.base import HotspotRecommender


@dataclass
class RecMetrics:
    """
    Metrics for evaluating recommended hotspots against ground truth.
    """
    target_species_found: int = 0
    target_species_missed: int = 0
    false_positive_hotspots: int = 0


@dataclass
class EndToEndAggregateMetrics:
    """
    Aggregate metrics for end-to-end evaluation.
    """
    n: int = 0
    target_species_found: int = 0
    target_species_missed: int = 0
    false_positive_hotspots: int = 0    
    

def evaluate(recs: list[Recommendation], ground_truth: list[Recommendation], k: int | None = None) -> RecMetrics:
    """
    Evaluate the recommendations against the ground truth.

    Parameters:
    recs (list[Recommendation]): The recommendations to evaluate.
    ground_truth (list[Recommendation]): The ground truth recommendations.
    k (int | None): Optional limit on the number of recommendations to consider.

    Returns:
    RecMetrics: Evaluation metrics.
    """
    gt_dict = {r.locality_id: r for r in ground_truth}
    hits: set[str] = set()
    metrics: RecMetrics = RecMetrics()
    
    # Sort recommendations by score (highest first)
    recs.sort(key=lambda r: r.score, reverse=True)
    
    # Limit to top-k if specified
    if k:
        recs = recs[:k]
    
    # Evaluate each recommendation
    for rec in recs:
        if rec.locality_id in gt_dict:
            hits.add(rec.locality_id)
            # Give credit for all target species found, whether predicted or not
            metrics.target_species_found += int(gt_dict[rec.locality_id].score)
        else:
            metrics.false_positive_hotspots += 1
    
    # Count missed locations
    for gt in gt_dict.values():
        if gt.locality_id not in hits:
            metrics.target_species_missed += int(gt.score)
    
    return metrics


def run_end_to_end_evals(
    recommender: HotspotRecommender,
    dataset: list[EndToEndEvalDatapoint],
    k: int | None = None
) -> list[RecMetrics]:
    """
    Run end-to-end evaluations on a dataset.
    
    Parameters:
    recommender (HotspotRecommender): The recommender to evaluate.
    dataset (list[EndToEndEvalDatapoint]): The evaluation dataset.
    k (int | None): Optional limit on the number of recommendations to consider.
    
    Returns:
    list[RecMetrics]: List of evaluation metrics for each datapoint.
    """
    return [
        evaluate(
            recommender.recommend(
                TargetArea(area_type=TargetAreaType.COUNTY, area_id=datapoint.target_location),
                datapoint.target_date,
                datapoint.life_list
            ),
            datapoint.ground_truth,
            k=k
        ) 
        for datapoint in tqdm(dataset)
    ]


def aggregate_end_to_end_eval_metrics(metrics: list[RecMetrics]) -> EndToEndAggregateMetrics:
    """
    Aggregate end-to-end evaluation metrics.
    
    Parameters:
    metrics (list[RecMetrics]): List of evaluation metrics.
    
    Returns:
    EndToEndAggregateMetrics: Aggregated metrics.
    """
    agg = EndToEndAggregateMetrics()
    agg.n = len(metrics)
    
    for m in metrics:
        agg.target_species_found += m.target_species_found
        agg.target_species_missed += m.target_species_missed
        agg.false_positive_hotspots += m.false_positive_hotspots
    
    return agg


def load_observer_ids(file: str, start_idx: int = 0, n: int | None = None) -> list[str]:
    """
    Load observer IDs from a file.
    
    The file must be a CSV with a column called 'observer_id' (other columns don't matter).
    If given, start_idx and n are used to slice the file so that only the n ids
    starting at start_idx are returned.
    
    Parameters:
    file (str): Path to the CSV file.
    start_idx (int): Starting index for slicing.
    n (int | None): Number of IDs to return.
    
    Returns:
    list[str]: List of observer IDs.
    """
    with open(file, 'r') as f:
        reader = csv.DictReader(f)
        observer_ids = [
            row['observer_id'] 
            for row in islice(reader, start_idx, start_idx + n if n else None)
        ]
    return observer_ids