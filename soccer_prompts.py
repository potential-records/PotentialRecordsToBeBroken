import ast


tablenames = ["player_performance"]

player_performance = [
    'Position', 'PlayingTime_MP', 'PlayingTime_Starts', 'PlayingTime_Min', 'PlayingTime_90s',
    'Performance_Gls', 'Performance_Ast', 'Performance_GPlusA', 'Performance_GMinusPK',
    'Performance_PK', 'Performance_PKatt', 'Performance_CrdY', 'Performance_CrdR',
    'Expected_xG', 'Expected_npxG', 'Expected_xAG', 'Expected_npxGPlusxAG',
    'Progression_PrgC', 'Progression_PrgP', 'Progression_PrgR',
    'Per90Minutes_Gls', 'Per90Minutes_Ast', 'Per90Minutes_GPlusA', 'Per90Minutes_GMinusPK',
    'Per90Minutes_GPlusAMinusPK', 'Per90Minutes_xG', 'Per90Minutes_xAG', 'Per90Minutes_xGPlusxAG',
    'Per90Minutes_npxG', 'Per90Minutes_npxGPlusxAG', 'player_name', 'team_name', 'player_id', 'team_id'
]

column_description = {
    "Position": "Player's position on the field",
    "PlayingTime_MP": "Number of matches played",
    "PlayingTime_Starts": "Number of matches started",
    "PlayingTime_Min": "Total minutes played",
    "PlayingTime_90s": "Number of 90-minute periods played",
    "Performance_Gls": "Total goals scored",
    "Performance_Ast": "Total assists",
    "Performance_GPlusA": "Total goals plus assists",
    "Performance_GMinusPK": "Goals minus penalty kicks",
    "Performance_PK": "Penalty kicks scored",
    "Performance_PKatt": "Penalty kicks attempted",
    "Performance_CrdY": "Yellow cards received",
    "Performance_CrdR": "Red cards received",
    "Expected_xG": "Expected goals",
    "Expected_npxG": "Non-penalty expected goals",
    "Expected_xAG": "Expected assists",
    "Expected_npxGPlusxAG": "Non-penalty expected goals plus expected assists",
    "Progression_PrgC": "Progressive carries",
    "Progression_PrgP": "Progressive passes",
    "Progression_PrgR": "Progressive runs",
    "Per90Minutes_Gls": "Goals per 90 minutes",
    "Per90Minutes_Ast": "Assists per 90 minutes",
    "Per90Minutes_GPlusA": "Goals plus assists per 90 minutes",
    "Per90Minutes_GMinusPK": "Goals minus penalty kicks per 90 minutes",
    "Per90Minutes_GPlusAMinusPK": "Goals plus assists minus penalty kicks per 90 minutes",
    "Per90Minutes_xG": "Expected goals per 90 minutes",
    "Per90Minutes_xAG": "Expected assists per 90 minutes",
    "Per90Minutes_xGPlusxAG": "Expected goals plus expected assists per 90 minutes",
    "Per90Minutes_npxG": "Non-penalty expected goals per 90 minutes",
    "Per90Minutes_npxGPlusxAG": "Non-penalty expected goals plus expected assists per 90 minutes",
    "player_name": "Name of the player",
    "team_name": "Name of the team",
    "player_id": "Unique identifier for the player",
    "team_id": "Unique identifier for the team"
}



def getQUPrompt(query):
    
    prompt = f"""
    Your task is to analyze a soccer record statement and create a structured query understanding.

    Record Statement: {query}

    1. Identify key entities:
    - player: Individual soccer players mentioned
    - team: Teams the player represents (e.g., Manchester City)
    - rivalteam: Opposition teams mentioned
    - venue: Soccer stadiums/locations
    - season: Season year (e.g., 2025)

    2. Identify record context:
    - What record/achievement is being discussed
    - Statistical aspect (goals, assists, xG, clean sheets, etc.)
    - All specific conditions (against team, at venue, in season)
    - Timeframe if mentioned (career, season, game)
    - Type (in a game, in a season, career)

    Return a JSON object within <QU> tags with:
    - Empty arrays [] for entities not present
    - All identified entities as string arrays
    - Clear recordcontext capturing the statistical achievement

    Example 1:
    Statement: "Erling Haaland scored the most goals in the 2025 season against Liverpool at Old Trafford"
    <QU>
    {{
        "player": ["Erling Haaland"],
        "team": [],
        "rivalteam": ["Liverpool"],
        "venue": ["Old Trafford"],
        "season": ["2025"],
        "recordcontext": ["most goals in a season against a team at venue"]
    }}
    </QU>

    Example 2:
    Statement: "Kevin De Bruyne had the most assists in the 2024 season at Etihad Stadium"
    <QU>
    {{
        "player": ["Kevin De Bruyne"],
        "team": [],
        "rivalteam": [],
        "venue": ["Etihad Stadium"],
        "season": ["2024"],
        "recordcontext": ["most assists in a season at venue"]
    }}
    </QU>

    Example 3:
    Statement: "Mohamed Salah scored 20 goals for Liverpool in the 2025 season"
    <QU>
    {{
        "player": ["Mohamed Salah"],
        "team": ["Liverpool"],
        "rivalteam": [],
        "venue": [],
        "season": ["2025"],
        "recordcontext": ["20 goals for team in season"]
    }}
    </QU>

    Guidelines:
    1. Always include all entity keys even if empty
    2. Keep recordcontext concise but complete
    3. Don't assume information not in statement
    4. Capture only explicitly mentioned seasons
    5. Include venue only when specific location mentioned
    6. Distinguish between team (player's team) and rivalteam (opposition)
    7. For statistical aspects, use terms like goals, assists, xG, clean sheets, etc.

    Record Statement: {query}
    <QU>
    """
    
    return prompt
    


def getTemplatePrompt(finalqu, statement):
    
    if type(finalqu) == str:
        finalqu = ast.literal_eval(finalqu)
    
    prompt = f"""
    You are a SQL generator for verifying SOCCER STATISTICAL RECORDS. Your ONLY job is to produce a query that checks whether a claim about a "record" (e.g., highest, most, best, fastest) is true by returning the TOP 5 entities that compete for that record.

    Statement: {statement}
    QueryUnderstanding: {finalqu}


    Requirements:
    1. Focus on verifying the RECORD CONTEXT (e.g., "highest", "most", "best", "first", etc.)
    2. Return top 5 records by default to allow comparison.
    3. Filter by player_id = ##playerid## in WHERE *only* if the record is PERSONAL to the player (e.g., "his best", "career-best", "[Player]'s highest"). For global records (e.g., "in history", "ever", "all-time"), NEVER filter by player.
    4. Use placeholders in WHERE *only* when the record is explicitly scoped to that context:
        - ##playerid## : only if statement's record context is *personal* to the player (e.g., "his best", "career-best", "[Player]'s highest")
       - ##teamid## → only if the record is about performances *for* or *by* a specific team i.e., the record is team-scoped (e.g., "for Saudi Arabia", "by Portuguese players")
       - ##rivalteamid## → only if the record is about performances *against* a specific opponent i.e., the record is opponent-scoped (e.g., "against India")
       - ##venueid## → only if the record is venue-specific i.e., the record is venue-scoped (e.g., "at Dubai")
    5. NEVER use actual names (e.g., 'Lionel Messi', 'Argentina') anywhere in the SQL.
    6. In WHERE/GROUP BY/HAVING, use ONLY ID columns: player_id, team_id.
    7. Names (player_name, team_name, etc.) may appear ONLY in SELECT — never in filtering or grouping.
    8. Include ONLY columns needed to verify the claim.
    9. Assume correct match format — no match_type filter.


    Available Tables:
    player_performance: {', '.join(player_performance)}

    Column Descriptions:
    """
    
    for key, item in column_description.items():
        prompt += f"{key}: {item}\n"
        

    prompt += f"""
    Example 1:
    Statement: "Erling Haaland scored the most goals in the 2025 season"
    Query Understanding: {{
        "player": ["Erling Haaland"],
        "season": ["2025"],
        "recordcontext": ["most goals in season"]
    }}
    <TemplateSQL>
    SELECT player_id, player_name, SUM(Performance_Gls) AS total_goals
    FROM player_performance
    WHERE season = 2025
    GROUP BY player_id, player_name
    ORDER BY total_goals DESC
    LIMIT 5;
    </TemplateSQL>

    Example 2:
    Statement: "Kevin De Bruyne had the most assists in the 2024 season"
    Query Understanding: {{
        "player": ["Kevin De Bruyne"],
        "season": ["2024"],
        "recordcontext": ["most assists in season"]
    }}
    <TemplateSQL>
    SELECT player_id, player_name, SUM(Performance_Ast) as total_assists
    FROM player_performance
    WHERE season = 2024
    GROUP BY player_id, player_name
    ORDER BY total_assists DESC
    LIMIT 5;
    </TemplateSQL>

    Example 3:
    Statement: "Mohamed Salah scored 20 goals for Liverpool in the 2025 season"
    Query Understanding: {{
        "player": ["Mohamed Salah"],
        "team": ["Liverpool"],
        "season": ["2025"],
        "recordcontext": ["20 goals for team in season"]
    }}
    <TemplateSQL>
    SELECT player_id, player_name, SUM(Performance_Gls) AS total_goals
    FROM player_performance
    WHERE team_id = ##teamid## AND season = 2025
    GROUP BY player_id, player_name
    ORDER BY total_goals DESC
    LIMIT 5;
    </TemplateSQL>

    Example 4:
    Statement: "Kylian Mbappe recorded the highest xG against Real Madrid in the 2025 season"
    Query Understanding: {{
        "player": ["Kylian Mbappe"],
        "rivalteam": ["Real Madrid"],
        "season": ["2025"],
        "recordcontext": ["highest xG against team in season"]
    }}
    <TemplateSQL>
    SELECT player_id, player_name, Expected_xG
    FROM player_performance
    WHERE team_id = ##rivalteamid## AND season = 2025
    ORDER BY Expected_xG DESC
    LIMIT 5;
    </TemplateSQL>
    """

    prompt += f"""
    Guidelines:
    - ALWAYS return top 5 to enable verification of the claim
    - DO NOT include WHERE player_id = ##playerid## — let the ranking decide if the player appears
    - Use GROUP BY when aggregating (e.g., career stats)
    - Use HAVING for post-aggregation filters (e.g., min matches)
    - For "in an innings" claims, do NOT group — use raw rows
    - If the statement says "his best", "his highest", or "[Player]'s career-best", then filter by player_id = ##playerid## — because the record is self-referential.
    - If the statement claims a global record ("in history", "of all time", "ever", "world record"), DO NOT filter by player_id.
    - If the schema doesn't have a column for an entity (e.g., venue), ignore that entity in the SQL
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
    TemplateSQL: SELECT player_name, Performance_Gls FROM player_performance WHERE team__id = ##teamid## AND season = 2025
    Metadata: {{"France": 123}}
    FullSQL: <SQL>SELECT player_name, Performance_Gls FROM player_performance WHERE team_id = 123 AND season = 2025</SQL>

    Example 2:
    TemplateSQL: SELECT * FROM player_performance WHERE player_id = ##playerid##
    Metadata: {{"Erling Haaland": 103}}
    Output: <SQL>SELECT * FROM player_performance WHERE player_id = 103</SQL>
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
    Given a soccer record statement and a player name, identify the correct player from the provided data.

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
    Record Statement: "Erling Haaland scored the most goals in the 2025 season"
    Looking for Player: Erling Haaland
    Player Data: [{{'player_id': 123, 'player_name': 'E. Haaland', 'total_goals': 201}}, {{'player_id': 456, 'player_name': 'E. Haaland', 'total_goals': 19}}]
    <ID>123</ID>

    Record Statement: {statement}
    Looking for Player: {queriedEntity}
    Player Data: {entityData}
    <ID>
    """
    
    return prompt
