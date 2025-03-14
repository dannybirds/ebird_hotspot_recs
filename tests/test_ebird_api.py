from datetime import datetime
import logging
from typing import Callable
import unittest
from unittest.mock import ANY, patch, mock_open, MagicMock
import json

import pandas as pd

from sitta.common.base import Species
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
        mock_exists.side_effect = has_mock_cache_dir # lambda path: mock_cache_dir in path
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
        mock_response_data_str = json.dumps(mock_response_data).encode('utf-8')

        mock_exists.return_value = False
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = mock_response_data_str
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
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
        mock_get_observations_on_date.return_value = [
            {'comName': 'Northern Cardinal', 'speciesCode': 'nocar', 'sciName': 'Cardinalis cardinalis', 'locationPrivate': False, 'locId': 'L123456'}
        ]
        location_id = 'UNUSED'
        date = datetime(2023, 10, 1)
        expected: dict[Species, set[str]] = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456'}
        }

        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.get_species_seen(location_id, date, window=0)
        self.assertEqual(result, expected)

    @patch('sitta.data.ebird_api.EBirdAPICaller.get_observations_on_date')
    def test_get_species_seen_with_window(self, mock_get_observations_on_date: MagicMock):
        mock_get_observations_on_date.side_effect = [
            [{'comName': 'Northern Cardinal', 'speciesCode': 'nocar', 'sciName': 'Cardinalis cardinalis', 'locationPrivate': False, 'locId': 'L123456'}],
            [{'comName': 'Blue Jay', 'speciesCode': 'bluja', 'sciName': 'Cyanocitta cristata', 'locationPrivate': False, 'locId': 'L234567'}],
            [{'comName': 'American Robin', 'speciesCode': 'amerob', 'sciName': 'Turdus migratorius', 'locationPrivate': False, 'locId': 'L345678'}]
        ]
        location_id = 'UNUSED'
        date = datetime(2023, 10, 1)
        expected = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis') : {'L123456'},
            Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'): {'L234567'},
            Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius'): {'L345678'}
        }
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.get_species_seen(location_id, date, window=1)
        self.assertCountEqual(result, expected)

    @patch('sitta.data.ebird_api.EBirdAPICaller.get_observations_on_date')
    def test_get_species_seen_excludes_private_locations(self, mock_get_observations_on_date: MagicMock):
        mock_get_observations_on_date.side_effect = [
            [{'comName': 'Northern Cardinal', 'speciesCode': 'nocar', 'sciName': 'Cardinalis cardinalis', 'locationPrivate': False, 'locId': 'L123456'}],
            [{'comName': 'Blue Jay', 'speciesCode': 'bluja', 'sciName': 'Cyanocitta cristata', 'locationPrivate': True, 'locId': 'L234567'}],
            [{'comName': 'American Robin', 'speciesCode': 'amerob', 'sciName': 'Turdus migratorius', 'locationPrivate': False, 'locId': 'L345678'}]
        ]
        location_id = 'L123456'
        date = datetime(2023, 10, 1)
        expected = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456'},
            # Blue Jay should not be included because its location is private
            Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius'): {'L345678'}
        }
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.get_species_seen(location_id, date, window=1)
        self.assertCountEqual(result, expected)        

    @patch('sitta.data.ebird_api.EBirdAPIDataProvider.get_species_seen_on_dates')
    def test_get_historical_species_seen(self, mock_get_species_seen_on_date: MagicMock):
        mock_get_species_seen_on_date.return_value = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456'},
            Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'): {'L234567'},
            Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius'): {'L345678'}
        }
        location_id = 'UNUSED'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1
        expected = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456'},
            Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'): {'L234567'},
            Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius'): {'L345678'}
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
        expected: dict[Species, set[str]] = dict()
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.get_historical_species_seen_in_window(location_id, target_date, num_years, day_window)
        self.assertEqual(result, expected)

    @patch('sitta.data.ebird_api.EBirdAPICaller.get_taxonomy')
    def test_sci_name_to_code_map(self, mock_get_taxonomy: MagicMock):
        mock_get_taxonomy.return_value = [
            {'sciName': 'Cardinalis cardinalis', 'speciesCode': 'nocar'},
            {'sciName': 'Cyanocitta cristata', 'speciesCode': 'bluja'},
            {'sciName': 'Turdus migratorius', 'speciesCode': 'amerob'},
            {'sciName': 'Fantasticus nihila', 'speciesCode': 'fannih'}
        ]
        expected = {
            'Fantasticus nihila': 'fannih',
            'Cardinalis cardinalis': 'nocar',
            'Cyanocitta cristata': 'bluja',
            'Turdus migratorius': 'amerob'
        }
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        result = ebird_provider.sci_name_to_code_map()
        self.assertEqual(result, expected)

    @patch('sitta.data.ebird_api.EBirdAPIDataProvider.get_species_seen')
    def test_make_sightings_dataframe(self, mock_get_species_seen: MagicMock):
        mock_get_species_seen.side_effect = [
            {Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456'}},
            {Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'): {'L234567'}},
            {Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius'): {'L345678'}}
        ]
        location_id = 'UNUSED'
        dates = [datetime(2023, 10, 1), datetime(2023, 10, 2), datetime(2023, 10, 3)]
        expected_data = {
            'nocar': [True, False, False],
            'bluja': [False, True, False],
            'amerob': [False, False, True]
        }
        expected_df = pd.DataFrame(expected_data, index=dates).fillna(False) # type: ignore
        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
        test_df = ebird_provider.make_sightings_dataframe(location_id, dates)
        self.assertEqual(test_df.shape, expected_df.shape) 
        self.assertTrue(test_df.equals(expected_df)) # type: ignore

    @patch('sitta.data.ebird_api.EBirdAPIDataProvider.get_species_seen')
    def test_make_historical_sightings_dataframe_for_location(self, mock_get_species_seen: MagicMock):
        location_id = 'UNUSED'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1

        mock_get_species_seen.side_effect = [
            {Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456'}},
            {Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'): {'L234567'}},
            {Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius'): {'L345678'}},
        ] * 3

        dates = [
            datetime(2021, 9, 30), datetime(2021, 10, 1), datetime(2021, 10, 2),
            datetime(2022, 9, 30), datetime(2022, 10, 1), datetime(2022, 10, 2),
            datetime(2023, 9, 30), datetime(2023, 10, 1), datetime(2023, 10, 2)
        ]

        expected_data = {
            'nocar': [True, False, False] * 3,
            'bluja': [False, True, False] * 3,
            'amerob': [False, False, True] * 3
        }
        expected_df = pd.DataFrame(expected_data, index=dates).fillna(False) # type: ignore

        ebird_provider = EBirdAPIDataProvider(api_key="UNUSED")
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