import os
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Optional
from datetime import datetime

from sitta.data.ebird_api import EBirdAPIDataProvider
from sitta.common.base import LifeList, Recommendation, Species, TargetArea, TargetAreaType
from sitta.recommenders.base import  HotspotRecommender

class ClaudeRecommender(HotspotRecommender):
    """
    A recommender that uses Claude to analyze historical birding data and make recommendations.
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "claude-3-7-sonnet-20250219",
        historical_years: int = 5,
        day_window: int = 7,
        max_tokens: int = 4000,
        temperature: float = 0
    ):
        """
        Initialize the Claude recommender.
        
        Parameters:
        api_key (str, optional): The Claude API key. If None, will try to get from ANTHROPIC_API_KEY env var.
        model (str): The Claude model to use.
        historical_years (int): Number of years of historical data to consider.
        day_window (int): Window size in days around the target date.
        max_tokens (int): Maximum tokens in Claude's response.
        temperature (float): Temperature parameter for Claude (0.0 = deterministic).
        """
        t_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not t_api_key:
            raise ValueError("API key must be provided or set as ANTHROPIC_API_KEY environment variable")
        
        self.api_key: str = t_api_key
        self.model = model
        self.historical_years = historical_years
        self.day_window = day_window
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.provider = EBirdAPIDataProvider()
        
    def call_claude(self, prompt: str) -> dict[str, Any]:
        """
        Call the Claude API with a prompt using Python's built-in urllib.
        
        Parameters:
        prompt (str): The prompt to send to Claude.
        
        Returns:
        dict: The parsed JSON response from Claude.
        """
        headers: dict[str, str] = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        data: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "system": "You are an expert birding and wildlife assistant. You analyze birding data and make recommendations based on patterns."
        }
        
        # Convert data to JSON string and encode as bytes
        data_bytes = json.dumps(data).encode('utf-8')
        
        # Create request object
        url = "https://api.anthropic.com/v1/messages"
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        
        try:
            # Make the request
            with urllib.request.urlopen(req) as response:
                response_body = response.read().decode('utf-8')
                if response.getcode() != 200:
                    raise Exception(f"API call failed: {response.getcode()} {response_body}")
                return json.loads(response_body)
        except urllib.error.HTTPError as e:
            # Handle HTTP errors
            error_body = e.read().decode('utf-8')
            raise Exception(f"API call failed: {e.code} {error_body}")
    
    def format_species_data(self, species_data: dict[Species, set[str]]) -> str:
        """Format the species data for including in the prompt."""
        formatted_data: list[dict[str, Any]] = []
        for species, locations in species_data.items():
            formatted_data.append({
                "common_name": species.common_name,
                "scientific_name": species.scientific_name,
                "species_code": species.species_code,
                "locations": list(locations)
            })
        return json.dumps(formatted_data, indent=2)
    
    def format_life_list(self, life_list: LifeList) -> str:
        """Format the life list for including in the prompt."""
        return json.dumps({k: v.isoformat() for k, v in life_list.items()}, indent=2)
        
    def recommend(self, target_area: TargetArea, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        """
        Recommend hotspots based on Claude's analysis of historical data.
        
        Parameters:
        location (str): The eBird location ID.
        target_date (datetime): The target date for birding.
        life_list (LifeList): The user's life list.
        
        Returns:
        list[Recommendation]: A list of recommendations.
        """
        if target_area.area_type == TargetAreaType.LAT_LONG or target_area.area_id is None:
            raise NotImplementedError("Lat long targeting not yet implemented.")

        # Get historical data
        historical_window = self.provider.get_historical_species_seen_in_window(
            target_area.area_id, target_date, num_years=self.historical_years, day_window=self.day_window
        )
        
        # Filter out species already on life list
        #historical_window = {k: v for k, v in historical_window.items() if k.species_code not in life_list}
        
        # Format data for Claude
        prompt = f"""
        I need recommendations for birding hotspots in target area '{target_area}' on {target_date.strftime('%Y-%m-%d')}.
        
        The user has the following life list (species they've already seen):
        {self.format_life_list(life_list)}
        
        Historical species seen within {self.day_window} days of this date in the past {self.historical_years} years:
        {self.format_species_data(historical_window)}
                
        Based on this data, please analyze:
        1. Which species are most likely to be seen on the target date that aren't on the life list?
        2. Which locations have the highest probability of yielding new lifers?
        3. Any patterns in the data that suggest particular species or locations might be more promising?
        
        Return your recommendations in this exact JSON format:
        {{
            "recommendations": [
                {{
                    "location": "location_id",
                    "score": 0.95,  // A score between 0 and 1 reflecting confidence
                    "species": ["species_code1", "species_code2"]  // Species codes for expected lifers
                }},
                ...
            ]
        }}
        
        Only include the JSON in your response, no other text.
        """
        
        # Call Claude
        try:
            print("====== CLAUDE RECOMMENDER ===")
            print(f"Calling Claude with prompt: {prompt}")
            #response = self.call_claude(prompt)
            #response_content = response["content"][0]["text"]

            # TEMPORARY: Simulate a response for testing
            response_content = """
{
    "recommendations": [
        {
            "location": "L268000",
            "score": 0.92,
            "species": ["ameavo", "sooshe", "briter1", "norgan", "shbdow", "comeid", "redkno", "margod"]
        },
        {
            "location": "L566310",
            "score": 0.89,
            "species": ["pipplo", "redkno", "wessan", "buwtea", "margod", "manshe", "greshe", "wispet"]
        },
        {
            "location": "L2865928",
            "score": 0.85,
            "species": ["whfibi", "triher", "shbdow", "seaspa", "clarai11"]
        },
        {
            "location": "L109152", 
            "score": 0.82,
            "species": ["yehbla", "rostern1", "rudtur", "semsan", "semplo"]
        },
        {
            "location": "L2113967",
            "score": 0.78,
            "species": ["ameavo", "shbdow", "seaspa", "whrsan", "willet1"]
        },
        {
            "location": "L283564",
            "score": 0.75,
            "species": ["triher", "rebmer", "blkski", "seaspa"]
        },
        {
            "location": "L123004",
            "score": 0.72,
            "species": ["sumtan", "yebcha", "chwwid", "blugrb1"]
        },
        {
            "location": "L9315964",
            "score": 0.68,
            "species": ["norhar2", "seaspa", "clarai11", "sstspa"]
        },
        {
            "location": "L273407",
            "score": 0.65,
            "species": ["leabit", "marwre", "virrai", "swaspa"]
        },
        {
            "location": "L715762",
            "score": 0.63,
            "species": ["louwat", "woewar1", "rehwoo"]
        }
    ]
}
"""
            
            # Extract JSON from response
            try:
                json_start = response_content.find("{")
                json_end = response_content.rfind("}") + 1
                json_str = response_content[json_start:json_end]
                result = json.loads(json_str)
                
                # Convert to Recommendation objects
                recommendations: list[Recommendation] = []
                for rec in result.get("recommendations", []):
                    # Find Species objects for the recommended species
                    species_list: list[Species] = []
                    for species_code in rec.get("species", []):
                        matching_species = [s for s in historical_window.keys() if s.species_code == species_code]
                        if matching_species:
                            species_list.append(matching_species[0])
                    
                    recommendations.append(
                        Recommendation(
                            locality_id=rec["location"],
                            score=float(rec["score"]) * 10,  # Scale to be comparable with other recommenders
                            species=species_list
                        )
                    )
                
                return recommendations
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing Claude response: {e}")
                print(f"Response was: {response_content}")
                raise e
                
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            raise e
