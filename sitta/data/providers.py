"""
Data providers for accessing eBird data from different sources.

Provides a unified interface for retrieving eBird data from either the eBird API or a local DB.
"""

from abc import ABC, abstractmethod
import functools
from datetime import datetime

import pandas as pd

from sitta.data.data_handling import get_all_dates_in_calendar_month_for_previous_years, get_annual_date_window, get_date_window
from sitta.common.base import Sightings


class EBirdDataProvider(ABC):
    """
    Abstract base class for eBird data providers.
    """

    def make_sightings_dataframe(self, location_id: str, dates: list[datetime]) -> pd.DataFrame:
        df = pd.DataFrame()
        for d in dates:
            species = [k for k in self.get_species_seen(location_id, d).keys()]
            s_df = pd.DataFrame({s.species_code: True for s in species}, index=[d])
            df = pd.concat([df, s_df], axis=0)
        df.fillna(False, inplace=True) # pyright: ignore[reportUnknownMemberType]
        df.infer_objects()
        df = self.set_sightings_dataframe_names(df)
        return df
    

    def make_historical_sightings_dataframe_for_location(self, location_id: str, target_date: datetime, num_years: int, day_window: int) -> pd.DataFrame:
        """
        Create a DataFrame of historical sightings for a given location and date.

        Parameters:
        location_id (str): The eBird location identifier.
        target_date (datetime): The target date around which to query in past years.
        num_years (int): The number of years to query, including the target year.
        day_window (int): The window size in days around target_date.month/target_date.day.

        Returns:
        pd.DataFrame: A DataFrame with species codes as columns and dates as indices.
        """
        dates = get_annual_date_window(target_date, day_window, num_years)
        df = self.make_sightings_dataframe(location_id, dates)
        return df

    def set_sightings_dataframe_names(self, df: pd.DataFrame) -> pd.DataFrame:
        df.index.name = 'date' # pyright: ignore[reportUnknownMemberType]
        df.columns.name = 'species_code'
        return df
    
    @abstractmethod
    @functools.cache
    def sci_name_to_code_map(self) -> dict[str, str]:
        """
        Get a dictionary mapping scientific names to species codes.

        The result is cached, so this function can be called many times but will only load the data once.

        Returns:
        dict[str, str]: A dictionary mapping scientific names to species codes.
        """
        pass
    
    @abstractmethod
    def get_species_seen_on_dates(self, location_id: str, target_dates: list[datetime]) -> Sightings:
        """
        Get species observed in an eBird location on specific dates.
        
        Parameters:
        location_id (str): The eBird location identifier.
        target_dates (list[datetime]): The list of dates for the query.
        
        Returns:
        Sightings: A dictionary of species observed and the locations where they were seen.
        """
        pass

    def get_species_seen(self, location_id: str, target_date: datetime, window: int = 0) -> Sightings:
        """
        Get species observed in an eBird location within a window of days around a target date.
        
        Parameters:
        location_id (str): The eBird location identifier.
        date (datetime): The date for the query.
        window (int): The window size in days around the given date.
        
        Returns:
        Sightings: A dictionary of species observed and the locations where they were seen.
        """
        dates = get_date_window(target_date, window)
        return self.get_species_seen_on_dates(location_id, dates)


    def get_historical_species_seen_in_window(
        self, location_id: str, target_date: datetime, num_years: int, day_window: int
    ) -> Sightings:
        """
        Get species observed in previous years within a window of days around the target date.
        
        Parameters:
        location_id (str): The eBird location identifier.
        target_date (datetime): The target date.
        num_years (int): Number of years to go back.
        day_window (int): Number of days before and after the target date to include.
        
        Returns:
        Sightings: A dictionary of species observed and the locations where they were seen.
        """
        dates = [datetime(target_date.year - y, target_date.month, target_date.day) for y in range(1, num_years + 1)]
        return self.get_species_seen_on_dates(location_id, dates)

    
    def get_historical_species_seen_in_calendar_month(
        self, location_id: str, target_date: datetime, num_years: int
    ) -> Sightings:
        """
        Get species observed in the same calendar month as the target date in previous years.
        
        Parameters:
        location_id (str): The eBird location identifier.
        target_date (datetime): The target date.
        num_years (int): Number of years to go back.
        
        Returns:
        Sightings: A dictionary of species observed and the locations where they were seen.
        """
        dates = get_all_dates_in_calendar_month_for_previous_years(target_date, num_years)
        return self.get_species_seen_on_dates(location_id, dates)

