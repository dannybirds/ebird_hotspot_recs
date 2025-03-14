"""
Interface with the eBird API to retrieve observation data.
"""

from datetime import datetime
import functools
import hashlib
import os
from typing import Any
import urllib.request
import urllib.parse
import json
import logging

from sitta.common.base import Sightings, Species
from sitta.data.data_handling import get_all_dates_in_calendar_month_for_previous_years
from sitta.data.providers import EBirdDataProvider

DEFAULT_CACHE_DIR = os.path.expanduser("~/.ebird-api-cache")
DEFAULT_MAX_RESULTS = 1000

logger = logging.getLogger(__name__)


class EBirdAPICaller:
    """
    Helper class for making API calls to eBird with reponse caching.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize the API-based data provider.
        
        Parameters:
        api_key (Optional[str]): The eBird API key. If None, will try to get from EBIRD_API_KEY env var.
        """
        api_key = api_key or os.environ.get("EBIRD_API_KEY")
        if not api_key:
            raise ValueError("eBird API key must be provided or set as EBIRD_API_KEY environment variable")
        self.api_key: str = api_key

    def get_cache_or_fetch(self, url: str, params: dict[str, str], headers: dict[str, str] | None = None, cache_dir: str = DEFAULT_CACHE_DIR) -> Any:
        """
        Get a cached response for a given URL, params, and headers; or fetch and cache the response if not cached.

        Parameters:
        url (str): The URL to fetch.
        params (dict[str, str]): The parameters to include in the request.
        headers (dict[str, str] | None): The headers to include in the request.
        cache_dir (str): The directory to cache responses in.

        Raises:
        Exception: If the response status is not 200.

        Returns:
        Any: The response data.
        """
        if not os.path.exists(cache_dir):
            logger.info(f"Creating cache directory: {cache_dir}")
            os.makedirs(cache_dir)

        headers = headers or {}
        if "X-eBirdApiToken" not in headers:
            headers["X-eBirdApiToken"] = self.api_key
        query_string = urllib.parse.urlencode(params)
        url = f"{url}?{query_string}"
        
        cache_key = hashlib.md5((url + str(headers)).encode()).hexdigest()
        cache_path = os.path.join(cache_dir, cache_key)
        
        if os.path.exists(cache_path):
            logger.debug(f"Cache hit: {cache_path}")
            with open(cache_path, 'r') as cache_file:
                s = cache_file.read()
                return json.loads(s)
        
        logger.debug(f"Cache miss: {cache_path}")
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                logger.debug(f"Fetched data from {url}") 
                data = json.loads(response.read().decode())
                with open(cache_path, 'w') as cache_file:
                    logger.debug(f"Writing cache file: {cache_path}")
                    json.dump(data, cache_file)
                return data
            else:
                raise Exception(f"Error: {response.status}")
    
    def get_observations_on_date(self, location_id: str, date: datetime, max_results: int=DEFAULT_MAX_RESULTS) -> list[dict[str, Any]]:
        """
        Query species observed in an eBird location on a given day.

        Parameters:
        location_id (str): The eBird location identifier.
        date (datetime): The date for the query.
        max_results (int): Maximum number of results to return.

        Returns:
        list: A list of checklists for the specified date.
        """
        url = f"https://api.ebird.org/v2/data/obs/{location_id}/historic/{date.year}/{date.month}/{date.day}"
        params: dict[str, str] = {
            "maxResults": str(max_results),
            "detail": "full"
        }
        return self.get_cache_or_fetch(url, params)
    
    def get_taxonomy(self) -> Any:
        """
        Query the eBird taxonomy.

        Returns:
        list: A list of species in the eBird taxonomy.
        """
        url = "https://api.ebird.org/v2/ref/taxonomy/ebird"
        params = {'fmt': 'json'}
        return self.get_cache_or_fetch(url, params)    


class EBirdAPIDataProvider(EBirdDataProvider):
    """
    eBird data provider that uses the eBird API as the data source.
    """
    
    def __init__(self, api_key: str | None = None):
        """
        Initialize the API-based data provider.
        
        Parameters:
        api_key (Optional[str]): The eBird API key. If None, will try to get from EBIRD_API_KEY env var.
        """
        self.fetcher = EBirdAPICaller(api_key=api_key)
    
    def get_species_seen_on_dates(self, location_id: str, target_dates: list[datetime]) -> Sightings:
        """
        Get species observed using the eBird API.
        
        Parameters:
        location_id (str): The eBird location identifier.
        target_dates (list[datetime]): The list of dates for the query.
        
        Returns:
        Sightings: A dictionary of species observed and the locations where they were seen, 
        which can be sub-locations of the given location_id (e.g. hotspots within a county).
        """
        
        species_seen: dict[Species, set[str]] = {}
        for d in target_dates:
            observations = self.fetcher.get_observations_on_date(location_id, d)
            if observations:
                for species in observations:
                    if species.get('locationPrivate', False):
                        continue
                    sp = Species(
                        common_name=species['comName'],
                        species_code=species['speciesCode'],
                        scientific_name=species['sciName']
                    )
                    if sp not in species_seen:
                        species_seen[sp] = set()
                    species_seen[sp].add(species['locId'])
        
        return species_seen
            
    @functools.cache
    def sci_name_to_code_map(self) -> dict[str, str]:
        """
        Get a dictionary mapping scientific names to species codes.

        The result is cached, so this function can be called many times but will only load the data once.

        Returns:
        dict[str, str]: A dictionary mapping scientific names to species codes.
        """
        taxonomy = self.fetcher.get_taxonomy()
        return {species['sciName']: species['speciesCode'] for species in taxonomy}
