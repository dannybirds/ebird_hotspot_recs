import os
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Optional
from datetime import datetime

from common import LifeList, Recommendation, Species
from recommenders import AnyHistoricalSightingRecommender, CalendarMonthHistoricalSightingRecommender, HotspotRecommender, sightings_to_recommendations
from data_handling import get_historical_species_seen_in_window, get_historical_species_seen_in_calendar_month

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
        
    def recommend(self, location: str, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        """
        Recommend hotspots based on Claude's analysis of historical data.
        
        Parameters:
        location (str): The eBird location ID.
        target_date (datetime): The target date for birding.
        life_list (LifeList): The user's life list.
        
        Returns:
        list[Recommendation]: A list of recommendations.
        """
        # Get historical data
        historical_window = get_historical_species_seen_in_window(
            location, target_date, num_years=self.historical_years, day_window=self.day_window
        )
        
        historical_month = get_historical_species_seen_in_calendar_month(
            location, target_date, num_years=self.historical_years
        )
        
        # Filter out species already on life list
        historical_window = {k: v for k, v in historical_window.items() if k.species_code not in life_list}
        historical_month = {k: v for k, v in historical_month.items() if k.species_code not in life_list}
        
        # Format data for Claude
        prompt = f"""
        I need recommendations for birding hotspots in location '{location}' on {target_date.strftime('%Y-%m-%d')}.
        
        The user has the following life list (species they've already seen):
        {self.format_life_list(life_list)}
        
        Historical species seen within {self.day_window} days of this date in the past {self.historical_years} years:
        {self.format_species_data(historical_window)}
        
        Historical species seen in the same calendar month in the past {self.historical_years} years:
        {self.format_species_data(historical_month)}
        
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
            response = self.call_claude(prompt)
            response_content = response["content"][0]["text"]
            
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
                        # If not found in window data, check month data
                        elif not matching_species:
                            matching_species = [s for s in historical_month.keys() if s.species_code == species_code]
                            if matching_species:
                                species_list.append(matching_species[0])
                    
                    recommendations.append(
                        Recommendation(
                            location=rec["location"],
                            score=float(rec["score"]) * 10,  # Scale to be comparable with other recommenders
                            species=species_list
                        )
                    )
                
                return recommendations
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing Claude response: {e}")
                print(f"Response was: {response_content}")
                # Fallback to the historical data recommender
                return sightings_to_recommendations(historical_window)
                
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            # Fallback to the historical data recommender
            return sightings_to_recommendations(historical_window)


class HybridRecommender(HotspotRecommender):
    """
    A recommender that combines multiple recommendation approaches, including a Claude-based recommender.
    """
    
    def __init__(
        self,
        historical_years: int = 5,
        day_window: int = 7,
        claude_api_key: Optional[str] = None,
        claude_weight: float = 0.7,
        historical_window_weight: float = 0.2,
        historical_month_weight: float = 0.1
    ):
        """
        Initialize the hybrid recommender.
        
        Parameters:
        historical_years (int): Number of years of historical data to consider.
        day_window (int): Window size in days around the target date.
        claude_api_key (str, optional): The Claude API key.
        claude_weight (float): Weight for Claude's recommendations.
        historical_window_weight (float): Weight for historical window recommendations.
        historical_month_weight (float): Weight for historical month recommendations.
        """
        self.claude_recommender = ClaudeRecommender(
            api_key=claude_api_key,
            historical_years=historical_years,
            day_window=day_window
        )
        self.historical_window_recommender = AnyHistoricalSightingRecommender(
            historical_years=historical_years,
            day_window=day_window
        )
        self.historical_month_recommender = CalendarMonthHistoricalSightingRecommender(
            historical_years=historical_years
        )
        
        self.claude_weight = claude_weight
        self.historical_window_weight = historical_window_weight
        self.historical_month_weight = historical_month_weight
        
        # Ensure weights sum to 1
        total_weight = claude_weight + historical_window_weight + historical_month_weight
        if abs(total_weight - 1.0) > 0.001:
            self.claude_weight /= total_weight
            self.historical_window_weight /= total_weight
            self.historical_month_weight /= total_weight
    
    def recommend(self, location: str, target_date: datetime, life_list: LifeList) -> list[Recommendation]:
        """
        Get recommendations from all recommenders and blend them together.
        
        Parameters:
        location (str): The eBird location ID.
        target_date (datetime): The target date for birding.
        life_list (LifeList): The user's life list.
        
        Returns:
        list[Recommendation]: A list of recommendations.
        """
        # Get recommendations from each recommender
        claude_recs = self.claude_recommender.recommend(location, target_date, life_list)
        window_recs = self.historical_window_recommender.recommend(location, target_date, life_list)
        month_recs = self.historical_month_recommender.recommend(location, target_date, life_list)
        
        # Combine all recommendations
        all_locs: set[str] = set()
        for rec_list in [claude_recs, window_recs, month_recs]:
            for rec in rec_list:
                all_locs.add(rec.location)
        
        # Create weighted score for each location
        location_to_rec: dict[str, Recommendation] = {}
        for loc in all_locs:
            # Find each recommender's score for this location
            claude_score = next((rec.score for rec in claude_recs if rec.location == loc), 0)
            window_score = next((rec.score for rec in window_recs if rec.location == loc), 0)
            month_score = next((rec.score for rec in month_recs if rec.location == loc), 0)
            
            # Calculate weighted score
            weighted_score = (
                claude_score * self.claude_weight +
                window_score * self.historical_window_weight +
                month_score * self.historical_month_weight
            )
            
            # Combine species lists from all recommenders
            species_set: set[Species] = set()
            for rec_list in [claude_recs, window_recs, month_recs]:
                for rec in rec_list:
                    if rec.location == loc:
                        species_set.update(rec.species)
            
            location_to_rec[loc] = Recommendation(
                location=loc,
                score=weighted_score,
                species=list(species_set)
            )
        
        # Convert to list and sort by score
        recs = list(location_to_rec.values())
        recs.sort(key=lambda r: r.score, reverse=True)
        
        return recs