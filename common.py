
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Species:
    common_name: str
    species_code: str
    scientific_name: str

type LifeList = dict[Species, datetime]
type Sightings = dict[Species, set[str]]

@dataclass(frozen=True)
class Recommendation:
    location: str
    score: float
    species: set[Species]

@dataclass
class EndToEndEvalDatapoint:
    target_location: str
    target_date: datetime
    life_list: LifeList
    ground_truth: list[Recommendation]