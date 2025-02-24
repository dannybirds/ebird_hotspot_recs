
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Species:
    common_name: str
    species_code: str
    scientific_name: str

type LifeList = dict[str, datetime]
type Sightings = dict[Species, set[str]]

@dataclass(frozen=True)
class Recommendation:
    location: str
    score: float
    species: list[Species]

@dataclass
class EndToEndEvalDatapoint:
    target_location: str
    target_date: datetime
    life_list: LifeList
    ground_truth: list[Recommendation]
    observer_id: str = "unknown"

def to_json_default(o: Any) -> Any:
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
    if '__datetime__' in d:
        return datetime.fromisoformat(d['value'])
    if '__recommendation__' in d:
        d.pop('__recommendation__')
        return Recommendation(**d)
    if '__species__' in d:
        d.pop('__species__')
        return Species(**d)
    return d