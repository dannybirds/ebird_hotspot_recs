"""
Base recommender interfaces and common utility functions.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from sitta.data.providers import EBirdDataProvider
from sitta.common.base import LifeList, Species, Recommendation, Sightings, TargetArea


def sightings_to_recommendations(sightings: Sightings) -> list[Recommendation]:
    """
    Convert a dictionary of species to locations to a list of recommendations.
    The score is the number of species seen at the location.
    
    Useful for turning ground truth sightings into recommendations that
    have the correct number of species seen.
    
    Parameters:
    sightings (Sightings): Dictionary mapping species to sets of location IDs.
    
    Returns:
    list[Recommendation]: Sorted list of recommendations by score (descending).
    """
    locs_to_species: dict[str, set[Species]] = dict()
    for species, locs in sightings.items():
        for loc in locs:
            if loc not in locs_to_species:
                locs_to_species[loc] = set()
            locs_to_species[loc].add(species)
    
    recs = [
        Recommendation(
            locality_id=loc,
            score=len(species),
            species=sorted(list(species), key=lambda s: s.common_name)
        ) for loc, species in locs_to_species.items()
    ]
    
    return sorted(recs, key=lambda r: r.score, reverse=True)


class HotspotRecommender(ABC):
    """
    Abstract base class for hotspot recommendation systems.
    
    Implementations should provide a recommend method that returns a
    list of recommendations based on a location, date, and life list.
    """
    
    @abstractmethod
    def recommend(self, target_area: TargetArea, target_date: datetime, species: list[Species] | list[str]) -> list[Recommendation]:
        """
        Generate hotspot recommendations for a target area, date, and species list.
        
        Parameters:
        target_area (TargetArea): The target area to generate recommendations for.
        target_date (datetime): The date to generate recommendations for.
        species (list[Species|str]): The list of species to consider for recommendations, can be Species objects or species codes.
        
        Returns:
        list[Recommendation]: List of recommendations sorted by score.
        """
        pass

    @abstractmethod
    def recommend_from_life_list(self, target_area: TargetArea, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        """
        Generate hotspot recommendations for a target area and date, that should included species not in the given life list.
        
        Parameters:
        target_area (TargetArea): The target area to generate recommendations for.
        target_date (datetime): The date to generate recommendations for.
        life_list (LifeList): The list of species to avoid.
        
        Returns:
        list[Recommendation]: List of recommendations sorted by score.
        """
        pass
    

class CandidateSpeciesRetriever(ABC):
    """
    Abstract base class for retrieving candidate species for target area and date.
    
    Implementations should provide a get_candidate_species method that returns a list of species
    that are likely to be seen in the given area on the given date. This is useful for finding
    unseen target species given a list of previously seen species.
    """
    
    @abstractmethod
    def get_candidate_species(self, target_area: TargetArea, target_date: datetime) -> Sightings:
        """
        Retrieve candidate species for a given location and date.
        
        Parameters:
        target_area (TargetArea): The target area to retrieve candidate species for.
        target_date (datetime): The date to retrieve candidate species for.
        
        Returns:
        list[Species]: List of candidate species.
        """
        pass

class HistoricalDayWindowCandidateSpeciesRetriever(CandidateSpeciesRetriever):
    """
    Retriever for species previosly observed in target area and around date.
    
    Parameters:
    provider (EBirdDataProvider): The data provider to use for retrieving species.
    num_years (int): The number of years to look back for historical sightings.
    day_window (int): The number of days around the target date (in previous years) to consider.
    """

    def __init__(self, provider: EBirdDataProvider, num_years: int, day_window: int) -> None:
        super().__init__()
        self.provider = provider
        self.num_years = num_years
        self.day_window = day_window
    
    
    def get_candidate_species(self, target_area: TargetArea, target_date: datetime) -> Sightings:
        """
        Retrieve historically observed species for a given location and date.
        
        Parameters:
        target_area (TargetArea): The target area to retrieve historically observed species for.
        target_date (datetime): The date to retrieve historically observed species for.
        
        Returns:
        list[Species]: List of historically observed species.
        """
        s = self.provider.get_historical_species_seen_in_window(
            target_area,
            target_date,
            num_years=self.num_years,
            day_window=self.day_window
        )
        return s