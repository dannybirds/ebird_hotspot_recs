import argparse
import logging
from datetime import datetime
import sys

from data_handling import get_species_seen, parse_life_list_csv
from recommenders import AnyHistoricalSightingRecommender

logger = logging.getLogger(__name__)

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Not a valid date: '{s}'.")
        return datetime.today()

def main():
    parser = argparse.ArgumentParser(description="Main for testing things right now.")
    parser.add_argument('--date', type=valid_date, help='Target date as yyyy-mm-dd', default=datetime.today())
    parser.add_argument('--location', type=str, help='EBird location ID')
    parser.add_argument('--life_list', type=str, help='CSV file path to life list')
    args = parser.parse_args()

    # Configure logging to print everything to stdout
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler(sys.stdout)])

    # Read life list and filter to only include species seen before the target date.
    life_list = {k: v for k,v in parse_life_list_csv(args.life_list).items() if v < args.date}

    recommender = AnyHistoricalSightingRecommender(historical_years=5, day_window=7)
    recs = recommender.recommend(args.location, args.date, life_list)
    print("RECOMMENDATIONS\n")
    print(recs)
    print("\n")

    # get actual sightings on the target date, filtered to only include species not in the life list
    ground_truth_sightings = {k: v for k, v in get_species_seen(args.location, args.date, window=0).items() if k not in life_list}    
    print("GROUND TRUTH")
    print(ground_truth_sightings)
    print("\n")

if __name__ == "__main__":
    main()