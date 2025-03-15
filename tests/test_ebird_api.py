from datetime import datetime
import logging
from typing import Any, Callable
import unittest
from unittest.mock import ANY, patch, mock_open, MagicMock
import json

import pandas as pd

from test_utils import BLUE_JAY, CARDINAL, ROBIN, create_mock_ebird_api_species_observation_response, create_mock_taxonomy_response, create_test_species, mock_url_response
from sitta.common.base import Sightings, Species
from sitta.data.ebird_api import EBirdAPICaller, EBirdAPIDataProvider

class TestEbirdApi(unittest.TestCase):

    def setUp(self):
        # turn this on for debugging
        if False:
            logging.basicConfig(level=logging.DEBUG)

    @patch("sitta.data.ebird_api.urllib.request.urlopen")
    @patch("sitta.data.ebird_api.os.path.exists")
    @patch("sitta.data.ebird_api.open", new_callable=mock_open)
    def test_get_cache_or_fetch_cache_hit(self, mock_open: MagicMock, mock_exists: MagicMock, mock_urlopen: MagicMock):
        mock_cache_dir = "mock_cache_dir"
        has_mock_cache_dir : Callable[[str], bool] = lambda path: mock_cache_dir in path
        mock_exists.side_effect = has_mock_cache_dir
        mock_open.return_value.read.return_value = json.dumps({"data": "cached_data"})
        
        url = "https://api.ebird.org/v2/product/lists/L123456"
        params = {"maxResults": str(10)}
        headers = {"X-eBirdApiToken": "fake_api_key"}

        ebird_api_caller = EBirdAPICaller(api_key="fake_api_key")
        
        result = ebird_api_caller.get_cache_or_fetch(url, params, headers, mock_cache_dir)
        self.assertEqual(result, {"data": "cached_data"})
        # cache file should be opened once
        mock_open.assert_called_once()
        # open call should contain the cache directory
        self.assertIn(mock_cache_dir,  mock_open.call_args.args[0])
        # open call should be in read mode
        self.assertEqual('r', mock_open.call_args.args[1])
        # urlopen should not be called
        mock_urlopen.assert_not_called()

    @patch("sitta.data.ebird_api.json.dump")
    @patch("sitta.data.ebird_api.urllib.request.urlopen")
    @patch("sitta.data.ebird_api.os.path.exists")
    @patch("sitta.data.ebird_api.os.makedirs")
    @patch("sitta.data.ebird_api.open", new_callable=mock_open)
    def test_get_cache_or_fetch_cache_miss(self, mock_open: MagicMock, mock_makedirs: MagicMock, mock_exists: MagicMock, mock_urlopen: MagicMock, mock_json_dump: MagicMock):
        mock_cache_dir = "mock_cache_dir" 
        mock_response_data = {"data": "fetched_data"}
        
        mock_exists.return_value = False
        mock_urlopen.return_value = mock_url_response(mock_response_data)
        
        url = "https://api.ebird.org/v2/product/lists/L654321"
        params = {"maxResults": str(10)}
        headers = {"X-eBirdApiToken": "fake_api_key"}

        ebird_api_caller = EBirdAPICaller(api_key="fake_api_key")
        
        result = ebird_api_caller.get_cache_or_fetch(url, params, headers, mock_cache_dir)
        self.assertEqual(result, mock_response_data)
        # cache file should be opened once
        mock_open.assert_called_once()
        # open call should contain the cache directory
        self.assertIn(mock_cache_dir,  mock_open.call_args.args[0])
        # open call should be in write mode
        self.assertEqual('w', mock_open.call_args.args[1])
        # urlopen should be called once
        mock_urlopen.assert_called_once()
        # json.dump should be called once with the response data
        mock_json_dump.assert_called_once_with(mock_response_data, ANY)

    @patch('sitta.data.ebird_api.EBirdAPICaller.get_observations_on_date')
    def test_get_species_seen_no_window(self, mock_get_observations_on_date: MagicMock):
        # Use utility to create mock API response
        mock_get_observations_on_date.return_value = create_mock_ebird_api_species_observation_response([CARDINAL])
        
        location_id = 'UNUSED'
        date = datetime(2023, 10, 1)
        
        # Expected results - just cardinal at the first location
        expected = {CARDINAL: {'L123450'}}

        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.get_species_seen(location_id, date, window=0)
        self.assertEqual(result, expected)

    @patch('sitta.data.ebird_api.EBirdAPICaller.get_observations_on_date')
    def test_get_species_seen_with_window(self, mock_get_observations_on_date: MagicMock):
        # Set up three different responses for the three dates in the window
        mock_get_observations_on_date.side_effect = [
            create_mock_ebird_api_species_observation_response([CARDINAL]),
            create_mock_ebird_api_species_observation_response([BLUE_JAY]),
            create_mock_ebird_api_species_observation_response([ROBIN])
        ]
        
        location_id = 'UNUSED'
        date = datetime(2023, 10, 1)
        
        # Expected merged results from all three days
        expected = {
            CARDINAL: {'L123450'},
            BLUE_JAY: {'L123450'},
            ROBIN: {'L123450'}
        }
        
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.get_species_seen(location_id, date, window=1)
        self.assertCountEqual(result, expected)

    @patch('sitta.data.ebird_api.EBirdAPICaller.get_observations_on_date')
    def test_get_species_seen_excludes_private_locations(self, mock_get_observations_on_date: MagicMock):
        # Create responses with one private location
        public_response = create_mock_ebird_api_species_observation_response([CARDINAL])
        private_response: list[dict[str, Any]] = [
            {
                'comName': BLUE_JAY.common_name,
                'speciesCode': BLUE_JAY.species_code,
                'sciName': BLUE_JAY.scientific_name,
                'locationPrivate': True,  # This one is private
                'locId': 'L123451'
            }
        ]
        
        # Set up the mock to return our custom responses
        mock_get_observations_on_date.side_effect = [
            public_response,
            private_response,
            create_mock_ebird_api_species_observation_response([ROBIN])
        ]
        
        location_id = 'L123456'
        date = datetime(2023, 10, 1)
        
        # Expected results without the private location's species
        expected = {
            CARDINAL: {'L123450'},
            ROBIN: {'L123450'}
        }
        
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.get_species_seen(location_id, date, window=1)
        self.assertCountEqual(result, expected)       

    @patch('sitta.data.ebird_api.EBirdAPIDataProvider.get_species_seen_on_dates')
    def test_get_historical_species_seen(self, mock_get_species_seen_on_date: MagicMock):
        # Create test species sightings for the historical data
        test_species = create_test_species(3)
        mock_get_species_seen_on_date.return_value = {
            test_species[0]: {'L123450'},
            test_species[1]: {'L123451'},
            test_species[2]: {'L123452'}
        }
        
        location_id = 'UNUSED'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1
        
        # Expected results should match what we mocked
        expected = {
            test_species[0]: {'L123450'},
            test_species[1]: {'L123451'},
            test_species[2]: {'L123452'}
        }
        
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.get_historical_species_seen_in_window(location_id, target_date, num_years, day_window)
        self.assertEqual(result, expected)

    @patch('sitta.data.ebird_api.EBirdAPIDataProvider.get_species_seen_on_dates')
    def test_get_historical_species_seen_no_species(self, mock_get_species_seen_on_date: MagicMock):
        mock_get_species_seen_on_date.return_value = dict()
        
        location_id = 'L123456'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1
        expected: Sightings = dict()
        
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.get_historical_species_seen_in_window(location_id, target_date, num_years, day_window)
        self.assertEqual(result, expected)

    @patch('sitta.data.ebird_api.EBirdAPICaller.get_taxonomy')
    def test_sci_name_to_code_map(self, mock_get_taxonomy: MagicMock):
        # Create mock taxonomy response with test species
        test_species = create_test_species(4)
        mock_get_taxonomy.return_value = create_mock_taxonomy_response(test_species)
        
        # Expected mapping from scientific name to species code
        expected = {
            species.scientific_name: species.species_code for species in test_species
        }
        
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.sci_name_to_code_map()
        self.assertEqual(result, expected)

    @patch('sitta.data.ebird_api.EBirdAPIDataProvider.get_species_seen')
    def test_make_sightings_dataframe(self, mock_get_species_seen: MagicMock):
        # Define the species we'll see on each day
        mock_get_species_seen.side_effect = [
            {CARDINAL: {'L123456'}},
            {BLUE_JAY: {'L234567'}},
            {ROBIN: {'L345678'}}
        ]
        
        location_id = 'UNUSED'
        dates = [datetime(2023, 10, 1), datetime(2023, 10, 2), datetime(2023, 10, 3)]
        
        # Expected dataframe
        expected_data = {
            CARDINAL.species_code: [True, False, False],
            BLUE_JAY.species_code: [False, True, False],
            ROBIN.species_code: [False, False, True]
        }
        expected_df = pd.DataFrame(expected_data, index=dates).fillna(False) # pyright: ignore[reportUnknownMemberType]
        
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        test_df = ebird_provider.make_sightings_dataframe(location_id, dates)
        
        self.assertEqual(test_df.shape, expected_df.shape)
        self.assertTrue(test_df.equals(expected_df)) # pyright: ignore[reportUnknownMemberType]

    @patch('sitta.data.ebird_api.EBirdAPIDataProvider.get_species_seen')
    def test_make_historical_sightings_dataframe_for_location(self, mock_get_species_seen: MagicMock):
        location_id = 'UNUSED'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1

        mock_get_species_seen.side_effect = [
            {CARDINAL: {'L123456'}},
            {BLUE_JAY: {'L234567'}},
            {ROBIN: {'L345678'}},
        ] * 3

        dates = [
            datetime(2021, 9, 30), datetime(2021, 10, 1), datetime(2021, 10, 2),
            datetime(2022, 9, 30), datetime(2022, 10, 1), datetime(2022, 10, 2),
            datetime(2023, 9, 30), datetime(2023, 10, 1), datetime(2023, 10, 2)
        ]

        expected_data = {
            CARDINAL.species_code: [True, False, False] * 3,
            BLUE_JAY.species_code: [False, True, False] * 3,
            ROBIN.species_code: [False, False, True] * 3
        }
        expected_df = pd.DataFrame(expected_data, index=dates) # type: ignore

        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        ebird_provider.set_sightings_dataframe_names(expected_df)
        
        result_df = ebird_provider.make_historical_sightings_dataframe_for_location(location_id, target_date, num_years, day_window)
        self.assertTrue(result_df.equals(expected_df)) # type: ignore
        mock_get_species_seen.assert_called()

    @patch('sitta.data.ebird_api.EBirdAPIDataProvider.get_species_seen')
    def test_make_historical_sightings_dataframe_for_location_empty_dates(self, mock_get_species_seen: MagicMock):
        location_id = 'UNUSED'
        target_date = datetime(2023, 10, 1)
        num_years = 0
        day_window = 1

        mock_get_species_seen.return_value = {}

        expected_df = pd.DataFrame()
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result_df = ebird_provider.make_historical_sightings_dataframe_for_location(location_id, target_date, num_years, day_window)
        self.assertTrue(result_df.equals(expected_df)) # type: ignore
        mock_get_species_seen.assert_not_called()

if __name__ == "__main__":
    unittest.main()