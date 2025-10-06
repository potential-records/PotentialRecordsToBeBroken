import ast


tablenames = ["player_performance"]

player_performance = [
    'match_id', 'match_name', 'match_date', 'match_venue', 'match_city', 'match_type', 'player_id', 
    'player_name', 'team_id',   'team_name',  'opponent_team_id', 'opponent_team_name', 'runs_scored_in_inning', 
    'balls_played_in_inning', 'fours_in_inning', 'sixes_in_inning', 'batting_position', 'fifty_in_balls', 
    'hundred_in_balls', 'wicket_taken_in_inning', 'balls_bowled_in_inning', 'runs_conceded_in_inning', 
    'fours_conceded_in_inning', 'sixes_conceded_in_inning', 'maiden_in_inning,economy', 'is_out', 
    'is_player_of_match', 'venue_id'
]


column_description = {
    "match_id": "ID of the match",
    "match_name": "Name/identifier of the match",
    "match_date": "Date when the match was played",
    "match_venue": "Venue of the match",
    "match_city": "City where the match was played",
    "match_type": "Type of match (Test/ODI/T20/IPL)",
    "player_id": "ID of players",
    "player_name": "Name of the player",
    "team_id": "ID of the home team",
    "team_name": "Name of the team",
    "opponent_team_id": "ID of the opponent team",
    "opponent_team_name": "Name of the opponent team",
    "runs_scored_in_inning": "runs scored by the player in particular match",
    "balls_played_in_inning": "number of balls played by the player in the particular match",
    "fours_in_inning": "number of 4's hit by player in particular match",
    "sixes_in_inning": "number of 6's hit by player in particular match in particular match",
    "batting_position": "position (0-10) at which player came to bat in particular match",
    "fifty_in_balls": "number of balls played to hit 50 runs by player in particular match",
    "hundred_in_balls": "number of balls played to hit 100 runs by player in particular match",
    "wicket_taken_in_inning": "number of wickets taken by the player in particular match",
    "balls_bowled_in_inning": "number of balls bowled by the player in particular match",
    "runs_conceded_in_inning": "total runs conceded by the player in particular match",
    "fours_conceded_in_inning": "number of 4's conceded by the player in particular match",
    "sixes_conceded_in_inning": "number of 6's conceded by the player in particular match",
    "maiden_in_inning": "number of maiden overs bowled by player in particular match",
    "economy": "bowling economy of the player in particular match",
    "is_out": "1 if player was dismissed during batting else 0",
    "is_player_of_match": "1 if the player was the player of the match after the match else 0",
    "venue_id": "ID of the venue where match was played"
}




def getQUPrompt(query):
    
    prompt = f"""
    Your task is to analyze a cricket record statement and create a structured query understanding.

    Record Statement: {query}

    1. Identify key entities:
    - player: Individual cricket players mentioned
    - team: Teams/countries the players represent  
    - rivalteam: Opposition teams mentioned
    - venue: Cricket grounds/stadiums/locations
    - format: Game format (Test/ODI/T20/IPL)

    2. Identify record context:
    - What record/achievement is being discussed
    - Statistical aspect (most runs, highest score, best average, etc.)
    - All specific conditions (against team, at venue, in format)
    - Timeframe if mentioned (career/year/series)
    - Type (in an innings, in a series, in career)

    Return a JSON object within <QU> tags with:
    - Empty arrays [] for entities not present
    - All identified entities as string arrays
    - Clear recordcontext capturing the statistical achievement

    Example 1:
    Statement: "Virat Kohli scored highest runs against England in an innings"
    <QU>
    {{
        "player": ["Virat Kohli"],
        "team": [],
        "rivalteam": ["England"],
        "venue": [],
        "format": [],
        "recordcontext": ["highest runs against a team in an innings"]
    }}
    </QU>

    Example 2:
    Statement: "Rohit Sharma hit most sixes in ODIs at Melbourne Cricket Ground"
    <QU>
    {{
        "player": ["Rohit Sharma"],
        "team": [],
        "rivalteam": [],
        "venue": ["Melbourne Cricket Ground"],
        "format": ["ODI"],
        "recordcontext": ["most sixes at venue in format"]
    }}
    </QU>

    Guidelines:
    1. Always include all entity keys even if empty
    2. Keep recordcontext concise but complete
    3. Don't assume information not in statement
    4. Capture only explicitly mentioned formats
    5. Include venue only when specific location mentioned
    6. Distinguish between team (player's team) and rivalteam (opposition)

    Record Statement: {query}
    <QU>
    """
    
    return prompt



def getTemplatePrompt(finalqu, statement):
    
    if type(finalqu) == str:
        finalqu = ast.literal_eval(finalqu)

    prompt = f"""
    You are a SQL generator for verifying CRICKET STATISTICAL RECORDS. Your ONLY job is to produce a query that checks whether a claim about a "record" (e.g., highest, most, best, fastest) is true by returning the TOP 5 entities that compete for that record.

    Statement: {statement}
    QueryUnderstanding: {finalqu}


    Requirements:
    1. Focus on verifying the RECORD CONTEXT (e.g., "highest", "most", "best", "first", etc.)
    2. Return top 5 records by default to allow comparison.
    3. Filter by player_id = ##playerid## in WHERE *only* if the record is PERSONAL to the player (e.g., "his best", "career-best", "[Player]'s highest"). For global records (e.g., "in history", "ever", "all-time"), NEVER filter by player.
    4. Use placeholders in WHERE *only* when the record is explicitly scoped to that context:
        - ##playerid## : only if statement's record context is *personal* to the player (e.g., "his best", "career-best", "[Player]'s highest")
       - ##teamid## → only if the record is about performances *for* or *by* a specific team i.e., the record is team-scoped (e.g., "for India", "by Australian players")
       - ##rivalteamid## → only if the record is about performances *against* a specific opponent i.e., the record is opponent-scoped (e.g., "against Pakistan")
       - ##venueid## → only if the record is venue-specific i.e., the record is venue-scoped (e.g., "at Eden Gardens")
    5. NEVER use actual names (e.g., 'Virat Kohli', 'Australia') anywhere in the SQL.
    6. In WHERE/GROUP BY/HAVING, use ONLY ID columns: player_id, team_id, opponent_team_id, venue_id.
    7. Names (player_name, team_name, etc.) may appear ONLY in SELECT — never in filtering or grouping.
    8. Include ONLY columns needed to verify the claim.
    9. Assume correct match format (ODI/T20/etc.) — no match_type filter.


    Available Tables:
    player_performance: {', '.join(player_performance)}

    Column Descriptions:
    """
    
    for key, item in column_description.items():
        prompt += f"{key}: {item}\n"
        

    prompt += f"""
    Example 1:
    Statement: "Virat Kohli became the player with highest number of centuries in ODI"
    QueryUnderstanding: {{
        "player": ["Virat Kohli"],
        "format": ["ODI"],
        "recordcontext": ["most century"]
    }}
    <TemplateSQL>
    SELECT 
        player_id,
        player_name,
        COUNT(*) as total_centuries
    FROM player_performance
    WHERE runs_scored_in_inning >= 100
    GROUP BY player_id, player_name
    ORDER BY total_centuries DESC
    LIMIT 5;
    </TemplateSQL>

    Example 2:
    Statement: "Rohit Sharma scored highest runs against Australia in an ODI innings"
    QueryUnderstanding: {{
        "player": ["Rohit Sharma"],
        "rivalteam": ["Australia"],
        "format": ["ODI"],
        "recordcontext": ["highest runs against team in an innings"]
    }}
    <TemplateSQL>
    SELECT 
        player_id,
        player_name,
        runs_scored_in_inning
    FROM player_performance
    WHERE opponent_team_id = ##rivalteamid##
    ORDER BY runs_scored_in_inning DESC
    LIMIT 5;
    </TemplateSQL>

    Example 3:
    Statement: "MS Dhoni has the best strike rate among wicketkeepers with 50+ innings"
    QueryUnderstanding: {{
        "player": ["MS Dhoni"],
        "role": ["wicketkeeper"],
        "recordcontext": ["best strike rate with min 50 innings"]
    }}
    <TemplateSQL>
    SELECT 
        player_id,
        player_name,
        SUM(runs_scored_in_inning) * 100.0 / NULLIF(SUM(balls_played_in_inning), 0) AS strike_rate,
        COUNT(*) as innings
    FROM player_performance
    WHERE balls_played_in_inning > 0
    GROUP BY player_id, player_name
    HAVING innings >= 50
    ORDER BY strike_rate DESC
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
    """

    prompt += f"""
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
    TemplateSQL: SELECT * FROM player_performance WHERE team_id = ##teamid## AND opponent_team_id = ##rivalteamid##
    Metadata: {{'Afghanistan': 102, 'Ireland': 205}}
    Output: <SQL>SELECT * FROM player_performance WHERE team_id = 102 AND opponent_team_id = 205</SQL>
    
    Example 2:
    TemplateSQL: SELECT * FROM player_performance WHERE player_id = ##playerid##
    Metadata: {{'David Warner': 204, 'Australia': 301}}
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
    Given a cricket record statement and a player name, identify the correct player from the provided data.

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
    Record Statement: "Virat Kohli scored highest runs in ODIs"
    Looking for Player: Virat Kohli
    Player Data: [{{'player_id': 123, 'player_name': 'V. Kohli', 'total_runs': 12000}}, {{'player_id': 456, 'player_name': 'V. Kohli', 'total_runs': 1100}}]
    <ID>456</ID>

 
    Record Statement: {statement}
    Looking for Player: {queriedEntity}
    Player Data: {entityData}
    <ID>
    """
    
    return prompt
