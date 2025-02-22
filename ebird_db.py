import os
import pprint
import psycopg
from datetime import datetime
import psycopg.rows
from common import LifeList, Species

DB_NAME = "ebird_us"

def open_connection(autocommit: bool=False) -> psycopg.Connection:
    conn = psycopg.connect(f"dbname={DB_NAME} user={os.getenv("POSTGRES_USER")} password={os.getenv("POSTGRES_PWD")}", autocommit=autocommit)
    return conn

def create_life_lists(observer_ids: list[str]) -> dict[str, LifeList]:
    """
    Create a life list for an observer.
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
            pprint.pp(rows)

    life_lists: dict[str,LifeList] = {}
    for row in rows:
        observer_id = row.pop('observer_id')
        s = Species(
            common_name=row.pop('common_name'),
            species_code=row.pop('species_code'),
            scientific_name=row.pop('scientific_name')
        )
        first_seen = row.pop('first_seen')
        if observer_id not in life_lists:
            life_lists[observer_id] = {}
        life_lists[observer_id][s] = first_seen
    return life_lists

def lookup_counties_with_lifers(life_list: LifeList, target_date: datetime) -> list[str]:
    """
    Lookup the counties that have lifers on the target date.
    """
    #counties = set[str]
    #for species, date in life_list.items():
    #    if date <= target_date:
    #        #counties.add(species.county)
    return []
