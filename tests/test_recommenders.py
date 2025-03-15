import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
from sitta.data.ebird_api import EBirdAPIDataProvider
from sitta.recommenders.base import sightings_to_recommendations
from sitta.recommenders.heuristic import DayWindowHistoricalSightingRecommender, Recommendation, sightings_to_recommendations

from test_utils import BLUE_JAY, CARDINAL, ROBIN, create_test_sightings

class TestRecommenders(unittest.IsolatedAsyncioTestCase):
    @patch('sitta.recommenders.heuristic.EBirdAPIDataProvider.get_historical_species_seen_in_window')
    async def test_any_historical_sighting_recommender(self, mock_get_historical_species_seen_in_window: MagicMock):
        location = "Test Location"
        target_date = datetime(2023, 10, 1)

        # Use the life list with only one species
        life_list = {CARDINAL.species_code: datetime(2022, 5, 1)}
        
        # Create mock historical sightings with predefined species
        mock_historical_sightings = {
            BLUE_JAY: ["Location 1", "Location 2"],
            ROBIN: ["Location 1"],
            CARDINAL: ["Location 3"]
        }

        mock_get_historical_species_seen_in_window.return_value = mock_historical_sightings

        provider = EBirdAPIDataProvider(api_key="fake_key")
        recommender = DayWindowHistoricalSightingRecommender(historical_years=3, day_window=1, provider=provider)
        recommendations = recommender.recommend(location, target_date, life_list)

        expected_recommendations = [
            Recommendation(location="Location 1", score=2, species=[BLUE_JAY, ROBIN]),
            Recommendation(location="Location 2", score=1, species=[BLUE_JAY])
        ]

        self.assertCountEqual(recommendations, expected_recommendations)

    def test_sightings_to_recommendations(self):
        # Create test sightings using the utility function
        sightings = create_test_sightings(species_list=[CARDINAL, BLUE_JAY, ROBIN])
        
        # Create expected recommendations manually for clarity
        expected_recommendations = sorted([
            Recommendation(location="L123452", score=1, species=[ROBIN]),
            Recommendation(location="L123451", score=2, species=[ROBIN, BLUE_JAY]),
            Recommendation(location="L123450", score=3, species=[ROBIN, BLUE_JAY, CARDINAL])
        ], key=lambda x: x.score, reverse=True)

        recommendations = sightings_to_recommendations(sightings)
        self.maxDiff = None
        self.assertCountEqual(recommendations, expected_recommendations)


if __name__ == '__main__':
    unittest.main()