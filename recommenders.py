from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from data_handling import Species, get_historical_species_seen, get_species_seen

@dataclass(frozen=True)
class Recommendation:
    location: str
    score: float
    species: set[Species]

class HotspotRecommender(ABC):
    @abstractmethod
    def recommend(self, location: str, target_date: datetime, life_list: dict[Species, datetime]) -> list[Recommendation]:
        pass

class AnyHistoricalSightingRecommender(HotspotRecommender):
    def __init__(self, historical_years: int=3, day_window: int=1):
        self.historical_years = historical_years
        self.day_window = day_window

    def recommend(self, location: str, target_date: datetime, life_list: dict[Species, datetime]) -> list[Recommendation]:
        # read historical data for the target date
        historical_sightings = get_historical_species_seen(location, target_date, num_years=self.historical_years, day_window=self.day_window)
        # filter to unseen species
        historical_sightings = {k: v for k, v in historical_sightings.items() if k not in life_list}
        # invert to key by locations, and score by number of species
        locs_to_species: dict[str, set[Species]] = dict()
        for species, locs in historical_sightings.items():
            for loc in locs:
                if loc not in locs_to_species:
                    locs_to_species[loc] = set()
                locs_to_species[loc].add(species)
        recs = [Recommendation(location=loc, score=len(species), species=species) for loc, species in locs_to_species.items()]
        return sorted(recs, key=lambda r: r.score, reverse=True)
