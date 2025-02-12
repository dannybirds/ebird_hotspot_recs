from datetime import datetime, timedelta
from dataclasses import dataclass

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

def get_species_seen(location_id: str, date: datetime, window: int=0) -> set[Species]:
    """
    Query species observed in an eBird location on +/- window days around the given date.

    Parameters:
    location_id (str): The eBird location identifier.
    date (datetime): The date for the query.
    window (int): The window size in days around the given date.

    Returns:
    list[Species]: A list of species observed in the specified location and date range.
    """
    dates = get_date_window(date, window)
    species_seen: set[Species] = set()
    for d in dates:
        observations = get_observations_on_date(location_id, d)
        for species in observations:
            species_obj = Species(
                common_name=species['comName'],
                species_code=species['speciesCode'],
                scientific_name=species['sciName']
            )
            species_seen.add(species_obj)
    return species_seen

def get_historical_species_seen(location_id: str, target_date: datetime, num_years: int, day_window: int) -> set[Species]:
    """
    Query species observed in an eBird location for day_window days around (target_date.month, target_date.day) for num_years before target_date.year.

    Parameters:
    location_id (str): The eBird location identifier.
    target_date (datetime): The target date around which to query in past years.
    num_years (int): The number of years before target_date.year to query.
    day_window (int): The window size in days around target_date.month/target_date.day.

    Returns:
    list[Species]: A list of species observed.
    """
    species_seen: set[Species] = set()
    dates = [datetime(target_date.year - y, target_date.month, target_date.day) for y in range(1, num_years + 1)]
    for d in dates:
        species_seen.update(get_species_seen(location_id, d, day_window))
    return species_seen
