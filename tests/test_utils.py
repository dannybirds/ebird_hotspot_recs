"""
Shared test utilities for Sitta package tests.

This module provides common fixtures, helpers, and mock factories to reduce
duplication across test files.
"""

import json
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

from sitta.common.base import LifeList, Recommendation, Sightings, Species


# Common test species
CARDINAL = Species("Northern Cardinal", "nocar", "Cardinalis cardinalis")
BLUE_JAY = Species("Blue Jay", "bluja", "Cyanocitta cristata")
ROBIN = Species("American Robin", "amerob", "Turdus migratorius")
SPARROW = Species("House Sparrow", "houspa", "Passer domesticus")
MOURNING_DOVE = Species("Mourning Dove", "modo", "Zenaida macroura")
SONG_SPARROW = Species("Song Sparrow", "sosp", "Melospiza melodia")
EUROPEAN_STARLING = Species("European Starling", "eust", "Sturnus vulgaris")
RED_WINGED_BLACKBIRD = Species("Red-winged Blackbird", "rwbl", "Agelaius phoeniceus")
COMMON_GRACKLE = Species("Common Grackle", "cogr", "Quiscalus quiscula")
AMERICAN_GOLDFINCH = Species("American Goldfinch", "amgo", "Spinus tristis")



def create_test_species(count: int = 3) -> list[Species]:
    """Create a list of test species with predictable names and codes.
    
    Args:
        count: Number of species to create (max 10)
        
    Returns:
        List of Species objects
    """
    base_species = [
        CARDINAL,
        BLUE_JAY,
        ROBIN,
        SPARROW,
        MOURNING_DOVE,
        SONG_SPARROW,
        EUROPEAN_STARLING,
        RED_WINGED_BLACKBIRD,
        COMMON_GRACKLE,
        AMERICAN_GOLDFINCH
    ]
    if count > len(base_species):
        raise ValueError(f"Count exceeds available species: {len(base_species)}")
    return base_species[:min(count, len(base_species))]


def create_test_recommendations(
    species_per_location: int = 2, 
    location_count: int = 3,
    base_location_id: str = "L12345"
) -> list[Recommendation]:
    """Create test recommendations with predictable values.
    
    Args:
        species_per_location: Number of species per location
        location_count: Number of locations to create
        base_location_id: Base string for location IDs
        
    Returns:
        List of Recommendation objects
    """
    all_species = create_test_species(species_per_location * location_count)
    recommendations: list[Recommendation] = []
    
    for i in range(location_count):
        loc_id = f"{base_location_id}{i}"
        species_offset = i * species_per_location
        species_subset = all_species[species_offset:species_offset + species_per_location]
        
        recommendations.append(
            Recommendation(
                location=loc_id,
                score=float(len(species_subset)),
                species=species_subset
            )
        )
    
    return recommendations


def create_test_life_list(species_list: list[Species] | None = None) -> LifeList:
    """Create a test life list with the given species.
    
    Args:
        species_list: List of species to include in the life list
        
    Returns:
        Life list dictionary mapping species codes to dates
    """
    if species_list is None:
        species_list = create_test_species(3)
        
    base_date = datetime(2023, 1, 1)
    return {
        species.species_code: base_date + timedelta(days=i)
        for i, species in enumerate(species_list)
    }


def create_test_sightings(
    species_list: list[Species] | None = None,
    location_count: int = 3,
    base_location_id: str = "L12345"
) -> Sightings:
    """Create test sightings data.
    
    Args:
        species_list: List of species to use (creates default of 3 if None)
        location_count: Number of locations to include
        base_location_id: Base string for location IDs, which will be suffixed with the index
        to create unique location IDs.
        
    Returns:
        Sightings dictionary where:
        first species is sighted at base_location_id0;
        second at base_location_id0 and base_location_id1; 
        third at base_location_id0, base_location_id1, and base_location_id2, etc.
    """
    if species_list is None:
        species_list = create_test_species(3)
        
    sightings: Sightings = {}
    for i, species in enumerate(species_list):
        # Distribute species across locations
        locs: set[str] = set()
        for j in range(min(location_count, i + 1)):
            locs.add(f"{base_location_id}{j}")
        sightings[species] = locs
        
    return sightings


# Mock response helpers for API tests
def create_mock_ebird_api_species_observation_response(species_list: list[Species] | None = None) -> list[dict[str, Any]]:
    """Create a mock eBird API response for observations.
    
    Args:
        species_list: List of species to include in the response
        
    Returns:
        List of dictionaries mimicking eBird API response format
    """
    if species_list is None:
        species_list = create_test_species(3)
        
    return [
        {
            'comName': species.common_name,
            'speciesCode': species.species_code,
            'sciName': species.scientific_name,
            'locationPrivate': False, 
            'locId': f"L12345{i}"
        }
        for i, species in enumerate(species_list)
    ]


def create_mock_taxonomy_response(species_list: list[Species] | None = None) -> list[dict[str, str]]:
    """Create a mock eBird taxonomy API response.
    
    Args:
        species_list: List of species to include in the response
        
    Returns:
        List of dictionaries mimicking eBird taxonomy API response format
    """
    if species_list is None:
        species_list = create_test_species(3)
        
    return [
        {
            'sciName': species.scientific_name,
            'speciesCode': species.species_code,
        }
        for species in species_list
    ]


def mock_url_response(data: Any, status: int = 200) -> MagicMock:
    """Create a mock URL response object.
    
    Args:
        data: Response data to return
        status: HTTP status code
        
    Returns:
        Mock object that can be used as the return value for urllib.request.urlopen
    """
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.read.return_value = json.dumps(data).encode('utf-8')
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value = mock_response
    return mock_urlopen