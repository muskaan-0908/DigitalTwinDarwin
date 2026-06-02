from dotenv import load_dotenv
import os
import json
import streamlit as st
import google.generativeai as genai
from rag import retrieve
from memory import (
    load_long_term_memory,
    format_memory_for_prompt,
    update_long_term_memory,
    save_long_term_memory,
)
from conversation_summary import (
    maybe_summarise, get_prompt_context,
    render_summary_sidebar, SUMMARY_CSS
)
from memory_dashboard import render_memory_dashboard as _render_mem_dash, DASHBOARD_CSS, clear_memory
from persona import get_persona_prompt

st.set_page_config(
    page_title="Charles Darwin — Digital Twin",
    page_icon="DigitalTwin",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()
print("KEY =", os.getenv("GEMINI_API_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash")


st.markdown("""
<style>
[data-testid="stSidebar"] button[data-testid="stBaseButton-header"],
[data-testid="stSidebar"] button[kind="header"],
[data-testid="stSidebar"] > div > div > div > button,
button[data-testid="stSidebarNavCollapseButton"],
[data-testid="stSidebarContent"] button {
  background-color: #1a0f00 !important;
  border: 2px solid #c9a84c !important;
  border-radius: 10px !important;
  box-shadow: 0 0 0 2px #c9a84c, 0 4px 20px rgba(0,0,0,0.9) !important;
  opacity: 1 !important;
  padding: 6px !important;
  display: block !important;
  visibility: visible !important;
}
[data-testid="stSidebar"] button svg,
[data-testid="stSidebarContent"] button svg {
  fill: #F8E7A1 !important;
  color: #F8E7A1 !important;
}
section[data-testid="stSidebar"] + div button,
div[data-testid="stSidebarCollapsedControl"] button,
div[data-testid="collapsedControl"] button,
button[kind="header"],
.stSidebarCollapsedControl button {
  background-color: #1a0f00 !important;
  border: 2px solid #c9a84c !important;
  border-radius: 10px !important;
  box-shadow: 0 0 0 2px #c9a84c, 0 4px 20px rgba(0,0,0,0.9) !important;
  opacity: 1 !important;
  padding: 6px !important;
}
section[data-testid="stSidebar"] + div button svg,
div[data-testid="stSidebarCollapsedControl"] button svg,
div[data-testid="collapsedControl"] button svg {
  fill: #F8E7A1 !important;
  color: #F8E7A1 !important;
}
</style>
""", unsafe_allow_html=True)



st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400;1,600&family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');

:root {
  --parchment-light: #fdf8ee;
  --parchment-mid:   #f4ead6;
  --parchment-dark:  #e8d9b8;
  --ink-dark:        #1a0f00;
  --ink-mid:         #3d2b1f;
  --ink-warm:        #5c4a2a;
  --gold:            #9b7b2e;
  --gold-light:      #c9a84c;
  --gold-shine:      #e8c96b;
  --green-dark:      #1b3a1d;
  --green-mid:       #2d5a30;
  --shadow-warm:     rgba(60,30,0,0.15);
  --shadow-gold:     rgba(155,123,46,0.25);
}

* { box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] {
  font-family: 'Crimson Text', Georgia, serif !important;
  color: var(--ink-mid) !important;
}

[data-testid="stAppViewContainer"] {
  background-color: var(--parchment-light);
  background-image:
    radial-gradient(ellipse at top left,    rgba(212,185,140,0.35) 0%, transparent 55%),
    radial-gradient(ellipse at bottom right, rgba(180,150,100,0.30) 0%, transparent 55%);
}

[data-testid="stSidebar"] {
  background-color: var(--parchment-mid) !important;
  background-image: linear-gradient(180deg, rgba(155,123,46,0.08) 0%, transparent 30%) !important;
  border-right: 2px solid var(--gold) !important;
  box-shadow: 4px 0 20px var(--shadow-warm) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
section[data-testid="stSidebar"] { min-width: 300px !important; max-width: 300px !important; }

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small {
  color: var(--ink-mid) !important;
  font-family: 'Crimson Text', Georgia, serif !important;
}

[data-testid="stSidebar"] div {
  color: var(--ink-mid) !important;
  font-family: 'Crimson Text', Georgia, serif !important;
}

[data-testid="collapsedControl"],
[data-testid="collapsedControl"] > button,
button[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] > button {
  background-color: #1a0f00 !important;
  border-radius: 10px !important;
  border: 2px solid #c9a84c !important;
  box-shadow: 0 0 0 3px #c9a84c, 0 4px 16px rgba(0,0,0,0.8) !important;
  opacity: 1 !important;
  visibility: visible !important;
  z-index: 9999 !important;
}
[data-testid="collapsedControl"]:hover,
[data-testid="stSidebarCollapsedControl"]:hover,
[data-testid="stSidebarCollapsedControl"] > button:hover {
  background-color: #9b7b2e !important;
}
[data-testid="collapsedControl"] svg,
[data-testid="collapsedControl"] span,
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapsedControl"] span {
  fill: #F8E7A1 !important;
  color: #F8E7A1 !important;
  opacity: 1 !important;
  font-size: 1.4rem !important;
}

[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] small {
  color: var(--ink-mid) !important;
  font-family: 'Crimson Text', Georgia, serif !important;
}
h1 { font-family: 'Playfair Display', Georgia, serif !important; font-weight: 700 !important; color: var(--ink-dark) !important; }
h2, h3 { font-family: 'Playfair Display', Georgia, serif !important; color: var(--ink-mid) !important; }

.darwin-header {
  background: linear-gradient(135deg, #1a0f00 0%, #3d2b1f 40%, #5c4a2a 100%);
  border-radius: 16px;
  padding: 28px 36px;
  margin-bottom: 24px;
  box-shadow: 0 8px 32px var(--shadow-warm), 0 2px 8px var(--shadow-gold);
  border: 1px solid var(--gold);
  position: relative;
  overflow: hidden;
}
.darwin-header::before {
  content: '';
  position: absolute; top: -50%; right: -20%;
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(201,168,76,0.15) 0%, transparent 70%);
  pointer-events: none;
}
.darwin-header .badge {
  display: inline-block;
  background: rgba(201,168,76,0.18);
  border: 1px solid rgba(201,168,76,0.4);
  color: #e8c96b !important;
  padding: 3px 12px; border-radius: 20px;
  font-size: 0.78rem; font-family: 'Crimson Text', serif !important;
  letter-spacing: 0.5px; margin: 3px 4px 0 0;
}

.darwin-scene {
  max-width: 900px; margin: 10px auto 25px auto;
  text-align: center; font-family: 'EB Garamond', serif;
  font-style: italic; font-size: 1.15rem; color: #5c4a2a;
  padding: 12px 20px; border-left: 4px solid #9b7b2e;
  background: rgba(155,123,46,0.06); border-radius: 10px;
}

[data-testid="stChatMessage"] {
  border-radius: 18px !important; padding: 18px 22px !important;
  margin-bottom: 16px !important; box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important;
  background: linear-gradient(135deg, #fefcf9 0%, #f5eedc 100%) !important;
  border: 1px solid #e5dac4 !important;
  border-left: 5px solid var(--ink-warm) !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] div,
[data-testid="stChatMessage"] * {
  color: var(--ink-mid) !important;
  font-family: 'Crimson Text', Georgia, serif !important;
  font-size: 1.08rem !important;
  background: transparent !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]),
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
  background: linear-gradient(135deg, #fdf8eb 0%, #faf0d0 100%) !important;
  border: 1px solid #dfc98a !important; border-left: 5px solid var(--gold) !important;
  box-shadow: 0 2px 12px var(--shadow-gold) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) p,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) span:not([data-testid]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) *,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) p,
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) span:not([data-testid]),
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) * {
  color: var(--ink-mid) !important; font-family: 'EB Garamond', 'Crimson Text', Georgia, serif !important;
  font-size: 1.1rem !important; line-height: 1.75 !important;
}

[data-testid="chatAvatarIcon-user"] {
  background-color: var(--ink-warm) !important; border: 2px solid var(--ink-dark) !important; border-radius: 50% !important;
}
[data-testid="chatAvatarIcon-user"] svg { fill: #ffffff !important; }
[data-testid="chatAvatarIcon-user"] p  { color: #ffffff !important; }

[data-testid="chatAvatarIcon-assistant"] {
  background-color: var(--gold) !important; border: 2px solid var(--gold-light) !important; border-radius: 50% !important;
}
[data-testid="chatAvatarIcon-assistant"] svg { fill: var(--ink-dark) !important; }
[data-testid="chatAvatarIcon-assistant"] p  { color: var(--ink-dark) !important; }

[data-testid="stChatInput"] { background: transparent !important; }
[data-testid="stChatInput"] > div { background: transparent !important; border: none !important; }
[data-testid="stChatInput"] textarea {
  background: #fffdf7 !important; color: var(--ink-dark) !important;
  border: 1.5px solid var(--gold) !important; border-radius: 12px !important;
  font-family: 'Crimson Text', Georgia, serif !important; font-size: 1.05rem !important;
  padding: 12px 16px !important; box-shadow: 0 2px 12px var(--shadow-gold) !important;
  caret-color: var(--gold) !important;
}
[data-testid="stChatInput"] textarea:focus {
  border-color: var(--gold-light) !important; box-shadow: 0 4px 20px var(--shadow-gold) !important; outline: none !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--ink-warm) !important; font-style: italic !important; opacity: 0.7; }

.st-key-letter_mode [data-baseweb="checkbox"]:has(input:checked) > div:first-of-type {
  background-color: var(--gold) !important;
}
.st-key-letter_mode [data-baseweb="checkbox"]:not(:has(input:checked)) > div:first-of-type {
  background-color: var(--parchment-dark) !important;
}
.st-key-letter_mode [data-baseweb="checkbox"] > div:first-of-type > div {
  background-color: var(--parchment-light) !important;
}

.stButton > button {
  font-family: 'Crimson Text', Georgia, serif !important; font-size: 0.95rem !important;
  color: var(--ink-mid) !important;
  background: linear-gradient(135deg, var(--parchment-dark) 0%, var(--parchment-mid) 100%) !important;
  border: 1.5px solid var(--gold) !important; border-radius: 8px !important;
  padding: 6px 16px !important; transition: all 0.2s ease !important;
  box-shadow: 0 2px 8px var(--shadow-warm) !important;
}
.stButton > button:hover {
  background: linear-gradient(135deg, var(--gold) 0%, var(--gold-light) 100%) !important;
  color: var(--parchment-light) !important; border-color: var(--gold-light) !important;
  box-shadow: 0 4px 16px var(--shadow-gold) !important; transform: translateY(-1px) !important;
}


[data-testid="stSidebar"] .stButton > button {
  background: linear-gradient(135deg, var(--parchment-dark) 0%, var(--parchment-mid) 100%) !important;
  color: var(--ink-mid) !important;
  border: 1px solid rgba(155,123,46,0.45) !important;
  border-radius: 20px !important;
  font-family: 'Crimson Text', serif !important;
  font-size: 0.88rem !important;
  padding: 5px 14px !important;
  text-align: left !important;
  box-shadow: none !important;
  transition: all 0.2s ease !important;
  margin-bottom: 2px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
  background: linear-gradient(135deg, var(--gold) 0%, var(--gold-light) 100%) !important;
  color: var(--parchment-light) !important;
  transform: translateX(3px) !important;
  box-shadow: 2px 2px 8px var(--shadow-gold) !important;
}

.darwin-header h1,
.darwin-header h1 a,
.darwin-header [data-testid="stHeadingWithActionElements"],
.darwin-header [data-testid="stHeadingWithActionElements"] span {
  color: #F8E7A1 !important;
}

.darwin-header p,
.darwin-header p span,
.darwin-header div:not(.badge) {
  color: #F4D77A !important;
}

.darwin-header .badge {
  color: #e8c96b !important;
}
[data-testid="stMetricValue"] {
  color: var(--ink-dark) !important; font-family: 'Playfair Display', serif !important;
  font-size: 1.6rem !important; font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
  color: var(--ink-warm) !important; font-family: 'Crimson Text', serif !important;
  font-size: 0.85rem !important; text-transform: uppercase; letter-spacing: 0.8px;
}

hr {
  border: none !important; height: 1px !important;
  background: linear-gradient(90deg, transparent, var(--gold), transparent) !important;
  margin: 18px 0 !important; opacity: 0.6;
}

[data-testid="stAlert"] {
  background: linear-gradient(135deg, rgba(155,123,46,0.10) 0%, rgba(155,123,46,0.05) 100%) !important;
  border: 1px solid rgba(155,123,46,0.4) !important; border-left: 4px solid var(--gold) !important;
  border-radius: 10px !important;
}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] div {
  color: var(--ink-mid) !important;
  font-family: 'EB Garamond', Georgia, serif !important;
  font-style: italic; font-size: 1rem !important;
}

.era-badge {
  display: inline-block;
  background: linear-gradient(135deg, var(--ink-dark) 0%, var(--ink-mid) 100%);
  color: var(--gold-shine) !important; padding: 5px 14px; border-radius: 20px;
  font-size: 0.82rem; font-family: 'Crimson Text', serif; letter-spacing: 0.5px;
  border: 1px solid var(--gold); box-shadow: 0 2px 8px var(--shadow-warm);
}

.timeline-label {
  font-family: 'Playfair Display', Georgia, serif !important;
  color: var(--ink-dark) !important; font-size: 0.95rem; font-weight: 600;
  letter-spacing: 0.3px; margin-bottom: 4px;
}

[data-testid="stSidebar"] img {
  border-radius: 12px !important; border: 3px solid var(--gold) !important;
  box-shadow: 0 6px 24px var(--shadow-warm) !important;
}

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #2a1a08; }
::-webkit-scrollbar-thumb { background: var(--gold); border-radius: 4px; border: 1px solid #1a0f00; }
::-webkit-scrollbar-thumb:hover { background: var(--gold-light); }

[data-testid="stCaptionContainer"] {
  color: var(--gold-shine) !important; font-family: 'Crimson Text', serif !important;
  font-style: italic; font-size: 0.92rem !important;
}

[data-testid="stSlider"] > div > div > div > div {
  background: linear-gradient(90deg, var(--gold) 0%, var(--gold-light) 100%) !important;
}
[data-testid="stSlider"] > div > div > div > div > div {
  background: var(--gold-light) !important; border: 2px solid var(--parchment-dark) !important;
  box-shadow: 0 2px 8px var(--shadow-gold) !important;
}

[data-testid="stExpander"] {
  border: 1.5px solid var(--gold) !important;
  border-radius: 12px !important;
  box-shadow: 0 2px 12px var(--shadow-gold) !important;
  margin-top: 12px !important;
  overflow: hidden !important;
  background: linear-gradient(135deg, #fdf6e3 0%, #faf0d0 100%) !important;
}
[data-testid="stExpander"] details summary {
  background: linear-gradient(135deg, #3d2b1f 0%, #5c4a2a 100%) !important;
}
[data-testid="stExpander"] details summary:hover {
  background: linear-gradient(135deg, #5c4a2a 0%, #9b7b2e 100%) !important;
}
[data-testid="stExpander"] > div:last-child { background: transparent !important; padding: 16px 20px !important; }


[data-testid="stExpander"] summary p,
[data-testid="stExpander"] details summary p {
  color: #F8E7A1 !important;
  font-family: 'Playfair Display', Georgia, serif !important;
  font-size: 0.95rem !important;
  font-weight: 600 !important;
}
[data-testid="stExpander"] summary svg {
  fill: #c9a84c !important;
  color: #c9a84c !important;
}

.doc-card {
  background: rgba(155,123,46,0.07);
  border: 1px solid rgba(155,123,46,0.35);
  border-left: 4px solid var(--gold);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 14px;
}
.doc-card-title {
  font-family: 'Playfair Display', serif;
  font-size: 0.88rem; font-weight: 700;
  color: var(--ink-dark) !important;
  text-transform: uppercase; letter-spacing: 0.8px;
  margin-bottom: 8px; padding-bottom: 5px;
  border-bottom: 1px solid rgba(155,123,46,0.25);
}
.doc-card-text {
  font-family: 'EB Garamond', 'Crimson Text', Georgia, serif;
  font-size: 1rem; color: var(--ink-mid) !important;
  font-style: italic; line-height: 1.75; white-space: pre-wrap;
}

.memory-card {
  background: linear-gradient(135deg, #fdf6e3 0%, #faf0d0 100%);
  border: 1px solid rgba(155,123,46,0.4);
  border-left: 4px solid var(--gold);
  border-radius: 10px; padding: 12px 16px; margin-bottom: 10px;
}
.memory-card p {
  color: var(--ink-mid) !important; font-family: 'Crimson Text', Georgia, serif !important;
  font-size: 1rem !important; margin: 0 !important; line-height: 1.6;
}
.memory-card .mem-ts {
  color: var(--ink-warm) !important; font-size: 0.78rem !important;
  font-style: italic; margin-top: 4px !important;
}
.memory-header {
  font-family: 'Playfair Display', serif; font-size: 1.1rem; font-weight: 700;
  color: var(--ink-dark) !important; margin-bottom: 14px; padding-bottom: 8px;
  border-bottom: 1px solid rgba(155,123,46,0.3);
}
.memory-empty {
  font-family: 'EB Garamond', serif; font-style: italic;
  color: var(--ink-warm) !important; font-size: 0.95rem; text-align: center; padding: 20px;
}
.memory-stat {
  display: inline-block; background: var(--ink-mid); color: var(--gold-shine) !important;
  padding: 3px 10px; border-radius: 12px; font-size: 0.8rem;
  font-family: 'Crimson Text', serif; border: 1px solid var(--gold);
  margin-right: 6px; margin-bottom: 12px;
}

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { background: transparent !important; }
button[data-testid="stBaseButton-header"] { display: none !important; }
.block-container {
  padding-top: 1rem !important; max-width: 100% !important;
  transition: all 0.3s ease-in-out !important;
}
section[data-testid="stSidebar"] {
  transition: transform 0.45s cubic-bezier(0.4, 0, 0.2, 1),
              margin 0.45s cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 0.45s ease !important;
  will-change: transform, margin !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
  margin-left: -300px !important;
  transform: translateX(-10px) !important;
  box-shadow: none !important;
}
.main .block-container, .block-container {
  transition: all 0.45s cubic-bezier(0.4, 0, 0.2, 1) !important;
  max-width: 100% !important; will-change: padding, margin !important;
}
div[data-testid="collapsedControl"],
div[data-testid="stSidebarCollapsedControl"] {
  transition: all 0.45s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<style>{DASHBOARD_CSS}</style>", unsafe_allow_html=True)
st.markdown(f"<style>{SUMMARY_CSS}</style>", unsafe_allow_html=True)



import random

def get_thinking_phrase(query):
    q = query.lower().strip()
    
    if q in ["hi", "hii", "hello", "hey", "greetings"] or len(q.split()) <= 2 and any(word in q for word in ["hi", "hello", "hey", "good morning", "good day"]):
        return random.choice([
            "Adjusting my spectacles...",
            "Preparing to converse...",
            "Taking a seat in the study..."
        ])
        
    if any(word in q for word in ["evolution", "natural selection", "adaptation", "species", "organism"]):
        return random.choice([
            "Examining nature's clues...",
            "Tracing patterns in the evidence...",
            "Considering the workings of nature..."
        ])
    elif any(word in q for word in ["voyage", "beagle", "journey", "travel"]):
        return random.choice([
            "Comparing notes from the Beagle...",
            "Consulting expedition records...",
            "Reviewing voyage observations..."
        ])
    elif any(word in q for word in ["why", "explain", "theory", "hypothesis"]):
        return random.choice([
            "Weighing competing explanations...",
            "Reflecting upon my studies...",
            "Tracing patterns in the evidence..."
        ])
    else:
        return random.choice([
            "Leafing through my journals...",
            "Consulting expedition records...",
            "Reflecting upon my studies..."
        ])

def ask_darwin(question, year):
    phrase = get_thinking_phrase(question)
    with st.spinner(phrase):
        retrieved_docs = retrieve(question)
        st.session_state["last_retrieved_docs"] = retrieved_docs

        long_term_memory  = load_long_term_memory()
        long_term_context = format_memory_for_prompt(long_term_memory)
        system_prompt = get_persona_prompt(
            long_term_context, retrieved_docs,
            year=year,
            letter_mode=st.session_state.get("letter_mode", False)
        )

        prompt   = f"{system_prompt}\n\nUser Question:\n{question}"
        response = model.generate_content(prompt, stream=True)

    for chunk in response:
        text = getattr(chunk, "text", None)
        if text:
            yield text


def render_retrieved_docs():
    docs  = st.session_state.get("last_retrieved_docs", [])
    label = f" Retrieved Source Passages ({len(docs)} found)"

    with st.expander(label, expanded=False):
        if not docs:
            st.markdown(
                '<p style="color:var(--ink-warm);font-style:italic;'
                'font-family:\'Crimson Text\',serif;">'
                'No passages retrieved yet — send a message to Darwin first.</p>',
                unsafe_allow_html=True,
            )
            return
        for i, doc in enumerate(docs, 1):
            preview = doc.strip()
            if len(preview) > 600:
                preview = preview[:600] + "…"
            st.markdown(
                f'<div class="doc-card">'
                f'<div class="doc-card-title">Passage {i}</div>'
                f'<div class="doc-card-text">{preview}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )



if "messages" not in st.session_state:
    st.session_state.messages = []

if "show_memory" not in st.session_state:
    st.session_state.show_memory = False

if "last_retrieved_docs" not in st.session_state:
    st.session_state.last_retrieved_docs = []

if "pill_prompt" not in st.session_state:
    st.session_state.pill_prompt = None

if "session_count_incremented" not in st.session_state:
    mem = load_long_term_memory()
    mem["session_count"] = mem.get("session_count", 0) + 1
    save_long_term_memory(mem)
    st.session_state.session_count_incremented = True

if "selected_year" not in st.session_state:
    st.session_state.selected_year = 1870



with st.sidebar:

    try:
        st.image("image/charlesdarwin.jpg", use_container_width=True)
    except Exception:
        st.markdown("<div style='text-align:center;font-size:4rem;'>🧑🏼‍🔬</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center;margin-top:10px;'>
      <div style='font-family:Playfair Display,serif;font-size:1.35rem;font-weight:700;color:#1a0f00;'>Charles Darwin</div>
      <div style='font-family:Crimson Text,serif;font-size:0.92rem;color:#5c4a2a;letter-spacing:1px;margin-top:2px;'>1809 – 1882</div>
      <div style='font-family:Crimson Text,serif;font-size:0.9rem;color:#3d2b1f;margin-top:8px;font-style:italic;line-height:1.5;'>
        English naturalist, geologist<br>and biologist.<br>
        Author of <em>On the Origin of Species</em> (1859).
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")


    st.markdown('<p class="timeline-label"> Travel in Time</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:Crimson Text,serif;font-size:0.85rem;color:#5c4a2a;margin-top:-6px;">Speak to Darwin at any point in his life</p>', unsafe_allow_html=True)

    year = st.slider(
        label="Year:",
        min_value=1831, max_value=1882, value=st.session_state.selected_year, step=1,
        help="1831 = young naturalist on the Beagle. 1859 = just published Origin. 1882 = elder statesman.",
    )
    st.session_state.selected_year = year

    if year <= 1836:
        era_text = "🚢 Aboard HMS Beagle"
        era_note = "Darwin is a young naturalist on the voyage. *Origin of Species* is still decades away."
    elif year <= 1841:
        era_text = "🏙️ Gower Street, London"
        era_note = "Darwin is living at 'Macaw Cottage', quietly formulating his theory."
    elif year <= 1858:
        era_text = "🏡 Down House, Kent"
        era_note = "Darwin is accumulating evidence in private. He has not yet published."
    elif year <= 1860:
        era_text = "📖 *Origin of Species* published"
        era_note = "The book came out in 1859. Darwin is bracing for the scientific storm."
    elif year <= 1871:
        era_text = "🌿 Defending evolution"
        era_note = "Huxley fights Darwin's battles publicly. *The Descent of Man* is coming."
    else:
        era_text = "🧓 Elder statesman of science"
        era_note = "Darwin is celebrated but still experimenting — earthworms, plants, orchids."

    st.markdown(f'<span class="era-badge">{era_text}</span>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Crimson Text,serif;font-size:0.85rem;color:#5c4a2a;margin-top:8px;font-style:italic;">{era_note}</p>', unsafe_allow_html=True)

    st.markdown("---")

    st.info(
        '"It is not the strongest of the species that survives, '
        'nor the most intelligent. It is the one most adaptable to change."'
    )

    st.markdown("---")


    st.markdown('<p style="font-family:Playfair Display,serif;font-size:0.9rem;font-weight:600;color:#3d2b1f;">Try asking:</p>', unsafe_allow_html=True)

    if year <= 1836:
        suggestions = [
            "What did you see in the Galápagos?",
            "Describe the coral reefs you've observed.",
            "What is it like aboard HMS Beagle?",
        ]
    elif year <= 1858:
        suggestions = [
            "What theory are you working on?",
            "Tell me about your pigeon experiments.",
            "What do you think of Malthus's ideas?",
        ]
    elif year <= 1860:
        suggestions = [
            "How are people reacting to your book?",
            "Explain natural selection.",
            "Do humans share ancestry with apes?",
        ]
    else:
        suggestions = [
            "What are you researching now?",
            "Tell me about earthworms.",
            "How do you feel about your legacy?",
        ]

    for s in suggestions:
        if st.button(s, key=f"pill_{s}", use_container_width=True):
            st.session_state.pill_prompt = s
            st.rerun()

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑 Clear Chat", use_container_width=True, key="clear_chat"):
            st.session_state.messages = []
            st.session_state.last_retrieved_docs = []
            st.rerun()
    with col2:
        st.metric("Messages", len(st.session_state.messages))

    st.markdown("---")


    st.markdown('<p class="timeline-label"> Memory & Summaries</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:Crimson Text,serif;font-size:0.82rem;color:#5c4a2a;margin-top:-4px;">What Darwin remembers about you</p>', unsafe_allow_html=True)

    mem_btn_label = "✖ Hide Dashboard" if st.session_state.show_memory else " View Memory Dashboard"
    if st.button(mem_btn_label, use_container_width=True, key="toggle_memory"):
        st.session_state.show_memory = not st.session_state.show_memory
        st.rerun()

if "letter_mode" not in st.session_state:
    st.session_state.letter_mode = True

letter_mode = st.toggle(
    " Letter Mode",
    key="letter_mode"
)


current_year = st.session_state.selected_year

st.markdown(f"""
<div class="darwin-header">
  <h1 style="color:#F8E7A1 !important;font-size:2.8rem !important;font-weight:800 !important;
             font-family:'Playfair Display',serif !important;margin-bottom:10px !important;
             text-shadow: 0 2px 8px rgba(0,0,0,0.5);">
    The Darwin Archive
  </h1>
  <p style="color:#F4D77A !important;font-size:1.1rem !important;margin-top:0 !important;
            font-style:italic;opacity:1 !important;">
    An AI persona grounded in Charles Darwin's own writings · Speaking to you from the 1800s
  </p>
  <div style="margin-top:12px;">
    <span class="badge">Aboard the Beagle</span>
    <span class="badge">Conversations at Down House</span>
    <span class="badge">1831–1882 Timeline Experience</span>
    <span class="badge">Drawn from Darwin's Notes</span>
  </div>
</div>
""", unsafe_allow_html=True)


render_summary_sidebar()


if st.session_state.show_memory:
    with st.container():
        _render_mem_dash(load_long_term_memory())
    st.markdown("---")


if current_year <= 1836:
    scene_text = f"The year is {current_year}. You find Darwin aboard HMS Beagle, somewhere in the southern seas..."
elif current_year <= 1841:
    scene_text = f"The year is {current_year}. You find Darwin at his London residence on Upper Gower Street..."
elif current_year <= 1858:
    scene_text = f"The year is {current_year}. You find Darwin at Down House, surrounded by specimens and notebooks..."
elif current_year in (1859, 1860):
    scene_text = f"The year is {current_year}. Darwin has just published On the Origin of Species..."
else:
    scene_text = f"The year is {current_year}. You find Darwin at Down House, an elder statesman of natural science..."

st.markdown(f'<div class="darwin-scene">{scene_text}</div>', unsafe_allow_html=True)


if len(st.session_state.messages) == 0:
    if current_year <= 1836:
        welcome = ("Good day! I am Charles Darwin, naturalist on this extraordinary voyage. "
                   "The variety of life I have observed — from the coral reefs to the tortoises "
                   "of the Galápagos — fills me with endless wonder. What would you like to discuss?")
    elif current_year <= 1841:
        welcome = ("Good day! Do forgive the noise of the city — it rather tries my nerves. "
                   "I confess I am deep in thought on matters of great consequence, though not yet ready "
                   "to speak of them openly. What brings you to see me?")
    elif current_year <= 1858:
        welcome = ("Good day! I am deep in my investigations here at Down House. "
                   "I have been quietly working on a rather large theory for some years now — "
                   "though I am not yet ready to publish. What brings you to see me?")
    elif current_year in (1859, 1860):
        welcome = ("Good day! You find me in a rather anxious state — my book has just been published "
                   "and the reaction from the scientific and religious community is quite something. "
                   "I welcome your questions.")
    else:
        welcome = ("Good day! Do sit down. I have been in correspondence with naturalists around the world "
                   "and have much on my mind. What would you like to discuss?")

    with st.chat_message("assistant", avatar="🧑🏼‍🔬"):
        st.markdown(welcome)


for message in st.session_state.messages:
    avatar = "🧑🏼‍🔬" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"], unsafe_allow_html=True)


if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    render_retrieved_docs()


typed_prompt = st.chat_input(f"Ask Darwin something (speaking to him in {current_year})...")


prompt = st.session_state.pill_prompt or typed_prompt


if st.session_state.pill_prompt:
    st.session_state.pill_prompt = None

if prompt:

    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})


    with st.chat_message("assistant", avatar="🧑🏼‍🔬"):
        response_text = st.write_stream(ask_darwin(prompt, current_year))
        
        from uncertainty import get_uncertainty_score
        unc = get_uncertainty_score(response_text)
        unc_html = (
            f'<div style="margin-top: 10px; padding: 6px 12px; background: rgba(0,0,0,0.03); '
            f'border-left: 3px solid {unc["colour"]}; border-radius: 4px; '
            f'font-size: 0.9rem; color: {unc["colour"]}; font-family: \'Crimson Text\', serif;">'
            f'{unc["icon"]} <strong>Confidence:</strong> {unc["label"]} (Score: {unc["score"]}/100)</div>'
        )
        st.markdown(unc_html, unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": response_text + "\n\n" + unc_html})


    maybe_summarise(st.session_state.messages, year=st.session_state.selected_year)


    user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
    if len(user_msgs) % 3 == 0:
        with st.spinner("Darwin is filing away memories..."):
            update_long_term_memory(
                st.session_state.messages,
                session_count=load_long_term_memory().get("session_count", 0)
            )


    st.rerun()