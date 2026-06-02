import os
import json
import streamlit as st
import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()


SUMMARY_EVERY   = 10    
KEEP_RECENT     = 4     
SUMMARY_FILE    = "summary.json"


SUMMARY_CSS = """


.sum-header {
    font-family: 'Playfair Display', serif;
    font-size: 0.88rem;
    font-weight: 700;
    color: #1a0f00;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin: 0 0 8px 0;
    display: flex;
    align-items: center;
    gap: 7px;
}

.sum-box {
    background: linear-gradient(135deg, #fdf6e3 0%, #faf0d0 100%);
    border: 1px solid #dfc98a;
    border-left: 4px solid #9b7b2e;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 8px;
}

.sum-title {
    font-family: 'Playfair Display', serif;
    font-size: 0.78rem;
    font-weight: 700;
    color: #5c4a2a;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}

.sum-text {
    font-family: 'EB Garamond', 'Crimson Text', serif;
    font-size: 0.88rem;
    color: #3d2b1f;
    line-height: 1.6;
    font-style: italic;
}

.sum-meta {
    font-family: 'Crimson Text', serif;
    font-size: 0.7rem;
    color: rgba(92,74,42,0.55);
    margin-top: 6px;
    text-align: right;
}

.sum-empty {
    font-family: 'Crimson Text', serif;
    font-size: 0.82rem;
    font-style: italic;
    color: rgba(92,74,42,0.5);
    text-align: center;
    padding: 8px;
}
"""




def _load_summary() -> dict:
    default = {"text": "", "message_count": 0, "year": 1870}
    if not os.path.exists(SUMMARY_FILE):
        return default
    try:
        with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except Exception:
        return default


def _save_summary(data: dict):
    try:
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[summary] Save failed: {e}")




def _call_gemini_summary(
    messages_to_compress: list[dict],
    existing_summary: str,
    year: int,
) -> str:

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return existing_summary

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        convo = "\n".join(
            f"{'USER' if m['role'] == 'user' else 'DARWIN'}: {m['content']}"
            for m in messages_to_compress
        )

        prior = f"Existing summary:\n{existing_summary}\n\n" if existing_summary else ""

        prompt = f"""You are summarising a conversation between a user and a digital twin
of Charles Darwin speaking from the year {year}.

{prior}New conversation to incorporate:
{convo}

Write a concise narrative summary (3-6 sentences, past tense) that captures:
- The main topics discussed
- Any interesting positions Darwin took
- What the user seemed most curious about
- The emotional tone of the exchange

Write in the style of a 19th-century correspondent's note. Be vivid but brief.
Return only the summary text, no preamble."""

        resp = model.generate_content(prompt)
        return resp.text.strip()

    except Exception as e:
        print(f"[summary] Gemini call failed: {e}")
        return existing_summary



def maybe_summarise(messages: list[dict], year: int = 1870) -> bool:
    total = len(messages)
    if total < SUMMARY_EVERY:
        return False

    saved = _load_summary()
    last_summarised_at = saved.get("message_count", 0)

    if total - last_summarised_at < SUMMARY_EVERY:
        return False

    messages_to_compress = messages[:total - KEEP_RECENT]
    existing_summary     = saved.get("text", "")

    new_summary = _call_gemini_summary(messages_to_compress, existing_summary, year)

    summary_data = {
        "text":          new_summary,
        "message_count": total,
        "year":          year,
    }
    _save_summary(summary_data)
    st.session_state["conversation_summary"] = new_summary
    return True



def get_prompt_context(messages: list[dict]) -> list[dict]:
    summary_text = st.session_state.get("conversation_summary", "")

    if not summary_text:
        saved        = _load_summary()
        summary_text = saved.get("text", "")
        if summary_text:
            st.session_state["conversation_summary"] = summary_text

    recent = messages[-KEEP_RECENT:] if len(messages) > KEEP_RECENT else messages

    if summary_text and len(messages) > KEEP_RECENT:
        summary_msg = {
            "role":    "system",
            "content": f"[CONVERSATION SUMMARY SO FAR]\n{summary_text}\n[END SUMMARY]"
        }
        return [summary_msg] + recent
    else:
        return recent



def render_summary_sidebar() -> None:

    summary_text = st.session_state.get("conversation_summary", "")
    if not summary_text:
        saved        = _load_summary()
        summary_text = saved.get("text", "")
        count        = saved.get("message_count", 0)
    else:
        count = _load_summary().get("message_count", 0)

    st.markdown(
        '<div class="sum-header">Story So Far</div>',
        unsafe_allow_html=True
    )

    if not summary_text:
        st.markdown(
            '<div class="sum-empty">No summary yet. Keep conversing<br>with Darwin to build one.</div>',
            unsafe_allow_html=True
        )
        return

    st.markdown(f"""
    <div class="sum-box">
        <div class="sum-title">The Conversation Thus Far</div>
        <div class="sum-text">{summary_text}</div>
        <div class="sum-meta">Compiled from {count} exchanges</div>
    </div>
    """, unsafe_allow_html=True)


    if st.button("↺ Refresh Summary", use_container_width=True, key="refresh_summary"):
        messages = st.session_state.get("messages", [])
        if messages:
            year     = st.session_state.get("selected_year", 1870)
            saved    = _load_summary()
            existing = saved.get("text", "")
            new      = _call_gemini_summary(messages, existing, year)
            summary_data = {
                "text":          new,
                "message_count": len(messages),
                "year":          year,
            }
            _save_summary(summary_data)
            st.session_state["conversation_summary"] = new
            st.rerun()



def clear_summary():
    _save_summary({"text": "", "message_count": 0, "year": 1870})
    if "conversation_summary" in st.session_state:
        del st.session_state["conversation_summary"]