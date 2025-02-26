from abc import ABC, abstractmethod
from datetime import datetime

from data_handling import get_historical_species_seen_in_window
from common import LifeList, Species, Recommendation


def sightings_to_recommendations(sightings: dict[Species, set[str]]) -> list[Recommendation]:
    """
    Convert a dictionary of species to locations to a list of recommendations. The score is the number of species seen at the location.
    
    Useful for turning ground truth sightings into recommendations that have the correct number of species seen.
    """
    locs_to_species: dict[str, set[Species]] = dict()
    for species, locs in sightings.items():
        for loc in locs:
            if loc not in locs_to_species:
                locs_to_species[loc] = set()
            locs_to_species[loc].add(species)
    recs = [Recommendation(location=loc, score=len(species), species=list(species)) for loc, species in locs_to_species.items()]
    return sorted(recs, key=lambda r: r.score, reverse=True)

class HotspotRecommender(ABC):
    @abstractmethod
    def recommend(self, location: str, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        pass

class AnyHistoricalSightingRecommender(HotspotRecommender):
    def __init__(self, historical_years: int=3, day_window: int=1):
        self.historical_years = historical_years
        self.day_window = day_window

    def recommend(self, location: str, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        # read historical data for the target date
        historical_sightings = get_historical_species_seen_in_window(location, target_date, num_years=self.historical_years, day_window=self.day_window)
        # filter to unseen species
        historical_sightings = {k: v for k, v in historical_sightings.items() if k.species_code not in life_list}
        return sightings_to_recommendations(historical_sightings)
    