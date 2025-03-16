"""
Common data models and types used throughout the Sitta package.
"""

from enum import Enum
import logging

from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Species:
    """
    Represents a bird species with its common name, species code, and scientific name.
    """
    common_name: str
    species_code: str
    scientific_name: str


# Type aliases for improved code readability
type LifeList = dict[str, datetime]
type Sightings = dict[Species, set[str]]


class TargetAreaType(Enum):
    """
    Enum representing different types of areas that can be targeted for recommendations.
    """
    COUNTRY = "country"
    STATE = "state"
    COUNTY = "county"
    LOCALITY = "locality"
    LAT_LONG = "lat_long"

@dataclass
class TargetArea:
    """
    Represents a target area for birding recommendations.
    
    Attributes:
        area_type (TargetAreaType): The type of area (e.g., country, state).
        area_id (str): The identifier for the area.
        latitude (float): Latitude of the area.
        longitude (float): Longitude of the area.
    """
    area_type: TargetAreaType
    area_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    def __post_init__(self):
        if self.area_type == TargetAreaType.LAT_LONG and (self.latitude is None or self.longitude is None):
            raise ValueError("Latitude and longitude must be provided for LAT_LONG type in TargetArea.")
        if self.area_type != TargetAreaType.LAT_LONG and self.area_id is None:
            raise ValueError("Area ID must be provided for non-LAT_LONG types in TargetArea.")

@dataclass(frozen=True)
class Recommendation:
    """
    Represents a recommendation for a birding location with associated species.
    
    score should be interpretable as the expected number of species from the list that can be seen at the location.
    """
    locality_id: str
    score: float
    species: list[Species]

    def __eq__(self, value: object) -> bool:
        if type(value) is not Recommendation:
            return False
        return self.locality_id == value.locality_id and self.score == value.score and set(self.species) == set(value.species)


@dataclass
class EndToEndEvalDatapoint:
    """
    Datapoint for end-to-end evaluation of recommender systems.
    """
    target_location: str
    target_date: datetime
    life_list: LifeList
    ground_truth: list[Recommendation]
    observer_id: str = "unknown"


def to_json_default(o: Any) -> Any:
    """
    Custom JSON serializer for Sitta types.
    
    Parameters:
    o (Any): Object to serialize
    
    Returns:
    Any: JSON-serializable representation
    """
    if isinstance(o, datetime):
        return {'__datetime__': True, 'value': o.isoformat()}
    elif isinstance(o, Recommendation):
        d = o.__dict__.copy()
        d['__recommendation__'] = True
        return d
    elif isinstance(o, Species):
        d = o.__dict__.copy()
        d['__species__'] = True
        return d
    else:
        return o.__dict__
    

def from_json_object_hook(d: dict[str, Any]) -> Any:
    """
    Custom JSON deserializer for Sitta types.
    
    Parameters:
    d (dict): Dictionary to deserialize
    
    Returns:
    Any: Deserialized object
    """
    if '__datetime__' in d:
        return datetime.fromisoformat(d['value'])
    if '__recommendation__' in d:
        d.pop('__recommendation__')
        return Recommendation(**d)
    if '__species__' in d:
        d.pop('__species__')
        return Species(**d)
    return d


def valid_date(s: str) -> datetime:
    """
    Parse a date string in YYYY-MM-DD format.

    Parameters:
    s (str): Date string.

    Returns:
    datetime: Parsed date.
    """
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        logger.warning(f"Not a valid date: '{s}'.")
        return datetime.today()