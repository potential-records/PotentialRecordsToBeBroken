import os
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import gc
from tqdm import tqdm


MODEL = '/scratch/nitishk_iitp/models/llama-3.1-8B'
BATCH_SIZE = 20

valid_sports = ['cricket', 'basketball', 'baseball', 'soccer']


tokenizer = AutoTokenizer.from_pretrained(
    MODEL,
    padding_side='left',
    trust_remote_code=True,
    local_files_only=True
)
tokenizer.pad_token = tokenizer.eos_token

quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    quantization_config=quant_config,
    device_map="auto",
    dtype=torch.float16,
    trust_remote_code=True,
    local_files_only=True
)


def create_prompt(statement):
    
    return f"""Classify the following sports insight statement into one of these categories: cricket, basketball, baseball, or soccer.
Respond with ONLY the sport name, nothing else.

Statement: {statement}

Sport:"""


def validate_classification(output):
    cleaned = output.strip().lower().split('\n')[0].split(',')[0].split('.')[0].strip()
    
    for sport in valid_sports:
        if cleaned.startswith(sport) or cleaned == sport:
            return sport
    
    return "unknown"


def classify_sports(statements, batch_size=BATCH_SIZE):
    results = []
    
    for i in tqdm(range(0, len(statements), batch_size), desc="Classifying"):
        batch_statements = statements[i:i + batch_size]
       
        chat_prompts = []
        for s in batch_statements:
            user_message = create_prompt(s)
            messages = [{"role": "user", "content": user_message}]
            formatted_prompt = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            chat_prompts.append(formatted_prompt)
        
        inputs = tokenizer(
            chat_prompts,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
            padding=True
        ).to(model.device)
    
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.1,
                top_p=0.9,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )
        
        for j, output_seq in enumerate(outputs):
            input_length = inputs.input_ids[j].shape[0]
            generated_text = tokenizer.decode(
                output_seq[input_length:],
                skip_special_tokens=True
            ).strip().lower()
            
            classification = validate_classification(generated_text)
            results.append({
                "statement": batch_statements[j],
                "sport": classification,
            })
        
        del inputs, outputs
        torch.cuda.empty_cache()
        gc.collect()
    
    return results


def load_statements(input_data):
    if isinstance(input_data, list):
        statements = [s for s in input_data if pd.notna(s)]
        print(f"Loaded {len(statements)} statements from list input.")
        return statements

    elif isinstance(input_data, str) and os.path.isfile(input_data):
        df = pd.read_csv(input_data)
        statements = df[df.columns[0]].dropna().astype(str).tolist()
        print(f"Loaded {len(statements)} statements from {input_data}")
        return statements

    else:
        raise ValueError("Input must be either a list of strings or a valid CSV file path.")


def save_results_to_csv(results, output_file):
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"Results saved to {output_file}")



# statements = load_statements([
#     "LeBron James scored 30 points in the game.",
#     "Virat Kohli hit a century in the ODI match.",
#     "The Yankees won the World Series.",
#     "Manchester United defeated Liverpool 2-1."
# ])
# results = classify_sports(statements)
# save_results_to_csv(results, "classified_sports.csv")