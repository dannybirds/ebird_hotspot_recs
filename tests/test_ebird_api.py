import logging
import sys
import unittest
from unittest.mock import ANY, patch, mock_open, MagicMock
import json
import os
import urllib

from ebird_hotspot_recs.ebird_api import get_cache_or_fetch, get_recent_checklists

class TestEbirdApi(unittest.TestCase):

    def setUp(self):
        # turn this on for debugging
        if False:
            logging.basicConfig(level=logging.DEBUG)

    @patch("ebird_hotspot_recs.ebird_api.urllib.request.urlopen")
    @patch("ebird_hotspot_recs.ebird_api.os.path.exists")
    @patch("ebird_hotspot_recs.ebird_api.open", new_callable=mock_open)
    def test_get_cache_or_fetch_cache_hit(self, mock_open, mock_exists, mock_urlopen):
        mock_cache_dir = "mock_cache_dir" 
        mock_exists.side_effect = lambda path: mock_cache_dir in path
        mock_open.return_value.read.return_value = json.dumps({"data": "cached_data"})
        
        url = "https://api.ebird.org/v2/product/lists/L123456"
        params = {"maxResults": 10}
        headers = {"X-eBirdApiToken": "fake_api_key"}
        
        result = get_cache_or_fetch(url, params, headers, mock_cache_dir)
        self.assertEqual(result, {"data": "cached_data"})
        # cache file should be opened once
        mock_open.assert_called_once()
        # open call should contain the cache directory
        self.assertIn(mock_cache_dir,  mock_open.call_args.args[0])
        # open call should be in read mode
        self.assertEqual('r', mock_open.call_args.args[1])
        # urlopen should not be called
        mock_urlopen.assert_not_called()

    @patch("ebird_hotspot_recs.ebird_api.json.dump")
    @patch("ebird_hotspot_recs.ebird_api.urllib.request.urlopen")
    @patch("ebird_hotspot_recs.ebird_api.os.path.exists")
    @patch("ebird_hotspot_recs.ebird_api.os.makedirs")
    @patch("ebird_hotspot_recs.ebird_api.open", new_callable=mock_open)
    def test_get_cache_or_fetch_cache_miss(self, mock_open, mock_makedirs, mock_exists, mock_urlopen, mock_json_dump):
        mock_cache_dir = "mock_cache_dir" 
        mock_response_data = {"data": "fetched_data"}
        mock_response_data_str = json.dumps(mock_response_data).encode('utf-8')

        mock_exists.return_value = False
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = mock_response_data_str
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        url = "https://api.ebird.org/v2/product/lists/L654321"
        params = {"maxResults": 10}
        headers = {"X-eBirdApiToken": "fake_api_key"}
        
        result = get_cache_or_fetch(url, params, headers, mock_cache_dir)
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

if __name__ == "__main__":
    unittest.main()