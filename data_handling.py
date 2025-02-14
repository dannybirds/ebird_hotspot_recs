from datetime import datetime, timedelta
from dataclasses import dataclass
import functools

from ebird_api import get_observations_on_date

@dataclass(frozen=True)
class Species:
    common_name: str
    species_code: str
    scientific_name: str


def get_date_window(d: datetime, w: int) -> list[datetime]:
    """
    Get a list of datetimes within a window around a given datetime.

    Parameters:
    d (datetime): The central datetime.
    W (int): The window size in days.

    Returns:
    list[datetime]: A list of datetimes within the window size around the given datetime.
    """
    if w < 0:
        raise ValueError(f"Window size w must be non-negative, got {w=}")
    return [d + timedelta(days=i) for i in range(-w, w + 1)]

def get_species_seen(location_id: str, date: datetime, window: int=0) -> dict[Species, set[str]]:
    """
    Query species observed in an eBird location on +/- window days around the given date.

    Parameters:
    location_id (str): The eBird location identifier.
    date (datetime): The date for the query.
    window (int): The window size in days around the given date.

    Returns:
    dict[Species, set[str]]: A dictionary of species observed and the locations where they were seen.
    """
    dates = get_date_window(date, window)
    species_seen: dict[Species, set[str]] = dict()
    for d in dates:
        observations = get_observations_on_date(location_id, d)
        if observations:
            for species in observations:
                if species['locationPrivate']:
                    continue
                sp = Species(
                    common_name=species['comName'],
                    species_code=species['speciesCode'],
                    scientific_name=species['sciName']
                )
                if sp not in species_seen:
                    species_seen[sp] = set()
                species_seen[sp].add(species['locId'])
    return species_seen

def get_historical_species_seen(location_id: str, target_date: datetime, num_years: int, day_window: int) -> dict[Species, set[str]]:
    """
    Query species observed in an eBird location for day_window days around (target_date.month, target_date.day) for num_years before target_date.year.

    Parameters:
    location_id (str): The eBird location identifier.
    target_date (datetime): The target date around which to query in past years.
    num_years (int): The number of years before target_date.year to query.
    day_window (int): The window size in days around target_date.month/target_date.day.

    Returns:
    dict[Species, set[str]]: A dictionary of species observed and the locations where they were seen.
    """
    dates = [datetime(target_date.year - y, target_date.month, target_date.day) for y in range(1, num_years + 1)]
    species_seen: dict[Species, set[str]] = dict()
    for d in dates:
        yearly_species_seen = get_species_seen(location_id, d, day_window)
        for sp, locs in yearly_species_seen.items():
            if sp not in species_seen:
                species_seen[sp] = set()
            species_seen[sp].update(locs)
    return species_seen

@functools.cache
def sci_name_to_code_map() -> dict[str, str]:
    """
    Query the eBird taxonomy and return a dictionary mapping scientific names to species codes.

    The result is cached, so this function can be called many times but will only load the data once.

    Returns:
    dict[str, str]: A dictionary mapping scientific names to species codes.
    """
    from ebird_api import get_taxonomy
    taxonomy = get_taxonomy()
    return {species['sciName']: species['speciesCode'] for species in taxonomy}


def parse_life_list_csv(life_list_csv_path: str) -> dict[Species, datetime]:
    """
    Parse a life list CSV file and return a dictionary of species and the date they were first seen.

    Parameters:
    life_list_csv_path (str): The path to the life list CSV file.

    Returns:
    dict[Species, datetime]: A dictionary of species and the date they were first seen.
    """
    import csv
    species_dates: dict[Species, datetime] = dict()
    with open(life_list_csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sp = Species(
                common_name=row['Common Name'],
                species_code=sci_name_to_code_map()[row['Scientific Name']],
                scientific_name=row['Scientific Name']
            )
            species_dates[sp] = datetime.strptime(row['Date'], "%d %b %Y")
    return species_dates


    