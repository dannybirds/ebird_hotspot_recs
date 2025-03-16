"""
Command-line interface for the Sitta package.
"""

import argparse
import asyncio
import json
import logging
import pprint
import sys
import random
from datetime import datetime

from tqdm import tqdm

from sitta.data.ebird_api import EBirdAPIDataProvider
from sitta.common.base import valid_date
from sitta.data.data_handling import parse_life_list_csv
from sitta.data.ebird_db import create_life_lists, fetch_all_gt_hotspots
from sitta.common.base import EndToEndEvalDatapoint, from_json_object_hook, to_json_default
from sitta.evaluation.metrics import (
    run_end_to_end_evals,
    aggregate_end_to_end_eval_metrics,
    evaluate,
    load_observer_ids
)
from sitta.recommenders.base import HotspotRecommender, sightings_to_recommendations
from sitta.recommenders.heuristic import (
    DayWindowHistoricalSightingRecommender,
    CalendarMonthHistoricalSightingRecommender,
)

logger = logging.getLogger(__name__)


def make_recommendation(args: argparse.Namespace) -> None:
    """
    Generate and evaluate recommendations for a given location, date, and life list.
    
    Parameters:
    args (argparse.Namespace): Command-line arguments.
    """

    provider = EBirdAPIDataProvider()
    sci_name_map = provider.sci_name_to_code_map()

    # Read life list and filter to only include species seen before the target date.
    life_list = {k: v for k, v in parse_life_list_csv(sci_name_map, args.life_list).items() if v < args.date}

    # Create and run recommender
    recommender = DayWindowHistoricalSightingRecommender(historical_years=5, day_window=7)
    recs = recommender.recommend(args.location, args.date, life_list)
    
    print("RECOMMENDATIONS\n")
    pprint.pp(recs)
    print("\n")

    # Get actual sightings on the target date, filtered to only include species not in the life list
    sightings = provider.get_species_seen(args.location, args.date, window=0)
    ground_truth_sightings = {
        k: v for k, v in sightings.items() 
        if k.species_code not in life_list
    }    
    
    print("GROUND TRUTH")
    pprint.pp(sightings_to_recommendations(ground_truth_sightings))
    print("\n")

    print("ERRORS")
    pprint.pp(evaluate(recs, sightings_to_recommendations(ground_truth_sightings)))

    # Create dataset and run end-to-end evaluation
    dataset = [
        EndToEndEvalDatapoint(
            args.location,
            args.date,
            life_list,
            sightings_to_recommendations(ground_truth_sightings)
        )
    ]
    
    agg_metrics = aggregate_end_to_end_eval_metrics(run_end_to_end_evals(recommender, dataset))

    print("AGGREGATE METRICS")
    pprint.pp(agg_metrics)


async def make_e2e_eval_data(args: argparse.Namespace) -> None:
    """
    Create end-to-end evaluation data.
    
    Parameters:
    args (argparse.Namespace): Command-line arguments.
    """
    observer_ids = load_observer_ids(args.eval_observer_ids, 0, 10) # 200)
    print(f"Loaded {len(observer_ids)} observer IDs.")
    
    life_lists = create_life_lists(observer_ids)
    print(f"Fetched {len(life_lists)} life lists.")
    
    all_datapoints: list[EndToEndEvalDatapoint] = []
    for observer_id, life_list in tqdm(life_lists.items()):
        datapoints = await fetch_all_gt_hotspots(observer_id, life_list, args.date)
        # one datapoint per observer ID
        if datapoints:
            all_datapoints.append(random.choice(datapoints))
    
    with open(args.eval_file, 'w') as f:
        json.dump(all_datapoints, f, default=to_json_default)


def run_e2e_eval(args: argparse.Namespace) -> None:
    """
    Run end-to-end evaluation.
    
    Parameters:
    args (argparse.Namespace): Command-line arguments.
    """
    with open(args.eval_file, 'r') as f:
        data_json = json.load(f, object_hook=from_json_object_hook)
    
    dataset = [EndToEndEvalDatapoint(**d) for d in data_json]
    print(f"Loaded {len(dataset)} datapoints.")
    
    recommenders: dict[str, HotspotRecommender] = {}
    recommenders['day_window'] = DayWindowHistoricalSightingRecommender(historical_years=5, day_window=7)
    recommenders['calendar_month'] = CalendarMonthHistoricalSightingRecommender(historical_years=5)
    
    # Run evaluation
    results = {n: aggregate_end_to_end_eval_metrics(run_end_to_end_evals(r, dataset, k=1)) for n, r in recommenders.items()}
    
    print("AGGREGATED RESULTS")
    pprint.pp(results)


def main():
    """
    Main entry point for the command-line interface.
    """
    parser = argparse.ArgumentParser(description="Sitta - Bird lifer recommendation system")
    parser.add_argument(
        '--mode',
        type=str,
        help='Mode to run',
        choices=['recommend', 'make_e2e_eval_data', 'run_e2e_eval'],
        default='recommend'
    )
    parser.add_argument(
        '--date',
        type=valid_date,
        help='Target date as yyyy-mm-dd',
        default=datetime.today()
    )
    parser.add_argument(
        '--location',
        type=str,
        help='EBird location ID'
    )
    parser.add_argument(
        '--life_list',
        type=str,
        help='CSV file path to life list'
    )
    parser.add_argument(
        '--eval_observer_ids',
        type=str,
        help='path to observer IDs to use for make_e2e_eval_data'
    )
    parser.add_argument(
        '--eval_file',
        type=str,
        help='file to read or write e2e eval data from or to'
    )
    args = parser.parse_args()

    # Configure logging to print everything to stdout
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Run selected mode
    match args.mode:
        case 'recommend':
            make_recommendation(args)
        case 'make_e2e_eval_data':
            asyncio.run(make_e2e_eval_data(args))
        case 'run_e2e_eval':
            run_e2e_eval(args)
        case _:
            logger.error(f"Unknown mode: {args.mode}")
            sys.exit(1)


if __name__ == "__main__":
    main()