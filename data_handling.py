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

def get_species_seen(location_id: str, date: datetime, window: int=0) -> list[Species]:
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
    return list(species_seen)
