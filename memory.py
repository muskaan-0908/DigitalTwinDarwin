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
    
    import re
from collections import Counter
from datetime import datetime
 
_TOPIC_MAP = {
    "Natural Selection": ["select", "survival", "adapt", "fit", "breed", "pigeon"],
    "Evolution":         ["evolut", "descent", "transmut", "species", "origin"],
    "Geology":           ["geolog", "strata", "lyell", "rock", "fossil", "sediment"],
    "Beagle Voyage":     ["beagle", "voyage", "travel", "galapag", "island", "coral"],
    "Population":        ["malthus", "populat", "struggle", "competition"],
    "Variation":         ["heredit", "inherit", "variation", "trait", "domest"],
    "Botany":            ["plant", "flower", "orchid", "insectivorous", "worm"],
    "Wallace":           ["wallace", "priority", "linnean", "joint"],
    "Religion":          ["god", "creator", "faith", "church", "belief", "design"],
}
_STOP = {"the","a","an","and","or","of","to","in","is","it","that","was","he","she"}
 
 
def _infer_topic(text: str) -> str:
    t = text.lower()
    for topic, kws in _TOPIC_MAP.items():
        if any(k in t for k in kws):
            return topic
    words = re.findall(r"[a-z]{5,}", t)
    freq = Counter(w for w in words if w not in _STOP)
    return freq.most_common(1)[0][0].title() if freq else "General"
 
 
def log_conversation_turn(role: str, text: str, timeline_year: int = 1870,
                          filename: str = "long_term_memory.json") -> None:
    """
    Log one conversation turn for the memory dashboard.
    Call after every user message and every Darwin response in app.py.
    role: "user" or "darwin"
    """
    data = load_long_term_memory(filename)
    topic = _infer_topic(text)
    entry = {
        "role": role,
        "text": text[:400],
        "topic": topic,
        "year": timeline_year,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    data.setdefault("conversation_log", []).append(entry)
    # cap at 500 turns
    if len(data["conversation_log"]) > 500:
        data["conversation_log"] = data["conversation_log"][-500:]
 
    data.setdefault("topic_counts", {})
    data["topic_counts"][topic] = data["topic_counts"].get(topic, 0) + 1
 
    data.setdefault("session_activity", [])
    if data["session_activity"]:
        slot = data["session_activity"][-1]
        if role == "user":
            slot["user_turns"] = slot.get("user_turns", 0) + 1
        else:
            slot["darwin_turns"] = slot.get("darwin_turns", 0) + 1
 
    save_long_term_memory(data, filename)
 
 
def start_dashboard_session(timeline_year: int = 1870,
                            filename: str = "long_term_memory.json") -> None:
    """
    Call once when a new Streamlit session begins (guard with session_state).
    Creates a new slot in session_activity.
    """
    data = load_long_term_memory(filename)
    data.setdefault("session_activity", [])
    data["session_activity"].append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "user_turns": 0,
        "darwin_turns": 0,
        "year": timeline_year,
    })
    save_long_term_memory(data, filename)
 
 
def get_dashboard_data(filename: str = "long_term_memory.json") -> dict:
    """Returns all data needed to render the Memory Dashboard page."""
    data = load_long_term_memory(filename)
    return {
        "session_count":   data.get("session_count", 0),
        "facts":           data.get("facts", []),
        "unique_topics":   len(data.get("topic_counts", {})),
        "total_turns":     len(data.get("conversation_log", [])),
        "topic_counts":    data.get("topic_counts", {}),
        "conversation_log":   data.get("conversation_log", [])[-60:],
        "session_activity":   data.get("session_activity", [])[-15:],
    }
 