import unittest
from datetime import datetime
from data_handling import get_date_window, get_historical_species_seen, get_species_seen, Species
from unittest.mock import patch

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
            {'comName': 'Northern Cardinal', 'speciesCode': 'nocar', 'sciName': 'Cardinalis cardinalis'}
        ]
        location_id = 'L123456'
        date = datetime(2023, 10, 1)
        expected: set[Species] = set(
            [Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis')]
        )
        result = get_species_seen(location_id, date, window=0)
        self.assertEqual(result, expected)

    @patch('data_handling.get_observations_on_date')
    def test_get_species_seen_with_window(self, mock_get_observations_on_date):
        mock_get_observations_on_date.side_effect = [
            [{'comName': 'Northern Cardinal', 'speciesCode': 'nocar', 'sciName': 'Cardinalis cardinalis'}],
            [{'comName': 'Blue Jay', 'speciesCode': 'bluja', 'sciName': 'Cyanocitta cristata'}],
            [{'comName': 'American Robin', 'speciesCode': 'amerob', 'sciName': 'Turdus migratorius'}]
        ]
        location_id = 'L123456'
        date = datetime(2023, 10, 1)
        expected = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'),
            Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'),
            Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius')
        }
        result = get_species_seen(location_id, date, window=1)
        self.assertCountEqual(result, expected)

    @patch('data_handling.get_species_seen')
    def test_get_historical_species_seen(self, mock_get_species_seen):
        mock_get_species_seen.side_effect = [
            {Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis')},
            {Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata')},
            {Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius')}
        ]
        location_id = 'L123456'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1
        expected = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'),
            Species(common_name='Blue Jay', species_code='bluja', scientific_name='Cyanocitta cristata'),
            Species(common_name='American Robin', species_code='amerob', scientific_name='Turdus migratorius')
        }
        result = get_historical_species_seen(location_id, target_date, num_years, day_window)
        self.assertEqual(result, expected)

    @patch('data_handling.get_species_seen')
    def test_get_historical_species_seen_no_species(self, mock_get_species_seen):
        mock_get_species_seen.return_value = set()
        location_id = 'L123456'
        target_date = datetime(2023, 10, 1)
        num_years = 3
        day_window = 1
        expected = set()
        result = get_historical_species_seen(location_id, target_date, num_years, day_window)
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()