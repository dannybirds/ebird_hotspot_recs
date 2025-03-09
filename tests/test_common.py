import json
from typing import Any
import unittest
from datetime import datetime
from sitta.common.base import Recommendation, Species, from_json_object_hook, to_json_default, EndToEndEvalDatapoint

class TestCommon(unittest.TestCase):
    def test_datetime_serialization(self):
        dt = datetime(2023, 10, 5, 15, 30, 45)
        expected: dict[str, Any] = {'__datetime__': True, 'value': '2023-10-05T15:30:45'}
        self.assertEqual(to_json_default(dt), expected)
        # And test the roundtrip
        rt = from_json_object_hook(expected)
        self.assertEqual(rt, dt)

    def test_end_to_end_eval_datapoint_json_roundtrip(self):
        s1 = Species(common_name='Fake Species 1', species_code='faksp1', scientific_name='Lorem Ipsum')
        s2 = Species(common_name='Fake Species 2', species_code='faksp2', scientific_name='Dolor Sit')
        datapoint = EndToEndEvalDatapoint(
            target_location='US-NY-001',
            target_date=datetime(2023, 10, 5, 15, 30, 45),
            life_list={s1.species_code: datetime(2023, 10, 5, 5, 30, 45)},
            ground_truth=[Recommendation(location='L123456', score=1.0, species=[s2])]
        )
        json_str = json.dumps(datapoint, default=to_json_default)
        rt = EndToEndEvalDatapoint(**json.loads(json_str, object_hook=from_json_object_hook))
        self.assertEqual(rt, datapoint)

if __name__ == '__main__':
    unittest.main()