"""
Interface with the eBird database to retrieve observation data.
"""

import functools
import os
import psycopg
from datetime import datetime
import psycopg.rows

from sitta.data.providers import EBirdDataProvider
from sitta.common.base import EndToEndEvalDatapoint, LifeList, Recommendation, Sightings, Species, TargetArea, TargetAreaType

DB_NAME = "ebird_us"
LOCALITIES_TABLE = "localities"
CHECKLISTS_TABLE = "checklists"
SPECIES_TABLE = "species"
OBSERVATIONS_TABLE = "observations"

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
        gts[county].append(Recommendation(locality_id=row['locality_id'], score=row['c'], species=list(species_set)))
    
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


class LocalDBDataProvider(EBirdDataProvider):
    """
    eBird data provider that uses the eBird API as the data source.
    """

    def __init__(self, db_name: str|None = None, postgres_user: str|None = None, postgres_pwd:str|None = None) -> None:
        """
        Initialize the DB-based data provider.
        """
        db_name = db_name or DB_NAME
        if not db_name:
            raise ValueError("db_name must be provided")
        self.db_name = db_name

        postgres_user = postgres_user or os.getenv('POSTGRES_USER')
        if not postgres_user:
            raise ValueError("postgres_user must be provided or set as POSTGRES_USER environment variable")
        self.postgres_user = postgres_user

        postgres_pwd = postgres_pwd or os.getenv('POSTGRES_PWD')
        if not postgres_pwd:
            raise ValueError("postgres_pwd must be provided or set as POSTGRES_PWD environment variable")
        self.postgres_pwd = postgres_pwd

    def get_species_seen_on_dates(self, target_area: TargetArea, target_dates: list[datetime]) -> Sightings:
        """
        Get species observed using the local database.
        
        Parameters:
        location_id (str): The eBird location identifier.
        target_dates (list[datetime]): The dates for the query.
        
        Returns:
        Sightings: A dictionary of species observed and the locations where they were seen, 
        which can be sub-locations of the given location_id (e.g. hotspots within a county).
        """
        if target_area.area_type == TargetAreaType.LAT_LONG or target_area.area_id is None:
            raise NotImplementedError("Lat long targeting not yet implemented.")
        species_seen: dict[Species, set[str]] = {}
        with open_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                q = """
                SELECT
                    observation_date, species_code, scientific_name, common_name ARRAY_AGG(locality_id) AS locality_ids
                FROM checklists JOIN observations USING (sampling_event_id) JOIN species USING (species_code)
                WHERE
                    %s = ANY(ARRAY[county_code, state_code, country_code, locality_id])
                    AND observation_date = ANY(%s)
                GROUP BY observation_date, species_code, scientific_name, common_name ;
                """
                cur.execute(q, [target_area.area_id, target_dates])
                rows = cur.fetchall()
                
                for row in rows:
                    sp = Species(
                        common_name=row['common_name'],
                        species_code=row['species_code'],
                        scientific_name=row['scientific_name']
                    )
                    if sp not in species_seen:
                        species_seen[sp] = set()
                    species_seen[sp].update(row['locality_ids'])

        return species_seen
    
    @functools.cache
    def sci_name_to_code_map(self) -> dict[str, str]:
        """
        Create a mapping from scientific names to species codes.
        
        Returns:
            Dictionary mapping scientific names to species codes
        """
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT scientific_name, species_code FROM {SPECIES_TABLE}")
                species_map = {row[0]: row[1] for row in cur.fetchall()}
        return species_map
