# Potential Records To Be Broken

An LLM-based end-to-end pipeline that processes sports record-type statements, and generates SQL queries to verify statistical claims across multiple sports domains.

## Features

- **Record-type Statement Classification**: Automatically identifies Record vs Non-Record statements
- **Sport Categorization**: Classifies the statements into their respective sports (Baseball/Basketball/Cricket/Soccer)
- **Query Understanding**: Extracts named entities, game-specific contraints, and the statistical record context from the statements
- **Entity Resolution**: Uses FAISS vector search(to get candidate entities) + SQL retrieval(of game statistics) to disambiguate entities and then inject entity metadata into the SQL query
- **SQL Generation**: Converts the natural language statistical record context to an executable SQL query for each statement

## Architecture

The system follows a sophisticated pipeline:

### Core Components

1. **Record Classifier** - Identifies record-breaking statements
2. **Sport Classifier** - Categorizes statements into specific sports
3. **Sports Processor** - Unified processor for all sports with:
   - Query Understanding
   - Entity resolution
   - SQL query generation
   - Query execution & output result
4. **Vector Databases** - FAISS indices for entity lookup
5. **SQL Databases** - Sport-specific statistical databases

## Installation

```bash
cd <your_project_directory>/
```

```bash
git clone https://github.com/khyaati/PotentialRecordsToBeBroken.git
```

```bash
conda create --name sports_env python=3.10
conda activate sports_env 
pip install -r requirements.txt
```

## Database Set Up

- `records/` contains the datasets of all 4 sports

```bash
python vector_store.py
```

- This will create 2 directories namely, `db/` and `vector_db/`
- The SQL databases generated will be stored in `db/`
- The vector databases created for entity lookup will be stored in `vector_db/`

## Usage

- Scroll to the bottom of `main.py`
- Either add your statements to the list
- OR paste the path to your CSV file
- Then run:

```bash
python main.py
```

- Output will be saved to `Results.json`

## Datasets Created

**Human-labelled:**

- `LABELLED_DATASETS/Human/` contain 2 CSV files as below
- `record_statements.csv` is a collection of 2733 statements human-classified 'Record' or 'Non-Record'
- `sport_statements.csv` is a collection of 931 'Record' statements human-classified sport-wise (i.e., baseball, basketball, cricket, soccer)

**LLM-labelled:**

- `LABELLED_DATASETS/LLM/` contains 2 CSV files as below
- `record_classified.csv` is a collection of 58,464 statements classified as 'Record' or 'Non-Record' by `Llama-3.3-70B-Instruct` (~97% precision on test set)
- `sport_classified.csv` is a collection of 2734 'Record' statements classified sports-wise (i.e., baseball, basketball, cricket, soccer) by `Llama-3.1-8B` (~99% precision on test set)

## Cricket Data Creation

- Raw JSON files containing match-wise data were obtained from [www.cricsheet.org](https://www.cricsheet.org)
(Men's T20I)
- A script was then designed to curate the JSON data into CSV files to best suit the pipeline
- Note that `records/cricket/` directory already contains the cricket data needed to test this pipeline
- To create your own, download the JSON data from the above mentioned source, add its path to the script, and then run:

```bash
python extractStats/schema_cricket.py
```

## Quick Example

**Input Statement:**
"Virat Kohli became the highest scorer against England in T20s."

**System Output:**

- Identifies as "Record" statement
- Classifies as "Cricket" sport
- Extracts out the exact record context, here, "highest scorer against England in T20s"  
- Resolves "Virat Kohli" and "England" entities, and maps them to their IDs in the database
- Generates and executes a SQL query based on the record context extracted
- Returns statistical verification for the record claim in the input statement
