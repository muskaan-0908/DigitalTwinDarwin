import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def load_long_term_memory(filename="long_term_memory.json"):
    """
    Loads long term memory facts and session count from a JSON file.
    If the file does not exist or is invalid, returns a default structure.
    """
    default_memory = {"facts": [], "session_count": 0}
    if not os.path.exists(filename):
        return default_memory
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return default_memory
            
            if "facts" not in data or not isinstance(data["facts"], list):
                data["facts"] = []
            if "session_count" not in data:
                data["session_count"] = 0
            return data
    except Exception as e:
        
        return default_memory

def save_long_term_memory(memory_data, filename="long_term_memory.json"):
    """
    Saves long term memory dict to a JSON file.
    """
    try:
        
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving long-term memory: {e}")
        return False

def format_memory_for_prompt(memory_data):
    """
    Formats the facts from memory into a string representation for the persona prompt.
    """
    facts = memory_data.get("facts", [])
    if not facts:
        return "No prior context about this user."
    
    formatted_facts = "\n".join(f"- {fact}" for fact in facts)
    return f"You remember the following key facts about this user from previous conversations:\n{formatted_facts}"

def update_long_term_memory(messages, filename="long_term_memory.json"):
    """
    Analyzes the conversation history and updates the facts in long-term memory.
    Uses Gemini API to extract/refine facts.
    """
    if not messages:
        return False
    
    
    memory = load_long_term_memory(filename)
    current_facts = memory.get("facts", [])
    
    
    conversation_history = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        conversation_history += f"{role.upper()}: {content}\n"
    
    prompt = f"""
You are the memory manager for Charles Darwin's digital twin.
Your task is to analyze the conversation history between Darwin and a user, and update the list of long-term facts about the user.

Existing facts about the user:
{json.dumps(current_facts, indent=2)}

New conversation history:
{conversation_history}

Analyze the history and perform the following:
1. Identify any new personal details, interests, or background information the user shared about themselves.
2. Check if any new information contradicts, updates, or renders obsolete the existing facts.
3. Consolidate and output the updated list of facts. Keep each fact concise, clear, and focused strictly on the USER (not Darwin).

Respond ONLY with a valid JSON array of strings representing the updated facts. Do not include markdown formatting like ```json or any other text.
Example response:
[
  "The user is studying evolutionary biology.",
  "The user is interested in Darwin's voyage to the Galapagos Islands."
]
"""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("GEMINI_API_KEY not found in environment. Skipping memory update.")
            return False
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        
        if text.startswith("```"):
            
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
        updated_facts = json.loads(text)
        if isinstance(updated_facts, list):
            
            memory["facts"] = [str(fact) for fact in updated_facts]
            save_long_term_memory(memory, filename)
            return True
        else:
            print("Gemini response was not a JSON list.")
            return False
    except Exception as e:
        print(f"Failed to update long-term memory: {e}")
        return False