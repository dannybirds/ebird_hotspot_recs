"""
Interface with the eBird database to retrieve observation data.
"""

import os
import psycopg
from datetime import datetime
import psycopg.rows

from sitta.common.base import EndToEndEvalDatapoint, LifeList, Recommendation

DB_NAME = "ebird_us"

def open_connection(autocommit: bool=False) -> psycopg.Connection:
    """
    Open a connection to the eBird database.
    
    Parameters:
    autocommit (bool): Whether to enable autocommit mode.
    
    Returns:
    psycopg.Connection: A connection to the eBird database.
    """
    conn = psycopg.connect(
        f"dbname={DB_NAME} user={os.getenv('POSTGRES_USER')} password={os.getenv('POSTGRES_PWD')}", 
        autocommit=autocommit
    )
    return conn

async def open_async_connection(autocommit: bool=False) -> psycopg.AsyncConnection:
    """
    Open a connection to the eBird database.
    
    Parameters:
    autocommit (bool): Whether to enable autocommit mode.
    
    Returns:
    psycopg.Connection: A connection to the eBird database.
    """
    conn = await psycopg.AsyncConnection.connect(
        f"dbname={DB_NAME} user={os.getenv('POSTGRES_USER')} password={os.getenv('POSTGRES_PWD')}", 
        autocommit=autocommit
    )
    return conn


def create_life_lists(observer_ids: list[str]) -> dict[str, LifeList]:
    """
    Create life lists for a list of observers.

    Parameters:
    observer_ids (list[str]): A list of eBird observer IDs.
    
    Returns:
    dict[str, LifeList]: A dictionary of observer IDs to life lists.
    """
    q = """
    SELECT
        observer_id,
        species_code,
        common_name,
        scientific_name,
        MIN(observation_date) AS first_seen
    FROM observations JOIN checklists USING(sampling_event_id) JOIN species USING(species_code)
    WHERE observer_id = ANY(%s)
    GROUP BY
        observer_id,
        species_code,
        common_name,
        scientific_name;
    """
    with open_connection() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(q, [observer_ids,])
            rows = cur.fetchall()

    life_lists: dict[str, LifeList] = {}
    for row in rows:
        observer_id = row.pop('observer_id')
        first_seen = row.pop('first_seen')
        if observer_id not in life_lists:
            life_lists[observer_id] = {}
        life_lists[observer_id][row['species_code']] = datetime.combine(first_seen, datetime.min.time())
    return life_lists


async def fetch_all_gt_hotspots(observer_id: str, life_list: LifeList, target_date: datetime) -> list[EndToEndEvalDatapoint]:
    """
    Lookup the counties that have hotspots with lifers observed on the target date.
    
    Parameters:
    observer_id (str): The eBird observer ID.
    life_list (LifeList): The observer's life list.
    target_date (datetime): The target date.
    
    Returns:
    list[EndToEndEvalDatapoint]: A datapoint for each hotspot in each county.
    """
    q = """
    SELECT
        observation_date,
        county_code,
        locality_id,
        ARRAY_AGG(species_code) species_list,
        COUNT(*) AS c 
    FROM observations JOIN checklists USING (sampling_event_id) JOIN localities USING (locality_id)
    WHERE NOT (species_code = ANY(%s)) AND observation_date=%s AND type != 'P'
    GROUP BY observation_date, county_code, locality_id;
    """
    truncated_life_list = {k: v for k, v in life_list.items() if v < target_date}
    seen_species = [s for s in truncated_life_list.keys()]
    async with await open_async_connection() as conn:
        async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            await cur.execute(q, [seen_species, target_date])
            rows = await cur.fetchall()

    gts: dict[str, list[Recommendation]] = {}
    for row in rows:
        # This is unit testing it live!
        species_set = set(row['species_list'])
        assert species_set & set(seen_species) == set()
        county = row['county_code']
        # There are some hotspots that don't have a county code, skip those.
        if not county:
            continue
        if county not in gts:
            gts[county] = []
        gts[county].append(Recommendation(location=row['locality_id'], score=row['c'], species=list(species_set)))
    
    datapoints = [
        EndToEndEvalDatapoint(
            target_location=county,
            target_date=target_date,
            life_list=truncated_life_list,
            ground_truth=recs,
            observer_id=observer_id
        ) for county, recs in gts.items()
    ]
    return datapoints