import unittest

from test_utils import CARDINAL, create_test_recommendations
from sitta.common.base import Species
from sitta.recommenders.base import Recommendation
from sitta.evaluation.metrics import evaluate

class TestEvaluate(unittest.TestCase):

    def test_evaluate_exact_match(self):
        # Use the utility to create identical test recommendations for recs and ground truth
        recs = create_test_recommendations(species_per_location=1, location_count=2)
        ground_truth = create_test_recommendations(species_per_location=1, location_count=2)
        
        metrics = evaluate(recs, ground_truth)
        # 1 species at each of 2 locations = 2 species total
        self.assertEqual(metrics.target_species_found, 2.0)
        self.assertEqual(metrics.target_species_missed, 0)
        self.assertEqual(metrics.false_positive_hotspots, 0)

    def test_evaluate_one_mismatch(self):
        recs = [
            Recommendation(location="loc1", score=1.0, species=[CARDINAL]),
            Recommendation(location="loc3", score=3.0, species=[CARDINAL])
        ]
        
        ground_truth = [
            Recommendation(location="loc1", score=1.0, species=[CARDINAL]),
            Recommendation(location="loc2", score=2.0, species=[CARDINAL])
        ]
        
        metrics = evaluate(recs, ground_truth)
        self.assertEqual(metrics.target_species_found, 1.0)
        self.assertEqual(metrics.target_species_missed, 2.0)
        self.assertEqual(metrics.false_positive_hotspots, 1)

    def test_evaluate_no_matches(self):
        recs = [
            Recommendation(location="loc3", score=3.0, species=[CARDINAL]),
            Recommendation(location="loc4", score=4.0, species=[CARDINAL])
        ]
        
        ground_truth = [
            Recommendation(location="loc1", score=1.0, species=[CARDINAL]),
            Recommendation(location="loc2", score=2.0, species=[CARDINAL])
        ]
        
        metrics = evaluate(recs, ground_truth)
        self.assertEqual(metrics.target_species_found, 0)
        self.assertEqual(metrics.target_species_missed, 3.0)
        self.assertEqual(metrics.false_positive_hotspots, 2)

    def test_evaluate_empty_recs(self):
        recs = []
        ground_truth = [
            Recommendation(location="loc1", score=1.0, species=[CARDINAL]),
            Recommendation(location="loc2", score=2.0, species=[CARDINAL])
        ]
        
        metrics = evaluate(recs, ground_truth)
        self.assertEqual(metrics.target_species_found, 0)
        self.assertEqual(metrics.target_species_missed, 3.0)
        self.assertEqual(metrics.false_positive_hotspots, 0)

    def test_evaluate_empty_ground_truth(self):
        recs = [
            Recommendation(location="loc1", score=1.0, species=[CARDINAL]),
            Recommendation(location="loc2", score=2.0, species=[CARDINAL])
        ]
        ground_truth: list[Recommendation] = []
        
        metrics = evaluate(recs, ground_truth)
        self.assertEqual(metrics.target_species_found, 0)
        self.assertEqual(metrics.target_species_missed, 0)
        self.assertEqual(metrics.false_positive_hotspots, 2)
        
if __name__ == '__main__':
    unittest.main()