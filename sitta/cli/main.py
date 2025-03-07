import argparse
import json
import logging
from datetime import datetime
import pprint
import sys

from tqdm import tqdm

from data_handling import get_species_seen, parse_life_list_csv
from ebird_db import create_life_lists, fetch_all_gt_hotspots
from common import LifeList, from_json_object_hook, to_json_default
from evals import EndToEndEvalDatapoint, aggregate_end_to_end_eval_metrics, evaluate, load_observer_ids, run_end_to_end_evals
from recommenders import AnyHistoricalSightingRecommender, CalendarMonthHistoricalSightingRecommender, sightings_to_recommendations
import random

logger = logging.getLogger(__name__)

def valid_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Not a valid date: '{s}'.")
        return datetime.today()


def make_recommendation(args: argparse.Namespace) -> None:
    # Read life list and filter to only include species seen before the target date.
    life_list = {k: v for k,v in parse_life_list_csv(args.life_list).items() if v < args.date}

    recommender = AnyHistoricalSightingRecommender(historical_years=5, day_window=7)
    recs = recommender.recommend(args.location, args.date, life_list)
    print("RECOMMENDATIONS\n")
    pprint.pp(recs)
    print("\n")

    # get actual sightings on the target date, filtered to only include species not in the life list
    ground_truth_sightings = {k: v for k, v in get_species_seen(args.location, args.date, window=0).items() if k.species_code not in life_list}    
    print("GROUND TRUTH")
    pprint.pp(sightings_to_recommendations(ground_truth_sightings))
    print("\n")

    print("ERRORS")
    pprint.pp(evaluate(recs, sightings_to_recommendations(ground_truth_sightings)))

    dataset = [EndToEndEvalDatapoint(args.location, args.date, life_list, sightings_to_recommendations(ground_truth_sightings))]
    agg_metrics = aggregate_end_to_end_eval_metrics(run_end_to_end_evals(recommender, dataset))

    print("AGGREGATE METRICS")
    pprint.pp(agg_metrics)

def make_e2e_eval_data(args: argparse.Namespace) -> None:
    observer_ids = load_observer_ids(args.eval_observer_ids, 0, 200)
    print(f"Loaded {len(observer_ids)} observer IDs.")
    life_lists: dict[str, LifeList] = create_life_lists(observer_ids)
    print(f"Fetched {len(life_lists)} life lists.")
    all_datapoints: list[EndToEndEvalDatapoint] = []
    for observer_id, life_list in tqdm(life_lists.items()):
        datapoints = fetch_all_gt_hotspots(observer_id, life_list, args.date)
        if datapoints:
            all_datapoints.append(random.choice(datapoints))
    with open(args.eval_file, 'w') as f:
        json.dump(all_datapoints, f, default=to_json_default)


def run_e2e_eval(args: argparse.Namespace) -> None:
    with open(args.eval_file, 'r') as f:
        data_json = json.load(f, object_hook=from_json_object_hook)
    dataset = [EndToEndEvalDatapoint(**d) for d in data_json]
    print(f"Loaded {len(dataset)} datapoints.")
    # recommender = AnyHistoricalSightingRecommender(historical_years=5, day_window=7)
    recommender = CalendarMonthHistoricalSightingRecommender(historical_years=5)
    results = run_end_to_end_evals(recommender, dataset, k=1)
    print("RESULTS")
    pprint.pp(results)
    print("AGGREGATED RESULTS")
    pprint.pp(aggregate_end_to_end_eval_metrics(results))


def main():
    parser = argparse.ArgumentParser(description="Main for testing things right now.")
    parser.add_argument('--mode', type=str, help='Mode to run', choices=['recommend', 'make_e2e_eval_data', 'run_e2e_eval'], default='recommend')
    parser.add_argument('--date', type=valid_date, help='Target date as yyyy-mm-dd', default=datetime.today())
    parser.add_argument('--location', type=str, help='EBird location ID')
    parser.add_argument('--life_list', type=str, help='CSV file path to life list')
    parser.add_argument('--eval_observer_ids', type=str, help='path to observer IDs to use for make_e2e_eval_data')
    parser.add_argument('--eval_file', type=str, help='file to read or write e2e eval data from or to')
    args = parser.parse_args()

    # Configure logging to print everything to stdout
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler(sys.stdout)])

    match args.mode:
        case 'recommend':
            make_recommendation(args)
        case 'make_e2e_eval_data':
            make_e2e_eval_data(args)
        case 'run_e2e_eval':
            run_e2e_eval(args)
        case _:
            logger.error(f"Unknown mode: {args.mode}")
            sys.exit(1)


    

if __name__ == "__main__":
    main()