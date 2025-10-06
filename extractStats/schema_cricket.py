import os
import json
import pandas as pd
import logging
from difflib import SequenceMatcher


def setup_logger():
    logger = logging.getLogger('CricketDataProcessor')
    logger.setLevel(logging.INFO)
    
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler('cricket_data_processing.log')
    c_handler.setLevel(logging.INFO)
    f_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(formatter)
    f_handler.setFormatter(formatter)
    
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)
    
    return logger


logger = setup_logger()


def clean_venue_name(venue_name):
    if pd.isna(venue_name) or not isinstance(venue_name, str):
        return venue_name
    return venue_name.split(',')[0].strip()


def similar(a, b, threshold=0.85):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def group_similar_venues(venues_list, threshold=0.85):
    logger.info("Grouping similar venues...")
    groups = {}
    name_counts = {}
    
    for venue in venues_list:
        name = clean_venue_name(venue['venue'])
        if name:
            name_counts[name] = name_counts.get(name, 0) + 1
    
    remaining = sorted(venues_list, key=lambda x: -name_counts.get(clean_venue_name(x['venue']), 0))
    
    while remaining:
        current = remaining.pop(0)
        current_venue = clean_venue_name(current['venue'])
        current_city = current['city']
        
        if not current_venue:
            continue

        matched = False
        
        for group_key in groups:
            if similar(current_venue, group_key, threshold):
                matched = True
                break
                
        if not matched:
            groups[current_venue] = current_city
    
    logger.info(f"Grouped {len(venues_list)} venues into {len(groups)} unique venues")
    return groups


def create_venue_table(match_info_list):
    logger.info("Creating venue table...")
    all_venues = {}

    for match in match_info_list:
        venue = clean_venue_name(match.get('venue', ''))
        city = match.get('city', '').strip()

        if venue and venue not in all_venues:
            all_venues[venue] = city

    venues_list = [{'venue': v, 'city': c} for v, c in all_venues.items()]
    grouped_venues = group_similar_venues(venues_list)
    
    venue_rows = []
    
    for venue_id, (venue_name, city) in enumerate(grouped_venues.items(), 1):
        venue_rows.append({
            'venue_id': int(venue_id),
            'venue_name': venue_name,
            'city': city
        })
        
    venue_df = pd.DataFrame(venue_rows)
    logger.info(f"Created venue table with {len(venue_df)} entries")
    return venue_df


def add_venue_ids_to_match_info(match_info_df, venue_df):
    logger.info("Adding venue IDs to match info...")
    venue_df = venue_df.copy()
    venue_df['venue_id'] = venue_df['venue_id'].astype(int)

    venue_mapping = (venue_df.drop_duplicates('venue_name').set_index('venue_name')['venue_id'].to_dict())
    venue_mapping.update({k.lower(): v for k, v in venue_mapping.items()})

    match_info_df['venue_id'] = (match_info_df['venue'].str.strip().map(venue_mapping).astype('Int64'))
    logger.info("Venue IDs added to match info")
    return match_info_df


match_info_list = []
teams_set = set()
players_dict = {}
player_performance_dict = {}
ball_by_ball_list = []
match_officials_list = []
officials_set = set()
match_players_list = []
player_partnership_dict = {}
batter_vs_bowler_dict = {}
wicket_dict = {}
team_stat_dict = {}
venue_dict = {}


def extract_match_info(data, match_id, player_df, team_df, file):
    logger.debug(f"Extracting match info for match {match_id}")
    raw_venue = data["info"].get("venue", "").strip()
    cleaned_venue = clean_venue_name(raw_venue)
    
    match_info = {
        "match_id": match_id,
        "match_name": data["info"]["event"]["name"] if "event" in data["info"] else "",
        "match_type": data["info"].get("match_type", ""),
        "city": data["info"]["city"] if "city" in data["info"] else "",
        "venue_id": None,
        "venue": cleaned_venue,
        "date": data["info"]["dates"][0],
        "team_1": team_df[team_df['team_name'] == data["info"]["teams"][0]].iloc[0]['team_id'],
        "team_2": team_df[team_df['team_name'] == data["info"]["teams"][1]].iloc[0]['team_id'],
        "toss_winner": team_df[team_df['team_name'] == data["info"]["toss"]["winner"]].iloc[0]['team_id'],
        "toss_decision": data["info"]["toss"]["decision"],
        "winner": data["info"]["outcome"]["winner"] if "winner" in data["info"]["outcome"] else data["info"]["outcome"]["result"],
        "result": ('by ' + str(list(data["info"]["outcome"]["by"].values())[0]) + ' ' + list(data["info"]["outcome"]["by"].keys())[0] if "winner" in data["info"]["outcome"] and "by" in data["info"]["outcome"] else ""),
        "player_of_match": player_df[player_df['player_name'] == data["info"]["player_of_match"][0]].iloc[0]['player_id'] if "player_of_match" in data["info"] else 0
    }

    match_info_list.append(match_info)


def extract_team_info(data):
    if "info" in data and "teams" in data["info"]:
        for team in data["info"]["teams"]:
            teams_set.add(team)


def extract_player_info(data, team_df):
    if "info" in data and "players" in data["info"]:
        for team, player_list in data["info"]["players"].items():
            for player in player_list:
                players_dict[(player, team)] = {
                    "player_name": player,
                    "team_id": team_df[team_df['team_name'] == team].iloc[0]['team_id']
                }


def extract_venue_info(data):
    if "info" in data:
        city = data["info"].get("city", "")
        raw_venue = data["info"].get("venue", "").strip()
        cleaned_venue = clean_venue_name(raw_venue)
        
        venue_dict[cleaned_venue] = {
            "city": city,
            "venue": cleaned_venue
        }


def create_player_performance(data, match_id, player_df, team_df):
    logger.debug(f"Creating player performance data for match {match_id}")
    if "info" not in data or "innings" not in data:
        logger.warning(f"No innings data found for match {match_id}")
        return

    teams = data["info"].get("teams", [])
    
    if len(teams) != 2:
        logger.warning(f"Invalid number of teams ({len(teams)}) for match {match_id}")
        return

    info = data["info"]
    innings = data["innings"][:2]
    
    raw_venue = info.get("venue", "")
    cleaned_venue = clean_venue_name(raw_venue)

    batting_positions = {}
    runs_scored = {}

    for inning in innings:
        team = inning["team"]
        try:
            team_id = team_df[team_df['team_name'] == team].iloc[0]['team_id']
        except IndexError:
            logger.warning(f"Team {team} not found in team_df for match {match_id}")
            continue

        position = 1
        for over in inning.get("overs", []):
            for delivery in over.get("deliveries", []):
                batter = delivery.get("batter", "")
                if batter:
                    key = (batter, team_id)
                    if key not in batting_positions:
                        batting_positions[key] = position
                        position += 1
                    runs_scored[key] = runs_scored.get(key, 0) + delivery.get("runs", {}).get("batter", 0)

    for team in teams:
        try:
            team_id = team_df[team_df['team_name'] == team].iloc[0]['team_id']
            opponent_team = teams[1] if team == teams[0] else teams[0]
            opponent_team_id = team_df[team_df['team_name'] == opponent_team].iloc[0]['team_id']
        except IndexError:
            logger.warning(f"Team {team} not found in team_df for match {match_id}")
            continue

        for player in info["players"].get(team, []):
            try:
                player_id = player_df[(player_df['player_name'] == player) & (player_df['team_id'] == team_id)].iloc[0]['player_id']
            except IndexError:
                logger.warning(f"Player {player} not found in player_df for match {match_id}")
                continue

            player_key = (match_id, player, team_id)

            runs = runs_scored.get((player, team_id), 0)
            batting_position = batting_positions.get((player, team_id), 0)

            player_performance_dict[player_key] = {
                "match_id": match_id,
                "match_name": info.get("event", {}).get("name", ""),
                "match_date": info.get("dates", [""])[0],
                "match_venue": cleaned_venue,
                "match_city": info.get("city", ""),
                "match_type": info.get("match_type", ""),
                "player_id": player_id,
                "player_name": player,
                "team_id": team_id,
                "team_name": team,
                "opponent_team_id": opponent_team_id,
                "opponent_team_name": opponent_team,
                "runs_scored_in_inning": 0,
                "balls_played_in_inning": 0,
                "fours_in_inning": 0,
                "sixes_in_inning": 0,
                "batting_position": batting_position,
                "50_in_balls": 0,
                "100_in_balls": 0,
                "wicket_taken_in_inning": 0,
                "balls_bowled_in_inning": 0,
                "runs_conceded_in_inning": 0,
                "fours_conceded_in_inning": 0,
                "sixes_conceded_in_inning": 0,
                "maiden_in_inning": 0,
                "economy": 0.0,
                "is_out": 0,
                "is_player_of_match": 1 if "player_of_match" in info and player in info["player_of_match"] else 0
            }
    
    logger.debug(f"Created player performance data for {len(info['players'].get(teams[0], [])) + len(info['players'].get(teams[1], []))} players in match {match_id}")


def extract_officials_info(data, match_id):
    if "info" in data and "officials" in data["info"]:
        for role, officials in data["info"]["officials"].items():
            for official in officials:
                officials_set.add(official)
                
                match_officials_list.append({
                    "match_id": match_id,
                    "official_id": official,
                    "role": role
                })


def extract_playerStat_info(data, match_id, team_df):
    logger.debug(f"Extracting player statistics for match {match_id}")
    if "innings" not in data:
        logger.warning(f"No innings data found for player stats in match {match_id}")
        return
    
    for inning_num, inning in enumerate(data["innings"][:2], start=1):
        team = inning["team"]
        opponent_team = data["info"]["teams"][1] if team == data["info"]["teams"][0] else data["info"]["teams"][0]
        
        team_id = team_df[team_df['team_name'] == team].iloc[0]['team_id']
        opponent_team_id = team_df[team_df['team_name'] == opponent_team].iloc[0]['team_id']

        position_set = set()

        for over in inning["overs"]:
            runs_in_over = 0
            valid_balls = 0
            
            current_bowler = over["deliveries"][0]["bowler"]
            bowler_key_for_maiden = (match_id, current_bowler, opponent_team_id)

            for delivery in over["deliveries"]:
                batter = delivery["batter"]
                bowler = delivery["bowler"]
                non_striker = delivery["non_striker"]

                batter_key = (match_id, batter, team_id)
                bowler_key = (match_id, bowler, opponent_team_id)
                non_striker_key = (match_id, non_striker, team_id)

                if batter_key not in player_performance_dict:
                    logger.warning(f"Batter key {batter_key} not found in player_performance_dict")
                    continue
                if bowler_key not in player_performance_dict:
                    logger.warning(f"Bowler key {bowler_key} not found in player_performance_dict")
                    continue
                if non_striker_key not in player_performance_dict:
                    logger.warning(f"Non-striker key {non_striker_key} not found in player_performance_dict")
                    continue

                batter_performance = player_performance_dict[batter_key]
                bowler_performance = player_performance_dict[bowler_key]
                non_striker_performance = player_performance_dict[non_striker_key]

                is_wide = "extras" in delivery and "wides" in delivery["extras"]
                is_noball = "extras" in delivery and "noballs" in delivery["extras"]
                is_valid_ball = not is_wide
                is_bowler_ball = not (is_wide or is_noball)

                if is_bowler_ball:
                    valid_balls += 1

                batter_runs = delivery["runs"]["batter"]
                total_runs = delivery["runs"]["total"]
                batter_performance["runs_scored_in_inning"] += batter_runs
                batter_performance["balls_played_in_inning"] += int(is_valid_ball)

                bowler_performance["balls_bowled_in_inning"] += int(is_bowler_ball)
                bowler_performance["runs_conceded_in_inning"] += batter_runs

                if is_wide:
                    bowler_performance["runs_conceded_in_inning"] += delivery["extras"]["wides"]
                if is_noball:
                    bowler_performance["runs_conceded_in_inning"] += delivery["extras"]["noballs"]

                if batter_runs == 4 and 'non_boundary' not in delivery["runs"]:
                    batter_performance["fours_in_inning"] += 1
                    bowler_performance["fours_conceded_in_inning"] += 1

                if batter_runs == 6 and 'non_boundary' not in delivery["runs"]:
                    batter_performance["sixes_in_inning"] += 1
                    bowler_performance["sixes_conceded_in_inning"] += 1

                if "wickets" in delivery:
                    for wicket in delivery["wickets"]:
                        kind = wicket["kind"]
                        player_out = wicket["player_out"]
                        if kind not in ["run out", "retired hurt"]:
                            bowler_performance["wicket_taken_in_inning"] += 1
                        if kind != "retired hurt":
                            out_key = (match_id, player_out, team_id)
                            if out_key in player_performance_dict:
                                player_performance_dict[out_key]["is_out"] = 1

                if batter not in position_set:
                    position_set.add(batter)
                    batter_performance["batting_position"] = len(position_set)
                if non_striker not in position_set:
                    position_set.add(non_striker)
                    non_striker_performance["batting_position"] = len(position_set)

                if batter_performance["runs_scored_in_inning"] >= 100:
                    if batter_performance["100_in_balls"] == 0:
                        batter_performance["100_in_balls"] = batter_performance["balls_played_in_inning"]
                        batter_performance["50_in_balls"] = 0
                elif batter_performance["runs_scored_in_inning"] >= 50:
                    if batter_performance["50_in_balls"] == 0:
                        batter_performance["50_in_balls"] = batter_performance["balls_played_in_inning"]

                
                if total_runs != 0 and not (
                    "extras" in delivery and 
                    delivery["runs"]["extras"] == total_runs and
                    any(k in delivery["extras"] for k in ["byes", "legbyes"]) and 
                    not any(k in delivery["extras"] for k in ["wides", "noballs"])
                ):
                    runs_in_over += total_runs

            
            if runs_in_over == 0 and valid_balls == 6:
                if bowler_key_for_maiden in player_performance_dict:
                    player_performance_dict[bowler_key_for_maiden]["maiden_in_inning"] += 1

            
            if bowler_key_for_maiden in player_performance_dict:
                balls = player_performance_dict[bowler_key_for_maiden]["balls_bowled_in_inning"]
                if balls > 0:
                    overs = (balls // 6) + (balls % 6) / 6
                    if overs > 0:
                        player_performance_dict[bowler_key_for_maiden]["economy"] = round(player_performance_dict[bowler_key_for_maiden]["runs_conceded_in_inning"] / overs, 2)


def extract_match_player(data, match_id, player_df, team_df):
    if "info" in data and "players" in data["info"]:
        for team, player_list in data["info"]["players"].items():
            for player in player_list:
                match_players_list.append({
                    "match_id": match_id,
                    "player_id": player_df[player_df['player_name'] == player].iloc[0]['player_id'],
                    "team_id": team_df[team_df['team_name'] == team].iloc[0]['team_id']
                })


def extract_player_partnership(data, match_id, player_df, team_df):
    logger.debug(f"Extracting player partnership for match {match_id}")
    if "innings" not in data:
        return
    
    for inning in data["innings"][0:min(2,len(data["innings"]))]:
        team = inning["team"]
        team_id = team_df[team_df['team_name'] == team].iloc[0]['team_id']
        
        for over in inning["overs"]:
            for ball_num, delivery in enumerate(over["deliveries"], start=1):
                player1 = delivery["batter"]
                player2 = delivery["non_striker"]
                
                if(player1 > player2):
                    player1, player2 = player2, player1
                
                partner_key1 = (match_id, player1, player2)
                partner_key2 = (match_id, player2, player1)
                
                batter_partnership = ""
                if partner_key1 in player_partnership_dict or partner_key2 in player_partnership_dict:
                    if partner_key1 in player_partnership_dict:
                        batter_partnership = player_partnership_dict[partner_key1]
                    else:
                        batter_partnership = player_partnership_dict[partner_key2]
                else:
                    player_partnership_dict[partner_key1] = {
                        "match_id": match_id,
                        "player1_id": player_df[(player_df['player_name'] == player1) & (player_df['team_id'] == team_id)].iloc[0]['player_id'],
                        "player2_id": player_df[(player_df['player_name'] == player2) & (player_df['team_id'] == team_id)].iloc[0]['player_id'],
                        "team_id": team_df[team_df['team_name'] == team].iloc[0]['team_id'],
                        "runs_scored_in_inning": 0,
                        "balls_played_in_inning": 0
                    }
                    batter_partnership = player_partnership_dict[partner_key1]

                batter_partnership["runs_scored_in_inning"] += delivery["runs"]["total"]
                
                ball_count = 1
                if("extras" in delivery and ("wides" in delivery["extras"] or "noballs" in delivery["extras"])):
                    ball_count = 0
                batter_partnership["balls_played_in_inning"] += ball_count


def create_batter_vs_bowler_stat(data, player_df, team_df):
    logger.debug("Creating batter vs bowler statistics...")
    if "innings" not in data:
        return
    
    for inning in data["innings"][0:min(2,len(data["innings"]))]:
        batter_team = inning["team"]
        bowler_team = data["info"]["teams"][1] if batter_team == data["info"]["teams"][0] else data["info"]["teams"][0]
        
        for over in inning["overs"]:
            for ball_num, delivery in enumerate(over["deliveries"], start=1):
                batter = delivery["batter"]
                bowler = delivery["bowler"]
                batterVsBowlerKey = (batter, bowler)
                
                batterVsBowlerStat = ""

                if batterVsBowlerKey in batter_vs_bowler_dict:
                    batterVsBowlerStat = batter_vs_bowler_dict[batterVsBowlerKey]
                else:
                    batter_vs_bowler_dict[batterVsBowlerKey] = {
                        'batter_id': player_df[player_df['player_name'] == batter].iloc[0]['player_id'],
                        'bowler_id': player_df[player_df['player_name'] == bowler].iloc[0]['player_id'],
                        'batter_team_id': team_df[team_df['team_name'] == batter_team].iloc[0]['team_id'],
                        'bowler_team_id': team_df[team_df['team_name'] == bowler_team].iloc[0]['team_id'],
                        'runs_scored_in_inning': 0,
                        'balls_played_in_inning': 0,
                        'fours_in_inning': 0,
                        'sixes_in_inning': 0,
                        'out': 0
                    }
                    batterVsBowlerStat = batter_vs_bowler_dict[batterVsBowlerKey]

                ball_count = 1
                if("extras" in delivery and ("wides" in delivery["extras"])):
                    ball_count = 0

                batterVsBowlerStat['balls_played_in_inning'] += ball_count
                batterVsBowlerStat['runs_scored_in_inning'] += delivery["runs"]["batter"]

                if delivery["runs"]["batter"] == 4:
                    batterVsBowlerStat["fours_in_inning"] += 1
                if delivery["runs"]["batter"] == 6:
                    batterVsBowlerStat["sixes_in_inning"] += 1

                if "wickets" in delivery and delivery['wickets'][0]['kind'] != 'run out' and delivery["wickets"][0]["kind"] != "retired hurt":
                   batterVsBowlerStat['out'] += 1


def create_wicket_stats(data, match_id, player_df, team_df):
    logger.debug(f"Creating wicket statistics for match {match_id}")
    if "innings" not in data:
        return

    for inning in data["innings"][0:min(2,len(data["innings"]))]:
        batter_team = inning["team"]
        bowler_team = data["info"]["teams"][1] if batter_team == data["info"]["teams"][0] else data["info"]["teams"][0]
        
        for over in inning["overs"]:
            for ball_num, delivery in enumerate(over["deliveries"], start=1):
                bowler = delivery["bowler"]

                if "wickets" not in delivery or delivery["wickets"][0]["kind"] == "retired hurt":
                    continue
              
                batter = delivery["wickets"][0]["player_out"]
                wicket_key = (match_id, batter)
                
                wicket_dict[wicket_key] = {
                    "match_id": match_id,
                    'batter': batter,
                    'bowler': bowler,
                    'batter_team_id': team_df[team_df['team_name'] == batter_team].iloc[0]['team_id'],
                    'bowler_team_id': team_df[team_df['team_name'] == bowler_team].iloc[0]['team_id'],
                    "wicket_kind": delivery['wickets'][0]['kind'],
                    "fielder": [fielder["name"] for fielder in delivery['wickets'][0]['fielders']] if "fielders" in delivery['wickets'][0] and "name" in delivery['wickets'][0]['fielders'][0] else ""
                }


def create_team_stats(data, match_id, team_df):
    logger.debug(f"Creating team statistics for match {match_id}")
    if "innings" not in data:
        return
    
    inn = 0
    
    for inning in data["innings"][0:min(2,len(data["innings"]))]:
        batter_team = inning["team"]
        key = (match_id, batter_team)
        inn += 1
        
        team_stat_dict[key] = {
            "match_id": match_id,
            "team_id": team_df[team_df['team_name'] == batter_team].iloc[0]['team_id'],
            "inning": inn,
            "total_score": 0,
            "wickets": 0,
            "50_in_balls": 0,
            "100_in_balls": 0
        }

        team_stat = team_stat_dict[key]

        tot_runs = 0
        ball_count = 0
        wicket_count = 0
        
        for over in inning["overs"]:
            for delivery in over["deliveries"]:
                tot_runs += delivery["runs"]["total"]

                bowler_ball_count = 1
                
                if("extras" in delivery and ("wides" in delivery["extras"] or "noballs" in delivery["extras"])):
                    bowler_ball_count = 0
                
                ball_count += bowler_ball_count
                
                if(tot_runs >= 50 and team_stat["50_in_balls"] == 0):
                    team_stat["50_in_balls"] = ball_count

                if(tot_runs >= 100 and team_stat["100_in_balls"] == 0):
                    team_stat["100_in_balls"] = ball_count

                if "wickets" in delivery and delivery["wickets"][0]["kind"] != "retired hurt":
                    wicket_count += 1
                      
        team_stat["total_score"] = tot_runs
        team_stat["wickets"] = wicket_count


def process_teams(json_files):
    logger.info("Processing team information...")
    global teams_set

    if isinstance(json_files, str):
        json_files = [json_files]

    for file in json_files:
        with open(file) as f:
            data = json.load(f)
        
        extract_team_info(data)
    
    team_df = pd.DataFrame([{"team_id": idx+1, "team_name": team} for idx, team in enumerate(teams_set)])
    logger.info(f"Processed {len(team_df)} teams")
    return team_df


def process_players(json_files, team_df):
    logger.info("Processing player information...")
    global players_dict

    if isinstance(json_files, str):
        json_files = [json_files]

    for file in json_files:
        with open(file) as f:
            data = json.load(f)
        
        extract_player_info(data, team_df)

    player_rows = []
    for idx, (player, team) in enumerate(players_dict.keys(), 1):
        team_id = team_df[team_df['team_name'] == team].iloc[0]['team_id']
        
        player_rows.append({
            "player_id": idx,
            "player_name": player,
            "team_id": team_id
        })
        
    player_df = pd.DataFrame(player_rows)
    logger.info(f"Processed {len(player_df)} players")
    return player_df


def process_files(json_files, player_df, team_df):
    logger.info("Starting to process all match files...")
    global venue_dict

    if isinstance(json_files, str):
        json_files = [json_files]
    
    total_files = len(json_files)
    logger.info(f"Found {total_files} JSON files to process")
    
    for idx, file_path in enumerate(json_files):
        if idx % 100 == 0:
            logger.info(f"Processing file {idx + 1}/{total_files}: {os.path.basename(file_path)}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)

        match_id = idx + 1
        file_name = os.path.basename(file_path)

        extract_venue_info(data)
        extract_officials_info(data, match_id)
        create_player_performance(data, match_id, player_df, team_df)
        extract_playerStat_info(data, match_id, team_df)
        extract_match_player(data, match_id, player_df, team_df)
        extract_player_partnership(data, match_id, player_df, team_df)
        create_batter_vs_bowler_stat(data, player_df, team_df)
        create_wicket_stats(data, match_id, player_df, team_df)
        create_team_stats(data, match_id, team_df)
        extract_match_info(data, match_id, player_df, team_df, file_name)

    logger.info("Finished processing all files, creating final dataframes...")
    venue_df = create_venue_table(match_info_list)
    match_info_df = pd.DataFrame(match_info_list)
    match_info_df = add_venue_ids_to_match_info(match_info_df, venue_df)
    match_info_df['venue_id'] = match_info_df['venue_id'].astype('Int64')

    player_performance_df = pd.DataFrame(player_performance_dict.values())
    
    player_performance_df = player_performance_df.merge(
        match_info_df[['match_id', 'venue_id']].astype({'venue_id': 'Int64'}),
        on='match_id',
        how='left',
        validate='many_to_one'
    )

    player_performance_df['venue_id'] = player_performance_df['venue_id'].astype('Int64')

    player_partnership_df = pd.DataFrame(player_partnership_dict.values())
    batter_vs_bowler_df = pd.DataFrame(batter_vs_bowler_dict.values())
    wickets_stat_df = pd.DataFrame(wicket_dict.values())
    team_stat_df = pd.DataFrame(team_stat_dict.values())

    logger.info("Data processing completed successfully!")
    logger.info(f"Generated dataframes:")
    logger.info(f"  - Player Performance: {len(player_performance_df)} rows")
    logger.info(f"  - Match Info: {len(match_info_df)} rows")
    logger.info(f"  - Teams: {len(team_df)} rows")
    logger.info(f"  - Players: {len(player_df)} rows")
    logger.info(f"  - Player Partnership: {len(player_partnership_df)} rows")
    logger.info(f"  - Batter vs Bowler: {len(batter_vs_bowler_df)} rows")
    logger.info(f"  - Team Stats: {len(team_stat_df)} rows")
    logger.info(f"  - Wicket Stats: {len(wickets_stat_df)} rows")
    logger.info(f"  - Venues: {len(venue_df)} rows")

    return {
        'player_performance': player_performance_df,
        'match_info': match_info_df,
        'teams': team_df,
        'players': player_df,
        'player_partnership': player_partnership_df,
        'batter_vs_bowler': batter_vs_bowler_df,
        'team_stat': team_stat_df,
        'wickets_stat': wickets_stat_df,
        'venues': venue_df
    }


if __name__ == "__main__":
    logger.info("Starting cricket data processing pipeline...")
    
    # Source: www.cricsheet.org (Men's T20I matches)
    json_dir = "./t20s_male_json"
    logger.info(f"Looking for JSON files in directory: {json_dir}")
    
    json_files = sorted([os.path.join(json_dir, f) for f in os.listdir(json_dir) if f.endswith('.json')])
    logger.info(f"Found {len(json_files)} JSON files")
    
    team_df = process_teams(json_files)  
    player_df = process_players(json_files, team_df)
    
    logger.info("Starting main data processing...")
    data = process_files(json_files, player_df, team_df)
    
    os.makedirs("Records", exist_ok=True)
    logger.info("Saving data to CSV files...")
    
    data['player_performance'].to_csv('../records/cricket/player_performance.csv', index=False)
    data['match_info'].to_csv('../records/cricket/match_info.csv', index=False)
    data['teams'].to_csv('../records/cricket/teams.csv', index=False)
    data['players'].to_csv('../records/cricket/players.csv', index=False)
    data['player_partnership'].to_csv('../records/cricket/player_partnership.csv', index=False)
    data['team_stat'].to_csv('../records/cricket/team_stat.csv', index=False)
    data['batter_vs_bowler'].to_csv('../records/cricket/batter_vs_bowler.csv', index=False)
    data['wickets_stat'].to_csv('../records/cricket/wickets_stat.csv', index=False)
    data['venues'].to_csv('../records/cricket/venues.csv', index=False)
    
    logger.info("All CSV files saved successfully in 'Records' directory!")
    logger.info("Cricket data processing pipeline completed!")