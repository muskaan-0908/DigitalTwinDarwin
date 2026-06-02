"""
conversation_summary.py  —  Rolling conversation summariser for DigitalTwin Darwin
-----------------------------------------------------------------------------------
How it works:

ROLLING SUMMARY STRATEGY:
  • After every SUMMARY_EVERY messages (default: 10), the oldest messages are
    compressed into a running summary using Gemini.
  • The summary is stored in st.session_state["conversation_summary"]
    AND persisted to summary.json so it survives page refreshes.
  • In app.py, instead of passing all 40+ messages to the LLM, we pass:
        [rolling_summary_block] + [last KEEP_RECENT messages]
  • This keeps the prompt lean and avoids context-window bloat.

SIDEBAR PANEL:
  • render_summary_sidebar() shows a "Story So Far" collapsible panel
    in the Victorian style, displaying the rolling summary.

USAGE IN app.py:
  1. Import:
        from conversation_summary import (
            maybe_summarise, get_prompt_context,
            render_summary_sidebar, SUMMARY_CSS
        )

  2. Inject CSS (once, after your existing CSS block):
        st.markdown(f"<style>{SUMMARY_CSS}</style>", unsafe_allow_html=True)

  3. After every assistant reply (where you currently call update_long_term_memory):
        maybe_summarise(st.session_state.messages, year=st.session_state.selected_year)

  4. In ask_darwin(), replace the raw messages history passed to the prompt with:
        context_messages = get_prompt_context(st.session_state.messages)
     Then use context_messages for your prompt instead of the full list.

  5. In the sidebar, after render_memory_dashboard():
        render_summary_sidebar()
"""

import os
import json
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
SUMMARY_EVERY   = 10    # compress after every N messages
KEEP_RECENT     = 4     # always keep the last N messages verbatim
SUMMARY_FILE    = "summary.json"

# ── CSS ───────────────────────────────────────────────────────────────────────
SUMMARY_CSS = """
/* ── CONVERSATION SUMMARY PANEL ─────────────────────────── */

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
/* ── END SUMMARY PANEL ───────────────────────────────────── */
"""


# ── Persistence ───────────────────────────────────────────────────────────────

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


# ── Gemini summariser ─────────────────────────────────────────────────────────

def _call_gemini_summary(
    messages_to_compress: list[dict],
    existing_summary: str,
    year: int,
) -> str:
    """
    Compress messages_to_compress into a new rolling summary,
    incorporating the existing summary if present.
    Returns the new summary string, or the old one on failure.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return existing_summary

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Format messages
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


# ── Core: maybe_summarise ─────────────────────────────────────────────────────

def maybe_summarise(messages: list[dict], year: int = 1870) -> bool:
    """
    Call after every assistant reply.
    Compresses old messages into a rolling summary when the total count
    crosses a SUMMARY_EVERY boundary.

    Returns True if a summary was generated, False otherwise.
    """
    total = len(messages)
    if total < SUMMARY_EVERY:
        return False

    # Load existing state
    saved = _load_summary()
    last_summarised_at = saved.get("message_count", 0)

    # Only trigger if we've accumulated SUMMARY_EVERY new messages since last run
    if total - last_summarised_at < SUMMARY_EVERY:
        return False

    # Messages to compress = everything except the last KEEP_RECENT
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


# ── Context builder for prompt ────────────────────────────────────────────────

def get_prompt_context(messages: list[dict]) -> list[dict]:
    """
    Returns a lean message list for use in the LLM prompt:
        [summary_message (if exists)] + [last KEEP_RECENT messages]

    Use this instead of the full messages list when building the Darwin prompt.

    In app.py, inside ask_darwin():
        from conversation_summary import get_prompt_context
        context = get_prompt_context(st.session_state.messages)
        # use `context` to build conversation_history for the prompt
    """
    summary_text = st.session_state.get("conversation_summary", "")

    # Also try loading from file (survives page refresh)
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


# ── Sidebar panel ─────────────────────────────────────────────────────────────

def render_summary_sidebar() -> None:
    """
    Render the 'Story So Far' panel in the Streamlit sidebar.
    Call from within `with st.sidebar:`.
    """
    summary_text = st.session_state.get("conversation_summary", "")
    if not summary_text:
        saved        = _load_summary()
        summary_text = saved.get("text", "")
        count        = saved.get("message_count", 0)
    else:
        count = _load_summary().get("message_count", 0)

    st.markdown(
        '<div class="sum-header">📖 Story So Far</div>',
        unsafe_allow_html=True
    )

    if not summary_text:
        st.markdown(
            '<div class="sum-empty">No summary yet — keep conversing<br>with Darwin to build one.</div>',
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

    # Manual refresh button
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


# ── Clear ─────────────────────────────────────────────────────────────────────

def clear_summary():
    """Call when the user clicks 'Clear Chat'."""
    _save_summary({"text": "", "message_count": 0, "year": 1870})
    if "conversation_summary" in st.session_state:
        del st.session_state["conversation_summary"]