import unittest
from datetime import datetime

from sitta.data.data_handling import get_all_dates_in_calendar_month_for_previous_years, get_annual_date_window, get_date_window, parse_life_list_csv
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


    @patch('builtins.open', new_callable=mock_open, read_data="Common Name,Scientific Name,Date\nNorthern Cardinal,Cardinalis cardinalis,01 Oct 2023\nBlue Jay,Cyanocitta cristata,02 Oct 2023\n")
    def test_parse_life_list_csv(self, mock_file: MagicMock):
        sci_name_to_code_map = {
            'Cardinalis cardinalis': 'nocar',
            'Cyanocitta cristata': 'bluja'
        }
        expected = {
            'nocar': datetime(2023, 10, 1),
            'bluja': datetime(2023, 10, 2)
        }
        result = parse_life_list_csv(sci_name_to_code_map, 'fake_path.csv')
        self.assertEqual(result, expected)

    @patch('builtins.open', new_callable=mock_open, read_data="Common Name,Scientific Name,Date\n")
    def test_parse_life_list_csv_empty_file(self, mock_file: MagicMock):
        sci_name_to_code_map: dict[str,str] = {}
        expected = {}
        result = parse_life_list_csv(sci_name_to_code_map, 'fake_path.csv')
        self.assertEqual(result, expected)

    @patch('builtins.open', new_callable=mock_open, read_data="Common Name,Scientific Name,Date\nNorthern Cardinal,Cardinalis cardinalis,01 Oct 2023\nBlue Jay,Cyanocitta cristata,invalid_date\n")
    def test_parse_life_list_csv_invalid_date(self, mock_file: MagicMock):
        sci_name_to_code_map = {
            'Cardinalis cardinalis': 'nocar',
            'Cyanocitta cristata': 'bluja'
        }
        with self.assertRaises(ValueError):
            parse_life_list_csv(sci_name_to_code_map, 'fake_path.csv')


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

if __name__ == '__main__':
    unittest.main()