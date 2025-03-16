"""
Base recommender interfaces and common utility functions.
"""

from abc import ABC, abstractmethod
from datetime import datetime

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
    def recommend(self, target_area: TargetArea, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        """
        Generate recommendations for a given location, target date, and life list.
        
        Parameters:
        location (str): The eBird location ID to generate recommendations for.
        target_date (datetime): The date to generate recommendations for.
        life_list (LifeList): The user's life list of species already seen.
        
        Returns:
        list[Recommendation]: List of recommendations sorted by score.
        """
        pass