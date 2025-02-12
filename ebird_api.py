from datetime import datetime
import hashlib
import os
import sys
from typing import Any
import urllib.request
import urllib.parse
import json
import logging

DEFAULT_CACHE_DIR = os.path.expanduser("~/.ebird-api-cache")
DEFAULT_MAX_RESULTS = 1000

logger = logging.getLogger(__name__)

def get_cache_or_fetch(url: str, params: dict[str, str], headers: dict[str, str] | None, cache_dir: str = DEFAULT_CACHE_DIR) -> Any:
    """
    Get a cached response for a given URL, params, and headers; or fetch and cache the response if not cached.

    Parameters:
    headers (dict[str, str]): The headers to include in the request.
    params (dict[str, str]): The parameters to include in the request.
    cache_dir (str): The directory to cache responses in.

    Raises:
    Exception: If the response status is not 200.

    Returns:
    Any: The response data.
    """
    if not os.path.exists(cache_dir):
        logger.info(f"Creating cache directory: {cache_dir}")
        os.makedirs(cache_dir)

    query_string = urllib.parse.urlencode(params)
    url = f"{url}?{query_string}"
    
    cache_key = hashlib.md5((url + str(headers)).encode()).hexdigest()
    cache_path = os.path.join(cache_dir, cache_key)
    
    if os.path.exists(cache_path):
        logger.debug(f"Cache hit: {cache_path}")
        with open(cache_path, 'r') as cache_file:
            return json.load(cache_file)
    
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


def get_observations_on_date(location_id: str, date: datetime, api_key: str=os.environ.get("EBIRD_API_KEY"), max_results: int=DEFAULT_MAX_RESULTS) -> list[dict[str,Any]]:
    """
    Query species observed in an eBird location on a given day.

    Parameters:
    location_id (str): The eBird location identifier.
    api_key (str): eBird API key.
    date (datetime): The date for the query.
    max_results (int): Maximum number of results to return.

    Returns:
    list: A list of checklists for the specified date.
    """
    url = f"https://api.ebird.org/v2/data/obs/{location_id}/historic/{date.year}/{date.month}/{date.day}"
    headers = {
        "X-eBirdApiToken": api_key
    }
    params = {
        "maxResults": max_results,
        "detail": "full"
    }

    return get_cache_or_fetch(url, params, headers)

def get_taxonomy(api_key: str=os.environ.get("EBIRD_API_KEY")):
    """
    Query the eBird taxonomy.

    Parameters:
    api_key (str): eBird API key.

    Returns:
    list: A list of species in the eBird taxonomy.
    """
    url = "https://api.ebird.org/v2/ref/taxonomy/ebird"
    headers = {
        "X-eBirdApiToken": api_key
    }
    params = {'fmt': 'json'}

    return get_cache_or_fetch(url, params, headers)