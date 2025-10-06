import os
import csv
import sqlite3
import faiss
import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings


os.makedirs('db', exist_ok=True)
os.makedirs('vector_db', exist_ok=True)


SPORT_CONFIGS = {
    'baseball': {
        'db_name': 'db/baseball.db',
        'tables': {
            'player_performance': """CREATE TABLE IF NOT EXISTS player_performance (
                gamesPlayed INT, groundOuts INT, airOuts INT, runs INT, doubles INT, triples INT,
                homeRuns INT, strikeOuts INT, baseOnBalls INT, intentionalWalks INT, hits INT,
                hitByPitch INT, avg FLOAT, atBats INT, obp FLOAT, slg FLOAT, ops FLOAT,
                caughtStealing INT, stolenBases INT, stolenBasePercentage FLOAT,
                groundIntoDoublePlay INT, numberOfPitches INT, plateAppearances FLOAT,
                totalBases INT, rbi FLOAT, leftOnBase FLOAT, sacBunts INT, sacFlies INT,
                babip FLOAT, groundOutsToAirouts FLOAT, catchersInterference INT,
                atBatsPerHomeRun FLOAT, player_id INT, play_group TEXT, season INT,
                gamesStarted FLOAT, era FLOAT, inningsPitched FLOAT, wins FLOAT, losses FLOAT,
                saves FLOAT, saveOpportunities FLOAT, holds FLOAT, blownSaves FLOAT,
                earnedRuns FLOAT, whip FLOAT, battersFaced FLOAT, outs FLOAT,
                gamesPitched FLOAT, completeGames FLOAT, shutouts FLOAT, strikes FLOAT,
                strikePercentage FLOAT, hitBatsmen FLOAT, balks FLOAT, wildPitches FLOAT,
                pickoffs FLOAT, winPercentage FLOAT, pitchesPerInning FLOAT,
                gamesFinished FLOAT, strikeoutWalkRatio FLOAT, strikeoutsPer9Inn FLOAT,
                walksPer9Inn FLOAT, hitsPer9Inn FLOAT, runsScoredPer9 FLOAT,
                homeRunsPer9 FLOAT, inheritedRunners FLOAT, inheritedRunnersScored FLOAT,
                player_name TEXT, team_id INT, position TEXT, team_name TEXT,
                team_abbreviation TEXT, division TEXT, league TEXT
            )""",
            'teams': """CREATE TABLE IF NOT EXISTS teams (
                team_id INT, team_name TEXT
            )""",
            'players': """CREATE TABLE IF NOT EXISTS players (
                player_id INT, player_name TEXT, team_id INT
            )"""
        },
        'csv_files': {
            'teams': 'records/baseball/teams.csv',
            'players': 'records/baseball/players.csv',
            'player_performance': 'records/baseball/player_performance.csv'
        },
        'team_query': "SELECT DISTINCT team_id, team_name FROM teams",
        'player_query': "SELECT DISTINCT player_id, player_name FROM players"
    },
    'basketball': {
        'db_name': 'db/basketball.db',
        'tables': {
            'player_performance': """CREATE TABLE IF NOT EXISTS player_performance (
                PLAYER_ID INT, SEASON_ID STR, TEAM_ID INT, TEAM_ABBREVIATION TEXT,
                PLAYER_AGE FLOAT, GP INT, GS FLOAT, MIN FLOAT, FGM INT, FGA INT,
                FG_PCT FLOAT, FG3M FLOAT, FG3A FLOAT, FG3_PCT FLOAT, FTM INT, FTA INT,
                FT_PCT FLOAT, OREB FLOAT, DREB FLOAT, REB FLOAT, AST INT, STL FLOAT,
                BLK FLOAT, TOV FLOAT, PF INT, PTS INT, PLAYER_NAME TEXT,
                Cumulative_Points INT, Cumulative_AST INT, Cumulative_REB FLOAT
            )""",
            'teams': """CREATE TABLE IF NOT EXISTS teams (
                TEAM_ID INT, TEAM_ABBREVIATION TEXT
            )""",
            'players': """CREATE TABLE IF NOT EXISTS players (
                PLAYER_ID INT, PLAYER_NAME TEXT, TEAM_ID INT
            )"""
        },
        'csv_files': {
            'teams': 'records/basketball/teams.csv',
            'players': 'records/basketball/players.csv',
            'player_performance': 'records/basketball/player_performance.csv'
        },
        'team_query': "SELECT DISTINCT TEAM_ID, TEAM_ABBREVIATION FROM teams",
        'player_query': "SELECT DISTINCT PLAYER_ID, PLAYER_NAME FROM players"
    },
    'cricket': {
        'db_name': 'db/cricket.db',
        'tables': {
            'player_performance': """CREATE TABLE IF NOT EXISTS player_performance (
                match_id INT, match_name TEXT, match_date DATETIME, match_venue TEXT,
                match_city TEXT, match_type TEXT, player_id INT, player_name TEXT,
                team_id INT, team_name TEXT, opponent_team_id INT, opponent_team_name TEXT,
                runs_scored_in_inning INT, balls_played_in_inning INT, fours_in_inning INT,
                sixes_in_inning INT, batting_position INT, fifty_in_balls INT,
                hundred_in_balls INT, wicket_taken_in_inning INT, balls_bowled_in_inning INT,
                runs_conceded_in_inning INT, fours_conceded_in_inning INT,
                sixes_conceded_in_inning INT, maiden_in_inning INT, economy FLOAT,
                is_out INT, is_player_of_match INT, venue_id INT
            )""",
            'teams': """CREATE TABLE IF NOT EXISTS teams (
                team_id INT, team_name TEXT
            )""",
            'players': """CREATE TABLE IF NOT EXISTS players (
                player_id INT, player_name TEXT, team_id INT
            )"""
        },
        'csv_files': {
            'teams': 'records/cricket/teams.csv',
            'players': 'records/cricket/players.csv',
            'player_performance': 'records/cricket/player_performance.csv'
        },
        'team_query': "SELECT DISTINCT team_name, team_id FROM teams",
        'player_query': "SELECT DISTINCT player_name, player_id FROM players"
    },
    'soccer': {
        'db_name': 'db/soccer.db',
        'tables': {
            'player_performance': """CREATE TABLE IF NOT EXISTS player_performance (
                Position TEXT, PlayingTime_MP INT, PlayingTime_Starts INT, PlayingTime_Min INT,
                PlayingTime_90s FLOAT, Performance_Gls INT, Performance_Ast INT,
                Performance_GPlusA INT, Performance_GMinusPK INT, Performance_PK INT,
                Performance_PKatt INT, Performance_CrdY INT, Performance_CrdR INT,
                Expected_xG FLOAT, Expected_npxG FLOAT, Expected_xAG FLOAT,
                Expected_npxGPlusxAG FLOAT, Progression_PrgC INT, Progression_PrgP INT,
                Progression_PrgR INT, Per90Minutes_Gls FLOAT, Per90Minutes_Ast FLOAT,
                Per90Minutes_GPlusA FLOAT, Per90Minutes_GMinusPK FLOAT,
                Per90Minutes_GPlusAMinusPK FLOAT, Per90Minutes_xG FLOAT,
                Per90Minutes_xAG FLOAT, Per90Minutes_xGPlusxAG FLOAT,
                Per90Minutes_npxG FLOAT, Per90Minutes_npxGPlusxAG FLOAT,
                player_name TEXT, team_name TEXT, player_id INT, team_id INT
            )""",
            'teams': """CREATE TABLE IF NOT EXISTS teams (
                team_id INT, team_name TEXT
            )""",
            'players': """CREATE TABLE IF NOT EXISTS players (
                player_id INT, player_name TEXT, team_id INT
            )"""
        },
        'csv_files': {
            'teams': 'records/soccer/teams.csv',
            'players': 'records/soccer/players.csv',
            'player_performance': 'records/soccer/player_performance.csv'
        },
        'team_query': "SELECT DISTINCT team_id, team_name FROM teams",
        'player_query': "SELECT DISTINCT player_id, player_name FROM players"
    }
}


def csv_to_db(sport_config, table_name):
    csv_file = sport_config['csv_files'][table_name]
    db_name = sport_config['db_name']
    
    with sqlite3.connect(db_name) as con:
        cur = con.cursor()
        cur.execute(sport_config['tables'][table_name])

        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            
            try:
                headers = next(reader)
                expected_columns = len(headers)
                print(f"{sport_config['db_name']} - {table_name}: Header defines {expected_columns} columns.")
            except StopIteration:
                print(f"Error: CSV file '{csv_file}' is empty.")
                return

            placeholders = ','.join(['?'] * expected_columns)
            insert_query = f"INSERT OR IGNORE INTO {table_name} VALUES ({placeholders})"

            rows_to_insert = []
            skipped_count = 0
            processed_count = 0

            for row in reader:
                processed_count += 1
                row_length = len(row)

                if row_length == expected_columns:
                    cleaned_row = [field.strip() if isinstance(field, str) else field for field in row]
                    rows_to_insert.append(cleaned_row)
                else:
                    skipped_count += 1

            if rows_to_insert:
                print(f"Inserting {len(rows_to_insert)} valid rows (skipped {skipped_count} inconsistent rows)...")
                try:
                    cur.executemany(insert_query, rows_to_insert)
                    print(f"Successfully inserted/ignored {cur.rowcount} rows into '{table_name}'.")
                except sqlite3.Error as e:
                    print(f"Database error during insertion: {e}")
            else:
                print(f"No valid rows found to insert into '{table_name}' (skipped {skipped_count} rows).")
        
        print(f"Finished processing '{csv_file}' for table '{table_name}'.\n")

def execute_query(query, db_name):
    query_lower = query.lower()

    try:
        with sqlite3.connect(db_name) as con:
            cur = con.cursor()
            cur.execute(query)

            if query_lower.strip().startswith('select'):
                results = cur.fetchall()
                col_names = [desc[0] for desc in cur.description] if cur.description else []
                return col_names, results 
            else:
                return [], []

    except sqlite3.Error as e:
        print(f"SQL error: {e}")
        return [], []
    except Exception as e:
        print(f"Error: {e}")
        return [], []

def load_entity_data(sport_config):
    db_name = sport_config['db_name']
    
    col_names, team_results = execute_query(sport_config['team_query'], db_name)
    if sport_config['team_query'].lower().find('team_name, team_id') != -1:
        team_names = [row[0] for row in team_results]
        team_ids = [row[1] for row in team_results]
    else:
        team_ids = [row[0] for row in team_results]
        team_names = [row[1] for row in team_results]
    
    col_names, player_results = execute_query(sport_config['player_query'], db_name)
    if sport_config['player_query'].lower().find('player_name, player_id') != -1:
        player_names = [row[0] for row in player_results]
        player_ids = [row[1] for row in player_results]
    else:
        player_ids = [row[0] for row in player_results]
        player_names = [row[1] for row in player_results]
    
    return team_ids, team_names, player_ids, player_names

def create_vector_store(sport, sport_config):
    print(f"\n=== Processing {sport} ===")
    
    csv_to_db(sport_config, 'teams')
    csv_to_db(sport_config, 'players')
    csv_to_db(sport_config, 'player_performance')
    
    team_ids, team_names, player_ids, player_names = load_entity_data(sport_config)
    
    embedding_function = HuggingFaceEmbeddings(
        model_name='/scratch/nitishk_iitp/models/paraphrase-MiniLM-L6-v2'
    )
    
    if team_names:
        teams_embedding = embedding_function.embed_documents(team_names)
        teams_embedding = np.array(teams_embedding, dtype=np.float32)
        
        teams_dimension = teams_embedding.shape[1]
        teams_index = faiss.IndexHNSWFlat(teams_dimension, 32)
        teams_index.add(teams_embedding)
        
        team_id_array = np.array(team_ids)
        faiss.write_index(teams_index, f'vector_db/{sport}_team_index.bin')
        np.save(f'vector_db/{sport}_team_ids.npy', team_id_array)
        print(f"Created team vector store for {sport}")
    
    if player_names:
        players_embedding = embedding_function.embed_documents(player_names)
        players_embedding = np.array(players_embedding, dtype=np.float32)
        
        players_dimension = players_embedding.shape[1]
        players_index = faiss.IndexFlatL2(players_dimension)
        players_index.add(players_embedding)
        
        player_id_array = np.array(player_ids)
        faiss.write_index(players_index, f'vector_db/{sport}_player_index.bin')
        np.save(f'vector_db/{sport}_player_ids.npy', player_id_array)
        print(f"Created player vector store for {sport}")

    
def main():   
    for sport, config in SPORT_CONFIGS.items():
        try:
            create_vector_store(sport, config)
            print(f"Completed {sport}")
        except Exception as e:
            print(f"Error processing {sport}: {e}")
    
    print("All sports processed!")


if __name__ == "__main__":
    main()