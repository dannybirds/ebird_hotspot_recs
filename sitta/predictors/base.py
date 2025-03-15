from abc import ABC, abstractmethod
from datetime import datetime

from sitta.common.base import Species


class BasePredictor(ABC):
    """
    Abstract base class for predictors that predict whether a species will be seen at a location on a target date.
    """
    
    @abstractmethod
    def predict(self, location_id: str, target_date: datetime, species: Species) -> float:
        """
        Returns the probability of a species being seen at a location.
        """
        pass