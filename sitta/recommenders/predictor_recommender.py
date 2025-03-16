from datetime import datetime
from sitta.common.base import LifeList, Recommendation, TargetArea
from sitta.predictors.base import BasePredictor


class PredictorRecommender():
    """
    Abstract base class for hotspot recommendation systems.
    
    Implementations should provide a recommend method that returns a
    list of recommendations based on a location, date, and life list.
    """
    
    def __init__(self, predictor: BasePredictor):
        """
        Initialize the recommender with a predictor.
        
        Parameters:
        predictor: The predictor to use for generating recommendations.
        """
        self.predictor = predictor

    def recommend(self, target_area: TargetArea, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        l: list[Recommendation] = []
        return l
        