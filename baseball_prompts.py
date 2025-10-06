import ast


tablenames = ["player_performance"]

player_performance = [
    'gamesPlayed', 'groundOuts', 'airOuts', 'runs', 'doubles', 'triples', 'homeRuns', 'strikeOuts',
    'baseOnBalls', 'intentionalWalks', 'hits', 'hitByPitch', 'avg', 'atBats', 'obp', 'slg', 'ops',
    'caughtStealing', 'stolenBases', 'stolenBasePercentage', 'groundIntoDoublePlay', 'numberOfPitches',
    'plateAppearances', 'totalBases', 'rbi', 'leftOnBase', 'sacBunts', 'sacFlies', 'babip',
    'groundOutsToAirouts', 'catchersInterference', 'atBatsPerHomeRun', 'player_id', 'play_group',
    'season', 'gamesStarted', 'era', 'inningsPitched', 'wins', 'losses', 'saves', 'saveOpportunities',
    'holds', 'blownSaves', 'earnedRuns', 'whip', 'battersFaced', 'outs', 'gamesPitched', 'completeGames',
    'shutouts', 'strikes', 'strikePercentage', 'hitBatsmen', 'balks', 'wildPitches', 'pickoffs',
    'winPercentage', 'pitchesPerInning', 'gamesFinished', 'strikeoutWalkRatio', 'strikeoutsPer9Inn',
    'walksPer9Inn', 'hitsPer9Inn', 'runsScoredPer9', 'homeRunsPer9', 'inheritedRunners',
    'inheritedRunnersScored', 'player_name', 'team_id', 'position', 'team_name', 'team_abbreviation',
    'division', 'league'
]

column_description = {
    "gamesPlayed": "Number of games played",
    "groundOuts": "Number of ground outs recorded",
    "airOuts": "Number of fly outs recorded",
    "runs": "Total runs scored",
    "doubles": "Number of doubles hit",
    "triples": "Number of triples hit",
    "homeRuns": "Number of home runs hit",
    "strikeOuts": "Number of strikeouts",
    "baseOnBalls": "Number of walks (bases on balls)",
    "intentionalWalks": "Number of intentional walks",
    "hits": "Total hits",
    "hitByPitch": "Number of times hit by pitch",
    "avg": "Batting average",
    "atBats": "Number of at-bats",
    "obp": "On-base percentage",
    "slg": "Slugging percentage",
    "ops": "On-base plus slugging",
    "caughtStealing": "Number of times caught stealing",
    "stolenBases": "Number of stolen bases",
    "stolenBasePercentage": "Stolen base success rate",
    "groundIntoDoublePlay": "Number of double plays grounded into",
    "numberOfPitches": "Total number of pitches thrown/seen",
    "plateAppearances": "Total plate appearances",
    "totalBases": "Total bases accumulated",
    "rbi": "Runs batted in",
    "leftOnBase": "Runners left on base",
    "sacBunts": "Sacrifice bunts",
    "sacFlies": "Sacrifice flies",
    "babip": "Batting average on balls in play",
    "groundOutsToAirouts": "Ratio of ground outs to fly outs",
    "catchersInterference": "Instances of catcher's interference",
    "atBatsPerHomeRun": "At bats per home run ratio",
    "player_id": "Unique identifier for the player",
    "play_group": "Category indicating if the stats are for hitting or pitching",
    "season": "The MLB season year",
    "gamesStarted": "Number of games started",
    "era": "Earned run average",
    "inningsPitched": "Total innings pitched",
    "wins": "Number of wins",
    "losses": "Number of losses",
    "saves": "Number of saves",
    "saveOpportunities": "Number of save opportunities",
    "holds": "Number of holds",
    "blownSaves": "Number of blown saves",
    "earnedRuns": "Earned runs allowed",
    "whip": "Walks and hits per inning pitched",
    "battersFaced": "Number of batters faced",
    "outs": "Total outs recorded",
    "gamesPitched": "Number of games pitched",
    "completeGames": "Number of complete games pitched",
    "shutouts": "Number of shutouts pitched",
    "strikes": "Total strikes thrown",
    "strikePercentage": "Percentage of strikes among all pitches",
    "hitBatsmen": "Number of batters hit by pitch",
    "balks": "Number of balks committed",
    "wildPitches": "Number of wild pitches",
    "pickoffs": "Number of pickoffs",
    "winPercentage": "Winning percentage",
    "pitchesPerInning": "Average pitches per inning",
    "gamesFinished": "Number of games finished",
    "strikeoutWalkRatio": "Strikeout to walk ratio",
    "strikeoutsPer9Inn": "Strikeouts per nine innings",
    "walksPer9Inn": "Walks per nine innings",
    "hitsPer9Inn": "Hits allowed per nine innings",
    "runsScoredPer9": "Runs scored per nine innings",
    "homeRunsPer9": "Home runs allowed per nine innings",
    "inheritedRunners": "Runners inherited from previous pitcher",
    "inheritedRunnersScored": "Inherited runners who scored",
    "player_name": "Name of the player",
    "team_id": "Unique identifier for the team",
    "position": "Player's position",
    "team_name": "Name of the team",
    "team_abbreviation": "Team abbreviation",
    "division": "Division the team belongs to",
    "league": "League the team belongs to"
}



def getQUPrompt(query):
    
    prompt = f"""
    Your task is to analyze a baseball record statement and create a structured query understanding.

    Record Statement: {query}

    1. Identify key entities:
    - player: Individual baseball players mentioned
    - team: Teams the player represents (e.g., Yankees)
    - rivalteam: Opposition teams mentioned
    - venue: Baseball stadiums/locations
    - season: MLB season year (e.g., 2025)

    2. Identify record context:
    - What record/achievement is being discussed
    - Statistical aspect (home runs, RBIs, ERA, strikeouts, etc.)
    - All specific conditions (against team, at venue, in season)
    - Timeframe if mentioned (career, season, game)
    - Type (in a game, in a season, career)

    Return a JSON object within <QU> tags with:
    - Empty arrays [] for entities not present
    - All identified entities as string arrays
    - Clear recordcontext capturing the statistical achievement

    Example 1:
    Statement: "Mike Trout hit the most home runs in the 2025 season against the Red Sox at Yankee Stadium"
    <QU>
    {{
        "player": ["Mike Trout"],
        "team": [],
        "rivalteam": ["Red Sox"],
        "venue": ["Yankee Stadium"],
        "season": ["2025"],
        "recordcontext": ["most home runs in a season against a team at venue"]
    }}
    </QU>

    Example 2:
    Statement: "Jacob deGrom had the lowest ERA in the 2024 season at Citi Field"
    <QU>
    {{
        "player": ["Jacob deGrom"],
        "team": [],
        "rivalteam": [],
        "venue": ["Citi Field"],
        "season": ["2024"],
        "recordcontext": ["lowest ERA in a season at venue"]
    }}
    </QU>

    Example 3:
    Statement: "Shohei Ohtani drove in 100 RBIs for the Angels in the 2025 season"
    <QU>
    {{
        "player": ["Shohei Ohtani"],
        "team": ["Angels"],
        "rivalteam": [],
        "venue": [],
        "season": ["2025"],
        "recordcontext": ["100 RBIs for team in season"]
    }}
    </QU>

    Guidelines:
    1. Always include all entity keys even if empty
    2. Keep recordcontext concise but complete
    3. Don't assume information not in statement
    4. Capture only explicitly mentioned seasons
    5. Include venue only when specific location mentioned
    6. Distinguish between team (player's team) and rivalteam (opposition)
    7. For statistical aspects, use terms like home runs, RBIs, ERA, strikeouts, etc.

    Record Statement: {query}
    <QU>
    """
    
    return prompt
    


def getTemplatePrompt(finalqu, statement):
    
    if type(finalqu) == str:
        finalqu = ast.literal_eval(finalqu)
    
    prompt = f"""
    You are a SQL generator for verifying BASEBALL STATISTICAL RECORDS. Your ONLY job is to produce a query that checks whether a claim about a "record" (e.g., highest, most, best, fastest) is true by returning the TOP 5 entities that compete for that record.

    Statement: {statement}
    QueryUnderstanding: {finalqu}


    Requirements:
    1. Focus on verifying the RECORD CONTEXT (e.g., "highest", "most", "best", "first", etc.)
    2. Return top 5 records by default to allow comparison.
    3. Filter by player_id = ##playerid## in WHERE clause if and if *only* the record is PERSONAL to the player (e.g., "his best", "career-best", "[Player]'s highest"). 
    4. For global records (e.g., "in history", "highest", "all-time"), NEVER filter by player and/or team.
    5. Use placeholders in WHERE *only* when the record is explicitly scoped to that context:
        - ##playerid## : only if statement's record context is *personal* to the player (e.g., "his best", "career-best", "[Player]'s highest")
       - ##teamid## → only if the record is about performances *for* or *by* a specific team i.e., the record is team-scoped (e.g., "for Angels", "by Astros players")
       - ##rivalteamid## → only if the record is about performances *against* a specific opponent i.e., the record is opponent-scoped (e.g., "against Red Sox")
       - ##venueid## → only if the record is venue-specific i.e., the record is venue-scoped (e.g., "at New Havens")
    6. NEVER use actual names (e.g., 'Mike Trout', 'Red Sox') anywhere in the SQL.
    7. In WHERE/GROUP BY/HAVING, use ONLY ID columns: player_id, team_id, opponent_team_id, venue_id.
    8. Names (player_name, team_name, etc.) may appear ONLY in SELECT — never in filtering or grouping.
    9. Include ONLY columns needed to verify the claim.
    10. Assume correct match format — no match_type filter.
    11. DONOT use play_group attribute in the WHERE clause. 


    Available Tables:
    player_performance: {', '.join(player_performance)}

    Column Descriptions:
    """
    
    for key, item in column_description.items():
        prompt += f"{key}: {item}\n"
        

    prompt += f"""
    Example 1:
    Statement: "Mike Trout hit the most home runs in the 2025 season"
    Query Understanding: {{
        "player": ["Mike Trout"],
        "season": ["2025"],
        "recordcontext": ["most home runs in season"]
    }}
    <TemplateSQL>
    SELECT player_id, player_name, homeRuns
    FROM player_performance
    WHERE season = 2025
    ORDER BY homeRuns DESC
    LIMIT 5;
    </TemplateSQL>

    Example 2:
    Statement: "Jacob deGrom had the lowest ERA in the 2024 season"
    Query Understanding: {{
        "player": ["Jacob deGrom"],
        "season": ["2024"],
        "recordcontext": ["lowest ERA in season"]
    }}
    <TemplateSQL>
    SELECT player_id, player_name, era
    FROM player_performance
    WHERE season = 2024
    ORDER BY era ASC
    LIMIT 5;
    </TemplateSQL>

    Example 3:
    Statement: "Shohei Ohtani drove in 100 RBIs for the Angels in the 2025 season"
    Query Understanding: {{
        "player": ["Shohei Ohtani"],
        "team": ["Angels"],
        "season": ["2025"],
        "recordcontext": ["100 RBIs for team in season"]
    }}
    <TemplateSQL>
    SELECT player_id, player_name, SUM(rbi) AS total_rebounds
    FROM player_performance
    WHERE team_id = ##teamid## AND season = 2025 AND total_rebounds >= 100
    GROUP BY player_id, player_name
    ORDER BY total_rebounds DESC
    LIMIT 5;
    </TemplateSQL>

    Example 4:
    Statement: "Gerrit Cole recorded the most strikeouts against the Astros in the 2025 season"
    Query Understanding: {{
        "player": ["Gerrit Cole"],
        "rivalteam": ["Astros"],
        "season": ["2025"],
        "recordcontext": ["most strikeouts against team in season"]
    }}
    <TemplateSQL>
    SELECT player_id, player_name, strikeOuts
    FROM player_performance
    WHERE team_id = ##rivalteamid## AND season = 2025
    ORDER BY strikeOuts DESC
    LIMIT 5;
    </TemplateSQL>

    Guidelines:
    - ALWAYS return top 5 to enable verification of the claim
    - DO NOT include WHERE player_id = ##playerid## — let the ranking decide if the player appears
    - Use GROUP BY when aggregating (e.g., career stats)
    - Use HAVING for post-aggregation filters (e.g., min matches)
    - For "in an innings" claims, do NOT group — use raw rows
    - If the statement says "his best", "his highest", or "[Player]'s career-best", then filter by player_id = ##playerid## — because the record is self-referential.
    - If the statement claims a global record ("in history", "of all time", "ever", "world record"), DO NOT filter by player_id.
    - If the schema doesn't have a column for an entity (e.g., venue), ignore that entity in the SQL
    

    FINAL INSTRUCTION: 
    YOU MUST RESPOND WITH EXACTLY ONE <TemplateSQL> BLOCK CONTAINING ONLY THE SQL QUERY.
    DO NOT INCLUDE ANY EXPLANATIONS, DO NOT USE BACKTICKS, DO NOT INCLUDE ```sql MARKERS OR MARKDOWN.
    FORMAT:
    <TemplateSQL>
    SELECT ... YOUR SQL QUERY HERE ...;
    </TemplateSQL>
    
    Statement: {statement}
    QueryUnderstanding: {finalqu}
    <TemplateSQL>
    """
    
    return prompt



def getFullSQLPrompt(finalqu, template, metadata):
    
    prompt = f"""
    You are a mechanical placeholder replacer. Your ONLY task is to replace placeholders in the SQL template with values from metadata — NOTHING ELSE.
    
    TemplateSQL: {template}
    Metadata: {metadata}
    
    Rules:
    1. ONLY replace placeholders that EXPLICITLY appear in the TemplateSQL.
    2. DO NOT add ANY new WHERE conditions, JOINs, or filters — even if metadata has extra keys.
    3. Replace:
       - ##playerid## → with numeric value from metadata (key may be player name or 'player')
       - ##teamid## → with numeric value from metadata (key may be team name or 'team')
       - ##rivalteamid## → with numeric value from metadata (key may be rival team name or 'rivalteam')
       - ##venueid## → with numeric value from metadata (key may be venue name or 'venue')
    4. If a placeholder appears but its value is missing or None in metadata, REMOVE THE ENTIRE CONDITION containing that placeholder.
       - Example: "WHERE a = 1 AND b = ##xyz##" → if ##xyz## is None → "WHERE a = 1"
       - If it's the only condition: "WHERE x = ##playerid##" → becomes no WHERE clause.
    5. Output format: <SQL>SELECT ...</SQL>
    6. NO explanations. NO extra text. NO markdown. ONLY the <SQL> block.
    
    Example 1:
    TemplateSQL: SELECT player_name, homeRuns FROM player_performance WHERE team_id = ##teamid## AND season = 2025
    Metadata: {{"Astros": 123}}
    FullSQL: <SQL>SELECT player_name, homeRuns FROM player_performance WHERE team_id = 123 AND season = 2025</SQL>

    Example 2:
    TemplateSQL: SELECT * FROM player_performance WHERE player_id = ##playerid##
    Metadata: {{'Mike Trout': 204}}
    Output: <SQL>SELECT * FROM player_performance WHERE player_id = 204</SQL>
    """

    prompt += f"""
    CRITICAL INSTRUCTIONS:
    1. Replace placeholders with EXACT numeric values from metadata
    2. Respond with ONLY: <SQL>SELECT ...</SQL>
    3. NO explanations, NO extra text, NO markdown
    4. If metadata value is None, remove the condition entirely
    5. Ensure resulting SQL is syntactically correct

    TemplateSQL: {template}
    Metadata: {metadata}
    <SQL>
    """
    
    return prompt
    


def getIdentifyEntityPrompt(statement, queriedEntity, entityData):
    
    prompt = f"""
    Given a baseball record statement and a player name, identify the correct player from the provided data.

    Record Statement: {statement}
    Looking for Player: {queriedEntity}
    Player Data: {entityData}

    Your task is to:
    1. Match the player name "{queriedEntity}" with the most likely player in the Player Data
    2. Consider variations in name formatting, nicknames, or partial matches
    3. Return only the player_id for the best matching player

    Rules:
    - Output MUST be in the format: <ID>123</ID>
    - NEVER use variables, braces, quotes, or code
    - If no match, return <ID>-1</ID>

    Example:
    Record Statement: "Mike Trout hit the most home runs in the 2025 season"
    Looking for Player: Mike Trout
    Player Data: [{{'player_id': 123, 'player_name': 'M. Trout', 'homeRuns': 507}}, {{'player_id': 456, 'player_name': 'M. Trout', 'homeRuns': 09}}]
    <ID>123</ID>

    Record Statement: {statement}
    Looking for Player: {queriedEntity}
    Player Data: {entityData}
    <ID>
    """
    
    return prompt
