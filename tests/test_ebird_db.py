
from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch

from sitta.common.base import Species
from sitta.data.ebird_db import LocalDBDataProvider


class TestEbirdApi(unittest.TestCase):

    @patch('sitta.data.ebird_db.open_connection')
    def test_sci_name_to_code_map(self, mock_open_connection: MagicMock):
        # Mock the db connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_open_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Make a fake map of names to code.
        mock_cursor.fetchall.return_value = [
            ('Scientific Name 1', 'species_code_1'),
            ('Scientific Name 2', 'species_code_2')
        ]

        # Call the function
        provider = LocalDBDataProvider(db_name='not_used', postgres_user='fake', postgres_pwd='alsofake')
        result = provider.sci_name_to_code_map()

        # Expected result
        expected_result = {
            'Scientific Name 1': 'species_code_1',
            'Scientific Name 2': 'species_code_2'
        }

        # Assert the result matches the expected result
        self.assertEqual(result, expected_result)

        # Ensure the correct SQL query was used
        mock_cursor.execute.assert_called_once_with("SELECT scientific_name, species_code FROM species")

    @patch('sitta.data.ebird_db.open_connection')
    def test_get_species_seen_no_window(self, mock_open_connection: MagicMock):
        # Mock the db connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_open_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {'species_code': 'nocar',
             'common_name': 'Northern Cardinal',
             'scientific_name': 'Cardinalis cardinalis',
             'observation_date': datetime(2023, 10, 1),
             'locality_ids': ['L123456', 'L234567']}
        ]

        location_id = 'UNUSED'
        date = datetime(2023, 10, 1)
        expected: dict[Species, set[str]] = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456', 'L234567'}
        }

        provider = LocalDBDataProvider(db_name='not_used', postgres_user='fake', postgres_pwd='alsofake')
        result = provider.get_species_seen(location_id, date, window=0)
        self.assertEqual(result, expected)

    @patch('sitta.data.ebird_db.open_connection')
    def test_get_species_in_calendar_month(self, mock_open_connection: MagicMock):
        # Mock the db connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_open_connection.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {'species_code': 'nocar',
             'common_name': 'Northern Cardinal',
             'scientific_name': 'Cardinalis cardinalis',
             'observation_date': datetime(2023, 10, 1),
             'locality_ids': ['L123456', 'L234567']}
        ]

        location_id = 'UNUSED'
        date = datetime(2023, 10, 1)
        expected: dict[Species, set[str]] = {
            Species(common_name='Northern Cardinal', species_code='nocar', scientific_name='Cardinalis cardinalis'): {'L123456', 'L234567'}
        }

        provider = LocalDBDataProvider(db_name='not_used', postgres_user='fake', postgres_pwd='alsofake')
        result = provider.get_historical_species_seen_in_calendar_month(location_id, date, num_years=1)
        self.assertEqual(result, expected)
