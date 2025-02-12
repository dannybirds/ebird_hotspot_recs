import argparse
import logging
from datetime import datetime
import sys

from data_handling import get_historical_species_seen, get_species_seen

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
    args = parser.parse_args()

    # Configure logging to print everything to stdout
    logging.basicConfig(level=logging.DEBUG, handlers=[logging.StreamHandler(sys.stdout)])

    if args.date:
        data = get_historical_species_seen(args.location, args.date, num_years=3, day_window=2)
        print(f"Observations around {args.date.strftime('%Y-%m-%d')}:")
        print(data)

if __name__ == "__main__":
    main()