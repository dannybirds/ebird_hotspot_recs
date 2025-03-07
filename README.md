# Sitta

A bird lifer recommendation system that helps birders find new life birds by analyzing eBird data.

## Overview

Sitta helps birders maximize their chances of finding new life birds by analyzing historical eBird data and making intelligent recommendations for birding hotspots. The system compares a user's life list against historical sighting patterns to suggest locations with the highest probability of yielding new birds.

## Features

- Generate recommendations based on historical sighting data
- Multiple recommendation algorithms:
  - Day-specific historical sightings
  - Calendar month historical sightings
  - (Future) LLM-based intelligent recommendations
- Evaluation framework to assess algorithm performance
- Integration with eBird API and databases

## Installation

```bash
# Clone the repository
git clone https://github.com/dannybirds/ebird_hotspot_recs.git
cd sitta

# Install the package
pip install -e .
```

## Usage

### Command Line Interface

```bash
# Generate recommendations for a location
sitta --mode recommend --location L123456 --date 2023-05-15 --life_list mylife.csv

# Create evaluation dataset
sitta --mode make_e2e_eval_data --eval_observer_ids observers.csv --eval_file eval_data.json --date 2023-05-15

# Run evaluation
sitta --mode run_e2e_eval --eval_file eval_data.json
```

### As a Library

```python
from datetime import datetime
from sitta.data import parse_life_list_csv
from sitta.recommenders import AnyHistoricalSightingRecommender

# Load life list
life_list = parse_life_list_csv("mylife.csv")

# Create recommender
recommender = AnyHistoricalSightingRecommender(historical_years=5, day_window=7)

# Get recommendations
recommendations = recommender.recommend(
    location="L123456",
    target_date=datetime(2023, 5, 15),
    life_list=life_list
)

# Print recommendations
for rec in recommendations:
    print(f"Location: {rec.location}, Score: {rec.score}")
    for species in rec.species:
        print(f"  - {species.common_name} ({species.scientific_name})")
```

## Project Structure

```
sitta/                      # Main package directory
├── common/                 # Common data structures and utilities
├── data/                   # Data handling functionality
├── recommenders/           # Recommendation algorithms
├── evaluation/             # Evaluation framework
└── cli/                    # Command-line interfaces

tests/                      # Test directory
```

## Requirements

- Python 3.10+
- eBird API key (set as environment variable `EBIRD_API_KEY`)
- PostgreSQL database with eBird data as created by the ebird_db package (optional for some features)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.