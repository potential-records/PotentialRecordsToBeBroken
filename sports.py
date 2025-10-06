import os
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from langchain_huggingface import HuggingFaceEmbeddings
import torch
import ast
import re
import numpy as np
import pandas as pd
import faiss
import json
from tqdm import tqdm

from sql_db import execute_query, getBaseballStatFromDB, getBasketballStatFromDB, getCricketStatFromDB, getSoccerStatFromDB

from baseball_prompts import getQUPrompt as getBaseballQUPrompt, getTemplatePrompt as getBaseballTemplatePrompt, getFullSQLPrompt as getBaseballFullSQLPrompt, getIdentifyEntityPrompt as getBaseballIdentifyEntityPrompt

from basketball_prompts import getQUPrompt as getBasketballQUPrompt, getTemplatePrompt as getBasketballTemplatePrompt, getFullSQLPrompt as getBasketballFullSQLPrompt, getIdentifyEntityPrompt as getBasketballIdentifyEntityPrompt

from cricket_prompts import getQUPrompt as getCricketQUPrompt, getTemplatePrompt as getCricketTemplatePrompt, getFullSQLPrompt as getCricketFullSQLPrompt, getIdentifyEntityPrompt as getCricketIdentifyEntityPrompt

from soccer_prompts import getQUPrompt as getSoccerQUPrompt, getTemplatePrompt as getSoccerTemplatePrompt, getFullSQLPrompt as getSoccerFullSQLPrompt, getIdentifyEntityPrompt as getSoccerIdentifyEntityPrompt


MODEL = '/scratch/nitishk_iitp/models/Qwen2.5-72B-Instruct'
BATCH_SIZE = 5
MAX_NEW_TOKENS = 1024


SPORT_CONFIGS = {
    "baseball": {
        "prompts": {
            "getQUPrompt": getBaseballQUPrompt,
            "getTemplatePrompt": getBaseballTemplatePrompt,
            "getFullSQLPrompt": getBaseballFullSQLPrompt,
            "getIdentifyEntityPrompt": getBaseballIdentifyEntityPrompt
        },
        "db": {
            "execute_query": lambda query: execute_query(query, 'db/baseball.db'),
            "getStatFromDB": getBaseballStatFromDB
        },
        "vector_db": {
            "player_index": "vector_db/baseball_player_index.bin",
            "team_index": "vector_db/baseball_team_index.bin",
            "player_ids": "vector_db/baseball_player_ids.npy",
            "team_ids": "vector_db/baseball_team_ids.npy"
        },
        "player_keywords": ["player", "hitter", "pitcher", "batter"]
    },
    "basketball": {
        "prompts": {
            "getQUPrompt": getBasketballQUPrompt,
            "getTemplatePrompt": getBasketballTemplatePrompt,
            "getFullSQLPrompt": getBasketballFullSQLPrompt,
            "getIdentifyEntityPrompt": getBasketballIdentifyEntityPrompt
        },
        "db": {
            "execute_query": lambda query: execute_query(query, 'db/basketball.db'),
            "getStatFromDB": getBasketballStatFromDB
        },
        "vector_db": {
            "player_index": "vector_db/basketball_player_index.bin",
            "team_index": "vector_db/basketball_team_index.bin",
            "player_ids": "vector_db/basketball_player_ids.npy",
            "team_ids": "vector_db/basketball_team_ids.npy"
        },
        "player_keywords": ["player", "scorer", "shooter"]
    },
    "cricket": {
        "prompts": {
            "getQUPrompt": getCricketQUPrompt,
            "getTemplatePrompt": getCricketTemplatePrompt,
            "getFullSQLPrompt": getCricketFullSQLPrompt,
            "getIdentifyEntityPrompt": getCricketIdentifyEntityPrompt
        },
        "db": {
            "execute_query": lambda query: execute_query(query, 'db/cricket.db'),
            "getStatFromDB": getCricketStatFromDB
        },
        "vector_db": {
            "player_index": "vector_db/cricket_player_index.bin",
            "team_index": "vector_db/cricket_team_index.bin",
            "player_ids": "vector_db/cricket_player_ids.npy",
            "team_ids": "vector_db/cricket_team_ids.npy"
        },
        "player_keywords": ["player", "batsman", "bowler"]
    },
    "soccer": {
        "prompts": {
            "getQUPrompt": getSoccerQUPrompt,
            "getTemplatePrompt": getSoccerTemplatePrompt,
            "getFullSQLPrompt": getSoccerFullSQLPrompt,
            "getIdentifyEntityPrompt": getSoccerIdentifyEntityPrompt
        },
        "db": {
            "execute_query": lambda query: execute_query(query, 'db/soccer.db'),
            "getStatFromDB": getSoccerStatFromDB
        },
        "vector_db": {
            "player_index": "vector_db/soccer_player_index.bin",
            "team_index": "vector_db/soccer_team_index.bin",
            "player_ids": "vector_db/soccer_player_ids.npy",
            "team_ids": "vector_db/soccer_team_ids.npy"
        },
        "player_keywords": ["player", "scorer", "goal scorer", "striker", "midfielder", "defender"]
    }
}


bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL,
    padding_side="left",
    trust_remote_code=True,
    local_files_only=True
)
tokenizer.pad_token_id = tokenizer.eos_token_id

model = AutoModelForCausalLM.from_pretrained(
    MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    dtype=torch.bfloat16,
    trust_remote_code=True,
    local_files_only=True
)


embedding_function = HuggingFaceEmbeddings(model_name='/scratch/nitishk_iitp/models/paraphrase-MiniLM-L6-v2')


class SportsProcessor:
    def __init__(self, sport):
        self.sport = sport
        self.config = SPORT_CONFIGS[sport]
        self.faiss_indices = {}
        self.entity_id_maps = {}
        self._load_vector_dbs()

    
    def _load_vector_dbs(self):
        """Load FAISS indices for the specific sport"""
        self.faiss_indices = {
            "player": faiss.read_index(self.config["vector_db"]["player_index"]),
            "team": faiss.read_index(self.config["vector_db"]["team_index"]),
        }
        self.entity_id_maps = {
            "player": np.load(self.config["vector_db"]["player_ids"]),
            "team": np.load(self.config["vector_db"]["team_ids"]),
        }


    
    def getLLMResponseBatch(self, prompts, batch_size=BATCH_SIZE):
        results = []
        
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i + batch_size]
            formatted_prompts = []
            
            for prompt in batch:
                messages = [{"role": "user", "content": prompt}]
                formatted_prompt = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                formatted_prompts.append(formatted_prompt)

            inputs = tokenizer(
                formatted_prompts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                padding_side='left'
            ).to(model.device)

            generated_ids = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                num_beams=1,
                do_sample=True,
                temperature=0.1,
                top_p=0.9,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.eos_token_id,
            )

            batch_outputs = []
            for j in range(len(generated_ids)):
                generated_output = tokenizer.decode(
                    generated_ids[j][inputs.input_ids.shape[1]:],
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True
                )
                batch_outputs.append(generated_output)
            
            results.extend(batch_outputs)

        return results

    
    def findEntityIDs(self, entities, etype, top=1):

        if not entities:
            return {}

        index = self.faiss_indices[etype]
        entity_ids = self.entity_id_maps[etype]

        query_embeddings = embedding_function.embed_documents(entities)
        query_embeddings = np.array(query_embeddings, dtype=np.float32)

        distances, indices = index.search(query_embeddings, k=top)

        results = {}
        for i, ent in enumerate(entities):
            best_match_ids = entity_ids[indices[i]]
            results[ent] = best_match_ids.tolist()
        
        return results

        
    def getEntityId(self, statement, queriedEntity, entityData):

        entityprompt = self.config["prompts"]["getIdentifyEntityPrompt"](statement, queriedEntity, entityData)
        
        try:
            llmResponse = self.getLLMResponseBatch([entityprompt])[0]
            entityId = re.findall(r"<ID>(.*?)</ID>", llmResponse, flags=re.DOTALL)
            return entityId[0] if entityId else None
        except Exception as e:
            print(f"Error parsing entityID response: {e}")
            return None

    
    def getEntityMetadata(self, finalqu_list, statements, batch_size=BATCH_SIZE):

        all_prompts = []
        prompt_to_context = []

        for idx, (statement, finalqu) in enumerate(zip(statements, finalqu_list)):
            players = finalqu.get("player", [])
            teams = finalqu.get("team", []) + finalqu.get("rivalteam", [])
            entities = players + teams

            player_id_map = self.findEntityIDs(players, "player")
            team_id_map = self.findEntityIDs(teams, "team")

            metadata = {}
            for player in players:
                ids = player_id_map.get(player, [])
                if not ids:
                    metadata[player] = None
                    continue
                
                entitiesData = self.config["db"]["getStatFromDB"](ids)
                if entitiesData:
                    prompt = self.config["prompts"]["getIdentifyEntityPrompt"](statement, player, entitiesData)
                    all_prompts.append(prompt)
                    prompt_to_context.append((idx, player, ids, entitiesData))
                else:
                    metadata[player] = ids[0] if ids else None

            for team in teams:
                ids = team_id_map.get(team, [])
                metadata[team] = ids[0] if ids else None

        if not all_prompts:
            metadata_list = []
            for idx, (statement, finalqu) in enumerate(zip(statements, finalqu_list)):
                players = finalqu.get("player", [])
                teams = finalqu.get("team", []) + finalqu.get("rivalteam", [])
                player_id_map = self.findEntityIDs(players, "player")
                team_id_map = self.findEntityIDs(teams, "team")
                
                md = {}
                for p in players:
                    ids = player_id_map.get(p, [])
                    md[p] = ids[0] if ids else None
                for t in teams:
                    ids = team_id_map.get(t, [])
                    md[t] = ids[0] if ids else None
                metadata_list.append(md)
            return metadata_list

        llm_responses = self.getLLMResponseBatch(all_prompts, batch_size=batch_size)

        metadata_list = [{} for _ in statements]
        for idx, (statement, finalqu) in enumerate(zip(statements, finalqu_list)):
            players = finalqu.get("player", [])
            teams = finalqu.get("team", []) + finalqu.get("rivalteam", [])
            player_id_map = self.findEntityIDs(players, "player")
            team_id_map = self.findEntityIDs(teams, "team")
        
            md = {}
            for t in teams:
                ids = team_id_map.get(t, [])
                md[t] = ids[0] if ids else None
            metadata_list[idx] = md

        for response, (stmt_idx, entity_name, candidate_ids, entitiesData) in zip(llm_responses, prompt_to_context):
            try:
                entityId = re.findall(r"<ID>(.*?)</ID>", response, flags=re.DOTALL)
                resolved_id = entityId[0] if entityId else None
                if resolved_id and resolved_id != "-1":
                    metadata_list[stmt_idx][entity_name] = resolved_id
                else:
                    metadata_list[stmt_idx][entity_name] = candidate_ids[0]
            except Exception as e:
                print(f"Error parsing entity ID for {entity_name} in statement {stmt_idx}: {e}")
                metadata_list[stmt_idx][entity_name] = candidate_ids[0] if candidate_ids else None

        return metadata_list

    
    def getQU_batch(self, statements, batch_size=BATCH_SIZE):

        prompts = [self.config["prompts"]["getQUPrompt"](s) for s in statements]
        responses = self.getLLMResponseBatch(prompts, batch_size=batch_size)

        final_results = []
        for i, conversation in enumerate(responses):
            try:
                assistant_response = ""
                
                if isinstance(conversation, list):
                    for msg in conversation:
                        if msg.get('role') == 'assistant':
                            assistant_response = msg.get('content', '')
                            break
                else:
                    assistant_response = conversation
                
                qu_matches = re.findall(r'<QU>(.*?)</QU>', assistant_response, flags=re.DOTALL)
                
                if qu_matches:
                    qu_content = qu_matches[0].strip()
                    try:
                        qu_dict = json.loads(qu_content)
                    except json.JSONDecodeError:
                        qu_dict = ast.literal_eval(qu_content)
                    final_results.append(dict(sorted(qu_dict.items())))
                else:
                    print(f"Warning: No <QU> tags found in response {i}")
                    final_results.append({})
            
            except Exception as e:
                print(f"Error parsing QU response {i}: {e}")
                final_results.append({})
                
        return final_results

    
    def getTemplateSQL_batch(self, finalqu_list, statements, batch_size=BATCH_SIZE):
        
        prompts = [self.config["prompts"]["getTemplatePrompt"](finalqu, s) for finalqu, s in zip(finalqu_list, statements)]
        responses = self.getLLMResponseBatch(prompts, batch_size=batch_size)

        templates = []
        
        for i, conversation in enumerate(responses):
            try:
                assistant_response = ""
                
                if isinstance(conversation, list):
                    for msg in conversation:
                        if msg.get('role') == 'assistant':
                            assistant_response = msg.get('content', '')
                            break
                else:
                    assistant_response = str(conversation)
                
                template_matches = re.findall(r'<TemplateSQL>(.*?)</TemplateSQL>', assistant_response, flags=re.DOTALL)
                
                if template_matches:
                    template = template_matches[0].replace("\n", " ").strip()
                    templates.append(template)
                else:
                    sql_pattern = r'(SELECT\s+.*?;)'
                    sql_matches = re.findall(sql_pattern, assistant_response, flags=re.DOTALL | re.IGNORECASE)
                    if sql_matches:
                        template = sql_matches[0].replace("\n", " ").strip()
                        templates.append(template)
                    else:
                        print(f"Warning: No SQL found in response {i}")
                        templates.append("SELECT 1;")
                        
            except Exception as e:
                print(f"Error extracting template SQL from response {i}: {e}")
                templates.append("SELECT 1;")
        
        return templates

        
    def getFullSQL_batch(self, finalqu_list, templates, metadata_list, batch_size=BATCH_SIZE):
        
        prompts = [self.config["prompts"]["getFullSQLPrompt"](fq, t, md) for fq, t, md in zip(finalqu_list, templates, metadata_list)]
        responses = self.getLLMResponseBatch(prompts, batch_size=batch_size)

        sqls = []
        
        for i, conversation in enumerate(responses):
            try:
                assistant_response = ""
                if isinstance(conversation, list):
                    for msg in conversation:
                        if msg.get('role') == 'assistant':
                            assistant_response = msg.get('content', '')
                            break
                else:
                    assistant_response = str(conversation)
                
                sql_matches = re.findall(r'<SQL>(.*?)</SQL>', assistant_response, flags=re.DOTALL | re.IGNORECASE)
                
                if sql_matches:
                    sql = sql_matches[0].strip()
                    sqls.append(sql)
                else:
                    template_sql = templates[i] if i < len(templates) else ""
                    metadata = metadata_list[i] if i < len(metadata_list) else {}
                    
                    if template_sql and metadata:
                        sql = template_sql

                        record_context = " ".join(finalqu_list[i].get("recordcontext", [])).lower()
                        filter_players = any(word in record_context for word in self.config["player_keywords"])
                        
                        for entity_name, entity_id in metadata.items():
                            if entity_id is not None:
                                
                                if entity_name in finalqu_list[i].get("rivalteam", []):
                                    if "##rivalteamid##" in sql:
                                        sql = sql.replace("##rivalteamid##", str(entity_id))
                                
                                elif entity_name in finalqu_list[i].get("venue", []):
                                    if "##venueid##" in sql:
                                        sql = sql.replace("##venueid##", str(entity_id))
                                
                                elif entity_name in finalqu_list[i].get("player", []):
                                    if filter_players and "##playerid##" in sql:
                                        sql = sql.replace("##playerid##", str(entity_id))
                        
                        sql = re.sub(r'##\w+##', 'NULL', sql)
                        sqls.append(sql)
                    else:
                        sqls.append(template_sql if template_sql else "SELECT 1;")
                        
            except Exception as e:
                print(f"Error extracting full SQL from response {i}: {e}")
                sqls.append("SELECT 1;")
        
        return sqls


        
    def process_statements(self, statements, batch_size=BATCH_SIZE):
        results = []

        if isinstance(statements, str):
            statements = [statements]

        finalqu_list = self.getQU_batch(statements, batch_size=batch_size)
        metadata_list = self.getEntityMetadata(finalqu_list, statements, batch_size=batch_size)
        templates = self.getTemplateSQL_batch(finalqu_list, statements, batch_size=batch_size)
        sqls = self.getFullSQL_batch(finalqu_list, templates, metadata_list, batch_size=batch_size)

        for st, fq, md, template, sql in zip(statements, finalqu_list, metadata_list, templates, sqls):
            try:
                columns, rows = self.config["db"]["execute_query"](sql)
                results.append({
                    "statement": st,
                    "results": {"columns": columns, "rows": rows}
                })
            except Exception as e:
                results.append({
                    "statement": st,
                    "qu": fq,
                    "template_sql": template,
                    "entity_metadata": md,
                    "sql": sql,
                    "error": str(e)
                })
        
        return results



def load_statements_from_csv(csv_file_path, column_name):
    try:
        df = pd.read_csv(csv_file_path)
        statements = df[column_name].dropna().astype(str).str.strip().tolist()
        return statements
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return []