import ast


tablenames = ["player_performance"]

player_performance = ['PLAYER_ID', 'SEASON_ID', 'TEAM_ID', 'TEAM_ABBREVIATION', 'PLAYER_AGE', 'GP', 'GS', 'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'PLAYER_NAME', 'Cumulative_Points', 'Cumulative_AST', 'Cumulative_REB']


column_description = {
    "PLAYER_ID": "Unique identifier for the player",
    "SEASON_ID": "Identifier for the NBA season",
    "TEAM_ID": "Unique identifier for the team",
    "TEAM_ABBREVIATION": "Team's abbreviation",
    "PLAYER_AGE": "Age of the player during the season",
    "GP": "Number of games played",
    "GS": "Number of games started",
    "MIN": "Total minutes played",
    "FGM": "Field goals made",
    "FGA": "Field goals attempted",
    "FG_PCT": "Field goal shooting percentage",
    "FG3M": "3-point field goals made",
    "FG3A": "3-point field goals attempted",
    "FG3_PCT": "3-point shooting percentage",
    "FTM": "Free throws made",
    "FTA": "Free throws attempted",
    "FT_PCT": "Free throw shooting percentage",
    "OREB": "Offensive rebounds",
    "DREB": "Defensive rebounds",
    "REB": "Total rebounds (offensive + defensive)",
    "AST": "Assists",
    "STL": "Steals",
    "BLK": "Blocks",
    "TOV": "Turnovers",
    "PF": "Personal fouls",
    "PTS": "Points scored",
    "PLAYER_NAME": "Name of the player",
    "Cumulative_Points": "Cumulative points scored up to the current game in the season",
    "Cumulative_AST": "Cumulative assists up to the current game in the season",
    "Cumulative_REB": "Cumulative rebounds up to the current game in the season"
}




def getQUPrompt(query):
    
    prompt = f"""
    Your task is to analyze a basketball record statement and create a structured query understanding.

    Record Statement: {query}

    1. Identify key entities:
    - player: Individual basketball players mentioned
    - team: Teams the player represents (e.g., Lakers)
    - rivalteam: Opposition teams mentioned
    - venue: Basketball arenas/stadiums/locations
    - season: NBA season (e.g., 2022-23)

    2. Identify record context:
    - What record/achievement is being discussed
    - Statistical aspect (points, assists, rebounds, steals, blocks, etc.)
    - All specific conditions (against team, at venue, in season)
    - Timeframe if mentioned (career, season, game)
    - Type (in a game, in a season, career)

    Return a JSON object within <QU> tags with:
    - Empty arrays [] for entities not present
    - All identified entities as string arrays
    - Clear recordcontext capturing the statistical achievement

    Example 1:
    Statement: "LeBron James scored the most points in the 2022-23 season against the Celtics at Staples Center"
    <QU>
    {{
        "player": ["LeBron James"],
        "team": [],
        "rivalteam": ["Celtics"],
        "venue": ["Staples Center"],
        "season": ["2022-23"],
        "recordcontext": ["most points in a season against a team at venue"]
    }}
    </QU>

    Example 2:
    Statement: "Stephen Curry made the most three-pointers in the 2021-22 season at Chase Center"
    <QU>
    {{
        "player": ["Stephen Curry"],
        "team": [],
        "rivalteam": [],
        "venue": ["Chase Center"],
        "season": ["2021-22"],
        "recordcontext": ["most three-pointers in a season at venue"]
    }}
    </QU>

    Example 3:
    Statement: "Kevin Durant averaged 30 points per game for the Nets in the 2022 season"
    <QU>
    {{
        "player": ["Kevin Durant"],
        "team": ["Nets"],
        "rivalteam": [],
        "venue": [],
        "season": ["2022"],
        "recordcontext": ["averaged 30 points per game for team in season"]
    }}
    </QU>

    Guidelines:
    1. Always include all entity keys even if empty
    2. Keep recordcontext concise but complete
    3. Don't assume information not in statement
    4. Capture only explicitly mentioned seasons
    5. Include venue only when specific location mentioned
    6. Distinguish between team (player's team) and rivalteam (opposition)
    7. For statistical aspects, use terms like points, assists, rebounds, steals, blocks, etc.

    Record Statement: {query}
    <QU>
    """
    
    return prompt
    


def getTemplatePrompt(finalqu, statement):
    
    if type(finalqu) == str:
        finalqu = ast.literal_eval(finalqu)
    
    prompt = f"""
    You are a SQL generator for verifying BASKETBALL STATISTICAL RECORDS. Your ONLY job is to produce a query that checks whether a claim about a "record" (e.g., highest, most, best, fastest) is true by returning the TOP 5 entities that compete for that record.

    Statement: {statement}
    QueryUnderstanding: {finalqu}


    Requirements:
    1. Focus on verifying the RECORD CONTEXT (e.g., "highest", "most", "best", "first", etc.)
    2. Return top 5 records by default to allow comparison.
    3. Filter by PLAYER_ID = ##playerid## in WHERE *only* if the record is PERSONAL to the player (e.g., "his best", "career-best", "[Player]'s highest"). For global records (e.g., "in history", "ever", "all-time"), NEVER filter by player.
    4. Use placeholders in WHERE *only* when the record is explicitly scoped to that context:
        - ##playerid## : only if statement's record context is *personal* to the player (e.g., "his best", "career-best", "[Player]'s highest")
       - ##teamid## → only if the record is about performances *for* or *by* a specific team i.e., the record is team-scoped (e.g., "for IND", "by IND players")
       - ##rivalteamid## → only if the record is about performances *against* a specific opponent i.e., the record is opponent-scoped (e.g., "against CHI")
       - ##venueid## → only if the record is venue-specific i.e., the record is venue-scoped (e.g., "PHX")
    5. NEVER use actual names (e.g., 'LeBron James', 'HOU') anywhere in the SQL.
    6. In WHERE/GROUP BY/HAVING, use ONLY ID columns: PLAYER_ID, TEAM_ID.
    7. Names (PLAYER_NAME, TEAM_ABBREVIATION, etc.) may appear ONLY in SELECT — never in filtering or grouping.
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
    Statement: "LeBron James scored the most points in the 2022-23 season"
    Query Understanding: {{
        "player": ["LeBron James"],
        "season": ["2022-23"],
        "recordcontext": ["most points in season"]
    }}
    <TemplateSQL>
    SELECT PLAYER_ID, PLAYER_NAME, SUM(PTS) AS total_points
    FROM player_performance
    WHERE SEASON_ID = '2022-23'
    GROUP BY PLAYER_ID, PLAYER_NAME
    ORDER BY total_points DESC
    LIMIT 5;
    </TemplateSQL>

    Example 2:
    Statement: "Stephen Curry made the most three-pointers in the 2021-22 season"
    Query Understanding: {{
        "player": ["Stephen Curry"],
        "season": ["2021-22"],
        "recordcontext": ["most three-pointers in season"]
    }}
    <TemplateSQL>
    SELECT PLAYER_ID, PLAYER_NAME, SUM(FG3M) three_pointers_made
    FROM player_performance
    WHERE SEASON_ID = '2021-22'
    GROUP BY PLAYER_ID, PLAYER_NAME
    ORDER BY three_pointers_made DESC
    LIMIT 5;
    </TemplateSQL>

    Example 3:
    Statement: "Kevin Durant averaged 30 points per game for the Nets in the 2022 season"
    Query Understanding: {{
        "player": ["Kevin Durant"],
        "team": ["Nets"],
        "season": ["2022"],
        "recordcontext": ["averaged 30 points per game for team in season"]
    }}
    <TemplateSQL>
    SELECT PLAYER_ID, PLAYER_NAME, (PTS / GP) as PPG
    FROM player_performance
    WHERE TEAM_ID = ##teamid## AND SEASON_ID = '2022'
    ORDER BY PPG DESC
    LIMIT 5;
    </TemplateSQL>

    Example 4:
    Statement: "LeBron James had the most assists against the Celtics in the 2022-23 season"
    Query Understanding: {{
        "player": ["LeBron James"],
        "rivalteam": ["Celtics"],
        "season": ["2022-23"],
        "recordcontext": ["most assists against team in season"]
    }}
    <TemplateSQL>
    SELECT PLAYER_ID, PLAYER_NAME, SUM(AST) AS total_assists
    FROM player_performance
    WHERE TEAM_ID = ##rivalteamid## AND SEASON_ID = '2022-23'
    GROUP BY PLAYER_ID, PLAYER_NAME
    ORDER BY total_assists DESC
    LIMIT 5;
    </TemplateSQL>


    Guidelines:
    - ALWAYS return top 5 to enable verification of the claim
    - DO NOT include WHERE PLAYER_ID = ##playerid## — let the ranking decide if the player appears
    - Use GROUP BY when aggregating (e.g., career stats)
    - Use HAVING for post-aggregation filters (e.g., min matches)
    - For "in an innings" claims, do NOT group — use raw rows
    - If the statement says "his best", "his highest", or "[Player]'s career-best", then filter by PLAYER_ID = ##playerid## — because the record is self-referential.
    - If the statement claims a global record ("in history", "of all time", "ever", "world record"), DO NOT filter by PLAYER_ID.
    - Default to TOP 5 unless specified
    - Include columns essential to validate the record
    - Use appropriate WHERE clauses with placeholders
    - Don't target game format from QU in SQL (assume table schema is for that format)
    - For average stats, calculate using relevant columns (e.g., PTS / GP for points per game)
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
    TemplateSQL: SELECT PLAYER_NAME, PTS FROM player_performance WHERE TEAM_ID = ##teamid## AND SEASON_ID = '2022-23'
    Metadata: {{"PHX": 103}}
    FullSQL: <SQL>SELECT PLAYER_NAME, PTS FROM player_performance WHERE TEAM_ID = 103 AND SEASON_ID = '2022-23'</SQL>

    Example 2:
    TemplateSQL: SELECT * FROM player_performance WHERE player_id = ##playerid##
    Metadata: {{"LeBron James": 123}}
    Output: <SQL>SELECT * FROM player_performance WHERE player_id = 123</SQL>
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
    Given a basketball record statement and a player name, identify the correct player from the provided data.

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
    Record Statement: "LeBron James scored the most points in the 2022-23 season"
    Looking for Player: LeBron James
    Player Data: [{{'player_id': 123, 'player_name': 'L. James', 'PTS': 127}}, {{'player_id': 456, 'player_name': 'L. James', 'PTS': 0}}]
    <ID>123</ID>

    Record Statement: {statement}
    Looking for Player: {queriedEntity}
    Player Data: {entityData}
    <ID>
    """
    
    return prompt
