import os
import json
import pandas as pd

from utils import load_statements
from classifyRecords import classify_records
from classifySports import classify_sports
from sports import SportsProcessor


UNIFIED_BATCH_SIZE = 5


def run_pipeline(input_data, output_path="Results.json"):
    
    all_statements = load_statements(input_data)
    if not all_statements:
        print("No valid statements found.")
        return

    record_labels = classify_records(all_statements, batch_size=UNIFIED_BATCH_SIZE)

    record_statements = [
        stmt for stmt, label in zip(all_statements, record_labels) if label == "Record"
    ]
    non_record_count = len(all_statements) - len(record_statements)
    print(f"Found {len(record_statements)} Record statements. Skipped {non_record_count} Non-Record.")

    if not record_statements:
        print("No Record statements to process further.")
        with open(output_path, 'w') as f:
            json.dump([], f, indent=2)
        return

    sport_results = classify_sports(record_statements, batch_size=UNIFIED_BATCH_SIZE)

    groups = {}
    for item in sport_results:
        sport = item["sport"]
        stmt = item["statement"]
        if sport in ["baseball", "basketball", "cricket", "soccer"]:
            groups.setdefault(sport, []).append(stmt)
        else:
            print(f"Skipping unsupported sport: '{sport}' for statement: {stmt[:50]}...")


    all_results = []

    for sport, statements in groups.items():
        print(f"Processing {len(statements)} {sport} statements...")
        
        try:
            processor = SportsProcessor(sport)
            results = processor.process_statements(statements, batch_size=UNIFIED_BATCH_SIZE)

            for r in results:
                r["sport"] = sport
                
            all_results.extend(results)
            print(f"Successfully processed {len(results)} {sport} statements")
            
        except Exception as e:
            print(f"Error processing {sport} statements: {e}")
            for stmt in statements:
                all_results.append({
                    "statement": stmt,
                    "sport": sport,
                    "error": f"Processing failed: {str(e)}"
                })
                
    

    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nFinal results saved to {output_path}")
    print(f"Total processed: {len(all_results)} statements across {len(groups)} sports")




if __name__ == "__main__":
    
    # 1. From list
    statements = [
        "Virat Kohli became highest scorer against England in an innings in T20s",
        "Kareem Abdul-Jabbar is just 10 points away from equalling Kobe Bryant, who has the highest number of points of all NBA players",
        "Aaron Judge and Shohei Ohtani have the second-highest number of homeruns in the 2025 MLB season",
        "Harry Maguire is the second-highest FIFA goal scorer and the highest goal scorer for Manchester United",
        "Sikandar Raza scored 107 runs off 52 balls for Zimbabwe against Gambia, the T20 century by a Zimbabwean batter since 2016"
    ]

    # 2. From CSV
    # statements = "statements.csv"

    run_pipeline(statements, output_path="Results.json")