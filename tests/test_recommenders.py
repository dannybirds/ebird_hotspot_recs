import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from recommenders import AnyHistoricalSightingRecommender, Recommendation, sightings_to_recommendations
from data_handling import Species

class TestRecommenders(unittest.TestCase):
    @patch('recommenders.get_historical_species_seen_in_window')
    def test_any_historical_sighting_recommender(self, mock_get_historical_species_seen_in_window: MagicMock):
        location = "Test Location"
        target_date = datetime(2023, 10, 1)

        a = Species("Species A", "A a", "aaa")
        b = Species("Species B", "B b", "bbb")
        c = Species("Species C", "C c", "ccc")
        life_list = {a.species_code: datetime(2022, 5, 1)}
        mock_historical_sightings = {
            b: ["Location 1", "Location 2"],
            c: ["Location 1"],
            a: ["Location 3"]
        }
        mock_get_historical_species_seen_in_window.return_value = mock_historical_sightings

        recommender = AnyHistoricalSightingRecommender(historical_years=3, day_window=1)
        recommendations = recommender.recommend(location, target_date, life_list)

        expected_recommendations = [
            Recommendation(location="Location 1", score=2, species=[b, c]),
            Recommendation(location="Location 2", score=1, species=[b])
        ]

        self.assertCountEqual(recommendations, expected_recommendations)

    def test_sightings_to_recommendations(self):
        a = Species("Species A", "A a", "aaa")
        b = Species("Species B", "B b", "bbb")
        c = Species("Species C", "C c", "ccc")
        
        sightings = {
            a: {"Location 1", "Location 2"},
            b: {"Location 1"},
            c: {"Location 3"}
        }

        expected_recommendations = [
            Recommendation(location="Location 1", score=2, species=[a, b]),
            Recommendation(location="Location 2", score=1, species=[a]),
            Recommendation(location="Location 3", score=1, species=[c])
        ]

        recommendations = sightings_to_recommendations(sightings)
        self.assertCountEqual(recommendations, expected_recommendations)


if __name__ == '__main__':
    unittest.main()