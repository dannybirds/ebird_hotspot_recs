import argparse
import logging
from datetime import datetime
import sys

from data_handling import get_historical_species_seen, get_species_seen, parse_life_list_csv

logger = logging.getLogger(__name__)

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Not a valid date: '{s}'.")
        return datetime.today()

def main():
    parser = argparse.ArgumentParser(description="Main for testing things right now.")
    parser.add_argument('--date', type=valid_date, help='Target date as yyyy-mm-dd')
    parser.add_argument('--location', type=str, help='EBird location ID')
    parser.add_argument('--life_list', type=str, help='CSV file path to life list')
    args = parser.parse_args()

    # Configure logging to print everything to stdout
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler(sys.stdout)])

    historical_data = get_historical_species_seen(args.location, args.date, num_years=3, day_window=2)
    life_list = parse_life_list_csv(args.life_list)

    lifers = {sp: locs for sp, locs in historical_data.items() if sp not in life_list}
    print(lifers)

if __name__ == "__main__":
    main()