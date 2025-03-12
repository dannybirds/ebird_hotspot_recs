import unittest
from datetime import datetime

import pandas as pd
from sitta.data.data_handling import get_all_dates_in_calendar_month_for_previous_years, get_annual_date_window, get_date_window, get_historical_species_seen_in_window, get_species_seen, Species, make_historical_sightings_dataframe_for_location, make_sightings_dataframe, parse_life_list_csv, sci_name_to_code_map
from unittest.mock import MagicMock, patch, mock_open

class TestDataHandling(unittest.TestCase):

    def test_zero_window(self):
        d = datetime(2023, 10, 1)
        W = 0
        expected = [datetime(2023, 10, 1)]
        result = get_date_window(d, W)
        self.assertEqual(result, expected)

    def test_one_day_window(self):
        d = datetime(2023, 10, 1)
        W = 1
        expected = [
            datetime(2023, 9, 30),
            datetime(2023, 10, 1),
            datetime(2023, 10, 2)
        ]
        result = get_date_window(d, W)
        self.assertEqual(result, expected)

    def test_two_day_window(self):
        d = datetime(2023, 10, 1)
        W = 2
        expected = [
            datetime(2023, 9, 29),
            datetime(2023, 9, 30),
            datetime(2023, 10, 1),
            datetime(2023, 10, 2),
            datetime(2023, 10, 3)
        ]
        result = get_date_window(d, W)
        self.assertEqual(result, expected)

    def test_negative_window(self):
        d = datetime(2023, 10, 1)
        W = -1
        with self.assertRaises(ValueError):
            get_date_window(d, W)

    @patch('sitta.data.data_handling.get_observations_on_date')
    def test_get_species_seen_no_window(self, mock_get_observations_on_date: MagicMock):
        mock_get_observations_on_date.return_value = [
            {'comName': 'Northern Cardinal', 'speciesCode': 'nocar', 'sciName': 'Cardinalis cardinalis', 'locationPrivate': False, 'locId': 'L123456'}
        ]
        location_id = 'UNUSED'
        date = datetime(2023, 10, 1)
        expected: dict[Species, set[str]] = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456'}
        }
        result = get_species_seen(location_id, date, window=0)
        self.assertEqual(result, expected)

    @patch('sitta.data.data_handling.get_observations_on_date')
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
        result = get_species_seen(location_id, date, window=1)
        self.assertCountEqual(result, expected)

    @patch('sitta.data.data_handling.get_observations_on_date')
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
        result = get_species_seen(location_id, date, window=1)
        self.assertCountEqual(result, expected)        

    @patch('sitta.data.data_handling.get_species_seen')
    def test_get_historical_species_seen(self, mock_get_species_seen: MagicMock):
        mock_get_species_seen.side_effect = [
            {Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456'}},
            {Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'): {'L234567'}},
            {Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius'): {'L345678'}}
        ]
        location_id = 'UNUSED'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1
        expected = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456'},
            Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'): {'L234567'},
            Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius'): {'L345678'}
        }
        result = get_historical_species_seen_in_window(location_id, target_date, num_years, day_window)
        self.assertEqual(result, expected)

    @patch('sitta.data.data_handling.get_species_seen')
    def test_get_historical_species_seen_no_species(self, mock_get_species_seen: MagicMock):
        mock_get_species_seen.return_value = dict()
        location_id = 'L123456'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1
        expected: dict[Species, set[str]] = dict()
        result = get_historical_species_seen_in_window(location_id, target_date, num_years, day_window)
        self.assertEqual(result, expected)

    @patch('sitta.data.data_handling.get_taxonomy')
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
        result = sci_name_to_code_map()
        self.assertEqual(result, expected)


    @patch('sitta.data.data_handling.sci_name_to_code_map')
    @patch('builtins.open', new_callable=mock_open, read_data="Common Name,Scientific Name,Date\nNorthern Cardinal,Cardinalis cardinalis,01 Oct 2023\nBlue Jay,Cyanocitta cristata,02 Oct 2023\n")
    def test_parse_life_list_csv(self, mock_file: MagicMock, mock_sci_name_to_code_map: MagicMock):
        mock_sci_name_to_code_map.return_value = {
            'Cardinalis cardinalis': 'nocar',
            'Cyanocitta cristata': 'bluja'
        }
        expected = {
            'nocar': datetime(2023, 10, 1),
            'bluja': datetime(2023, 10, 2)
        }
        result = parse_life_list_csv('fake_path.csv')
        self.assertEqual(result, expected)

    @patch('sitta.data.data_handling.sci_name_to_code_map')
    @patch('builtins.open', new_callable=mock_open, read_data="Common Name,Scientific Name,Date\n")
    def test_parse_life_list_csv_empty_file(self, mock_file: MagicMock, mock_sci_name_to_code_map: MagicMock):
        mock_sci_name_to_code_map.return_value = {}
        expected = {}
        result = parse_life_list_csv('fake_path.csv')
        self.assertEqual(result, expected)

    @patch('sitta.data.data_handling.sci_name_to_code_map')
    @patch('builtins.open', new_callable=mock_open, read_data="Common Name,Scientific Name,Date\nNorthern Cardinal,Cardinalis cardinalis,01 Oct 2023\nBlue Jay,Cyanocitta cristata,invalid_date\n")
    def test_parse_life_list_csv_invalid_date(self, mock_file: MagicMock, mock_sci_name_to_code_map: MagicMock):
        mock_sci_name_to_code_map.return_value = {
            'Cardinalis cardinalis': 'nocar',
            'Cyanocitta cristata': 'bluja'
        }
        with self.assertRaises(ValueError):
            parse_life_list_csv('fake_path.csv')


    def test_get_all_dates_in_calendar_month_for_previous_years(self):
        d = datetime(2023, 10, 1)
        num_years = 2
        expected = [datetime(2022, 10, i) for i in range(1, 32)]
        expected.extend([datetime(2021, 10, i) for i in range(1, 32)])
        result = get_all_dates_in_calendar_month_for_previous_years(d, num_years)
        self.assertEqual(result, expected)

    def test_get_all_dates_in_calendar_month_for_previous_years_leap_year(self):
        d = datetime(2023, 2, 28)
        num_years = 4
        expected = [
            datetime(2022, 2, 1), datetime(2022, 2, 2), datetime(2022, 2, 3), datetime(2022, 2, 4), datetime(2022, 2, 5),
            datetime(2022, 2, 6), datetime(2022, 2, 7), datetime(2022, 2, 8), datetime(2022, 2, 9), datetime(2022, 2, 10),
            datetime(2022, 2, 11), datetime(2022, 2, 12), datetime(2022, 2, 13), datetime(2022, 2, 14), datetime(2022, 2, 15),
            datetime(2022, 2, 16), datetime(2022, 2, 17), datetime(2022, 2, 18), datetime(2022, 2, 19), datetime(2022, 2, 20),
            datetime(2022, 2, 21), datetime(2022, 2, 22), datetime(2022, 2, 23), datetime(2022, 2, 24), datetime(2022, 2, 25),
            datetime(2022, 2, 26), datetime(2022, 2, 27), datetime(2022, 2, 28),

            datetime(2021, 2, 1), datetime(2021, 2, 2), datetime(2021, 2, 3), datetime(2021, 2, 4), datetime(2021, 2, 5),
            datetime(2021, 2, 6), datetime(2021, 2, 7), datetime(2021, 2, 8), datetime(2021, 2, 9), datetime(2021, 2, 10),
            datetime(2021, 2, 11), datetime(2021, 2, 12), datetime(2021, 2, 13), datetime(2021, 2, 14), datetime(2021, 2, 15),
            datetime(2021, 2, 16), datetime(2021, 2, 17), datetime(2021, 2, 18), datetime(2021, 2, 19), datetime(2021, 2, 20),
            datetime(2021, 2, 21), datetime(2021, 2, 22), datetime(2021, 2, 23), datetime(2021, 2, 24), datetime(2021, 2, 25),
            datetime(2021, 2, 26), datetime(2021, 2, 27), datetime(2021, 2, 28),

            datetime(2020, 2, 1), datetime(2020, 2, 2), datetime(2020, 2, 3), datetime(2020, 2, 4), datetime(2020, 2, 5),
            datetime(2020, 2, 6), datetime(2020, 2, 7), datetime(2020, 2, 8), datetime(2020, 2, 9), datetime(2020, 2, 10),
            datetime(2020, 2, 11), datetime(2020, 2, 12), datetime(2020, 2, 13), datetime(2020, 2, 14), datetime(2020, 2, 15),
            datetime(2020, 2, 16), datetime(2020, 2, 17), datetime(2020, 2, 18), datetime(2020, 2, 19), datetime(2020, 2, 20),
            datetime(2020, 2, 21), datetime(2020, 2, 22), datetime(2020, 2, 23), datetime(2020, 2, 24), datetime(2020, 2, 25),
            datetime(2020, 2, 26), datetime(2020, 2, 27), datetime(2020, 2, 28), datetime(2020, 2, 29),

            datetime(2019, 2, 1), datetime(2019, 2, 2), datetime(2019, 2, 3), datetime(2019, 2, 4), datetime(2019, 2, 5),
            datetime(2019, 2, 6), datetime(2019, 2, 7), datetime(2019, 2, 8), datetime(2019, 2, 9), datetime(2019, 2, 10),
            datetime(2019, 2, 11), datetime(2019, 2, 12), datetime(2019, 2, 13), datetime(2019, 2, 14), datetime(2019, 2, 15),
            datetime(2019, 2, 16), datetime(2019, 2, 17), datetime(2019, 2, 18), datetime(2019, 2, 19), datetime(2019, 2, 20),
            datetime(2019, 2, 21), datetime(2019, 2, 22), datetime(2019, 2, 23), datetime(2019, 2, 24), datetime(2019, 2, 25),
            datetime(2019, 2, 26), datetime(2019, 2, 27), datetime(2019, 2, 28)
        ]
        result = get_all_dates_in_calendar_month_for_previous_years(d, num_years)
        self.assertEqual(result, expected)

    def test_get_annual_date_window_zero_window(self):
        target_date = datetime(2023, 10, 1)
        w = 0
        years = 3
        expected = [
            datetime(2021, 10, 1),
            datetime(2022, 10, 1),
            datetime(2023, 10, 1)
        ]
        result = get_annual_date_window(target_date, w, years)
        self.assertEqual(result, expected)

    def test_get_annual_date_window_one_day_window(self):
        target_date = datetime(2023, 10, 1)
        w = 1
        years = 2
        expected = [
            datetime(2022, 9, 30),
            datetime(2022, 10, 1),
            datetime(2022, 10, 2),
            datetime(2023, 9, 30),
            datetime(2023, 10, 1),
            datetime(2023, 10, 2)
        ]
        result = get_annual_date_window(target_date, w, years)
        self.assertEqual(result, expected)

    def test_get_annual_date_window_two_day_window(self):
        target_date = datetime(2023, 10, 1)
        w = 2
        years = 1
        expected = [
            datetime(2023, 9, 29),
            datetime(2023, 9, 30),
            datetime(2023, 10, 1),
            datetime(2023, 10, 2),
            datetime(2023, 10, 3)
        ]
        result = get_annual_date_window(target_date, w, years)
        self.assertEqual(result, expected)   

    def test_get_annual_date_window_no_years(self):
        target_date = datetime(2023, 10, 1)
        w = 1
        years = 0
        expected = []
        result = get_annual_date_window(target_date, w, years)
        self.assertEqual(result, expected)

    @patch('sitta.data.data_handling.get_species_seen')
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

        test_df = make_sightings_dataframe(location_id, dates)
        self.assertEqual(test_df.shape, expected_df.shape)
        self.assertTrue(test_df.equals(expected_df)) # type: ignore     

    @patch('sitta.data.data_handling.get_species_seen')
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

        result_df = make_historical_sightings_dataframe_for_location(location_id, target_date, num_years, day_window)
        self.assertTrue(result_df.equals(expected_df)) # type: ignore
        mock_get_species_seen.assert_called()

    @patch('sitta.data.data_handling.get_species_seen')
    def test_make_historical_sightings_dataframe_for_location_empty_dates(self, mock_get_species_seen: MagicMock):
        location_id = 'UNUSED'
        target_date = datetime(2023, 10, 1)
        num_years = 0
        day_window = 1

        mock_get_species_seen.return_value = {}

        expected_df = pd.DataFrame()

        result_df = make_historical_sightings_dataframe_for_location(location_id, target_date, num_years, day_window)
        self.assertTrue(result_df.equals(expected_df)) # type: ignore
        mock_get_species_seen.assert_not_called()

if __name__ == '__main__':
    unittest.main()