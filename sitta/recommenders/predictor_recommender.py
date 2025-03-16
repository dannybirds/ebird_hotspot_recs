from datetime import datetime
from sitta.data.ebird_api import EBirdAPIDataProvider
from sitta.recommenders.base import HistoricalDayWindowCandidateSpeciesRetriever, HotspotRecommender
from sitta.common.base import LifeList, Recommendation, Species, TargetArea, TargetAreaType
from sitta.predictors.base import BasePredictor


class PredictorRecommender(HotspotRecommender):
    """
    Abstract base class for hotspot recommendation systems.
    
    Implementations should provide a recommend method that returns a
    list of recommendations based on a location, date, and life list.
    """
    
    def __init__(self, predictor: BasePredictor, provider: EBirdAPIDataProvider | None = None):
        """
        Initialize the recommender with a predictor.
        
        Parameters:
        predictor: The predictor to use for generating recommendations.
        """
        self.predictor = predictor
        provider = provider or EBirdAPIDataProvider()
        self.provider = provider
        self.retriever = HistoricalDayWindowCandidateSpeciesRetriever(
            provider,
            num_years=10,
            day_window=7
        )

    def recommend(self, target_area: TargetArea, target_date: datetime, species: list[Species] | list[str]) -> list[Recommendation]:
        if target_area.area_type == TargetAreaType.LAT_LONG or target_area.area_id is None:
            raise NotImplementedError("Lat long targeting not yet implemented.")
        target_species_codes = {s.species_code if isinstance(s, Species) else s for s in species}

        recs: list[Recommendation] = []
        hotspots = self.provider.get_hotspots_in_area(target_area)
        for hotspot in hotspots:
            species_probs = {s: self.predictor.predict(
                target_area.area_id,
                target_date,
                s
            ) for s in target_species_codes}
            recs.append(Recommendation(
                locality_id=hotspot,
                score=sum(species_probs.values()),
                species=[Species(common_name='TODO', species_code=s, scientific_name='TODO') for s, p in species_probs.items() if p > 0]
            ))
        return sorted(recs, key=lambda r: r.score, reverse=True)
    

    def recommend_from_life_list(self, target_area: TargetArea, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
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
        