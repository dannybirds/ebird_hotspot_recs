import json
from typing import Any
import unittest
from datetime import datetime
from test_utils import CARDINAL, create_test_life_list, create_test_recommendations
from sitta.common.base import from_json_object_hook, to_json_default, EndToEndEvalDatapoint

class TestCommon(unittest.TestCase):
    def test_datetime_serialization(self):
        dt = datetime(2023, 10, 5, 15, 30, 45)
        expected: dict[str, Any] = {'__datetime__': True, 'value': '2023-10-05T15:30:45'}
        self.assertEqual(to_json_default(dt), expected)
        # And test the roundtrip
        rt = from_json_object_hook(expected)
        self.assertEqual(rt, dt)

    def test_end_to_end_eval_datapoint_json_roundtrip(self):
        life_list = create_test_life_list([CARDINAL])
        ground_truth = create_test_recommendations(
            species_per_location=1, 
            location_count=1, 
            base_location_id="L"
        )
        
        # Create a test datapoint
        datapoint = EndToEndEvalDatapoint(
            target_location='US-NY-001',
            target_date=datetime(2023, 10, 5, 15, 30, 45),
            life_list=life_list,
            ground_truth=ground_truth
        )
        
        # Convert to JSON and back
        json_str = json.dumps(datapoint, default=to_json_default)
        rt = EndToEndEvalDatapoint(**json.loads(json_str, object_hook=from_json_object_hook))
        
        # Verify equality
        self.assertEqual(rt, datapoint)

if __name__ == '__main__':
    unittest.main()