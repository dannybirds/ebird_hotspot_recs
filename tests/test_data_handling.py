import unittest
from datetime import datetime
from data_handling import get_date_window, get_historical_species_seen, get_species_seen, Species, parse_life_list_csv, sci_name_to_code_map
from unittest.mock import patch, mock_open
from io import StringIO
import csv

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
            result = get_date_window(d, W)

    @patch('data_handling.get_observations_on_date')
    def test_get_species_seen_no_window(self, mock_get_observations_on_date):
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

    @patch('data_handling.get_observations_on_date')
    def test_get_species_seen_with_window(self, mock_get_observations_on_date):
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

    @patch('data_handling.get_observations_on_date')
    def test_get_species_seen_excludes_private_locations(self, mock_get_observations_on_date):
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

    @patch('data_handling.get_species_seen')
    def test_get_historical_species_seen(self, mock_get_species_seen):
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
        result = get_historical_species_seen(location_id, target_date, num_years, day_window)
        self.assertEqual(result, expected)

    @patch('data_handling.get_species_seen')
    def test_get_historical_species_seen_no_species(self, mock_get_species_seen):
        mock_get_species_seen.return_value = dict()
        location_id = 'L123456'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1
        expected: dict[Species, set[str]] = dict()
        result = get_historical_species_seen(location_id, target_date, num_years, day_window)
        self.assertEqual(result, expected)

    @patch('ebird_api.get_taxonomy')
    def test_sci_name_to_code_map(self, mock_get_taxonomy):
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


    @patch('data_handling.sci_name_to_code_map')
    @patch('builtins.open', new_callable=mock_open, read_data="Common Name,Scientific Name,Date\nNorthern Cardinal,Cardinalis cardinalis,01 Oct 2023\nBlue Jay,Cyanocitta cristata,02 Oct 2023\n")
    def test_parse_life_list_csv(self, mock_file, mock_sci_name_to_code_map):
        mock_sci_name_to_code_map.return_value = {
            'Cardinalis cardinalis': 'nocar',
            'Cyanocitta cristata': 'bluja'
        }
        expected = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): datetime(2023, 10, 1),
            Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'): datetime(2023, 10, 2)
        }
        result = parse_life_list_csv('fake_path.csv')
        self.assertEqual(result, expected)

    @patch('data_handling.sci_name_to_code_map')
    @patch('builtins.open', new_callable=mock_open, read_data="Common Name,Scientific Name,Date\n")
    def test_parse_life_list_csv_empty_file(self, mock_file, mock_sci_name_to_code_map):
        mock_sci_name_to_code_map.return_value = {}
        expected = {}
        result = parse_life_list_csv('fake_path.csv')
        self.assertEqual(result, expected)

    @patch('data_handling.sci_name_to_code_map')
    @patch('builtins.open', new_callable=mock_open, read_data="Common Name,Scientific Name,Date\nNorthern Cardinal,Cardinalis cardinalis,01 Oct 2023\nBlue Jay,Cyanocitta cristata,invalid_date\n")
    def test_parse_life_list_csv_invalid_date(self, mock_file, mock_sci_name_to_code_map):
        mock_sci_name_to_code_map.return_value = {
            'Cardinalis cardinalis': 'nocar',
            'Cyanocitta cristata': 'bluja'
        }
        with self.assertRaises(ValueError):
            parse_life_list_csv('fake_path.csv')


if __name__ == '__main__':
    unittest.main()