"""
memory_dashboard.py  —  Sidebar memory dashboard for DigitalTwin Darwin
------------------------------------------------------------------------
Drop-in module. Call render_memory_dashboard(memory_data) inside
your `with st.sidebar:` block.

Usage in app.py:
    from memory_dashboard import render_memory_dashboard, DASHBOARD_CSS
    # Add DASHBOARD_CSS to your existing st.markdown(...) CSS block (once, at top of app.py)
    # Then inside `with st.sidebar:`, call:
    render_memory_dashboard(load_long_term_memory())
"""

import streamlit as st
from memory import get_facts_by_category

# ── Category metadata ─────────────────────────────────────────────────────────

CATEGORY_CONFIG = {
    "background":      {"label": "Background",          "icon": "🏛️", "color": "#6b8e6b"},
    "interests":       {"label": "Interests",            "icon": "🔬", "color": "#9b7b2e"},
    "beliefs":         {"label": "Beliefs & Views",      "icon": "💭", "color": "#7b5ea7"},
    "questions_asked": {"label": "Topics Explored",      "icon": "📜", "color": "#5a7fa8"},
    "personal":        {"label": "Personal Details",     "icon": "🪶", "color": "#a86b3a"},
}

# ── CSS (inject once via st.markdown in app.py) ───────────────────────────────

DASHBOARD_CSS = """
/* ── MEMORY DASHBOARD ───────────────────────────────────── */

.mem-header {
    font-family: 'Playfair Display', serif;
    font-size: 0.88rem;
    font-weight: 700;
    color: #1a0f00;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin: 0 0 10px 0;
    display: flex;
    align-items: center;
    gap: 7px;
}

.mem-stats-row {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
}

.mem-stat-box {
    flex: 1;
    background: linear-gradient(135deg, #1a0f00 0%, #3d2b1f 100%);
    border: 1px solid #9b7b2e;
    border-radius: 10px;
    padding: 8px 6px;
    text-align: center;
}

.mem-stat-value {
    font-family: 'Playfair Display', serif;
    font-size: 1.35rem;
    font-weight: 700;
    color: #e8c96b;
    line-height: 1;
    display: block;
}

.mem-stat-label {
    font-family: 'Crimson Text', serif;
    font-size: 0.7rem;
    color: rgba(232,201,107,0.65);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-top: 3px;
    display: block;
}

.mem-category-block {
    margin-bottom: 10px;
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(155,123,46,0.25);
}

.mem-cat-header {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 7px 11px;
    background: linear-gradient(135deg, #2d1f0a 0%, #3d2b1f 100%);
    cursor: pointer;
    user-select: none;
}

.mem-cat-icon {
    font-size: 0.9rem;
    line-height: 1;
}

.mem-cat-label {
    font-family: 'Playfair Display', serif;
    font-size: 0.78rem;
    font-weight: 600;
    color: #c9a84c;
    flex: 1;
    letter-spacing: 0.3px;
}

.mem-cat-count {
    background: rgba(155,123,46,0.3);
    color: #e8c96b;
    font-family: 'Crimson Text', serif;
    font-size: 0.72rem;
    padding: 1px 7px;
    border-radius: 10px;
    border: 1px solid rgba(155,123,46,0.4);
}

.mem-facts-body {
    background: rgba(253,248,238,0.55);
    padding: 8px 10px;
}

.mem-fact-item {
    display: flex;
    align-items: flex-start;
    gap: 7px;
    padding: 5px 0;
    border-bottom: 1px solid rgba(155,123,46,0.12);
}

.mem-fact-item:last-child {
    border-bottom: none;
}

.mem-fact-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    margin-top: 6px;
    flex-shrink: 0;
}

.mem-fact-text {
    font-family: 'Crimson Text', serif;
    font-size: 0.82rem;
    color: #3d2b1f;
    line-height: 1.45;
    flex: 1;
}

.mem-fact-meta {
    font-family: 'Crimson Text', serif;
    font-size: 0.68rem;
    color: rgba(92,74,42,0.55);
    white-space: nowrap;
    margin-top: 5px;
}

.mem-empty {
    font-family: 'Crimson Text', serif;
    font-size: 0.82rem;
    font-style: italic;
    color: rgba(92,74,42,0.55);
    text-align: center;
    padding: 10px 8px;
    background: rgba(253,248,238,0.3);
    border-radius: 8px;
    border: 1px dashed rgba(155,123,46,0.3);
}

.mem-progress-bar-wrap {
    background: rgba(155,123,46,0.12);
    border-radius: 20px;
    height: 5px;
    margin: 6px 0 10px 0;
    overflow: hidden;
}

.mem-progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #9b7b2e, #e8c96b);
    border-radius: 20px;
    transition: width 0.4s ease;
}

.mem-refresh-note {
    font-family: 'Crimson Text', serif;
    font-size: 0.72rem;
    font-style: italic;
    color: rgba(92,74,42,0.5);
    text-align: center;
    margin-top: 6px;
}
/* ── END MEMORY DASHBOARD ───────────────────────────────── */
"""


# ── Main render function ──────────────────────────────────────────────────────

def render_memory_dashboard(memory_data: dict) -> None:
    """
    Render the memory dashboard inside the Streamlit sidebar.
    Call this from within a `with st.sidebar:` block.

    Args:
        memory_data: dict from load_long_term_memory()
    """
    facts_by_cat = get_facts_by_category(memory_data)
    total_facts   = sum(len(v) for v in facts_by_cat.values())
    session_count = memory_data.get("session_count", 0)
    total_turns   = memory_data.get("total_turns", 0)

    # ── Section header ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="mem-header">
        🧠 Darwin Knows About You
    </div>
    """, unsafe_allow_html=True)

    # ── Stats row ─────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="mem-stats-row">
        <div class="mem-stat-box">
            <span class="mem-stat-value">{total_facts}</span>
            <span class="mem-stat-label">Facts Learnt</span>
        </div>
        <div class="mem-stat-box">
            <span class="mem-stat-value">{session_count}</span>
            <span class="mem-stat-label">Sessions</span>
        </div>
        <div class="mem-stat-box">
            <span class="mem-stat-value">{total_turns}</span>
            <span class="mem-stat-label">Exchanges</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Memory fill progress bar (max display = 20 facts) ────────────────────
    MAX_DISPLAY = 20
    pct = min(total_facts / MAX_DISPLAY * 100, 100)
    st.markdown(f"""
    <div class="mem-progress-bar-wrap">
        <div class="mem-progress-bar-fill" style="width:{pct:.0f}%"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Empty state ───────────────────────────────────────────────────────────
    if total_facts == 0:
        st.markdown("""
        <div class="mem-empty">
            No memories yet. Darwin will learn about<br>you as you converse with him.
        </div>
        """, unsafe_allow_html=True)
        st.markdown(
            '<p class="mem-refresh-note">Memory updates after each exchange.</p>',
            unsafe_allow_html=True
        )
        return

    # ── Fact cards per category ───────────────────────────────────────────────
    for cat_key, cfg in CATEGORY_CONFIG.items():
        facts = facts_by_cat.get(cat_key, [])
        if not facts:
            continue

        color  = cfg["color"]
        icon   = cfg["icon"]
        label  = cfg["label"]
        count  = len(facts)

        # Build fact items HTML
        items_html = ""
        for fact in facts:
            session_tag = fact.get("added_session", 0)
            meta = f"Session {session_tag}" if session_tag else "This session"
            items_html += f"""
            <div class="mem-fact-item">
                <div class="mem-fact-dot" style="background:{color};"></div>
                <div style="flex:1;">
                    <div class="mem-fact-text">{fact['text']}</div>
                    <div class="mem-fact-meta">{meta}</div>
                </div>
            </div>"""

        st.markdown(f"""
        <div class="mem-category-block">
            <div class="mem-cat-header">
                <span class="mem-cat-icon">{icon}</span>
                <span class="mem-cat-label">{label}</span>
                <span class="mem-cat-count">{count}</span>
            </div>
            <div class="mem-facts-body">
                {items_html}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        '<p class="mem-refresh-note">Memory refreshes after each reply.</p>',
        unsafe_allow_html=True
    )


# ── Clear memory helper (wired to the "Clear Chat" button flow) ───────────────

def clear_memory(filename: str = "long_term_memory.json") -> None:
    """Wipe facts but preserve session_count and total_turns."""
    from memory import load_long_term_memory, save_long_term_memory
    data = load_long_term_memory(filename)
    data["facts"] = []
    save_long_term_memory(data, filename)