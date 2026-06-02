import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()


VALID_CATEGORIES = {"background", "interests", "beliefs", "questions_asked", "personal"}
DEFAULT_CATEGORY = "personal"


def _migrate_fact(fact) -> dict:
    if isinstance(fact, str):
        return {
            "text": fact,
            "category": DEFAULT_CATEGORY,
            "added_session": 0,
            "turn": 0,
        }
    return {
        "text": fact.get("text", ""),
        "category": fact.get("category", DEFAULT_CATEGORY),
        "added_session": fact.get("added_session", 0),
        "turn": fact.get("turn", 0),
    }



def load_long_term_memory(filename: str = "long_term_memory.json") -> dict:
    default = {"facts": [], "session_count": 0, "total_turns": 0}
    if not os.path.exists(filename):
        return default
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default


        raw_facts = data.get("facts", [])
        data["facts"] = [_migrate_fact(f) for f in raw_facts if f]

        data.setdefault("session_count", 0)
        data.setdefault("total_turns", 0)
        return data
    except Exception:
        return default


def save_long_term_memory(memory_data: dict, filename: str = "long_term_memory.json") -> bool:
    try:
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(memory_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[memory] Error saving: {e}")
        return False



def format_memory_for_prompt(memory_data: dict) -> str:
  
    facts = [f for f in memory_data.get("facts", []) if f.get("text")]
    if not facts:
        return "No prior context about this user."

    groups: dict[str, list[str]] = {}
    for fact in facts:
        cat = fact.get("category", DEFAULT_CATEGORY)
        groups.setdefault(cat, []).append(fact["text"])

    category_labels = {
        "background":      "Background",
        "interests":       "Interests",
        "beliefs":         "Beliefs & Views",
        "questions_asked": "Topics They Have Asked About",
        "personal":        "Personal Details",
    }

    lines = ["You remember the following about this user from previous conversations:"]
    for cat, label in category_labels.items():
        if cat in groups:
            lines.append(f"\n{label}:")
            for text in groups[cat]:
                lines.append(f"  - {text}")
    return "\n".join(lines)



def get_facts_by_category(memory_data: dict) -> dict[str, list[dict]]:

    groups: dict[str, list[dict]] = {}
    for fact in memory_data.get("facts", []):
        if not fact.get("text"):
            continue
        cat = fact.get("category", DEFAULT_CATEGORY)
        groups.setdefault(cat, []).append(fact)
    return groups



def update_long_term_memory(
    messages: list[dict],
    filename: str = "long_term_memory.json",
    session_count: int = 0,
) -> bool:
    
    if not messages:
        return False

    memory = load_long_term_memory(filename)
    current_facts = memory.get("facts", [])
    turn_number = len(messages)

    conversation_history = "\n".join(
        f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}"
        for msg in messages
    )

    existing_text = json.dumps(
        [f.get("text", "") for f in current_facts if f.get("text")],
        indent=2
    )

    prompt = f"""You are the memory manager for a Charles Darwin digital twin.
Analyse the conversation below and produce an updated list of facts about the USER (not Darwin).

EXISTING FACTS:
{existing_text}

CONVERSATION:
{conversation_history}

INSTRUCTIONS:
1. Extract new personal details, interests, beliefs, or questions the user revealed.
2. Update or remove facts that are now outdated or contradicted.
3. Assign each fact one category from: background | interests | beliefs | questions_asked | personal
4. Return ONLY valid JSON — an array of objects, each with "text" (string) and "category" (string).
   No markdown fences, no preamble, no extra keys.

Example:
[
  {{"text": "The user is a biology student.", "category": "background"}},
  {{"text": "The user is curious about barnacles.", "category": "interests"}}
]
"""

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[memory] GEMINI_API_KEY not set — skipping update.")
            return False

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        raw_facts = json.loads(text)
        if not isinstance(raw_facts, list):
            print("[memory] Unexpected response format.")
            return False

        updated_facts = []
        for item in raw_facts:
            if isinstance(item, str):
                item = {"text": item, "category": DEFAULT_CATEGORY}
            cat = item.get("category", DEFAULT_CATEGORY)
            if cat not in VALID_CATEGORIES:
                cat = DEFAULT_CATEGORY
            prev = next(
                (f for f in current_facts if f.get("text", "").strip().lower()
                 == item.get("text", "").strip().lower()),
                None
            )
            updated_facts.append({
                "text": item.get("text", "").strip(),
                "category": cat,
                "added_session": prev["added_session"] if prev else session_count,
                "turn": prev["turn"] if prev else turn_number,
            })

        memory["facts"] = [f for f in updated_facts if f["text"]]
        memory["total_turns"] = memory.get("total_turns", 0) + 1
        save_long_term_memory(memory, filename)
        return True

    except Exception as e:
        print(f"[memory] Update failed: {e}")
        return False