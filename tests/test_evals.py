import unittest
from sitta.data.data_handling import Species
from sitta.recommenders.base import Recommendation
from sitta.evaluation.metrics import evaluate

class TestEvaluate(unittest.TestCase):

    def test_evaluate_exact_match(self):
        a = Species("Species A", "A a", "aaa")
        recs = [Recommendation(location="loc1", score=1.0, species=[a]), Recommendation(location="loc2", score=2.0, species=[a])]
        ground_truth = [Recommendation(location="loc1", score=1.0, species=[a]), Recommendation(location="loc2", score=2.0, species=[a])]
        metrics = evaluate(recs, ground_truth)
        self.assertEqual(metrics.target_species_found, 3.0)
        self.assertEqual(metrics.target_species_missed, 0)
        self.assertEqual(metrics.false_positive_hotspots, 0)

    def test_evaluate_one_mismatch(self):
        a = Species("Species A", "A a", "aaa")
        recs = [Recommendation(location="loc1", score=1.0, species=[a]), Recommendation(location="loc3", score=3.0, species=[a])]
        ground_truth = [Recommendation(location="loc1", score=1.0, species=[a]), Recommendation(location="loc2", score=2.0, species=[a])]
        metrics = evaluate(recs, ground_truth)
        self.assertEqual(metrics.target_species_found, 1.0)
        self.assertEqual(metrics.target_species_missed, 2.0)
        self.assertEqual(metrics.false_positive_hotspots, 1)

    def test_evaluate_no_matches(self):
        a = Species("Species A", "A a", "aaa")
        recs = [Recommendation(location="loc3", score=3.0, species=[a]), Recommendation(location="loc4", score=4.0, species=[a])]
        ground_truth = [Recommendation(location="loc1", score=1.0, species=[a]), Recommendation(location="loc2", score=2.0, species=[a])]
        metrics = evaluate(recs, ground_truth)
        self.assertEqual(metrics.target_species_found, 0)
        self.assertEqual(metrics.target_species_missed, 3.0)
        self.assertEqual(metrics.false_positive_hotspots, 2)

    def test_evaluate_empty_recs(self):
        a = Species("Species A", "A a", "aaa")
        recs : list[Recommendation] = []
        ground_truth = [Recommendation(location="loc1", score=1.0, species=[a]), Recommendation(location="loc2", score=2.0, species=[a])]
        metrics = evaluate(recs, ground_truth)
        self.assertEqual(metrics.target_species_found, 0)
        self.assertEqual(metrics.target_species_missed, 3.0)
        self.assertEqual(metrics.false_positive_hotspots, 0)

    def test_evaluate_empty_ground_truth(self):
        a = Species("Species A", "A a", "aaa")
        recs = [Recommendation(location="loc1", score=1.0, species=[a]), Recommendation(location="loc2", score=2.0, species=[a])]
        ground_truth : list[Recommendation] = []
        metrics = evaluate(recs, ground_truth)
        self.assertEqual(metrics.target_species_found, 0)
        self.assertEqual(metrics.target_species_missed, 0)
        self.assertEqual(metrics.false_positive_hotspots, 2)
        
if __name__ == '__main__':
    unittest.main()