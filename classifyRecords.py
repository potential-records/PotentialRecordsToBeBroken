import os
import re
import json
import torch
import pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from tqdm import tqdm


MODEL = '/scratch/nitishk_iitp/models/Llama-3.3-70B-Instruct'
BATCH_SIZE = 20


system_prompt = """Classify sport statements as "Record" or "Non-Record" based on these rules:

DEFINITION OF "Record":
- Mentions of an existing, new, broken, equalled, matched, tied, surpassed, posted, or all-time record.
- Superlatives like "first", "youngest", "oldest", "fastest", "highest", "most", "fewest", "longest", "biggest", including ranked forms ("second-fastest", "third-highest"), with an explicit scope (world, league, tournament, nation, club/franchise, venue/circuit/city, team, season, etc.).
- Explicit statistical superlatives in historical context (e.g., "highest score ever", "fastest in tournament history", "youngest player to do X").
- Matching or surpassing another record-holder's achievement.
- Team- and season-scoped bests/leaders (e.g., "biggest win of their season", "top scorer for her team this season").
- Clear near-term/potential claims when the record context and scope are explicit (e.g., "needs one wicket to become the second-fastest Kiwi to 50 T20I wickets").
- **Career or season milestones that mark a significant first, last, or landmark count** 
  (e.g., "Ty Madden recorded his first career win", "John Smith scored his 10th goal of the season", 
  "Player X reached 100 career appearances", "Player Y played his final match").

DEFINITION OF "Non-Record":
- Routine match outcomes (e.g., "Team A defeated Team B 2-1", "Player X scored a goal").
- Statistics describing only a single match without linking to history, season, or career 
  (e.g., "Team A had 65% possession", "Player Y made 5 tackles").
- Generic performance reporting (e.g., "Player X scored twice", "Team B advanced to the semifinals").
- Running or repeated counts that are ordinary and not framed as milestones 
  (e.g., "Player X scored his second goal of the game", "Team A now has 3 wins this season").
- Previews, predictions, or commentary (e.g., "Team A faces Team B tomorrow", "Coach expects a tough match").
- Rankings or standings unless explicitly milestone-related 
  (e.g., "Team A is third in the table", "Player Y is ranked 5th").
- Narrative or descriptive statements with no implication of achievement, milestone, or record.

CLASSIFICATION RULES:
1. Label as "Record" only if the statement explicitly highlights a historical achievement, superlative, or a meaningful career/season milestone (first, last, landmark count).
2. If the statement only reports routine performance, temporary stats, match outcomes, rankings, or general updates with no milestone framing — label "Non-Record".
3. When uncertain, default to "Non-Record".

OUTPUT FORMAT:
"<statement>" -> Record
"<statement>" -> Non-Record
"""

examples_data = [
    # Record 
    ("Yashasvi Jaiswal became the youngest Indian batsman to post 75-plus runs in T20Is, breaking Rohit Sharma's 13-year-old record.", "Record"),
    ("Jason Holder became the first West Indian to take a hat-trick in T20Is.", "Record"),
    ("South Africa posted the highest score in Antigua with 194.", "Record"),
    ("Australia set the highest-ever T20 international first powerplay score of 113/1 for the opening six overs.", "Record"),
    ("Mohammad Rizwan equalled Babar Azam's record as the fastest man to 2000 T20I runs.", "Record"),
    ("Raza is the third highest run-scorer in T20Is this year and has the second-best strike rate among the top 20 run-scorers.", "Record"),
    ("Finn Allen posted the highest score by a New Zealander in T20Is, beating Brendon McCullum's 123.", "Record"),
    ("Marsh's side became the first nation to concede more than 200 in four consecutive T20 internationals.", "Record"),
    ("Lockie Ferguson needs one wicket to become the second-fastest Kiwi bowler to reach 50 T20I wickets.", "Record"),
    ("Mali scored the second fastest goal in the tournament in 133 seconds.", "Record"),
    ("Shohei Ohtani became the first MLB player with 43 home runs and 43 stolen bases in the same season.", "Record"),
    ("Texas rookie Evan Carter became the fourth-youngest player to hit cleanup in a World Series game at 21 years, 62 days.", "Record"),
    ("The Braves became the third team in AL/NL history to belt 300 home runs in a season.", "Record"),
    ("The Braves' starting pitchers allowed three runs or fewer in 25 straight games, setting a franchise record.", "Record"),
    ("Shohei Ohtani raised his season run total to 128, surpassing Ichiro Suzuki's single-season high by a Japanese player.", "Record"),
    ("The Dodgers matched an MLB postseason record with 33 consecutive scoreless innings.", "Record"),
    ("Jose Quintana tied for the second-longest streak in postseason history with three consecutive scoreless starts.", "Record"),
    ("Freeman's 10 RBIs this series are the most in a World Series in Dodgers history.", "Record"),
    ("Maria Lopez became the top scorer for her team this season.", "Record"),
    ("Japan's 5-0 win was their biggest of the season.", "Record"),
    ("Ty Madden recorded his first career win.", "Record"),
    ("John Smith scored his 10th goal of the season.", "Record"),
    ("Adam Zampa reached 100 career appearances.", "Record"),
    ("Virat Kohli played his final international match.", "Record"),
    # Non Record
    ("Zack Wheeler pitched seven innings for the Phillies, allowing four hits and no walks with seven strikeouts.", "Non-Record"),
    ("Pelicans guard CJ McCollum led the team with 25 points.", "Non-Record"),
    ("Australia have won seven consecutive matches ahead of the semifinals.", "Non-Record"),
    ("Malawi and Burkina Faso have met six times since 2000, with Burkina Faso winning four and two ending in draws.", "Non-Record"),
    ("Despite a nervier-than-expected closing 20 minutes, Colombia held on to take all three points.", "Non-Record"),
    ("Ghana's best chance in the game fell to Antoine Semenyo in the sixth minute.", "Non-Record"),
    ("Bafana Bafana hope to qualify for their 12th Afcon tournament.", "Non-Record"),
    ("Tonga defeated the Cook Islands 3-1 in the FIFA World Cup qualifiers.", "Non-Record"),
    ("Andrej Kramaric equalized for Croatia in the second half.", "Non-Record"),
    ("Mattia Zaccagni's finish was reminiscent of Del Piero's famous goal in 2006.", "Non-Record"),
    ("Croatia dominated the first half with 58% possession and 10 shots on goal.", "Non-Record"),
    ("Dominik Livakovic kept a clean sheet for Croatia.", "Non-Record"),
    ("Scotland have lost all three Nations League games so far.", "Non-Record"),
    ("Andrej Kramaric scored a 70th-minute winner for Croatia.", "Non-Record"),
    ("Cyprus are ranked 125th and Latvia 136th in FIFA rankings.", "Non-Record"),
    ("Tomas Chory received a red card after the final whistle.", "Non-Record"),
    ("Turkey finished second in Group F and will play Austria next.", "Non-Record"),
    ("The Czech Republic will look to bounce back in this Nations League fixture.", "Non-Record"),
    ("Argentina won their opening three matches of the tournament.", "Non-Record"),
    ("Chris Jordan hit 30 runs off 15 balls.", "Non-Record"),
    ("Brazil have now scored 12 goals in their last 3 matches.", "Non-Record"),
    ("Leo Messi scored his second goal of the game.", "Non-Record"),
    ("India advanced to the semifinals.", "Non-Record"),
    ("Jordan averages 10 points per game this season.", "Non-Record"),
]

few_shot_examples = [f'{json.dumps(s)} -> {label}' for s, label in examples_data]

def build_prompt(statement: str) -> str:
    examples = "\n".join(few_shot_examples)
    return f"{system_prompt}\n{examples}\n{json.dumps(statement)} ->"


quant = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL,
    padding_side='left',
    trust_remote_code=True,
    local_files_only=True
)

if tokenizer.pad_token_id is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    quantization_config=quant,
    dtype=torch.bfloat16,
    device_map="auto",
    local_files_only=True
)


LABEL_RE = re.compile(r'^\s*("?)(?P<label>non-?\s*record|record)\b', re.IGNORECASE)

def parse_label(generated: str) -> str:
    m = LABEL_RE.search(generated)
    if m:
        label = m.group("label").lower().replace(" ", "")
        if "record" in label and not label.startswith("non"):
            return "Record"
        return "Non-Record"

    head = generated.strip().lower()
    if head.startswith("non"):
        return "Non-Record"
    if head.startswith("rec"):
        return "Record"
    return "Non-Record"


def classify_records(statements, batch_size=BATCH_SIZE):
    
    results = []
    for i in tqdm(range(0, len(statements), batch_size), desc="Classifying Records"):
        batch = statements[i:i + batch_size]
        
        prompts = [build_prompt(stmt) for stmt in batch]

        inputs = tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=4096
        ).to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        for j, output in enumerate(outputs):
            input_length = inputs.input_ids[j].shape[0]
            generated_text = tokenizer.decode(output[input_length:], skip_special_tokens=True)
            label = parse_label(generated_text)
            results.append(label)

        torch.cuda.empty_cache()

    return results


def load_statements(input_data):
    if isinstance(input_data, list):
        statements = [str(s) for s in input_data if pd.notna(s)]
        print(f"Loaded {len(statements)} statements from list input.")
        return statements
    elif isinstance(input_data, str) and os.path.isfile(input_data):
        df = pd.read_csv(input_data)
        statements = df[df.columns[0]].dropna().ast(str).tolist()
        print(f"Loaded {len(statements)} statements from {input_data}")
        return statements
    else:
        raise ValueError("Input must be a list of strings or a valid CSV file path.")

def save_results(statements, labels, output_path):
    df = pd.DataFrame({"Statements": statements, "Labels": labels})
    df.to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")