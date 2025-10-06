import sqlite3


SPORT_CONFIGS = {
    'baseball': {
        'db_name': 'db/baseball.db',
        'get_stat_function': 'getBaseballStatFromDB'
    },
    'basketball': {
        'db_name': 'db/basketball.db', 
        'get_stat_function': 'getBasketballStatFromDB'
    },
    'cricket': {
        'db_name': 'db/cricket.db',
        'get_stat_function': 'getCricketStatFromDB'
    },
    'soccer': {
        'db_name': 'db/soccer.db',
        'get_stat_function': 'getSoccerStatFromDB'
    }
}


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


def getBaseballStatFromDB(ids):
    if not ids:
        return []
    
    query = f"""
    SELECT 
        player_id,
        MAX(player_name) as player_name,
        play_group,
        SUM(homeRuns) as total_home_runs,
        SUM(rbi) as total_rbi,
        SUM(hits) as total_hits,
        SUM(atBats) as total_at_bats,
        SUM(strikeOuts) as total_strikeouts,
        SUM(inningsPitched) as total_innings_pitched,
        SUM(earnedRuns) as total_earned_runs,
        SUM(wins) as total_wins,
        SUM(gamesPlayed) as total_games_played
    FROM player_performance 
    WHERE player_id IN ({','.join(str(i) for i in ids)})
    GROUP BY player_id, play_group
    """
    
    columns, results = execute_query(query, 'db/baseball.db')
    
    entityData = []
    for row in results:
        temp = {}
        for x in range(len(columns)):
            temp[columns[x]] = row[x]
        entityData.append(temp)
    
    return entityData

 
def getBasketballStatFromDB(ids):
    if not ids:
        return []
    
    query = f"""
    SELECT 
        PLAYER_ID,
        PLAYER_NAME,
        SUM(PTS) AS points,
        SUM(FG3M) AS three_pointers_made
    FROM player_performance
    WHERE PLAYER_ID IN ({','.join(str(i) for i in ids)})
    GROUP BY PLAYER_ID
    """
    
    columns, results = execute_query(query, 'db/basketball.db')
    
    entityData = []
    for row in results:
        temp = {}
        for x in range(len(columns)):
            temp[columns[x]] = row[x]
        entityData.append(temp)
    
    return entityData


def getCricketStatFromDB(ids):
    if not ids:
        return []
    
    query = f"""SELECT player_id, MAX(player_name) as player_name, 
                sum(runs_scored_in_inning) as total_runs, 
                sum(wicket_taken_in_inning) as total_wickets 
                FROM player_performance 
                WHERE player_id IN ({','.join(str(i) for i in ids)}) 
                GROUP BY player_id"""
    
    columns, results = execute_query(query, 'db/cricket.db')
    
    entityData = []
    for row in results:
        temp = {}
        for x in range(len(columns)):
            temp[columns[x]] = row[x]
        entityData.append(temp)

    return entityData


def getSoccerStatFromDB(ids):
    if not ids:
        return []
    
    query = f"""
    SELECT 
        player_id, 
        MAX(player_name) as player_name,
        MAX(team_name) as team_name,
        SUM(Performance_Gls) as total_goals,
        SUM(Performance_Ast) as total_assists,
        SUM(Performance_GPlusA) as total_goals_plus_assists,
        SUM(PlayingTime_Min) as total_minutes,
        SUM(PlayingTime_MP) as total_matches_played,
        AVG(Expected_xG) as avg_xg,
        AVG(Expected_xAG) as avg_xag,
        SUM(Performance_CrdY) as total_yellow_cards,
        SUM(Performance_CrdR) as total_red_cards
    FROM player_performance
    WHERE player_id IN ({','.join(str(i) for i in ids)})
    GROUP BY player_id
    """
    
    columns, results = execute_query(query, 'db/soccer.db')
    
    entityData = []
    for row in results:
        temp = {}
        for x in range(len(columns)):
            temp[columns[x]] = row[x]
        entityData.append(temp)
    
    return entityData


def get_all_stat_functions():
    
    return {
        'baseball': getBaseballStatFromDB,
        'basketball': getBasketballStatFromDB, 
        'cricket': getCricketStatFromDB,
        'soccer': getSoccerStatFromDB
    }
