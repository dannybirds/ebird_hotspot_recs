import argparse
import json
import logging
from datetime import datetime
import pprint
import sys
import os
import matplotlib.pyplot as plt
import numpy as np

from sitta.common.base import from_json_object_hook
from sitta.evaluation.metrics import EndToEndAggregateMetrics, EndToEndEvalDatapoint, aggregate_end_to_end_eval_metrics, run_end_to_end_evals
from sitta.recommenders.base import HotspotRecommender
from sitta.recommenders.heuristic import DayWindowHistoricalSightingRecommender, CalendarMonthHistoricalSightingRecommender

# Import Claude recommender classes
from sitta.recommenders.llm import ClaudeRecommender

logger = logging.getLogger(__name__)

def compare_recommenders(args: argparse.Namespace) -> None:
    """
    Compare multiple recommender algorithms on the same dataset.
    """
    # Load evaluation dataset
    with open(args.eval_file, 'r') as f:
        data_json = json.load(f, object_hook=from_json_object_hook)
    
    dataset = [EndToEndEvalDatapoint(**d) for d in data_json]
    print(f"Loaded {len(dataset)} datapoints.")
    
    # Select a subset for evaluation if specified
    if args.subset > 0 and args.subset < len(dataset):
        dataset = dataset[:args.subset]
        print(f"Using {len(dataset)} datapoints for evaluation.")
    
    # Define recommenders to compare
    recommenders: dict[str, HotspotRecommender] = {
        "Window-Based": DayWindowHistoricalSightingRecommender(historical_years=5, day_window=7),
        "Calendar-Month": CalendarMonthHistoricalSightingRecommender(historical_years=5),
    }
    
    # Add Claude recommender if API key is available
    claude_api_key = os.environ.get("ANTHROPIC_API_KEY") or args.claude_api_key
    if claude_api_key:
        recommenders.update({
            "Claude": ClaudeRecommender(api_key=claude_api_key, historical_years=5, day_window=7),
        })
    else:
        print("ANTHROPIC_API_KEY not found. Skipping Claude-based recommenders.")
    
    # Run evaluations
    results: dict[str, EndToEndAggregateMetrics] = {}
    for name, recommender in recommenders.items():
        print(f"\nEvaluating {name} recommender...")
        eval_results = run_end_to_end_evals(recommender, dataset, k=args.top_k)
        aggregated = aggregate_end_to_end_eval_metrics(eval_results)
        results[name] = aggregated
        
        print(f"Results for {name}:")
        pprint.pp(aggregated)
    
    # Calculate additional metrics
    print("\nAdditional Metrics:")
    for name, metrics in results.items():
        # Calculate precision, recall, F1
        precision = metrics.true_positives / (metrics.true_positives + metrics.false_positives) if (metrics.true_positives + metrics.false_positives) > 0 else 0
        recall = metrics.true_positives / (metrics.true_positives + metrics.false_negatives) if (metrics.true_positives + metrics.false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Calculate lifer effectiveness
        lifer_found_rate = metrics.found_lifers / (metrics.found_lifers + metrics.missed_lifers) if (metrics.found_lifers + metrics.missed_lifers) > 0 else 0
        
        print(f"\n{name}:")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1 Score: {f1:.4f}")
        print(f"  Lifer Found Rate: {lifer_found_rate:.4f}")
    
    # Save results to file
    if args.output:
        result_data: dict[str, dict[str, float]] = {
            name: {
                "found_lifers": metrics.found_lifers,
                "missed_lifers": metrics.missed_lifers,
                "abs_error": metrics.abs_error,
                "true_positives": metrics.true_positives,
                "false_positives": metrics.false_positives,
                "false_negatives": metrics.false_negatives,
                "precision": metrics.true_positives / (metrics.true_positives + metrics.false_positives) if (metrics.true_positives + metrics.false_positives) > 0 else 0,
                "recall": metrics.true_positives / (metrics.true_positives + metrics.false_negatives) if (metrics.true_positives + metrics.false_negatives) > 0 else 0,
                #"f1": 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0,
                "lifer_found_rate": metrics.found_lifers / (metrics.found_lifers + metrics.missed_lifers) if (metrics.found_lifers + metrics.missed_lifers) > 0 else 0
            } for name, metrics in results.items()
        }
        
        with open(args.output, 'w') as f:
            json.dump(result_data, f, indent=2)
        print(f"\nResults saved to {args.output}")
    
    # Visualize results if matplotlib is available
    try:
        plt.figure(figsize=(12, 8)) # type: ignore
        
        # Prepare data for plotting
        names = list(results.keys())
        precision_values = [results[name].true_positives / (results[name].true_positives + results[name].false_positives) if (results[name].true_positives + results[name].false_positives) > 0 else 0 for name in names]
        recall_values = [results[name].true_positives / (results[name].true_positives + results[name].false_negatives) if (results[name].true_positives + results[name].false_negatives) > 0 else 0 for name in names]
        f1_values = [2 * (p * r) / (p + r) if (p + r) > 0 else 0 for p, r in zip(precision_values, recall_values)]
        lifer_rates = [results[name].found_lifers / (results[name].found_lifers + results[name].missed_lifers) if (results[name].found_lifers + results[name].missed_lifers) > 0 else 0 for name in names]
        
        # Set up bar positions
        x = np.arange(len(names))
        width = 0.2
        
        # Create grouped bar chart
        plt.bar(x - 1.5*width, precision_values, width, label='Precision') # type: ignore
        plt.bar(x - 0.5*width, recall_values, width, label='Recall') # type: ignore
        plt.bar(x + 0.5*width, f1_values, width, label='F1 Score') # type: ignore
        plt.bar(x + 1.5*width, lifer_rates, width, label='Lifer Found Rate') # type: ignore
        
        plt.xlabel('Recommender') # type: ignore
        plt.ylabel('Score') # type: ignore
        plt.title('Recommender Performance Comparison') # type: ignore
        plt.xticks(x, names) # type: ignore
        plt.legend() # type: ignore
        plt.ylim(0, 1.0) # type: ignore
        
        # Add value labels
        for i, v in enumerate(precision_values):
            plt.text(i - 1.5*width, v + 0.02, f'{v:.2f}', ha='center', fontsize=8) # type: ignore
        for i, v in enumerate(recall_values):
            plt.text(i - 0.5*width, v + 0.02, f'{v:.2f}', ha='center', fontsize=8) # type: ignore
        for i, v in enumerate(f1_values):
            plt.text(i + 0.5*width, v + 0.02, f'{v:.2f}', ha='center', fontsize=8) # type: ignore
        for i, v in enumerate(lifer_rates):
            plt.text(i + 1.5*width, v + 0.02, f'{v:.2f}', ha='center', fontsize=8) # type: ignore
        
        # Show plot or save to file
        if args.plot_output:
            plt.savefig(args.plot_output) # type: ignore
            print(f"Plot saved to {args.plot_output}")
        else:
            plt.tight_layout()
            plt.show() # type: ignore
        
    except ImportError:
        print("Matplotlib not available for visualization.")

def main():
    parser = argparse.ArgumentParser(description="Evaluate and compare recommender algorithms.")
    parser.add_argument('--date', type=lambda s: datetime.strptime(s, "%Y-%m-%d") if s else datetime.today(), 
                        help='Target date as yyyy-mm-dd', default=None)
    parser.add_argument('--location', type=str, help='EBird location ID')
    parser.add_argument('--life_list', type=str, help='CSV file path to life list')
    parser.add_argument('--eval_observer_ids', type=str, help='path to observer IDs to use for make_e2e_eval_data')
    parser.add_argument('--eval_file', type=str, help='file to read or write e2e eval data from or to')
    parser.add_argument('--output', type=str, help='JSON file to save evaluation results')
    parser.add_argument('--plot_output', type=str, help='File to save comparison plot')
    parser.add_argument('--claude_api_key', type=str, help='Claude API key')
    parser.add_argument('--subset', type=int, help='Number of datapoints to use for evaluation', default=0)
    parser.add_argument('--top_k', type=int, help='Number of top recommendations to consider', default=3)
    
    args = parser.parse_args()

    # Configure logging to print everything to stdout
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(sys.stdout)])

    compare_recommenders(args)

if __name__ == "__main__":
    main()