import hashlib
import os
import sys
from typing import Any
import urllib.request
import urllib.parse
import json
import logging

DEFAULT_CACHE_DIR = os.path.expanduser("~/.ebird-api-cache")

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


def get_recent_checklists(hotspot_id: str, api_key: str, max_results: int=10) -> list[dict[str,Any]]:
    """
    Query recent checklists from an eBird hotspot.

    Parameters:
    hotspot_id (str): The eBird hotspot identifier.
    api_key (str): Your eBird API key.
    max_results (int): Maximum number of results to return (default is 10).

    Returns:
    list: A list of recent checklists.
    """
    url = f"https://api.ebird.org/v2/product/lists/{hotspot_id}"
    headers = {
        "X-eBirdApiToken": api_key
    }
    params = {
        "maxResults": max_results
    }
    
    return get_cache_or_fetch(url, params, headers)

def main():
    logging.basicConfig(level=logging.DEBUG)
    api_key = os.environ.get("EBIRD_API_KEY")
    bedwell_bayfront_park = 'L266125'
    prospect_park = 'L109516'
    checklists = get_recent_checklists(prospect_park, api_key)
    print(json.dumps(checklists, indent=4))

if __name__ == "__main__":
    main()