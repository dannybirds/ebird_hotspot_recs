import unittest
from datetime import datetime
from unittest.mock import patch
from recommenders import AnyHistoricalSightingRecommender, Recommendation
from data_handling import Species

class TestAnyHistoricalSightingRecommender(unittest.TestCase):
    @patch('recommenders.get_historical_species_seen')
    def test_recommend(self, mock_get_historical_species_seen):
        # Mock data
        location = "Test Location"
        target_date = datetime(2023, 10, 1)

        a = ("Species A", "A a", "aaa")
        b = ("Species B", "B b", "bbb")
        c = ("Species C", "C c", "ccc")
        life_list = {a: datetime(2022, 5, 1)}
        mock_historical_sightings = {
            b: ["Location 1", "Location 2"],
            c: ["Location 1"],
            a: ["Location 3"]
        }
        mock_get_historical_species_seen.return_value = mock_historical_sightings

        # Instantiate recommender
        recommender = AnyHistoricalSightingRecommender(historical_years=3, day_window=1)

        # Call recommend method
        recommendations = recommender.recommend(location, target_date, life_list)

        # Expected recommendations
        expected_recommendations = [
            Recommendation(location="Location 1", score=2, species={b, c}),
            Recommendation(location="Location 2", score=1, species={b})
        ]

        # Assertions
        self.assertEqual(len(recommendations), len(expected_recommendations))
        for rec, expected_rec in zip(recommendations, expected_recommendations):
            self.assertEqual(rec.location, expected_rec.location)
            self.assertEqual(rec.score, expected_rec.score)
            self.assertEqual(rec.species, expected_rec.species)

if __name__ == '__main__':
    unittest.main()