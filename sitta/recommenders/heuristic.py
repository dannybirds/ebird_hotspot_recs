"""
Heuristic-based recommender implementations.
"""

from datetime import datetime

from sitta.data.providers import EBirdDataProvider
from sitta.data.ebird_api import EBirdAPIDataProvider
from sitta.common.base import LifeList, Recommendation, Sightings, Species, TargetArea, TargetAreaType
from sitta.recommenders.base import CandidateSpeciesRetriever, HistoricalDayWindowCandidateSpeciesRetriever, HotspotRecommender, sightings_to_recommendations


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
        self.retriever = HistoricalDayWindowCandidateSpeciesRetriever(
            provider,
            num_years=historical_years,
            day_window=day_window
        )

    def recommend(self, target_area: TargetArea, target_date: datetime, species: list[Species] | list[str]) -> list[Recommendation]:
        historical_sightings = self.provider.get_historical_species_seen_in_window(
            target_area,
            target_date,
            num_years=self.historical_years,
            day_window=self.day_window
        )
        target_species_codes = {s.species_code if isinstance(s, Species) else s for s in species}
        # Filter to targeted species
        historical_sightings = {k: v for k, v in historical_sightings.items() if k.species_code in target_species_codes}
        return sightings_to_recommendations(historical_sightings)

    def recommend_from_life_list(self, target_area: TargetArea, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        """
        Generate recommendations for unseen species given a life list.
        
        Parameters:
        location (str): The eBird location ID.
        target_date (datetime): The target date.
        life_list (LifeList): The user's life list.
        
        Returns:
        list[Recommendation]: List of recommendations.
        """
        if target_area.area_type == TargetAreaType.LAT_LONG or target_area.area_id is None:
            raise NotImplementedError("Lat long targeting not yet implemented.")
        # Get likely species for the target area and date
        historical_sightings = self.retriever.get_candidate_species(
            target_area,
            target_date
        )
        
        # Filter to unseen species
        target_species = [k for k in historical_sightings.keys() if k.species_code not in life_list]
        return self.recommend(target_area, target_date, target_species)
    

class HistoricalCalendarMonthSpeciesRetriever(CandidateSpeciesRetriever):
    """
    Retriever for species observed in target area during the same calendar month in previous years.
    
    Parameters:
    provider (EBirdDataProvider): The data provider to use for retrieving species.
    num_years (int): The number of years to look back.
    """

    def __init__(self, provider: EBirdDataProvider, num_years: int) -> None:
        super().__init__()
        self.provider = provider
        self.num_years = num_years
    
    
    def get_candidate_species(self, target_area: TargetArea, target_date: datetime) -> Sightings:
        """
        Retrieve historically observed species for a given location and date.
        
        Parameters:
        target_area (TargetArea): The target area to retrieve historically observed species for.
        target_date (datetime): The date to retrieve historically observed species for.
        
        Returns:
        list[Species]: List of historically observed species.
        """
        s = self.provider.get_historical_species_seen_in_calendar_month(
            target_area,
            target_date,
            num_years=self.num_years,
        )
        return s


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
        self.retriever = HistoricalCalendarMonthSpeciesRetriever(
            self.provider,
            num_years=historical_years
        )

    def recommend(self, target_area: TargetArea, target_date: datetime, species: list[Species] | list[str]) -> list[Recommendation]:
        historical_sightings = self.provider.get_historical_species_seen_in_calendar_month(
            target_area,
            target_date,
            num_years=self.historical_years,
        )
        target_species_codes = {s.species_code if isinstance(s, Species) else s for s in species}
        # Filter to targeted species
        historical_sightings = {k: v for k, v in historical_sightings.items() if k.species_code in target_species_codes}
        return sightings_to_recommendations(historical_sightings)

    def recommend_from_life_list(self, target_area: TargetArea, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        """
        Generate recommendations based on historical month sightings.
        
        Parameters:
        location (str): The eBird location ID.
        target_date (datetime): The target date.
        life_list (LifeList): The user's life list.
        
        Returns:
        list[Recommendation]: List of recommendations.
        """
        if target_area.area_type == TargetAreaType.LAT_LONG or target_area.area_id is None:
            raise NotImplementedError("Lat long targeting not yet implemented.")
        # Get likely species for the target area and date
        historical_sightings = self.retriever.get_candidate_species(
            target_area,
            target_date
        )
        
        # Filter to unseen species
        target_species = [k for k in historical_sightings.keys() if k.species_code not in life_list]
        return self.recommend(target_area, target_date, target_species)