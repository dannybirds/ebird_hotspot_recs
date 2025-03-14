"""
Utilities for data handling.
"""

import calendar
from datetime import datetime, timedelta
import csv

from sitta.common.base import LifeList

def get_date_window(d: datetime, w: int) -> list[datetime]:
    """
    Get a list of datetimes within a window around a given datetime.

    Parameters:
    d (datetime): The central datetime.
    w (int): The window size in days.

    Returns:
    list[datetime]: A list of datetimes within the window size around the given datetime.
    """
    if w < 0:
        raise ValueError(f"Window size w must be non-negative, got {w=}")
    return [d + timedelta(days=i) for i in range(-w, w + 1)]

def get_annual_date_window(target_date: datetime, w: int, years: int) -> list[datetime]:
    """
    Returns a list of datetimes within a window around a given datetime for the specified number of past years.
    """
    dates = [datetime(target_date.year - y, target_date.month, target_date.day) for y in range(0, years)]
    return sorted([d + timedelta(days=i) for i in range(-w, w + 1) for d in dates])


def get_all_dates_in_calendar_month_for_previous_years(d: datetime, num_years: int) -> list[datetime]:
    """
    Get a list of all dates in the calendar month of a given datetime for the previous num_years years.

    Parameters:
    d (datetime): The datetime for which to get all dates in the calendar month.
    num_years (int): The number of years to go back.
    
    Returns:
    list[datetime]: A list of all dates in the calendar month for the previous num_years years.
    """
    dates: list[datetime] = []
    for year_delta in range(1, num_years + 1):
        y = d.year - year_delta
        _, n_days = calendar.monthrange(y, d.month)
        dates.extend([datetime(y, d.month, day) for day in range(1, n_days+1)])
    return dates


def parse_life_list_csv(sci_name_to_code: dict[str,str], life_list_csv_path: str) -> LifeList:
    """
    Parse a life list CSV file and return a dictionary of species codes and the date they were first seen.

    Parameters:
    life_list_csv_path (str): The path to the life list CSV file.

    Returns:
    dict[str, datetime]: A dictionary of species code and the date they were first seen.
    """
    species_dates: LifeList = dict()
    with open(life_list_csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = sci_name_to_code[row['Scientific Name']]
            species_dates[s] = datetime.strptime(row['Date'], "%d %b %Y")
    return species_dates