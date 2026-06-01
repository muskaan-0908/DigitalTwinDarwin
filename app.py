from dotenv import load_dotenv
import os
import streamlit as st
import google.generativeai as genai


from rag import retrieve
from memory import load_long_term_memory, format_memory_for_prompt, update_long_term_memory, save_long_term_memory
from persona import get_persona_prompt

st.set_page_config(
    page_title="Charles Darwin — Digital Twin",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)
load_dotenv()

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)
model = genai.GenerativeModel("gemini-2.5-flash")



st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400;1,600&family=EB+Garamond:ital,wght@0,400;0,500;1,400&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap');

/* ── ROOT VARIABLES ───────────────────────────── */
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
    --cream-green:     #e8f4e8;
    --shadow-warm:     rgba(60, 30, 0, 0.15);
    --shadow-gold:     rgba(155, 123, 46, 0.25);
}

/* ── GLOBAL RESET & BASE ─────────────────────── */
* { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Crimson Text', 'Georgia', serif !important;
    color: var(--ink-mid) !important;
}

/* ── BACKGROUND — Aged Parchment with Vignette ── */
[data-testid="stAppViewContainer"] {
    background-color: var(--parchment-light);
    background-image:
        radial-gradient(ellipse at top left, rgba(212,185,140,0.35) 0%, transparent 55%),
        radial-gradient(ellipse at bottom right, rgba(180,150,100,0.3) 0%, transparent 55%),
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='400' height='400' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
}

/* ── SIDEBAR ─────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: var(--parchment-mid) !important;
    background-image:
        linear-gradient(180deg, rgba(155,123,46,0.08) 0%, transparent 30%),
        url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='0.05'/%3E%3C/svg%3E") !important;
    border-right: 2px solid var(--gold) !important;
    box-shadow: 4px 0 20px var(--shadow-warm) !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}
            
button:has([data-testid="stIconMaterial"]) {
    background: #9b7b2e !important;
    border: 2px solid #c9a84c !important;
    border-radius: 10px !important;
}

button:has([data-testid="stIconMaterial"]) span {
    color: white !important;
}


/* ── SIDEBAR TEXT ───────────────────────────── */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] span {
            class="topic-pill"{
             color: var(--gold) !important;
    font-family: 'Crimson Text', Georgia, serif !important;
            }},
[data-testid="stSidebar"] div {
    color: var(--ink-mid) !important;
    font-family: 'Crimson Text', Georgia, serif !important;
}
[data-testid="collapsedControl"] {
    background-color: var(--ink-mid) !important;   /* button background */
    color: white !important;                /* icon color */
    border-radius: 10px !important;
    border: 2px solid #c9a84c !important;
}

/* Hover effect */
[data-testid="collapsedControl"]:hover {
    background-color: #c9a84c !important;
}

/* Arrow icon */
[data-testid="collapsedControl"] svg {
    fill: white !important;
    color: white !important;
}
/* ── MAIN AREA TEXT ─────────────────────────── */
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] small {
    color: var(--ink-mid) !important;
    font-family: 'Crimson Text', Georgia, serif !important;
}
/* ── MAIN TITLE ─────────────────────────────── */
h1 {
    font-family: 'Playfair Display', Georgia, serif !important;
    font-weight: 700 !important;
    color: var(--ink-dark) !important;
    letter-spacing: 0.5px;
    line-height: 1.2 !important;
}

h2, h3 {
    font-family: 'Playfair Display', Georgia, serif !important;
    color: var(--ink-mid) !important;
}

/* ── DECORATIVE HEADER BANNER ────────────────── */
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
    position: absolute;
    top: -50%;
    right: -20%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(201,168,76,0.15) 0%, transparent 70%);
    pointer-events: none;
}
/* FIX: Title colour — inline style wins over class in Streamlit */
.darwin-header h1 {
    color: #e8c96b !important;
    font-family: 'Playfair Display', serif !important;
    font-size: 2.2rem !important;
    margin: 0 !important;
    text-shadow: 0 2px 8px rgba(0,0,0,0.5);
}
.darwin-header .subtitle {
    color: rgba(232,201,107,0.75) !important;
    font-family: 'Crimson Text', serif !important;
    font-size: 1.05rem;
    margin-top: 6px;
    font-style: italic;
    letter-spacing: 0.3px;
}
.darwin-header .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 14px;
}
.darwin-header .badge {
    background: rgba(201,168,76,0.18);
    border: 1px solid rgba(201,168,76,0.4);
    color: var(--gold-shine) !important;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-family: 'Crimson Text', serif !important;
    letter-spacing: 0.5px;
}

/* ── BLINKING CURSOR in chat input ───────────── */
@keyframes blink-caret {
    0%, 100% { caret-color: var(--gold); }
    50%       { caret-color: transparent; }
}

/* ===== CHAT MESSAGES ===== */

[data-testid="stChatMessage"] {
    border-radius: 18px !important;
    padding: 18px 22px !important;
    margin-bottom: 16px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important;
}

/* USER */
[data-testid="stChatMessage"]:has([aria-label="user avatar"]) {
    background: linear-gradient(
        135deg,
        #e8f4e8 0%,
        #d8ecd8 100%
    ) !important;

    border-left: 5px solid #2d5a30 !important;
    border: 1px solid #b8d4b8 !important;
}

/* DARWIN */
[data-testid="stChatMessage"]:has([aria-label="assistant avatar"]) {
    background: linear-gradient(
        135deg,
        #fdf6e3 0%,
        #faf0d0 100%
    ) !important;

    border-left: 5px solid #9b7b2e !important;
    border: 1px solid #dfc98a !important;
}
/* Target text elements specifically, not * (avoids recolouring avatars) */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) p,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) span:not([data-testid]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stMarkdown {
    color: var(--green-dark) !important;
    font-family: 'Crimson Text', Georgia, serif !important;
    font-size: 1.08rem !important;
}

/* ── USER AVATAR — green circle ─────────────── */
[data-testid="chatAvatarIcon-user"] {
    background-color: var(--green-mid) !important;
    border: 2px solid var(--green-dark) !important;
    border-radius: 50% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="chatAvatarIcon-user"] svg {
    fill: #ffffff !important;
    color: #ffffff !important;
}
[data-testid="chatAvatarIcon-user"] p {
    color: #ffffff !important;
}

/* ── DARWIN BUBBLE — warm parchment with gold ── */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: linear-gradient(135deg, #fdf6e3 0%, #faf0d0 100%) !important;
    border: 1px solid #dfc98a !important;
    border-left: 4px solid var(--gold) !important;
    box-shadow: 0 2px 12px var(--shadow-gold) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]):hover {
    box-shadow: 0 4px 24px var(--shadow-gold) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) p,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) span:not([data-testid]),
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) .stMarkdown {
    color: var(--ink-mid) !important;
    font-family: 'EB Garamond', 'Crimson Text', Georgia, serif !important;
    font-size: 1.1rem !important;
    line-height: 1.75 !important;
}

/* ── DARWIN AVATAR — gold circle ─────────────── */
[data-testid="chatAvatarIcon-assistant"] {
    background-color: var(--gold) !important;
    border: 2px solid var(--gold-light) !important;
    border-radius: 50% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="chatAvatarIcon-assistant"] svg {
    fill: var(--ink-dark) !important;
    color: var(--ink-dark) !important;
}
[data-testid="chatAvatarIcon-assistant"] p {
    color: var(--ink-dark) !important;
}

/* ── CHAT INPUT BOX ──────────────────────────── */
[data-testid="stChatInput"] {
    background: transparent !important;
}
[data-testid="stChatInput"] textarea {
    background: linear-gradient(135deg, #fffdf7 0%, #fdf8ee 100%) !important;
    color: var(--ink-dark) !important;
    border: 1.5px solid var(--gold) !important;
    border-radius: 12px !important;
    font-family: 'Crimson Text', Georgia, serif !important;
    font-size: 1.05rem !important;
    padding: 12px 16px !important;
    box-shadow: 0 2px 12px var(--shadow-gold) !important;
    caret-color: var(--gold) !important;
    animation: blink-caret 1s step-end infinite !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--gold-light) !important;
    box-shadow: 0 4px 20px var(--shadow-gold) !important;
    outline: none !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--ink-warm) !important;
    font-style: italic !important;
    opacity: 0.7;
}

/* ── SLIDER ─────────────────────────────────── */
[data-testid="stSlider"] > div > div > div > div {
    background: linear-gradient(90deg, var(--gold) 0%, var(--gold-light) 100%) !important;
}
[data-testid="stSlider"] > div > div > div > div > div {
    background: var(--gold-light) !important;
    border: 2px solid var(--parchment-dark) !important;
    box-shadow: 0 2px 8px var(--shadow-gold) !important;
}

/* ── BUTTONS ─────────────────────────────────── */
.stButton > button {
    font-family: 'Crimson Text', Georgia, serif !important;
    font-size: 0.95rem !important;
    color: var(--ink-mid) !important;
    background: linear-gradient(135deg, var(--parchment-dark) 0%, var(--parchment-mid) 100%) !important;
    border: 1.5px solid var(--gold) !important;
    border-radius: 8px !important;
    padding: 6px 16px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px var(--shadow-warm) !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, var(--gold) 0%, var(--gold-light) 100%) !important;
    color: var(--parchment-light) !important;
    border-color: var(--gold-light) !important;
    box-shadow: 0 4px 16px var(--shadow-gold) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ── METRICS ─────────────────────────────────── */
[data-testid="stMetricValue"] {
    color: var(--ink-dark) !important;
    font-family: 'Playfair Display', serif !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: var(--ink-warm) !important;
    font-family: 'Crimson Text', serif !important;
    font-size: 0.85rem !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* ── DIVIDERS ────────────────────────────────── */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--gold), transparent) !important;
    margin: 18px 0 !important;
    opacity: 0.6;
}

/* ── INFO BOX (Darwin quote) ─────────────────── */
[data-testid="stAlert"] {
    background: linear-gradient(135deg, rgba(155,123,46,0.1) 0%, rgba(155,123,46,0.05) 100%) !important;
    border: 1px solid rgba(155,123,46,0.4) !important;
    border-left: 4px solid var(--gold) !important;
    border-radius: 10px !important;
    color: var(--ink-mid) !important;
}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] div {
    color: var(--ink-mid) !important;
    font-family: 'EB Garamond', Georgia, serif !important;
    font-style: italic;
    font-size: 1rem !important;
}

/* ── ERA BADGE ───────────────────────────────── */
.era-badge {
    display: inline-block;
    background: linear-gradient(135deg, var(--ink-dark) 0%, var(--ink-mid) 100%);
    color: var(--gold-shine) !important;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-family: 'Crimson Text', serif;
    letter-spacing: 0.5px;
    border: 1px solid var(--gold);
    box-shadow: 0 2px 8px var(--shadow-warm);
}

/* ── TOPIC PILLS ─────────────────────────────── */
.topic-pill {
    display: inline-block;
    background: linear-gradient(135deg, var(--parchment-dark) 0%, var(--parchment-mid) 100%);
    color: var(--ink-mid) !important;
    padding: 4px 12px;
    border-radius: 14px;
    font-size: 0.83rem;
    font-family: 'Crimson Text', serif;
    margin: 3px;
    border: 1px solid rgba(155,123,46,0.35);
    cursor: pointer;
    transition: all 0.2s ease;
}
.topic-pill:hover {
    background: linear-gradient(135deg, var(--gold) 0%, var(--gold-light) 100%);
    color: var(--parchment-dark) !important;
}

/* ── TIMELINE LABEL ──────────────────────────── */
.timeline-label {
    font-family: 'Playfair Display', Georgia, serif !important;
    color: var(--ink-dark) !important;
    font-size: 0.95rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    margin-bottom: 4px;
}

/* ── SIDEBAR IMAGE ───────────────────────────── */
[data-testid="stSidebar"] img {
    border-radius: 12px !important;
    border: 3px solid var(--gold) !important;
    box-shadow: 0 6px 24px var(--shadow-warm) !important;
}

/* ── SCROLLBAR STYLING ───────────────────────── */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-track {
    background: var(--ink-mid);
}
::-webkit-scrollbar-thumb {
    background: var(--ink-mid);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--ink-mid);
}

/* ── CAPTION ─────────────────────────────────── */
[data-testid="stCaptionContainer"] {
    color: var(--ink-warm) !important;
    font-family: 'Crimson Text', serif !important;
    font-style: italic;
    font-size: 0.92rem !important;
}
/* ── RETRIEVED DOCUMENTS EXPANDER ───────────── */
/* Refined Retrieved Documents Expander Styling */
/* Outer expander container */
[data-testid="stExpander"] {
    background: linear-gradient(135deg, #fdf6e3 0%, #faf0d0 100%) !important;
    border: 1.5px solid var(--gold) !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 12px var(--shadow-gold) !important;
    margin-top: 12px !important;
    overflow: hidden !important;
    transition: box-shadow 0.2s ease, transform 0.2s ease !important;
}
[data-testid="stExpander"]:hover {
    box-shadow: 0 4px 20px var(--shadow-gold) !important;
    transform: translateY(-2px) !important;
}
/* Expander header row */
[data-testid="stExpander"] summary {
    background: linear-gradient(135deg, #1a0f00 0%, #3d2b1f 60%, #5c4a2a 100%) !important;
    padding: 12px 18px !important;
    border-radius: 10px 10px 0 0 !important;
    cursor: pointer !important;
    border-bottom: 1.5px solid var(--gold) !important;
    transition: background 0.2s ease !important;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
[data-testid="stExpander"] summary:hover {
    background: linear-gradient(135deg, #3d2b1f 0%, #5c4a2a 100%) !important;
}
/* Header label text */
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary div {
    color: var(--gold-shine) !important;
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    margin: 0;
}
/* Expander chevron arrow */
[data-testid="stExpander"] summary svg {
    fill: var(--gold-light) !important;
    color: var(--gold-light) !important;
    width: 20px !important;
    height: 20px !important;
    transition: transform 0.2s ease !important;
}
[data-testid="stExpander"][open] summary svg {
    transform: rotate(180deg) !important;
}
/* Expander body / content area */
[data-testid="stExpander"] > div:last-child {
    background: transparent !important;
    padding: 16px 20px !important;
}
/* Nested inner expanders (per-document) */
[data-testid="stExpander"] [data-testid="stExpander"] {
    background: rgba(155,123,46,0.07) !important;
    border: 1px solid rgba(155,123,46,0.35) !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    margin-bottom: 10px !important;
}
[data-testid="stExpander"] [data-testid="stExpander"] summary {
    background: linear-gradient(135deg, #3d2b1f 0%, #5c4a2a 100%) !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 10px 14px !important;
    border-bottom: 1px solid rgba(201,168,76,0.4) !important;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
[data-testid="stExpander"] [data-testid="stExpander"] summary p,
[data-testid="stExpander"] [data-testid="stExpander"] summary span,
[data-testid="stExpander"] [data-testid="stExpander"] summary div {
    color: var(--gold-light) !important;
    font-family: 'Crimson Text', Georgia, serif !important;
    font-size: 0.9rem !important;
    font-weight: 600 !important;
    margin: 0;
}
[data-testid="stExpander"] [data-testid="stExpander"] summary svg {
    width: 18px !important;
    height: 18px !important;
}
/* Subheadings inside expander body (Metadata / Retrieved Passage) */
[data-testid="stExpander"] h3 {
    color: var(--ink-dark) !important;
    font-family: 'Playfair Display', serif !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin: 12px 0 6px 0 !important;
    border-bottom: 1px solid rgba(155,123,46,0.3);
    padding-bottom: 4px;
}
/* st.info boxes inside expander (retrieved passage) */
[data-testid="stExpander"] [data-testid="stAlert"] {
    background: linear-gradient(135deg, rgba(155,123,46,0.1) 0%, rgba(155,123,46,0.05) 100%) !important;
    border: 1px solid rgba(155,123,46,0.4) !important;
    border-left: 4px solid var(--gold) !important;
    border-radius: 8px !important;
    padding: 8px;
}
[data-testid="stExpander"] [data-testid="stAlert"] p,
[data-testid="stExpander"] [data-testid="stAlert"] div {
    color: var(--ink-mid) !important;
    font-family: 'EB Garamond', 'Crimson Text', Georgia, serif !important;
    font-size: 1rem !important;
    font-style: italic !important;
    line-height: 1.7 !important;
    margin: 0;
}
/* st.json inside expander (metadata) */
[data-testid="stExpander"] [data-testid="stJson"] {
    background: rgba(26,15,0,0.05) !important;
    border: 1px solid rgba(155,123,46,0.25) !important;
    border-radius: 8px !important;
    font-family: 'Courier New', monospace !important;
    font-size: 0.82rem !important;
    color: var(--ink-mid) !important;
    padding: 8px;
    overflow-x: auto;
}
/* General text inside expander body */
[data-testid="stExpander"] p,
[data-testid="stExpander"] li,
[data-testid="stExpander"] span:not([data-testid]) {
    color: var(--ink-mid) !important;
    font-family: 'Crimson Text', Georgia, serif !important;
    font-size: 0.95rem !important;
    margin: 0 0 0.5rem 0;
}
/* End of refined styling */
            
            button[data-testid="stBaseButton-header"] {
    display: none !important;
}
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header {
    background: transparent !important;
}
            .darwin-header h1 {
    color: #F8E7A1 !important;
}

.darwin-header p {
    color: #F4D77A !important;
}

.darwin-header .badge {
    color: #F8E7A1 !important;
}
            
    section[data-testid="stSidebar"] {
    min-width: 300px !important;
    max-width: 300px !important;
}
            
            [data-testid="stChatInput"] {
    background: transparent !important;
}

[data-testid="stChatInput"] > div {
    background: transparent !important;
    border: none !important;
}

[data-testid="stChatInput"] textarea {
    background: #fffdf7 !important;
}
            
            .block-container {
    padding-top: 1rem !important;
}
            
/* Smooth sidebar animation */
section[data-testid="stSidebar"] {
    transition: all 0.3s ease-in-out !important;
}

.main .block-container {
    transition: all 0.3s ease-in-out !important;
    max-width: 100% !important;
}

/* When sidebar is collapsed */
[data-testid="stSidebar"][aria-expanded="false"] {
    margin-left: -300px !important;
}
            
.darwin-scene {
    max-width: 900px;
    margin: 10px auto 25px auto;

    text-align: center;

    font-family: 'EB Garamond', serif;
    font-style: italic;
    font-size: 1.2rem;

    color: #5c4a2a;

    padding: 12px 20px;

    border-left: 4px solid #9b7b2e;
    background: rgba(155,123,46,0.06);

    border-radius: 10px;
}
</style>
            
""", unsafe_allow_html=True)


# -----------------------------------
# CHAT FUNCTION — streams + timeline
# -----------------------------------

def ask_darwin(question, year):
    
    retrieved_docs = retrieve(question)
    

    st.session_state["last_retrieved_docs"] = retrieved_docs

    long_term_memory = load_long_term_memory()
    long_term_context = format_memory_for_prompt(long_term_memory)

    system_prompt = get_persona_prompt(
        long_term_context,
        retrieved_docs,
        year=year
    )

    prompt = f"{system_prompt}\n\nUser Question:\n{question}"
    
    response = model.generate_content(prompt, stream=True)
    
    for chunk in response:
        text = getattr(chunk, "text", None)

        if text:
            yield text

# -----------------------------------
# SIDEBAR
# -----------------------------------

with st.sidebar:

    # Darwin portrait
    try:
        st.image("assets/charlesdarwin.jpg", use_container_width=True)
    except Exception:
        st.markdown("<div style='text-align:center;font-size:4rem;'></div>", unsafe_allow_html=True)

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

    # ── TIMELINE SLIDER ──────────────────────────
    st.markdown('<p class="timeline-label">🕰️ Travel in Time</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-family:Crimson Text,serif;font-size:0.85rem;color:#5c4a2a;margin-top:-6px;">Speak to Darwin at any point in his life</p>', unsafe_allow_html=True)

    year = st.slider(
        label="Year:",
        min_value=1831,
        max_value=1882,
        value=1870,
        step=1,
        help="Move the slider to change what Darwin knows. "
             "In 1831 he's a young naturalist on the Beagle. "
             "In 1859 he's just published Origin of Species. "
             "In 1882 he's an elder statesman of science."
    )

    # Show a context label based on the year
    if year <= 1836:
        era_text = "🚢 Aboard HMS Beagle"
        era_note = "Darwin is a young naturalist on the voyage. *Origin of Species* is still decades away."
    elif year <= 1841:
        era_text = "🏙️ Gower Street, London"
        era_note = "Darwin is living at 'Macaw Cottage', quietly formulating his theory after reading Malthus."
    elif year <= 1858:
        era_text = "🏡 Down House, Kent"
        era_note = "Darwin is accumulating evidence in private. He has not yet published."
    elif year <= 1860:
        era_text = "📖 *Origin of Species* published"
        era_note = "The book came out in 1859. Darwin is bracing for the scientific storm."
    elif year <= 1871:
        era_text = "🌿 Defending evolution"
        era_note = "Huxley is fighting Darwin's battles publicly. *The Descent of Man* is coming."
    else:
        era_text = "🧓 Elder statesman of science"
        era_note = "Darwin is celebrated but still experimenting — earthworms, plants, orchids."

    st.markdown(f'<span class="era-badge">{era_text}</span>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-family:Crimson Text,serif;font-size:0.85rem;color:#5c4a2a;margin-top:8px;font-style:italic;">{era_note}</p>', unsafe_allow_html=True)

    # Store year in session state so it persists
    if "selected_year" not in st.session_state:
        st.session_state.selected_year = year
    st.session_state.selected_year = year

    st.markdown("---")

    # Famous quote
    st.info(
        "\"It is not the strongest of the species that survives, "
        "nor the most intelligent. It is the one most adaptable to change.\""
    )

    st.markdown("---")

    # Suggested questions based on era
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
        st.markdown(f'<span class="topic-pill">{s}</span>', unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col2:
        msg_count = len(st.session_state.get("messages", []))
        st.metric("Messages", msg_count)


# -----------------------------------
# MAIN PAGE — Premium Header
# -----------------------------------

current_year = st.session_state.get("selected_year", 1870)

# FIX: Use inline style on <h1> so Streamlit's own heading CSS cannot override it
st.markdown(f"""
<div class="darwin-header">

<h1 style="
color:#F8E7A1 !important;
font-size:3rem !important;
font-weight:800 !important;
font-family:'Playfair Display',serif !important;
margin-bottom:10px !important;
display:block !important;
">
Charles Darwin — Digital Twin
</h1>

<p style="
color:#F4D77A !important;
font-size:1.15rem !important;
margin-top:0 !important;
font-style:italic;
">
An AI persona grounded in Darwin's own writings · Speaking to you from the year {current_year}
</p>

<div class="badges">
    <span class="badge">📚 RAG-Powered</span>
    <span class="badge">🧠 Long-Term Memory</span>
    <span class="badge">🕰️ Timeline-Aware</span>
    <span class="badge">✍️ Historically Accurate</span>
</div>

</div>
""", unsafe_allow_html=True)
# -----------------------------------
# CHAT HISTORY
# -----------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

# Increment session count on first load
if "session_count_incremented" not in st.session_state:
    memory_data = load_long_term_memory()
    memory_data["session_count"] = memory_data.get("session_count", 0) + 1
    save_long_term_memory(memory_data)
    st.session_state.session_count_incremented = True

# Show a welcome message if chat is empty
scene_text = ""

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
st.markdown(
    f"""
    <div class="darwin-scene">
        {scene_text}
    </div>
    """,
    unsafe_allow_html=True
)
if len(st.session_state.messages) == 0:
    with st.chat_message(
    "assistant",
    avatar="🧑🏼‍🔬"
):
    
        if current_year <= 1836:
            welcome = (
               
               
                "Good day! I am Charles Darwin, naturalist on this extraordinary voyage. "
                "The variety of life I have observed — from the coral reefs to the "
                "tortoises of the Galápagos — fills me with endless wonder. "
                "What would you like to discuss?"
            )
        elif current_year <= 1841:
            welcome = (
                
                
                "Good day! Do forgive the noise of the city — it rather tries my nerves. "
                "I confess I am deep in thought on matters of great consequence, though not yet ready "
                "to speak of them openly. What brings you to see me?"
            )
        elif current_year <= 1858:
            welcome = (
                
                
                "Good day! I am deep in my investigations here at Down House. "
                "I have been quietly working on a rather large theory for some years now — "
                "though I am not yet ready to publish. What brings you to see me?"
            )
        elif current_year in (1859, 1860):
            welcome = (
                
                
                "Good day! You find me in a rather anxious state — my book has just "
                "been published and the reaction from the scientific and religious "
                "community is quite something. I welcome your questions."
            )
        else:
            welcome = (
                
                
                "Good day! Do sit down. I have been in correspondence with naturalists "
                "around the world and have much on my mind. "
                "What would you like to discuss?"
            )
        st.markdown(welcome)

# Display full chat history
for message in st.session_state.messages:

    if message["role"] == "assistant":
        with st.chat_message("assistant", avatar="🧑🏼‍🔬"):
            st.markdown(
    "<div style='font-size:1rem;font-weight:700;margin-bottom:0.3rem;'>🧑🏼‍🔬 Charles Darwin</div>",
    unsafe_allow_html=True
)
            st.markdown(message["content"])

    else:
        with st.chat_message("user", avatar="👤"):
            st.markdown(
    "<div style='font-size:1rem;font-weight:700;margin-bottom:0.3rem;'>👤 You</div>",
    unsafe_allow_html=True
)
            st.markdown(message["content"])

# -----------------------------------
# USER INPUT
# -----------------------------------

prompt = st.chat_input(
    f"Ask Darwin something (speaking to him in {st.session_state.get('selected_year', 1870)})..."
)


if prompt:

    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )


    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🧑🏼‍🔬"):

            try:

                answer = st.write_stream(
                ask_darwin(
                prompt,
                st.session_state.selected_year
            )
        )

                docs = st.session_state.get(
            "last_retrieved_docs",
            []
        )

                if docs:

                    with st.expander(
                f" Retrieved Documents ({len(docs)})",
                expanded=False
            ):

                        for i, doc in enumerate(docs, 1):

                            source = (
                        doc.get("metadata", {})
                        .get("source", f"Document {i}")
                        if isinstance(doc, dict)
                        else f"Document {i}"
                    )

                            with st.expander(
                        f"📄 {source}",
                        expanded=False
                    ):

                                doc.get(
                                    "text",
                                    str(doc)
                                )
                            

                        else:
                                st.subheader(
                                "Retrieved Passage"
                            )

                                st.info(str(doc))

                st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

            except Exception as e:
                st.error(str(e))
    
