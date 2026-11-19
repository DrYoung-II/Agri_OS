"""
theme.py
Dark-green 'Agri_OS Africa' visual theme for the Streamlit app.
Pure CSS injection - no external assets required (works fully offline).
"""

import streamlit as st

PRIMARY_BG = "#07160f"          # near-black green background
SURFACE = "#0f2a1c"             # card surface
SURFACE_ALT = "#123424"         # alternate surface (hover/inputs)
BORDER = "#1f4d34"
PRIMARY = "#1b4332"             # deep forest green
PRIMARY_LIGHT = "#2d6a4f"
ACCENT = "#52b788"              # leaf green accent
ACCENT_LIGHT = "#95d5b2"
GOLD = "#e9c46a"                # harvest gold for money/highlights
TEXT = "#eafaf1"
TEXT_MUTED = "#9fc9b3"
DANGER = "#e07a5f"
INFO = "#4895ef"


def apply_theme():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Inter:wght@400;500;600&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        .stApp {{
            background: radial-gradient(1200px 600px at 10% -10%, #123424 0%, {PRIMARY_BG} 45%),
                        linear-gradient(180deg, {PRIMARY_BG} 0%, #050d09 100%);
            color: {TEXT};
        }}

        h1, h2, h3, h4, h5 {{
            font-family: 'Poppins', sans-serif !important;
            color: {TEXT} !important;
            font-weight: 700 !important;
        }}

        /* Sidebar */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0a1e13 0%, #08160e 100%);
            border-right: 1px solid {BORDER};
        }}
        section[data-testid="stSidebar"] * {{ color: {TEXT} !important; }}

        /* Radio nav styled as pill buttons */
        section[data-testid="stSidebar"] div[role="radiogroup"] label {{
            background: transparent;
            border-radius: 10px;
            padding: 8px 12px;
            margin-bottom: 4px;
            transition: all 0.15s ease-in-out;
            border: 1px solid transparent;
        }}
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
            background: {SURFACE_ALT};
            border: 1px solid {BORDER};
        }}

        /* Metric cards */
        div[data-testid="stMetric"] {{
            background: linear-gradient(160deg, {SURFACE} 0%, {SURFACE_ALT} 100%);
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.35);
        }}
        div[data-testid="stMetric"] label {{ color: {TEXT_MUTED} !important; }}
        div[data-testid="stMetricValue"] {{ color: {ACCENT_LIGHT} !important; font-size: 1.6rem !important; word-wrap: break-word !important; }}
        .stButton>button, .stDownloadButton>button {{
            background: linear-gradient(135deg, {ACCENT} 0%, {PRIMARY_LIGHT} 100%);
            color: #06170f;
            font-weight: 700;
            border: none;
            border-radius: 10px;
            padding: 0.55em 1.2em;
            box-shadow: 0 3px 10px rgba(82,183,136,0.25);
            transition: transform 0.1s ease-in-out;
        }}
        .stButton>button:hover, .stDownloadButton>button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(82,183,136,0.4);
            color: #06170f;
        }}

        /* Inputs */
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div,
        .stTextArea textarea, .stDateInput input {{
            background-color: {SURFACE_ALT} !important;
            color: {TEXT} !important;
            border: 1px solid {BORDER} !important;
            border-radius: 8px !important;
        }}

        /* Tabs */
        button[data-baseweb="tab"] {{
            color: {TEXT_MUTED} !important;
            font-weight: 600;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {ACCENT_LIGHT} !important;
            border-bottom: 3px solid {ACCENT} !important;
        }}

        /* Custom card class for use inside st.markdown */
        .agri-card {{
            background: linear-gradient(160deg, {SURFACE} 0%, {SURFACE_ALT} 100%);
            border: 1px solid {BORDER};
            border-radius: 16px;
            padding: 20px 22px;
            margin-bottom: 14px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.35);
        }}
        .agri-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}
        .badge-good {{ background: rgba(82,183,136,0.18); color: {ACCENT_LIGHT}; border: 1px solid {ACCENT}; }}
        .badge-warn {{ background: rgba(233,196,106,0.18); color: {GOLD}; border: 1px solid {GOLD}; }}
        .badge-bad  {{ background: rgba(224,122,95,0.18); color: {DANGER}; border: 1px solid {DANGER}; }}

        .agri-hero {{
            background: linear-gradient(120deg, #0e2a1b 0%, #123c26 60%, #0a2016 100%);
            border: 1px solid {BORDER};
            border-radius: 20px;
            padding: 28px 30px;
            margin-bottom: 18px;
        }}

        /* Chat bubbles */
        div[data-testid="stChatMessage"] {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 14px;
        }}

        hr {{ border-color: {BORDER} !important; }}

        ::-webkit-scrollbar {{ width: 10px; }}
        ::-webkit-scrollbar-track {{ background: {PRIMARY_BG}; }}
        ::-webkit-scrollbar-thumb {{ background: {PRIMARY_LIGHT}; border-radius: 10px; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, emoji: str = "🌾"):
    st.markdown(
        f"""
        <div class="agri-hero">
            <div style="font-size:2rem;">{emoji}</div>
            <div style="font-size:1.6rem; font-weight:800; margin-top:6px;">{title}</div>
            <div style="color:{TEXT_MUTED}; margin-top:4px;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str = "good"):
    cls = {"good": "badge-good", "warn": "badge-warn", "bad": "badge-bad"}.get(kind, "badge-good")
    return f'<span class="agri-badge {cls}">{text}</span>'


def card_open():
    st.markdown('<div class="agri-card">', unsafe_allow_html=True)


def card_close():
    st.markdown("</div>", unsafe_allow_html=True)
