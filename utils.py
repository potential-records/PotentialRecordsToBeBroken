import os
import pandas as pd

def load_statements(input_data):
    
    if isinstance(input_data, list):
        statements = [str(s) for s in input_data if pd.notna(s)]
        return statements
    
    elif isinstance(input_data, str) and os.path.isfile(input_data):
        df = pd.read_csv(input_data)
        statements = df[df.columns[0]].dropna().astype(str).tolist()
        return statements
    
    else:
        raise ValueError("Input must be a list of strings or a valid CSV file path.")