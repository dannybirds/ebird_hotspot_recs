"""
Heuristic-based recommender implementations.
"""

from datetime import datetime

from sitta.data.providers import EBirdDataProvider
from sitta.data.ebird_api import EBirdAPIDataProvider
from sitta.common.base import LifeList, Recommendation
from sitta.recommenders.base import HotspotRecommender, sightings_to_recommendations


class DayWindowHistoricalSightingRecommender(HotspotRecommender):
    """
    Recommender that uses historical sightings from specific days in previous years.
    
    This recommender looks at the same date (+/- a window) in previous years 
    to find species that were recorded at the location.
    """
    
    def __init__(self, historical_years: int=3, day_window: int=1, provider: EBirdDataProvider|None=None):
        """
        Initialize the recommender.
        
        Parameters:
        historical_years (int): Number of previous years to look at.
        day_window (int): Number of days before and after the target date to include.
        """
        self.historical_years = historical_years
        self.day_window = day_window
        provider = provider or EBirdAPIDataProvider()
        self.provider = provider 

    def recommend(self, location: str, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        """
        Generate recommendations based on historical sightings.
        
        Parameters:
        location (str): The eBird location ID.
        target_date (datetime): The target date.
        life_list (LifeList): The user's life list.
        
        Returns:
        list[Recommendation]: List of recommendations.
        """
        # Read historical data for the target date
        historical_sightings = self.provider.get_historical_species_seen_in_window(
            location,
            target_date,
            num_years=self.historical_years,
            day_window=self.day_window
        )
        
        # Filter to unseen species
        historical_sightings = {k: v for k, v in historical_sightings.items() if k.species_code not in life_list}
        
        return sightings_to_recommendations(historical_sightings)
    

class CalendarMonthHistoricalSightingRecommender(HotspotRecommender):
    """
    Recommender that uses historical sightings from the same calendar month in previous years.
    
    This recommender looks at the same month in previous years to find 
    species that were recorded at the location, providing broader historical context.
    """
    
    def __init__(self, historical_years: int=3):
        """
        Initialize the recommender.
        
        Parameters:
        historical_years (int): Number of previous years to look at.
        """
        self.historical_years = historical_years
        self.provider = EBirdAPIDataProvider()

    def recommend(self, location: str, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        """
        Generate recommendations based on historical month sightings.
        
        Parameters:
        location (str): The eBird location ID.
        target_date (datetime): The target date.
        life_list (LifeList): The user's life list.
        
        Returns:
        list[Recommendation]: List of recommendations.
        """
        # Read historical data for the target month
        historical_sightings = self.provider.get_historical_species_seen_in_calendar_month(
            location,
            target_date,
            num_years=self.historical_years
        )
        
        # Filter to unseen species
        historical_sightings = {k: v for k, v in historical_sightings.items() if k.species_code not in life_list}
        
        return sightings_to_recommendations(historical_sightings)