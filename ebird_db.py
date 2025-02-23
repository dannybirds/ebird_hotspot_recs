import os
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
    Create life lists for a list of observers.
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
        life_lists[observer_id][s] = datetime.combine(first_seen, datetime.min.time())
    return life_lists

def lookup_counties_with_lifers(life_list: LifeList, target_date: datetime) -> list[str]:
    """
    Lookup the counties that have lifers on the target date.
    """
    q = """
    SELECT 
        DISTINCT species_code, observation_date, county_code
    FROM observations JOIN checklists USING (sampling_event_id)
    WHERE NOT (species_code = ANY(%s)) AND observation_date=%s;
    """
    seen_species = [s.species_code for s in life_list.keys() if life_list[s] < target_date]
    with open_connection() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(q, [seen_species,target_date])
            rows = cur.fetchall()

    new_species = {row['species_code'] for row in rows}
    assert set(new_species) & set(seen_species) == set()
    counties = {row['county_code'] for row in rows}
    return list(counties)
