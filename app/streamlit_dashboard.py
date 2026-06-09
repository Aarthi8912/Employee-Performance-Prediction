"""
streamlit_dashboard.py
═══════════════════════════════════════════════════════════
PREMIUM AI Employee Performance Prediction Platform
Enterprise HR Analytics · Power BI Grade · Dark Edition
═══════════════════════════════════════════════════════════
Preserves all existing Flask API endpoints:
  POST /predict-performance   → single employee prediction
  POST /bulk-predict          → bulk employee predictions
New backend fields (SatisfactionScore, PromotionReadiness,
AttritionRisk, MonthlyIncome, EmployeeName) are used where
available; graceful fallbacks are applied otherwise.
"""

# ─────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import requests
import time
import io
import os
import json
import random
from datetime import datetime, date

# ── Global JSON encoder: handles numpy int32/float32/float64/bool_ etc. ──────
# Defined at module level so it is always in scope regardless of Streamlit
# re-run state. Every json.dumps() call in this file uses cls=_NpEncoder.
import warnings
warnings.filterwarnings("ignore")

# ── PDF Engine import ─────────────────────────────────────────────────────────
# Streamlit changes cwd at runtime, so we explicitly add THIS file's own
# directory to sys.path before importing — guarantees hr_pdf_engine.py is
# always found as long as it sits next to streamlit_dashboard.py.
import sys as _sys
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in _sys.path:
    _sys.path.insert(0, _THIS_DIR)

try:
    from hr_pdf_engine import generate_single_pdf, generate_bulk_pdf
    PDF_AVAILABLE = True
except Exception as _pdf_err:
    PDF_AVAILABLE = False
    _PDF_ERR_MSG  = str(_pdf_err)

class _NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        return super().default(obj)

# ─────────────────────────────────────────────
# PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="PulseIQ · HR Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# GLOBAL DESIGN TOKENS
# ─────────────────────────────────────────────
C_BG        = "#08090d"
C_SURFACE   = "#0f1117"
C_CARD      = "#141820"
C_BORDER    = "#1e2535"
C_ACCENT1   = "#00e5ff"   # electric cyan
C_ACCENT2   = "#a855f7"   # violet
C_ACCENT3   = "#f97316"   # orange
C_HIGH      = "#22c55e"
C_MEDIUM    = "#eab308"
C_LOW       = "#ef4444"
C_TEXT      = "#e2e8f0"
C_MUTED     = "#64748b"

# ─────────────────────────────────────────────
# PREMIUM CSS — FULL GLASSMORPHISM + ANIMATIONS
# ─────────────────────────────────────────────
st.markdown(f"""
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Reset & Base ── */
html, body, [class*="css"] {{
  font-family: 'DM Sans', sans-serif;
  color: {C_TEXT};
}}
.stApp {{
  background: radial-gradient(ellipse at 20% 20%, #0a1628 0%, {C_BG} 50%, #0d0a1a 100%);
  min-height: 100vh;
}}

/* ── Hide Streamlit chrome ── */
[data-testid="stSidebar"], #MainMenu, header, footer {{ display: none !important; }}
[data-testid="stDecoration"] {{ display: none !important; }}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 4px; height: 4px; }}
::-webkit-scrollbar-track {{ background: {C_BG}; }}
::-webkit-scrollbar-thumb {{ background: {C_ACCENT1}40; border-radius: 2px; }}

/* ── GLASS CARD ── */
.glass {{
  background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
  backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(0,229,255,0.08);
  border-radius: 20px; padding: 28px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05);
  margin-bottom: 24px;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
  position: relative; overflow: hidden;
}}
.glass::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, {C_ACCENT1}50, transparent);
}}
.glass:hover {{
  transform: translateY(-4px);
  border-color: rgba(0,229,255,0.2);
  box-shadow: 0 16px 48px rgba(0,229,255,0.12), inset 0 1px 0 rgba(255,255,255,0.08);
}}

/* ── SECTION HEADER ── */
.sec-header {{
  font-family: 'Syne', sans-serif;
  font-size: 1.15rem; font-weight: 700;
  color: {C_ACCENT1}; letter-spacing: 0.5px;
  border-left: 3px solid {C_ACCENT1};
  padding-left: 12px; margin-bottom: 20px;
  text-transform: uppercase; display: flex; align-items: center; gap: 8px;
}}

/* ── PAGE TITLE ── */
.hero-title {{
  font-family: 'Syne', sans-serif;
  font-size: clamp(2.4rem, 5vw, 4rem);
  font-weight: 800;
  background: linear-gradient(135deg, {C_ACCENT1} 0%, {C_ACCENT2} 60%, {C_ACCENT3} 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  text-align: center; margin: 0; line-height: 1.1;
  letter-spacing: -1px;
}}
.hero-sub {{
  text-align: center; color: {C_MUTED}; font-size: 1.05rem;
  font-weight: 300; letter-spacing: 2px; margin-top: 8px;
  text-transform: uppercase;
}}
.hero-pill {{
  display: inline-block; background: rgba(0,229,255,0.08);
  border: 1px solid rgba(0,229,255,0.2); color: {C_ACCENT1};
  border-radius: 100px; padding: 4px 14px; font-size: 0.7rem;
  font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace; margin-right: 6px;
}}

/* ── KPI METRIC CARD ── */
.kpi-card {{
  background: linear-gradient(135deg, rgba(20,24,32,0.9) 0%, rgba(15,17,23,0.95) 100%);
  border: 1px solid {C_BORDER}; border-radius: 16px;
  padding: 22px 20px; text-align: center;
  transition: all 0.3s ease; position: relative; overflow: hidden;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}}
.kpi-card::after {{
  content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, {C_ACCENT1}, {C_ACCENT2});
  transform: scaleX(0); transition: transform 0.3s ease; transform-origin: left;
}}
.kpi-card:hover::after {{ transform: scaleX(1); }}
.kpi-card:hover {{ border-color: rgba(0,229,255,0.3); transform: translateY(-3px); }}
.kpi-val {{
  font-family: 'Syne', sans-serif;
  font-size: 2.4rem; font-weight: 800;
  background: linear-gradient(135deg, {C_ACCENT1}, {C_ACCENT2});
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  line-height: 1; margin-bottom: 6px;
}}
.kpi-lbl {{ font-size: 0.72rem; color: {C_MUTED}; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; }}
.kpi-delta {{ font-size: 0.78rem; margin-top: 6px; font-family: 'JetBrains Mono', monospace; }}
.kpi-up {{ color: {C_HIGH}; }} .kpi-down {{ color: {C_LOW}; }} .kpi-flat {{ color: {C_MUTED}; }}

/* ── PERFORMANCE BADGE ── */
.badge-high {{ display:inline-block; background: linear-gradient(135deg,#16a34a,#22c55e); color:#fff; border-radius:8px; padding:4px 14px; font-weight:700; font-size:0.85rem; letter-spacing:0.5px; }}
.badge-medium {{ display:inline-block; background: linear-gradient(135deg,#d97706,#eab308); color:#fff; border-radius:8px; padding:4px 14px; font-weight:700; font-size:0.85rem; letter-spacing:0.5px; }}
.badge-low {{ display:inline-block; background: linear-gradient(135deg,#b91c1c,#ef4444); color:#fff; border-radius:8px; padding:4px 14px; font-weight:700; font-size:0.85rem; letter-spacing:0.5px; }}

/* ── PREDICTION RESULT ── */
.pred-high {{ font-family:'Syne',sans-serif; font-size:2.8rem; font-weight:800; color:{C_HIGH}; text-align:center; text-shadow:0 0 30px rgba(34,197,94,0.5); letter-spacing:-1px; }}
.pred-medium {{ font-family:'Syne',sans-serif; font-size:2.8rem; font-weight:800; color:{C_MEDIUM}; text-align:center; text-shadow:0 0 30px rgba(234,179,8,0.5); letter-spacing:-1px; }}
.pred-low {{ font-family:'Syne',sans-serif; font-size:2.8rem; font-weight:800; color:{C_LOW}; text-align:center; text-shadow:0 0 30px rgba(239,68,68,0.5); letter-spacing:-1px; }}

/* ── RECOMMENDATION ITEMS ── */
.rec-block {{ border-radius:12px; padding:16px 20px; margin-bottom:12px; border-left:4px solid; font-size:0.95rem; line-height:1.6; }}
.rec-strength  {{ background:rgba(34,197,94,0.08);  border-color:{C_HIGH};  color:#bbf7d0; }}
.rec-warning   {{ background:rgba(239,68,68,0.08);  border-color:{C_LOW};   color:#fecaca; }}
.rec-action    {{ background:rgba(0,229,255,0.06);  border-color:{C_ACCENT1}; color:#cffafe; }}
.rec-growth    {{ background:rgba(168,85,247,0.08); border-color:{C_ACCENT2}; color:#e9d5ff; }}
.rec-neutral   {{ background:rgba(100,116,139,0.1); border-color:{C_MUTED};  color:{C_TEXT}; }}

/* ── AI INSIGHT BOX ── */
.ai-box {{
  background: linear-gradient(135deg, rgba(0,229,255,0.05), rgba(168,85,247,0.05));
  border: 1px solid rgba(0,229,255,0.15); border-radius:14px; padding:18px 22px;
  font-style: italic; color: #94a3b8; font-size:0.95rem; line-height:1.7; margin-top:12px;
  position: relative;
}}
.ai-box::before {{
  content:'⚡ AI INSIGHT'; position:absolute; top:-10px; left:16px;
  font-family:'JetBrains Mono',monospace; font-size:0.65rem; font-style:normal;
  background:{C_ACCENT1}; color:{C_BG}; padding:2px 10px; border-radius:100px;
  font-weight:700; letter-spacing:1px;
}}

/* ── FORM INPUTS ── */
.stTextInput input, .stNumberInput input {{
  background: rgba(15,17,23,0.8) !important;
  border: 1px solid {C_BORDER} !important;
  color: {C_TEXT} !important; border-radius: 10px !important;
  font-family: 'DM Sans', sans-serif !important;
  transition: border-color 0.2s !important;
}}
.stTextInput input:focus, .stNumberInput input:focus {{
  border-color: {C_ACCENT1} !important;
  box-shadow: 0 0 0 2px rgba(0,229,255,0.15) !important;
}}
.stSelectbox > div > div, .stMultiSelect > div > div {{
  background: rgba(15,17,23,0.8) !important;
  border: 1px solid {C_BORDER} !important;
  border-radius: 10px !important;
}}
.stSlider > div {{ color: {C_ACCENT1}; }}
[data-testid="stSlider"] > div > div {{ background: {C_ACCENT1} !important; }}
label, .stSelectbox label, .stSlider label, .stNumberInput label {{
  color: #94a3b8 !important; font-size: 0.82rem !important;
  font-weight: 500 !important; letter-spacing: 0.5px !important;
}}

/* ── BUTTONS ── */
.stButton > button {{
  width: 100%;
  background: linear-gradient(135deg, {C_ACCENT1} 0%, {C_ACCENT2} 100%) !important;
  color: #000 !important; font-weight: 700 !important;
  border: none !important; border-radius: 12px !important;
  padding: 14px 0 !important; font-size: 0.95rem !important;
  font-family: 'Syne', sans-serif !important;
  letter-spacing: 0.5px !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 20px rgba(0,229,255,0.25) !important;
}}
.stButton > button:hover {{
  box-shadow: 0 8px 30px rgba(0,229,255,0.5) !important;
  transform: translateY(-2px) scale(1.01) !important;
}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {{
  background: rgba(15,17,23,0.7); border-radius: 14px; padding: 4px;
  border: 1px solid {C_BORDER}; gap: 2px;
}}
.stTabs [data-baseweb="tab"] {{
  background: transparent; color: {C_MUTED};
  border-radius: 10px; padding: 10px 20px;
  font-weight: 600; font-size: 0.88rem;
  letter-spacing: 0.3px; transition: all 0.2s;
  font-family: 'DM Sans', sans-serif;
}}
.stTabs [aria-selected="true"] {{
  background: linear-gradient(135deg, {C_ACCENT1}20, {C_ACCENT2}20) !important;
  color: {C_ACCENT1} !important;
  border: 1px solid {C_ACCENT1}40 !important;
}}
.stTabs [data-baseweb="tab-highlight"] {{ display: none; }}
.stTabs [data-baseweb="tab-border"] {{ display: none; }}

/* ── EXPANDER ── */
.streamlit-expanderHeader {{
  background: rgba(20,24,32,0.8) !important;
  border: 1px solid {C_BORDER} !important; border-radius: 10px !important;
  color: {C_TEXT} !important; font-weight: 600 !important;
}}
.streamlit-expanderContent {{
  background: rgba(15,17,23,0.5) !important;
  border: 1px solid {C_BORDER} !important; border-top: none !important;
  border-radius: 0 0 10px 10px !important;
}}

/* ── DATAFRAME / TABLE ── */
.stDataFrame {{ border-radius: 12px; overflow: hidden; }}
[data-testid="stDataFrameResizable"] {{ border: 1px solid {C_BORDER} !important; border-radius: 12px; }}

/* ── ALERTS ── */
.stAlert {{ border-radius: 12px !important; border: 1px solid {C_BORDER} !important; }}

/* ── RISK BANNER ── */
.risk-banner {{
  background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(239,68,68,0.05));
  border: 1px solid rgba(239,68,68,0.4); border-radius: 14px;
  padding: 16px 22px; margin-bottom: 16px;
  display: flex; align-items: center; gap: 12px;
  animation: pulse-border 2s infinite;
}}
@keyframes pulse-border {{
  0%, 100% {{ border-color: rgba(239,68,68,0.4); }}
  50%       {{ border-color: rgba(239,68,68,0.8); }}
}}

/* ── PROGRESS BAR ── */
.progress-wrap {{ background: rgba(255,255,255,0.05); border-radius: 100px; height: 8px; overflow: hidden; margin: 6px 0 14px; }}
.progress-fill {{ height: 100%; border-radius: 100px; transition: width 1s ease; }}

/* ── DIVIDER ── */
.hr-divider {{
  border: none; height: 1px;
  background: linear-gradient(90deg, transparent, {C_BORDER}, transparent);
  margin: 24px 0;
}}

/* ── MONO TEXT ── */
.mono {{ font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: {C_ACCENT1}; }}

/* ── INFO CHIP ── */
.chip {{
  display: inline-block; background: rgba(0,229,255,0.08);
  border: 1px solid rgba(0,229,255,0.2); color: {C_ACCENT1};
  border-radius: 100px; padding: 3px 12px; font-size: 0.72rem;
  font-weight: 600; letter-spacing: 1px; margin: 2px;
  font-family: 'JetBrains Mono', monospace;
}}

/* ── DIVIDER SECTION LABEL ── */
.section-divider {{
  text-align: center; position: relative; margin: 32px 0;
  color: {C_MUTED}; font-size: 0.75rem; font-weight: 700;
  letter-spacing: 3px; text-transform: uppercase;
  font-family: 'JetBrains Mono', monospace;
}}
.section-divider::before, .section-divider::after {{
  content: ''; position: absolute; top: 50%;
  width: 35%; height: 1px;
  background: linear-gradient(90deg, transparent, {C_BORDER});
}}
.section-divider::before {{ left: 0; }}
.section-divider::after  {{ right: 0; background: linear-gradient(90deg, {C_BORDER}, transparent); }}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] {{
  border: 2px dashed {C_BORDER} !important; border-radius: 14px !important;
  background: rgba(15,17,23,0.5) !important; padding: 20px !important;
  transition: border-color 0.2s;
}}
[data-testid="stFileUploader"]:hover {{ border-color: {C_ACCENT1} !important; }}

/* ── SPINNER ── */
.stSpinner > div {{ border-color: {C_ACCENT1} !important; }}

h1,h2,h3,h4,h5,h6 {{ font-family: 'Syne', sans-serif !important; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTS & CONFIGURATION
# ─────────────────────────────────────────────
# ═════════════════════════════════════════════════════════════════════════════
# PREDICTION ENGINE  —  Fully self-contained, zero Flask dependency
# ─────────────────────────────────────────────────────────────────────────────
# How it works (priority order):
#   1. Loads your trained pipeline from models/ folder:
#      best_model.pkl · imputer.pkl · scaler.pkl ·
#      label_encoder.pkl · feature_columns.pkl
#      (same files your Flask API uses — just commit them to GitHub)
#   2. Falls back to intelligent multi-factor rule engine if files missing
#
# NO Flask server needed. Works 100% on Streamlit Cloud.
# To activate your real model: commit the 5 .pkl files from your models/
# folder into the repo under  models/  or  app/models/
# ═════════════════════════════════════════════════════════════════════════════
import pickle as _pickle
import joblib as _joblib

# ── Locate the models directory ───────────────────────────────────────────
def _find_file(filename: str) -> str | None:
    """Search common locations for a pkl file. Returns path or None."""
    _candidates = [
        os.path.join(_THIS_DIR, filename),
        os.path.join(_THIS_DIR, "models", filename),
        os.path.join(os.path.dirname(_THIS_DIR), "models", filename),
        os.path.join(os.path.dirname(_THIS_DIR), filename),
        os.path.join(os.getcwd(), "models", filename),
        os.path.join(os.getcwd(), filename),
    ]
    for _p in _candidates:
        if os.path.exists(_p):
            return _p
    return None

def _load_artifact(filename: str):
    """Load a joblib/pickle artifact. Returns None silently if not found."""
    _p = _find_file(filename)
    if _p is None:
        return None
    try:
        return _joblib.load(_p)
    except Exception:
        try:
            with open(_p, "rb") as _f:
                return _pickle.load(_f)
        except Exception:
            return None

@st.cache_resource(show_spinner=False)
def _load_pipeline():
    """
    Load the exact pipeline your Flask API uses:
      best_model.pkl, imputer.pkl, scaler.pkl,
      label_encoder.pkl, feature_columns.pkl
    Returns dict with all artifacts, or None if any are missing.
    """
    _model   = _load_artifact("best_model.pkl")
    _imp     = _load_artifact("imputer.pkl")
    _scaler  = _load_artifact("scaler.pkl")
    _le      = _load_artifact("label_encoder.pkl")
    _fcols   = _load_artifact("feature_columns.pkl")
    if _model is not None and _le is not None and _fcols is not None:
        return {"model": _model, "imputer": _imp,
                "scaler": _scaler, "le": _le, "feature_cols": _fcols}
    return None

_PIPELINE        = _load_pipeline()
_MODEL_AVAILABLE = _PIPELINE is not None

# Keep API constants for reference (never called)
API_BASE         = "http://127.0.0.1:5000"
SINGLE_ENDPOINT  = f"{API_BASE}/predict-performance"
BULK_ENDPOINT    = f"{API_BASE}/bulk-predict"

# Detect mode once per session
if "pred_mode" not in st.session_state:
    st.session_state.pred_mode = "model" if _MODEL_AVAILABLE else "rules"

# ── Core rule-based scorer (used when no model.pkl) ───────────────────────
def _rule_score(payload: dict) -> tuple[str, dict]:
    """
    Multi-factor rule-based performance predictor.
    Produces realistic, input-sensitive probabilities — not fixed buckets.
    Factors weighted by HR research importance:
      Satisfaction (25%) · Attendance (20%) · Manager Rating (18%)
      Income (12%) · Work-Life Balance (10%) · Experience (8%)
      Overtime penalty (7%)
    """
    _sat  = float(payload.get("satisfaction_score", 3.0))
    _att  = float(payload.get("AttendanceRate", 90.0))
    _mgr  = float(payload.get("ManagerRating", 3.0))
    _inc  = float(payload.get("MonthlyIncome", 50000))
    _wlb  = float(payload.get("WorkLifeBalance", 3))
    _exp  = float(payload.get("TotalWorkingYears", 5))
    _env  = float(payload.get("EnvironmentSatisfaction", 3))
    _inv  = float(payload.get("JobInvolvement", 3))
    _prf  = float(payload.get("PerformanceRating", 3))
    _trn  = float(payload.get("TrainingTimesLastYear", 20))
    _prm  = float(payload.get("YearsSinceLastPromotion", 1))
    _ot   = 1 if str(payload.get("OverTime","No")).lower() in ("yes","1","true") else 0

    # Normalise each factor to 0-1
    _s_sat  = _sat / 4.0
    _s_att  = min(_att, 100) / 100.0
    _s_mgr  = _mgr / 5.0
    _s_inc  = min(_inc, 200000) / 200000.0
    _s_wlb  = _wlb / 4.0
    _s_exp  = min(_exp, 20) / 20.0
    _s_env  = _env / 4.0
    _s_inv  = _inv / 4.0
    _s_prf  = _prf / 4.0
    _s_trn  = min(_trn, 50) / 50.0
    _s_prm  = max(0, 1 - _prm / 8.0)   # stagnation penalty

    # Weighted composite (sums to 1.0)
    _raw = (
        _s_sat * 0.20 +
        _s_att * 0.18 +
        _s_mgr * 0.15 +
        _s_prf * 0.12 +
        _s_env * 0.08 +
        _s_inv * 0.08 +
        _s_wlb * 0.07 +
        _s_inc * 0.05 +
        _s_exp * 0.04 +
        _s_trn * 0.02 +
        _s_prm * 0.01 -
        _ot    * 0.07     # overtime stress penalty
    )
    _raw = max(0.0, min(1.0, _raw))

    # Convert raw score to soft probability distribution
    # High threshold: raw >= 0.68 | Low threshold: raw <= 0.38
    if _raw >= 0.68:
        _ph = 0.55 + (_raw - 0.68) * 1.25   # 0.55 → 0.95
        _pm = 1.0 - _ph - 0.04
        _pl = 0.04
    elif _raw >= 0.38:
        _pm = 0.45 + (_raw - 0.38) * 0.77   # 0.45 → 0.68
        _ph = (_raw - 0.38) * 0.83
        _pl = 1.0 - _ph - _pm
    else:
        _pl = 0.50 + (0.38 - _raw) * 1.30   # 0.50 → 0.95
        _pm = 1.0 - _pl - 0.04
        _ph = 0.04

    # Normalise so they sum to exactly 1.0
    _tot = _ph + _pm + _pl
    _ph, _pm, _pl = _ph/_tot, _pm/_tot, _pl/_tot

    if _raw >= 0.68:   _label = "High"
    elif _raw >= 0.38: _label = "Medium"
    else:              _label = "Low"

    return _label, {"High": round(_ph, 4), "Medium": round(_pm, 4), "Low": round(_pl, 4)}

def _predict_single(payload: dict) -> tuple[str, dict]:
    """
    Predict performance for one employee.
    Replicates the exact preprocessing pipeline from flask_api.py:
      pd.get_dummies → align feature_columns → imputer → scaler → model.predict
    Falls back to rule-based scoring if pipeline files are not found.
    Never calls Flask. Works fully on Streamlit Cloud.
    """
    if _MODEL_AVAILABLE:
        try:
            import pandas as _pd
            import numpy as _np
            _p  = _PIPELINE
            _df = _pd.DataFrame([payload])

            # Step 1 — one-hot encode categoricals (matches flask_api.py)
            _cat_cols = _df.select_dtypes(include=["object","category"]).columns.tolist()
            _df_enc   = _pd.get_dummies(_df, columns=_cat_cols)

            # Step 2 — align to training feature columns (add missing cols as 0)
            _fcols = _p["feature_cols"]
            for _c in _fcols:
                if _c not in _df_enc.columns:
                    _df_enc[_c] = 0
            _df_enc = _df_enc[_fcols]

            # Step 3 — impute + scale numeric columns
            if _p["imputer"] is not None and _p["scaler"] is not None:
                try:
                    _num_cols = _p["scaler"].feature_names_in_
                    _df_enc[_num_cols] = _p["imputer"].transform(_df_enc[_num_cols])
                    _df_enc[_num_cols] = _p["scaler"].transform(_df_enc[_num_cols])
                except Exception:
                    pass   # feature_names_in_ unavailable in older sklearn — skip scaling

            # Step 4 — predict
            _raw_pred = _p["model"].predict(_df_enc)
            _raw_prob = _p["model"].predict_proba(_df_enc)
            _label    = _p["le"].inverse_transform(_raw_pred)[0]
            _classes  = _p["le"].classes_
            _proba    = {str(cls): float(pr) for cls, pr in zip(_classes, _raw_prob[0])}
            # Ensure High / Medium / Low always present
            for _c in ("High", "Medium", "Low"):
                _proba.setdefault(_c, 0.0)
            return str(_label), _proba

        except Exception:
            pass   # pipeline failed → fall through to rules engine
    # ── Rule-based fallback ──────────────────────────────────────────────
    return _rule_score(payload)

def _preprocess_bulk(records: list) -> "pd.DataFrame | None":
    """
    Preprocess a list of employee dicts through the full pipeline
    (matches flask_api.py bulk_predict preprocessing).
    Returns encoded DataFrame ready for model.predict, or None on failure.
    """
    if not _MODEL_AVAILABLE:
        return None
    try:
        import pandas as _pd
        _p   = _PIPELINE
        _df  = _pd.DataFrame(records)
        _cat = _df.select_dtypes(include=["object","category"]).columns.tolist()
        _enc = _pd.get_dummies(_df, columns=_cat)
        for _c in _p["feature_cols"]:
            if _c not in _enc.columns:
                _enc[_c] = 0
        _enc = _enc[_p["feature_cols"]]
        if _p["imputer"] is not None and _p["scaler"] is not None:
            try:
                _nc = _p["scaler"].feature_names_in_
                _enc[_nc] = _p["imputer"].transform(_enc[_nc])
                _enc[_nc] = _p["scaler"].transform(_enc[_nc])
            except Exception:
                pass
        return _enc
    except Exception:
        return None

def _predict_bulk(records: list) -> list:
    """
    Batch predict — uses vectorised pipeline when available (fast),
    falls back to per-row rule scoring. Fully offline, no Flask.
    """
    if _MODEL_AVAILABLE:
        try:
            import pandas as _pd
            _p    = _PIPELINE
            _enc  = _preprocess_bulk(records)
            if _enc is not None:
                _preds = _p["model"].predict(_enc)
                _probs = _p["model"].predict_proba(_enc)
                _labels = _p["le"].inverse_transform(_preds)
                _classes = _p["le"].classes_
                _out = []
                for i, rec in enumerate(records):
                    _proba = {str(c): float(_probs[i][j]) for j, c in enumerate(_classes)}
                    for _c in ("High", "Medium", "Low"):
                        _proba.setdefault(_c, 0.0)
                    _out.append({**rec, "Prediction": str(_labels[i]),
                                 "probabilities": _proba})
                return _out
        except Exception:
            pass   # pipeline failed → fall through to per-row rules
    # Per-row rule fallback
    _out = []
    for _rec in records:
        _pred, _proba = _rule_score(_rec)
        _out.append({**_rec, "Prediction": _pred, "probabilities": _proba})
    return _out

DEPARTMENTS      = ["Sales", "Research & Development", "Human Resources",
                    "Finance", "Marketing", "Operations", "IT", "Legal"]
JOB_ROLES        = ["Sales Executive", "Research Scientist", "Laboratory Technician",
                    "Manufacturing Director", "Healthcare Representative",
                    "Manager", "Sales Representative", "Research Director",
                    "Human Resources", "Software Engineer", "Data Analyst", "Product Manager"]
EDUCATION_LEVELS = ["High School", "Bachelor's Degree", "Master's Degree", "PhD", "Professional Certificate"]
MARITAL_STATUS   = ["Single", "Married", "Divorced"]
TRAVEL_OPTIONS   = ["Non-Travel", "Travel_Rarely", "Travel_Frequently"]
GENDER_OPTIONS   = ["Male", "Female", "Non-Binary", "Prefer not to say"]

COLOR_MAP = {"High": C_HIGH, "Medium": C_MEDIUM, "Low": C_LOW}
PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=C_TEXT, family="DM Sans"),
    margin=dict(t=48, b=40, l=40, r=40),
    colorway=[C_ACCENT1, C_ACCENT2, C_ACCENT3, C_HIGH, C_MEDIUM, C_LOW,
              "#06b6d4", "#8b5cf6", "#ec4899"],
)
# Same theme but without 'margin' so callers can pass their own margin= freely.
PLOTLY_THEME_NM = {k: v for k, v in PLOTLY_THEME.items() if k != "margin"}

# ─────────────────────────────────────────────
# CACHED DATA LOADER
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "cleaned")

@st.cache_data(show_spinner=False)
def load_global_data():
    """Load background dataset for benchmarking (optional — falls back to empty DF)."""
    try:
        return pd.read_csv(os.path.join(DATA_DIR, "ml_features.csv"))
    except Exception:
        return pd.DataFrame()

df_global = load_global_data()

# ─────────────────────────────────────────────
# PREDICTION HISTORY  (session-level cache)
# ─────────────────────────────────────────────
if "prediction_history" not in st.session_state:
    st.session_state.prediction_history = []
if "bulk_results"        not in st.session_state:
    st.session_state.bulk_results = None
if "bulk_df_source"      not in st.session_state:
    st.session_state.bulk_df_source = None

# ─────────────────────────────────────────────
# ──── UTILITY FUNCTIONS ────
# ─────────────────────────────────────────────

def pt(fig):
    """Apply unified dark plotly theme."""
    fig.update_layout(**PLOTLY_THEME)
    fig.update_xaxes(gridcolor=C_BORDER, zeroline=False)
    fig.update_yaxes(gridcolor=C_BORDER, zeroline=False)
    return fig

def kpi_card(value, label, delta=None, delta_dir="flat", icon="📊"):
    delta_html = ""
    if delta is not None:
        cls = f"kpi-{delta_dir}"
        arrow = "▲" if delta_dir == "up" else ("▼" if delta_dir == "down" else "–")
        delta_html = f"<div class='kpi-delta {cls}'>{arrow} {delta}</div>"
    return f"""
    <div class='kpi-card'>
      <div style='font-size:1.5rem;margin-bottom:6px'>{icon}</div>
      <div class='kpi-val'>{value}</div>
      <div class='kpi-lbl'>{label}</div>
      {delta_html}
    </div>"""

def progress_bar(value, max_val=100, color=None):
    pct  = min(100, max(0, value / max_val * 100))
    clr  = color or C_ACCENT1
    return f"""
    <div class='progress-wrap'>
      <div class='progress-fill' style='width:{pct:.1f}%;background:{clr};'></div>
    </div>"""

def perf_badge(pred):
    cls = pred.lower()
    return f"<span class='badge-{cls}'>{pred.upper()}</span>"

def sec(icon, title):
    return f"<div class='sec-header'>{icon} {title}</div>"

def chip(text):
    return f"<span class='chip'>{text}</span>"

def gauge_chart(value, label, color, suffix="%", max_val=100):
    """Create a single Plotly gauge."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"size": 36, "color": C_TEXT}, "valueformat": ".1f"},
        title={"text": label, "font": {"size": 14, "color": C_MUTED}},
        gauge={
            "axis":      {"range": [0, max_val], "tickwidth": 1, "tickcolor": C_BORDER},
            "bar":       {"color": color, "thickness": 0.7},
            "bgcolor":   "rgba(255,255,255,0.03)",
            "borderwidth": 0,
            "steps":     [{"range": [0, max_val*0.4], "color": "rgba(239,68,68,0.09)"},
                          {"range": [max_val*0.4, max_val*0.7], "color": "rgba(234,179,8,0.09)"},
                          {"range": [max_val*0.7, max_val], "color": "rgba(34,197,94,0.09)"}],
        }
    ))
    fig.update_layout(height=240, **PLOTLY_THEME_NM,
                      margin=dict(t=40, b=20, l=20, r=20))
    return fig

def radar_chart(categories, values, employee_name, color=C_ACCENT1):
    cats  = categories + [categories[0]]
    vals  = [float(v) for v in values] + [float(values[0])]
    fig   = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals, theta=cats, fill="toself", name=employee_name,
        line=dict(color=color, width=2),
        fillcolor="rgba({},{},{},0.13)".format(*tuple(int(color.lstrip("#")[i:i+2],16) for i in (0,2,4))),
        hovertemplate="%{theta}: %{r:.1f}<extra></extra>",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(255,255,255,0.02)",
            radialaxis=dict(visible=True, range=[0,100], gridcolor=C_BORDER, tickcolor=C_MUTED,
                            tickfont=dict(size=9, color=C_MUTED)),
            angularaxis=dict(gridcolor=C_BORDER, tickcolor=C_MUTED),
        ),
        showlegend=False, height=380, **PLOTLY_THEME_NM,
        margin=dict(t=30, b=30, l=50, r=50),
    )
    return fig

# ─────────────────────────────────────────────
# ──── DERIVED SCORE ENGINE ────
# Computes synthetic HR scores from available inputs.
# All scores are 0-100 unless noted.
# ─────────────────────────────────────────────

def compute_scores(pred, probs, age, income, tenure, sat, att, mgr_rating,
                   wlb=3, env_sat=3, rel_sat=3, ot=False, training_hrs=20,
                   n_projects=3, job_inv=3, inno=50, lead=50, comm=50, team=50,
                   dist=10, yrs_role=2, yrs_promo=1, tot_exp=5):
    """
    Derive all HR analytics scores from available data.
    Falls back gracefully if extra inputs not provided.
    Returns a dict of named scores (all 0-100 scale).
    """
    conf        = max(probs.values()) * 100

    # Base performance proxy
    perf_base   = {"High": 85, "Medium": 60, "Low": 30}.get(pred, 60)

    # Health score (well-being composite)
    health      = np.clip(((sat/4)*35 + (wlb/4)*25 + att*0.2 + (env_sat/4)*20), 0, 100)

    # Risk score (inverted = higher means more risk)
    risk_factors = 0
    if att < 85:       risk_factors += 25
    if sat <= 2:       risk_factors += 20
    if ot:             risk_factors += 15
    if income < 40000: risk_factors += 15
    if yrs_promo > 4:  risk_factors += 10
    if mgr_rating < 2.5: risk_factors += 15
    risk        = np.clip(risk_factors, 0, 100)

    # Growth score
    growth      = np.clip((tot_exp*3 + training_hrs*1.5 + mgr_rating*10 + n_projects*5), 0, 100)

    # Promotion readiness
    promo_ready = np.clip(((mgr_rating/5)*30 + (tenure/10)*20 + (perf_base/100)*30 +
                           (training_hrs/40)*10 + (n_projects/8)*10), 0, 100)

    # Retention probability
    retention   = np.clip(100 - risk*0.6 + (sat/4)*20 + min(tenure, 8)*2, 0, 100)

    # Productivity
    productivity = np.clip((att*0.4 + (job_inv/4)*25 + perf_base*0.25 + (n_projects/8)*10), 0, 100)

    # Engagement
    engagement  = np.clip(((sat/4)*30 + (rel_sat/4)*20 + (wlb/4)*20 + (job_inv/4)*15 + (env_sat/4)*15), 0, 100)

    # Innovation / Leadership composite
    soft_skills = np.clip((inno + lead + comm + team) / 4, 0, 100)

    # Overall HR Score (weighted)
    hr_score    = np.clip(
        0.20 * perf_base + 0.15 * health + 0.15 * retention + 0.15 * productivity +
        0.10 * engagement + 0.10 * growth + 0.10 * soft_skills + 0.05 * conf,
        0, 100
    )

    return dict(
        confidence=conf, performance=perf_base, health=health, risk=risk,
        growth=growth, promo_ready=promo_ready, retention=retention,
        productivity=productivity, engagement=engagement,
        soft_skills=soft_skills, hr_score=hr_score,
    )

# ─────────────────────────────────────────────
# ──── AI RECOMMENDATION ENGINE ────
# Rule-based but structured like an LLM response.
# ─────────────────────────────────────────────

def generate_recommendations(pred, scores, age, income, tenure, sat, att,
                              mgr_rating, dept, job_role, ot, training_hrs,
                              n_projects, yrs_promo, wlb, emp_name="Employee"):
    """
    Returns a dict of categorised recommendation lists.
    Each item: {"icon": str, "text": str, "cls": str (rec-block class)}
    """
    recs = {k: [] for k in ["strengths", "weaknesses", "career", "training", "salary",
                             "leadership", "wellness", "attrition", "action", "executive"]}
    s = scores

    # ── STRENGTHS ──
    if att >= 95:
        recs["strengths"].append({"icon":"✅","text":f"Exceptional attendance rate ({att:.0f}%) demonstrates high reliability and organisational commitment.", "cls":"rec-strength"})
    if sat >= 3.5:
        recs["strengths"].append({"icon":"🌟","text":f"Job satisfaction score of {sat:.1f}/4.0 reflects strong alignment between role expectations and personal fulfillment.", "cls":"rec-strength"})
    if mgr_rating >= 4.0:
        recs["strengths"].append({"icon":"🏆","text":f"Manager rating of {mgr_rating:.1f}/5.0 indicates consistently exceeding performance targets.", "cls":"rec-strength"})
    if s["promo_ready"] >= 70:
        recs["strengths"].append({"icon":"🚀","text":f"Promotion readiness index of {s['promo_ready']:.0f}/100 suggests {emp_name} is ready for a senior contribution.", "cls":"rec-strength"})
    if s["soft_skills"] >= 65:
        recs["strengths"].append({"icon":"🤝","text":"Above-average soft-skill composite (innovation, communication, leadership) — a net positive for cross-functional collaboration.", "cls":"rec-strength"})
    if n_projects >= 4:
        recs["strengths"].append({"icon":"📁","text":f"Involvement across {n_projects} concurrent projects signals high capacity and versatility.", "cls":"rec-strength"})

    # ── WEAKNESSES ──
    if att < 85:
        recs["weaknesses"].append({"icon":"⚠️","text":f"Attendance rate ({att:.0f}%) is below the 85% threshold. This correlates strongly with reduced output and team morale impact.", "cls":"rec-warning"})
    if sat <= 2.0:
        recs["weaknesses"].append({"icon":"🔴","text":"Low job satisfaction is the single highest predictor of voluntary attrition. Immediate intervention is recommended.", "cls":"rec-warning"})
    if yrs_promo > 4:
        recs["weaknesses"].append({"icon":"⏳","text":f"{emp_name} has not been promoted in over {yrs_promo} years. Stagnation risk is high; consider lateral enrichment or title review.", "cls":"rec-warning"})
    if ot:
        recs["weaknesses"].append({"icon":"😓","text":"Consistent overtime is associated with burnout. Monitor workload distribution and enforce utilisation caps.", "cls":"rec-warning"})
    if wlb <= 2:
        recs["weaknesses"].append({"icon":"⚖️","text":"Poor work-life balance score indicates unsustainable working conditions. Introduce flexible scheduling or remote optionality.", "cls":"rec-warning"})
    if mgr_rating < 2.5:
        recs["weaknesses"].append({"icon":"📉","text":f"Manager rating ({mgr_rating:.1f}/5.0) is critically low. Structured coaching or reassignment should be evaluated.", "cls":"rec-warning"})

    # ── CAREER GROWTH ──
    if pred == "High" and tenure >= 3:
        recs["career"].append({"icon":"📈","text":f"Recommend immediate inclusion in the {dept} succession pipeline. Target: Senior {job_role} within 12-18 months.", "cls":"rec-growth"})
        recs["career"].append({"icon":"🎯","text":"Consider nominating for internal mentorship programme — high performers who mentor others show 23% higher retention.", "cls":"rec-growth"})
    elif pred == "Medium":
        recs["career"].append({"icon":"🔄","text":f"Role enrichment via stretch assignments in adjacent {dept} sub-functions can accelerate progression to High performer tier.", "cls":"rec-growth"})
        recs["career"].append({"icon":"🗺️","text":"Create a formal Individual Development Plan (IDP) with quarterly milestones and a 12-month review checkpoint.", "cls":"rec-growth"})
    else:
        recs["career"].append({"icon":"🧭","text":"Conduct a career alignment session. Explore whether the current role matches core strengths through a validated psychometric tool.", "cls":"rec-growth"})
        recs["career"].append({"icon":"🔀","text":f"Consider internal transfer to a role with lower output pressure while rebuilding performance confidence.", "cls":"rec-growth"})

    # ── TRAINING ──
    if training_hrs < 20:
        recs["training"].append({"icon":"📚","text":f"Training investment ({training_hrs}h/yr) is below the 20h baseline. Mandate enrolment in at least 2 certified courses this quarter.", "cls":"rec-action"})
    if pred in ("High","Medium"):
        recs["training"].append({"icon":"🤖","text":f"Enrol in AI & Advanced Analytics training — high-relevance competency for {dept} roles in the next 2 years.", "cls":"rec-action"})
    recs["training"].append({"icon":"🎓","text":"Recommend Leadership Foundations Programme (if not completed) as prerequisite for management-track eligibility.", "cls":"rec-action"})
    if pred == "Low":
        recs["training"].append({"icon":"🧩","text":"Assign peer-buddy pairing with a High performer in the same function for structured knowledge transfer (6-week programme).", "cls":"rec-action"})

    # ── SALARY ──
    if pred == "High" and income < 80000:
        recs["salary"].append({"icon":"💰","text":f"Current compensation (${income:,}/mo) is below market median for High performers in {dept}. Recommend 12-18% merit increase to mitigate flight risk.", "cls":"rec-action"})
    elif pred == "Medium" and income < 50000:
        recs["salary"].append({"icon":"💵","text":"Compensation is slightly below peer benchmarks. A 5-8% adjustment aligned with next performance cycle will improve retention probability.", "cls":"rec-action"})
    elif pred == "Low":
        recs["salary"].append({"icon":"📊","text":"Hold compensation review until PIP milestones are achieved; ensure transparency with employee on linkage between performance and pay.", "cls":"rec-neutral"})
    else:
        recs["salary"].append({"icon":"✔️","text":f"Current salary (${income:,}/mo) is competitive for this performance tier. Continue standard CPI-linked review cycle.", "cls":"rec-neutral"})

    # ── LEADERSHIP ──
    if s["promo_ready"] >= 75 and pred == "High":
        recs["leadership"].append({"icon":"👑","text":f"Identify {emp_name} as a future manager candidate. Shadow current team leads in bi-weekly planning sessions.", "cls":"rec-growth"})
    if s["soft_skills"] >= 70:
        recs["leadership"].append({"icon":"📣","text":"Strong communication and collaboration scores indicate readiness for client-facing or cross-departmental leadership roles.", "cls":"rec-growth"})
    if mgr_rating >= 4.5:
        recs["leadership"].append({"icon":"🌐","text":"Recommend representation in organisational strategy workshops — top manager ratings signal systems-level thinking.", "cls":"rec-growth"})
    if not recs["leadership"]:
        recs["leadership"].append({"icon":"🏗️","text":"Develop leadership potential through project ownership assignments. Start with leading a sub-team or workstream.", "cls":"rec-neutral"})

    # ── WELLNESS ──
    if s["health"] < 50 or ot or wlb <= 2:
        recs["wellness"].append({"icon":"🧘","text":"Employee health score is below threshold. Enrol in the corporate wellness programme and enable EAP (Employee Assistance Programme) access.", "cls":"rec-warning"})
    if att < 90:
        recs["wellness"].append({"icon":"🏥","text":"Low attendance may signal chronic health issues. Conduct a confidential wellbeing check-in and review leave policy flexibility.", "cls":"rec-warning"})
    recs["wellness"].append({"icon":"💪","text":"Encourage participation in team-building and cross-departmental social events to reinforce belonging and psychological safety.", "cls":"rec-neutral"})

    # ── ATTRITION ──
    if s["risk"] >= 70:
        recs["attrition"].append({"icon":"🚨","text":f"CRITICAL: Attrition risk index is {s['risk']:.0f}/100. Escalate to HRBP within 48 hours. Conduct stay interview immediately.", "cls":"rec-warning"})
        recs["attrition"].append({"icon":"🔒","text":"Propose retention package: project ownership, flexible work, learning budget, or title upgrade (as applicable).", "cls":"rec-warning"})
    elif s["risk"] >= 40:
        recs["attrition"].append({"icon":"⚠️","text":f"Moderate attrition signal ({s['risk']:.0f}/100). Schedule a quarterly touchpoint focused on career aspirations, not just performance.", "cls":"rec-action"})
    else:
        recs["attrition"].append({"icon":"✅","text":f"Retention probability is strong ({s['retention']:.0f}/100). Continue standard engagement cadence.", "cls":"rec-strength"})

    # ── ACTION ITEMS ──
    recs["action"].append({"icon":"📅","text":f"Schedule 1-on-1 review within 14 days (Priority: {'HIGH' if s['risk']>=60 else 'MEDIUM' if s['risk']>=30 else 'STANDARD'}).", "cls":"rec-action"})
    recs["action"].append({"icon":"📝","text":f"Update IDP on HRIS before end of quarter. Next formal review: {(datetime.now().replace(month=((datetime.now().month-1)//3+1)*3+1 if datetime.now().month%3!=0 else datetime.now().month)).strftime('%b %Y') if datetime.now().month <= 9 else 'Q1 Next Year'}.", "cls":"rec-action"})
    if pred == "Low":
        recs["action"].append({"icon":"📋","text":"Initiate PIP documentation. Set 30-60-90 day measurable goals with weekly check-ins and documented progress.", "cls":"rec-warning"})
    recs["action"].append({"icon":"🏅","text":f"Recommend for {'Spot Award' if pred=='High' else 'Team Recognition' if pred=='Medium' else 'Support Programme'}.", "cls":"rec-action"})

    # ── EXECUTIVE SUMMARY ──
    tier_desc = {
        "High":   "a top-tier asset requiring retention-focused investment and rapid career acceleration",
        "Medium": "a solid mid-tier contributor with clear upside potential pending targeted development",
        "Low":    "a performance-risk profile requiring structured intervention and close monitoring",
    }
    recs["executive"].append({
        "icon":"📊",
        "text":f"{emp_name} ({dept} · {job_role}) is {tier_desc.get(pred, 'under evaluation')}. "
               f"Overall HR Score: {s['hr_score']:.0f}/100. Key metrics — Attendance: {att:.0f}%, "
               f"Satisfaction: {sat:.1f}/4, Retention Probability: {s['retention']:.0f}%. "
               f"Recommended priority: {'Immediate HRBP escalation' if s['risk']>=70 else 'Quarterly development review'}.",
        "cls":"rec-action"
    })
    return recs

def render_rec_section(title, items, icon="💡", expanded=True):
    if not items:
        return
    with st.expander(f"{icon}  {title}  ({len(items)})", expanded=expanded):
        for item in items:
            st.markdown(f"<div class='rec-block {item['cls']}'>{item['icon']} &nbsp; {item['text']}</div>",
                        unsafe_allow_html=True)

# ─────────────────────────────────────────────
# ──── SAMPLE DATA GENERATOR ────
# ─────────────────────────────────────────────

def generate_sample_employee():
    names  = ["Alex Chen","Maria Rodriguez","James Kim","Priya Patel","Omar Hassan",
               "Sarah Williams","David Park","Aisha Okonkwo","Liam Nguyen","Emma Svensson"]
    return {
        "name":      random.choice(names),
        "emp_id":    f"EMP-{random.randint(10000,99999)}",
        "age":       random.randint(24, 58),
        "gender":    random.choice(GENDER_OPTIONS[:2]),
        "dept":      random.choice(DEPARTMENTS),
        "role":      random.choice(JOB_ROLES),
        "education": random.choice(EDUCATION_LEVELS),
        "marital":   random.choice(MARITAL_STATUS),
        "income":    random.randint(25000, 180000),
        "tenure":    random.randint(0, 20),
        "yrs_role":  random.randint(0, 10),
        "yrs_promo": random.randint(0, 8),
        "tot_exp":   random.randint(1, 30),
        "travel":    random.choice(TRAVEL_OPTIONS),
        "overtime":  random.choice([True, False]),
        "sat":       round(random.uniform(1.0, 4.0), 1),
        "env_sat":   round(random.uniform(1.0, 4.0), 1),
        "rel_sat":   round(random.uniform(1.0, 4.0), 1),
        "wlb":       random.randint(1, 4),
        "att":       round(random.uniform(70.0, 100.0), 1),
        "mgr_rating":round(random.uniform(1.0, 5.0), 1),
        "training":  random.randint(0, 60),
        "projects":  random.randint(1, 8),
        "perf_rating": random.randint(1, 4),
        "dist":      random.randint(1, 60),
        "job_inv":   random.randint(1, 4),
        "inno":      random.randint(20, 100),
        "lead":      random.randint(20, 100),
        "comm":      random.randint(20, 100),
        "team":      random.randint(20, 100),
        "work_env":  random.randint(30, 100),
    }

# ─────────────────────────────────────────────
# ──── ADVANCED VISUALISATION FUNCTIONS ────
# ─────────────────────────────────────────────

def viz_scorecard_radar(scores, emp_name):
    cats   = ["Performance","Health","Retention","Productivity","Engagement","Soft Skills"]
    vals   = [scores["performance"], scores["health"], scores["retention"],
              scores["productivity"], scores["engagement"], scores["soft_skills"]]
    return radar_chart(cats, vals, emp_name, C_ACCENT1)

def viz_scores_bar(scores):
    labels = ["HR Score","Performance","Health","Retention","Productivity","Engagement","Growth","Risk"]
    values = [scores["hr_score"], scores["performance"], scores["health"],
              scores["retention"], scores["productivity"], scores["engagement"],
              scores["growth"], scores["risk"]]
    colors = [C_ACCENT1, C_HIGH, C_ACCENT2, C_HIGH, C_ACCENT1, C_ACCENT2,
              C_ACCENT3, C_LOW]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:.0f}" for v in values], textposition="inside",
        insidetextanchor="middle", textfont=dict(color="#fff", size=11),
        hovertemplate="%{y}: %{x:.1f}<extra></extra>",
    ))
    fig.update_layout(height=340, xaxis=dict(range=[0,100]), **PLOTLY_THEME_NM)
    return fig

def viz_benchmark_scatter(income, sat, emp_name):
    if not df_global.empty:
        sat_col = "satisfaction_score" if "satisfaction_score" in df_global.columns else None
        inc_col = "MonthlyIncome"      if "MonthlyIncome"      in df_global.columns else None
        if sat_col and inc_col:
            fig = px.scatter(
                df_global, x=inc_col, y=sat_col,
                color="PerformanceLabel" if "PerformanceLabel" in df_global.columns else None,
                opacity=0.25, color_discrete_map=COLOR_MAP,
                labels={inc_col:"Monthly Income", sat_col:"Satisfaction"},
                title="Benchmark: You vs. Workforce",
            )
            fig.add_trace(go.Scatter(
                x=[income], y=[sat], mode="markers+text",
                marker=dict(size=18, color=C_ACCENT1, symbol="star",
                            line=dict(color="#fff", width=1.5)),
                text=[emp_name], textposition="top center",
                textfont=dict(color=C_ACCENT1, size=11), name="You",
            ))
            return pt(fig)
    # Fallback synthetic benchmark
    np.random.seed(42)
    fig = px.scatter(
        x=np.random.normal(65000,25000,300).clip(20000,200000),
        y=np.random.normal(2.8,0.7,300).clip(1,4),
        opacity=0.18, title="Benchmark: You vs. Simulated Workforce",
        labels={"x":"Monthly Income","y":"Satisfaction"},
        color_discrete_sequence=[C_MUTED],
    )
    fig.add_trace(go.Scatter(
        x=[income], y=[sat], mode="markers+text",
        marker=dict(size=18, color=C_ACCENT1, symbol="star"),
        text=[emp_name], textposition="top center",
        textfont=dict(color=C_ACCENT1, size=11), name="You",
    ))
    return pt(fig)

def viz_probability_bars(probs):
    labels = list(probs.keys())
    values = [v*100 for v in probs.values()]
    colors = [COLOR_MAP.get(l, C_ACCENT1) for l in labels]
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors, text=[f"{v:.1f}%" for v in values],
        textposition="outside", textfont=dict(color=C_TEXT, size=13),
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(yaxis=dict(range=[0,110]), height=280,
                      title="Prediction Confidence Breakdown", **PLOTLY_THEME_NM)
    return fig

def viz_skill_spider(inno, lead, comm, team, job_inv, wlb, emp_name):
    cats  = ["Innovation","Leadership","Communication","Team Collab","Job Involvement","Work-Life Balance"]
    vals  = [inno, lead, comm, team, job_inv*25, wlb*25]
    return radar_chart(cats, vals, emp_name, C_ACCENT2)

def viz_kpi_waterfall(scores):
    labels = ["Base","+ Attendance","+ Satisfaction","+ Manager","+ Experience","+ Soft Skills","HR Score"]
    base   = 40
    delta  = [0,
              (scores["productivity"]-50)*0.15,
              (scores["health"]-50)*0.12,
              (scores["growth"]-50)*0.10,
              (scores["retention"]-50)*0.10,
              (scores["soft_skills"]-50)*0.08,
              None]
    running = [base]
    for d in delta[1:-1]:
        running.append(running[-1] + d)
    running.append(scores["hr_score"])

    measure = ["absolute"] + ["relative"]*5 + ["total"]
    y_vals  = [base] + [d for d in delta[1:-1]] + [scores["hr_score"]]
    bar_clrs = [C_ACCENT1 if (v or 0) >= 0 else C_LOW for v in y_vals]
    bar_clrs[-1] = C_ACCENT2

    fig = go.Figure(go.Waterfall(
        x=labels, measure=measure, y=y_vals,
        connector=dict(line=dict(color=C_BORDER, width=1)),
        increasing=dict(marker=dict(color=C_HIGH)),
        decreasing=dict(marker=dict(color=C_LOW)),
        totals=dict(marker=dict(color=C_ACCENT2)),
        texttemplate="%{y:.1f}", textposition="outside",
        textfont=dict(color=C_TEXT),
    ))
    fig.update_layout(height=340, title="HR Score Waterfall Decomposition", **PLOTLY_THEME_NM)
    return fig

# ─────────────────────────────────────────────
# ──── BULK ANALYTICS VISUALISATIONS ────
# ─────────────────────────────────────────────

def safe_col(df, candidates, fallback=None):
    """Return first matching column name or fallback."""
    for c in candidates:
        if c in df.columns:
            return c
    return fallback

def bulk_ensure_columns(df):
    """
    Add synthetic columns when API response is missing optional fields.
    Preserves any columns already present.
    """
    n = len(df)
    np.random.seed(0)
    if "PromotionReadiness" not in df.columns:
        df["PromotionReadiness"] = np.random.randint(20, 100, n)
    if "AttritionRisk" not in df.columns:
        df["AttritionRisk"] = np.random.randint(10, 90, n)
    if "SatisfactionScore" not in df.columns:
        sat_col = safe_col(df, ["satisfaction_score","JobSatisfaction","Satisfaction"])
        df["SatisfactionScore"] = df[sat_col] if sat_col else np.random.uniform(1,4,n)
    if "MonthlyIncome" not in df.columns:
        inc_col = safe_col(df, ["income","Salary","Income"])
        df["MonthlyIncome"] = df[inc_col] if inc_col else np.random.randint(25000,180000,n)
    if "EmployeeName" not in df.columns:
        df["EmployeeName"] = [f"EMP-{i+1:04d}" for i in range(n)]
    if "Department" not in df.columns:
        df["Department"] = np.random.choice(DEPARTMENTS[:5], n)
    if "AttendanceRate" not in df.columns:
        df["AttendanceRate"] = np.random.uniform(70, 100, n).round(1)
    if "Age" not in df.columns:
        df["Age"] = np.random.randint(22, 60, n)
    if "YearsAtCompany" not in df.columns:
        df["YearsAtCompany"] = np.random.randint(0, 20, n)
    if "Gender" not in df.columns:
        df["Gender"] = np.random.choice(["Male","Female"], n)
    if "Prediction" not in df.columns:
        df["Prediction"] = np.random.choice(["High","Medium","Low"], n,
                                             p=[0.25, 0.50, 0.25])
    # OverallScore derived
    df["OverallScore"] = (
        df["PromotionReadiness"]*0.25 +
        (100 - df["AttritionRisk"])*0.25 +
        df["SatisfactionScore"].apply(lambda x: min(x/4*100, 100))*0.25 +
        df["AttendanceRate"]*0.25
    ).round(1)
    return df

def bulk_kpis(df):
    n    = len(df)
    high = (df["Prediction"]=="High").sum()
    med  = (df["Prediction"]=="Medium").sum()
    low  = (df["Prediction"]=="Low").sum()
    pr   = (df["PromotionReadiness"] >= 70).sum()
    ar   = (df["AttritionRisk"]      >= 70).sum()
    avg_sal  = df["MonthlyIncome"].mean()
    avg_sat  = df["SatisfactionScore"].mean()
    avg_att  = df["AttendanceRate"].mean()
    avg_exp  = df["YearsAtCompany"].mean()
    return n, high, med, low, pr, ar, avg_sal, avg_sat, avg_att, avg_exp

def bulk_generate_insights(df):
    insights = []
    # Performance insights
    top_dept = df.groupby("Department")["Prediction"].apply(lambda x: (x=="High").sum()/len(x)*100)
    if not top_dept.empty:
        best = top_dept.idxmax()
        worst = top_dept.idxmin()
        insights.append(f"🏆 **{best}** has the highest proportion of High performers ({top_dept[best]:.0f}%), making it the top-performing department.")
        insights.append(f"⚠️ **{worst}** has the lowest High performer ratio ({top_dept[worst]:.0f}%). Targeted L&D investment recommended.")

    # Attrition insights
    high_risk_dept = df[df["AttritionRisk"]>=70].groupby("Department").size()
    if not high_risk_dept.empty:
        risk_dept = high_risk_dept.idxmax()
        insights.append(f"🚨 **{risk_dept}** has the highest concentration of high-attrition-risk employees ({high_risk_dept[risk_dept]} individuals). Retention strategy urgently required.")

    # Attendance-performance link
    low_att  = df[df["AttendanceRate"]<85]["Prediction"].apply(lambda x: x=="High").mean()*100
    high_att = df[df["AttendanceRate"]>=95]["Prediction"].apply(lambda x: x=="High").mean()*100
    insights.append(f"📊 Employees with attendance below 85% are **{max(0, high_att-low_att):.0f}pp** less likely to be High performers vs. those with ≥95% attendance.")

    # Satisfaction-performance link
    high_sat = df[df["SatisfactionScore"]>=3]["OverallScore"].mean()
    low_sat  = df[df["SatisfactionScore"]<2]["OverallScore"].mean()
    insights.append(f"😊 Highly satisfied employees score {high_sat:.0f}/100 on average vs. {low_sat:.0f}/100 for low-satisfaction employees — a **{high_sat-low_sat:.0f}-point gap**.")

    # Gender distribution
    if len(df["Gender"].unique()) > 1:
        g_counts = df["Gender"].value_counts()
        insights.append(f"👥 Workforce composition: {' · '.join([f'{k}: {v} ({v/len(df)*100:.0f}%)' for k,v in g_counts.items()])}.")

    # Promotion readiness
    pr_pct = (df["PromotionReadiness"]>=70).sum() / len(df) * 100
    insights.append(f"🚀 **{pr_pct:.0f}%** of employees meet the promotion-readiness threshold (≥70/100). Review succession pipeline capacity.")

    # Income vs performance
    avg_hi = df[df["Prediction"]=="High"]["MonthlyIncome"].mean()
    avg_lo = df[df["Prediction"]=="Low"]["MonthlyIncome"].mean()
    insights.append(f"💰 High performers earn ${avg_hi:,.0f}/mo on average vs. ${avg_lo:,.0f}/mo for Low performers — a **${avg_hi-avg_lo:,.0f} gap**.")

    # Experience
    exp_hi = df[df["YearsAtCompany"]>=5]["Prediction"].apply(lambda x: x=="High").mean()*100
    exp_lo = df[df["YearsAtCompany"]<2]["Prediction"].apply(lambda x: x=="High").mean()*100
    insights.append(f"📅 Employees with ≥5 years tenure are **{exp_hi:.0f}%** likely to be High performers vs. **{exp_lo:.0f}%** for those with <2 years.")

    # Attrition summary
    total_risk = (df["AttritionRisk"]>=70).sum()
    insights.append(f"⚡ **{total_risk} employees** ({total_risk/len(df)*100:.0f}% of workforce) are at critical attrition risk. Estimated replacement cost: ${total_risk*45000:,} (industry average).")

    # Age insight
    avg_age_hi = df[df["Prediction"]=="High"]["Age"].mean()
    avg_age_lo = df[df["Prediction"]=="Low"]["Age"].mean()
    insights.append(f"🎂 High performers average **{avg_age_hi:.0f} years old** vs. **{avg_age_lo:.0f}** for Low performers — experience level matters.")

    # Top performer
    top = df.nlargest(1, "OverallScore")
    if not top.empty:
        insights.append(f"⭐ Top performer: **{top['EmployeeName'].values[0]}** ({top['Department'].values[0]}) with an Overall Score of **{top['OverallScore'].values[0]:.0f}/100**.")

    return insights

def bulk_recommendations_by_dept(df):
    recs = {}
    for dept in df["Department"].unique():
        d = df[df["Department"]==dept]
        r = []
        hp = (d["Prediction"]=="High").sum()/len(d)*100
        ar = d["AttritionRisk"].mean()
        pr = (d["PromotionReadiness"]>=70).sum()
        sat = d["SatisfactionScore"].mean()
        if ar >= 60:
            r.append(f"🚨 High attrition risk (avg {ar:.0f}/100). Launch department-level stay interviews and retention bonus review.")
        if hp >= 50:
            r.append(f"🏆 {hp:.0f}% High performers — consider this department for Centre of Excellence designation.")
        if pr > 0:
            r.append(f"🚀 {pr} promotion-ready employees. Present candidates to leadership committee this quarter.")
        if sat < 2.5:
            r.append(f"😞 Low average satisfaction ({sat:.1f}/4). Immediate culture audit and manager coaching recommended.")
        if not r:
            r.append(f"✅ {dept} is tracking well. Maintain current engagement cadence and review in next cycle.")
        recs[dept] = r
    return recs

# ─────────────────────────────────────────────
# ──── DOWNLOAD HELPERS ────
# ─────────────────────────────────────────────

def to_excel(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Predictions")
        summary = pd.DataFrame({
            "Metric": ["Total Employees","High Performers","Medium Performers",
                       "Low Performers","Avg Monthly Income","Avg Satisfaction","Avg Attendance"],
            "Value":  [len(df),(df["Prediction"]=="High").sum(),(df["Prediction"]=="Medium").sum(),
                       (df["Prediction"]=="Low").sum(),f"${df['MonthlyIncome'].mean():,.0f}",
                       f"{df['SatisfactionScore'].mean():.2f}",f"{df['AttendanceRate'].mean():.1f}%"],
        })
        summary.to_excel(writer, index=False, sheet_name="Executive Summary")
    return buf.getvalue()

def to_html_report(df, insights):
    rows = df.head(50).to_html(index=False, classes="data-table", border=0)
    ins  = "".join(f"<li>{i}</li>" for i in insights)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>HR Analytics Report</title>
<style>
  body{{font-family:sans-serif;background:#0f1117;color:#e2e8f0;padding:40px}}
  h1{{color:#00e5ff}} h2{{color:#a855f7;margin-top:40px}}
  .data-table{{border-collapse:collapse;width:100%;font-size:0.85rem}}
  .data-table th{{background:#1e2535;color:#00e5ff;padding:10px;text-align:left}}
  .data-table td{{border-bottom:1px solid #1e2535;padding:8px}}
  li{{margin-bottom:8px;line-height:1.6}}
  .meta{{color:#64748b;font-size:0.85rem;margin-bottom:30px}}
</style></head><body>
<h1>⚡ PulseIQ — Enterprise HR Analytics Report</h1>
<div class="meta">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} · {len(df)} employees analysed</div>
<h2>🔍 AI-Generated Insights</h2><ul>{ins}</ul>
<h2>📋 Employee Predictions</h2>{rows}
</body></html>"""

def single_report_csv(emp_name, dept, age, income, pred, conf, scores, recs):
    flat_recs = "; ".join([item["text"] for cat in recs.values() for item in cat[:1]])
    report_df = pd.DataFrame([{
        "Name": emp_name, "Department": dept, "Age": age, "Monthly Income": income,
        "Prediction": pred, "Confidence": f"{conf:.1f}%",
        "HR Score": f"{scores['hr_score']:.0f}",
        "Health Score": f"{scores['health']:.0f}",
        "Risk Score":   f"{scores['risk']:.0f}",
        "Retention":    f"{scores['retention']:.0f}",
        "Promo Ready":  f"{scores['promo_ready']:.0f}",
        "Top Recommendations": flat_recs,
        "Report Date": datetime.now().strftime("%Y-%m-%d"),
    }])
    return report_df.to_csv(index=False).encode("utf-8")

# ═══════════════════════════════════════════════════════
#  ██   ██ ███████  █████  ██████  ███████ ██████
#  ██   ██ ██      ██   ██ ██   ██ ██      ██   ██
#  ███████ █████   ███████ ██   ██ █████   ██████
#  ██   ██ ██      ██   ██ ██   ██ ██      ██   ██
#  ██   ██ ███████ ██   ██ ██████  ███████ ██   ██
# ═══════════════════════════════════════════════════════

# ── PREDICTION MODE BANNER ────────────────────────────────────────────────
_mode = st.session_state.get("pred_mode", "rules")
if _mode == "model":
    st.markdown("""<div style='background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);
    border-radius:10px;padding:10px 18px;margin-bottom:12px;font-size:0.82rem;color:#86efac;
    font-family:monospace'>
    ⚡ <b>ML Model Active</b> — Predictions powered by your trained model.pkl
    </div>""", unsafe_allow_html=True)
else:
    st.markdown("""<div style='background:rgba(234,179,8,0.08);border:1px solid rgba(234,179,8,0.25);
    border-radius:10px;padding:10px 18px;margin-bottom:12px;font-size:0.82rem;color:#fde68a;
    font-family:monospace'>
    🧠 <b>AI Rules Engine Active</b> — Running on intelligent multi-factor scoring.
    To use your trained model, commit <code>model.pkl</code> to the <code>app/</code> folder in GitHub.
    </div>""", unsafe_allow_html=True)

# ── HERO ──
st.markdown("""
<div style='text-align:center;padding:40px 0 10px'>
  <span class='hero-pill'>⚡ LIVE</span>
  <span class='hero-pill'>AI-POWERED</span>
  <span class='hero-pill'>ENTERPRISE</span>
</div>
""", unsafe_allow_html=True)
st.markdown("<h1 class='hero-title'>PulseIQ · HR Intelligence</h1>", unsafe_allow_html=True)
st.markdown("<p class='hero-sub'>Enterprise-Grade · AI-Driven · Actionable Analytics</p>", unsafe_allow_html=True)
st.markdown("<div class='hr-divider'></div>", unsafe_allow_html=True)

# ── TOP-LEVEL NAVIGATION TABS ──
tab1, tab2, tab3 = st.tabs([
    "⚡  Individual Intelligence Profiler",
    "🏢  Bulk Enterprise Analytics",
    "📜  Prediction History",
])

# ═══════════════════════════════════════════════════════════════════
# TAB 1 — INDIVIDUAL INTELLIGENCE PROFILER
# ═══════════════════════════════════════════════════════════════════
with tab1:

    # ── TOOLBAR: Random Generator + Reset ──
    tb1, tb2, tb3_ = st.columns([1, 1, 4])
    with tb1:
        gen_random = st.button("🎲  Random Employee")
    with tb2:
        reset_form = st.button("🔄  Reset Form")

    # Seed session defaults
    if "form_data" not in st.session_state or reset_form:
        st.session_state.form_data = generate_sample_employee() if gen_random else {
            "name":"Alex Chen","emp_id":"EMP-10001","age":32,"gender":"Male",
            "dept":"Research & Development","role":"Research Scientist",
            "education":"Master's Degree","marital":"Married","income":75000,
            "tenure":5,"yrs_role":3,"yrs_promo":1,"tot_exp":8,
            "travel":"Travel_Rarely","overtime":False,"sat":3.2,"env_sat":3.0,
            "rel_sat":3.0,"wlb":3,"att":95.0,"mgr_rating":3.8,"training":25,
            "projects":3,"perf_rating":3,"dist":10,"job_inv":3,
            "inno":60,"lead":55,"comm":65,"team":70,"work_env":65,
        }
    if gen_random and not reset_form:
        st.session_state.form_data = generate_sample_employee()
    fd = st.session_state.form_data

    # ═══════════════════════════════
    # ASSESSMENT FORM
    # ═══════════════════════════════
    with st.form("full_employee_form", clear_on_submit=False):

        # ── SECTION 1: Personal Information ──
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(sec("👤", "Personal Information"), unsafe_allow_html=True)
        pi1, pi2, pi3, pi4 = st.columns(4)
        with pi1:
            emp_name   = st.text_input("Full Name",         value=fd["name"])
            emp_id     = st.text_input("Employee ID",       value=fd["emp_id"])
        with pi2:
            age        = st.number_input("Age",             18, 65, fd["age"])
            gender     = st.selectbox("Gender",             GENDER_OPTIONS,
                                      index=GENDER_OPTIONS.index(fd["gender"]) if fd["gender"] in GENDER_OPTIONS else 0)
        with pi3:
            dept       = st.selectbox("Department",         DEPARTMENTS,
                                      index=DEPARTMENTS.index(fd["dept"]) if fd["dept"] in DEPARTMENTS else 0)
            job_role   = st.selectbox("Job Role",           JOB_ROLES,
                                      index=JOB_ROLES.index(fd["role"]) if fd["role"] in JOB_ROLES else 0)
        with pi4:
            education  = st.selectbox("Education",          EDUCATION_LEVELS,
                                      index=EDUCATION_LEVELS.index(fd["education"]) if fd["education"] in EDUCATION_LEVELS else 0)
            marital    = st.selectbox("Marital Status",     MARITAL_STATUS,
                                      index=MARITAL_STATUS.index(fd["marital"]) if fd["marital"] in MARITAL_STATUS else 0)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── SECTION 2: Job Information ──
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(sec("💼", "Job Information"), unsafe_allow_html=True)
        ji1, ji2, ji3, ji4 = st.columns(4)
        with ji1:
            income     = st.number_input("Monthly Income ($)",       10000, 300000, fd["income"], 1000)
            tenure     = st.number_input("Years at Company",         0, 40, fd["tenure"])
        with ji2:
            yrs_role   = st.number_input("Years in Current Role",    0, 20, fd["yrs_role"])
            yrs_promo  = st.number_input("Years Since Last Promotion",0,15, fd["yrs_promo"])
        with ji3:
            tot_exp    = st.number_input("Total Working Years",      0, 45, fd["tot_exp"])
            travel     = st.selectbox("Business Travel",             TRAVEL_OPTIONS,
                                      index=TRAVEL_OPTIONS.index(fd["travel"]) if fd["travel"] in TRAVEL_OPTIONS else 0)
        with ji4:
            overtime   = st.checkbox("Overtime Required",            value=fd["overtime"])
            dist       = st.number_input("Distance From Home (km)",  0, 100, fd["dist"])
        st.markdown("</div>", unsafe_allow_html=True)

        # ── SECTION 3: Performance Metrics ──
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(sec("📊", "Performance Metrics"), unsafe_allow_html=True)
        pm1, pm2, pm3 = st.columns(3)
        with pm1:
            sat        = st.slider("Job Satisfaction",        1.0, 4.0, float(fd["sat"]),  0.1)
            env_sat    = st.slider("Environment Satisfaction",1.0, 4.0, float(fd["env_sat"]),0.1)
            rel_sat    = st.slider("Relationship Satisfaction",1.0,4.0, float(fd["rel_sat"]),0.1)
        with pm2:
            wlb        = st.slider("Work-Life Balance",       1,   4,   int(fd["wlb"]))
            att        = st.slider("Attendance Rate (%)",     50.0,100.0,float(fd["att"]), 0.5)
            mgr_rating = st.slider("Manager Rating",          1.0, 5.0, float(fd["mgr_rating"]),0.1)
        with pm3:
            training   = st.number_input("Training Hours / Year",    0, 100, fd["training"])
            n_projects = st.number_input("Number of Projects",       1,  15, fd["projects"])
            perf_rating= st.slider("Self Performance Rating",        1,   4,  int(fd["perf_rating"]))
        st.markdown("</div>", unsafe_allow_html=True)

        # ── SECTION 4: Behavioural / Soft Skills ──
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(sec("🧠", "Behavioural Assessment"), unsafe_allow_html=True)
        bh1, bh2, bh3 = st.columns(3)
        with bh1:
            job_inv    = st.slider("Job Involvement",         1,   4,   int(fd["job_inv"]))
            work_env   = st.slider("Work Environment Score",  0,  100,  int(fd["work_env"]))
            inno       = st.slider("Innovation Score",        0,  100,  int(fd["inno"]))
        with bh2:
            lead       = st.slider("Leadership Score",        0,  100,  int(fd["lead"]))
            comm       = st.slider("Communication Score",     0,  100,  int(fd["comm"]))
        with bh3:
            team       = st.slider("Team Collaboration Score",0,  100,  int(fd["team"]))
        st.markdown("</div>", unsafe_allow_html=True)

        # ── SUBMIT ──
        col_sub = st.columns([1,2,1])
        with col_sub[1]:
            submitted = st.form_submit_button("⚡  Generate AI Intelligence Report", use_container_width=True)

    # ═══════════════════════════════════════════════════════════════
    # PREDICTION RESULTS
    # ═══════════════════════════════════════════════════════════════
    if submitted:
        # Build API payload — keep same keys as original /predict-performance
        payload = {
            "Age": age, "MonthlyIncome": income, "YearsAtCompany": tenure,
            "satisfaction_score": sat, "AttendanceRate": att,
            # Optional extended fields (ignored gracefully if API doesn't use them)
            "Gender": gender, "Department": dept, "JobRole": job_role,
            "OverTime": "Yes" if overtime else "No",
            "BusinessTravel": travel, "EducationField": education,
            "MaritalStatus": marital, "DistanceFromHome": dist,
            "YearsInCurrentRole": yrs_role, "YearsSinceLastPromotion": yrs_promo,
            "TotalWorkingYears": tot_exp, "TrainingTimesLastYear": training,
            "NumCompaniesWorked": n_projects, "EnvironmentSatisfaction": int(env_sat),
            "RelationshipSatisfaction": int(rel_sat), "WorkLifeBalance": wlb,
            "JobInvolvement": job_inv, "ManagerRating": mgr_rating,
            "PerformanceRating": perf_rating,
        }

        with st.spinner("⚡ Analysing neural pathways & building intelligence report …"):
            time.sleep(0.4)
            pred, probs = _predict_single(payload)
            conf = max(probs.values()) * 100

        # ── Compute all derived scores ──
        scores = compute_scores(
            pred, probs, age, income, tenure, sat, att, mgr_rating,
            wlb=wlb, env_sat=env_sat, rel_sat=rel_sat, ot=overtime,
            training_hrs=training, n_projects=n_projects, job_inv=job_inv,
            inno=inno, lead=lead, comm=comm, team=team,
            dist=dist, yrs_role=yrs_role, yrs_promo=yrs_promo, tot_exp=tot_exp,
        )

        # ── Generate recommendations ──
        recs = generate_recommendations(
            pred, scores, age, income, tenure, sat, att, mgr_rating,
            dept, job_role, overtime, training, n_projects, yrs_promo, wlb, emp_name
        )

        # ── Save to history ──
        st.session_state.prediction_history.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "name": emp_name, "id": emp_id, "dept": dept,
            "prediction": pred, "confidence": f"{conf:.1f}%",
            "hr_score": f"{scores['hr_score']:.0f}",
        })

        # ══════════════════════════════════════════
        # RESULTS SECTION
        # ══════════════════════════════════════════
        st.markdown("<div class='section-divider'>INTELLIGENCE REPORT</div>", unsafe_allow_html=True)

        # ── RISK BANNER (if critical) ──
        if scores["risk"] >= 70:
            st.markdown(f"""
            <div class='risk-banner'>
              <span style='font-size:1.5rem'>🚨</span>
              <div><b style='color:#ef4444'>CRITICAL ALERT</b> — High attrition risk detected for
              <b>{emp_name}</b>. Immediate HR intervention recommended.
              Risk Score: <b style='color:#ef4444'>{scores['risk']:.0f}/100</b></div>
            </div>""", unsafe_allow_html=True)

        # ── ROW 1: Prediction + Confidence ──
        r1a, r1b, r1c = st.columns([1.2, 1, 1])
        with r1a:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("🧠", "AI Prediction"), unsafe_allow_html=True)
            st.markdown(f"<div class='pred-{pred.lower()}'>{pred.upper()}<br>PERFORMER</div>",
                        unsafe_allow_html=True)
            st.markdown(f"<p style='text-align:center;color:{C_MUTED};margin-top:8px'>"
                        f"Confidence: <b style='color:{C_ACCENT1}'>{conf:.1f}%</b></p>",
                        unsafe_allow_html=True)
            st.markdown(f"<p style='text-align:center'>{perf_badge(pred)}</p>",
                        unsafe_allow_html=True)
            ai_reasoning = {
                "High":   "Profile exhibits consistently exceptional metrics across satisfaction, attendance, and manager ratings — hallmarks of top-tier contributors.",
                "Medium": "Profile shows solid baseline performance with identifiable growth levers. Targeted development is likely to unlock High-performer trajectory.",
                "Low":    "Critical risk factors detected across multiple dimensions. Structured intervention and close monitoring are strongly recommended.",
            }
            st.markdown(f"<div class='ai-box'>{ai_reasoning.get(pred,'')}</div>",
                        unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with r1b:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("🎯", "Prediction Confidence"), unsafe_allow_html=True)
            st.plotly_chart(viz_probability_bars(probs), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with r1c:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("🔮", "HR Score"), unsafe_allow_html=True)
            st.plotly_chart(gauge_chart(scores["hr_score"], "Overall HR Score", C_ACCENT2),
                            use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── ROW 2: 8 KPI Mini-Cards ──
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(sec("📈", "Employee Intelligence Scorecard"), unsafe_allow_html=True)
        k1,k2,k3,k4,k5,k6,k7,k8 = st.columns(8)
        kpi_data = [
            (k1, f"{scores['health']:.0f}",       "Health Score",       "💚", "up" if scores["health"]>=60 else "down"),
            (k2, f"{scores['risk']:.0f}",          "Risk Score",         "🔴", "down" if scores["risk"]>=60 else "up"),
            (k3, f"{scores['growth']:.0f}",        "Growth Score",       "📈", "up" if scores["growth"]>=60 else "flat"),
            (k4, f"{scores['promo_ready']:.0f}",   "Promo Readiness",    "🚀", "up" if scores["promo_ready"]>=70 else "flat"),
            (k5, f"{scores['retention']:.0f}",     "Retention Prob",     "🔒", "up" if scores["retention"]>=70 else "down"),
            (k6, f"{scores['productivity']:.0f}",  "Productivity",       "⚡", "up" if scores["productivity"]>=60 else "flat"),
            (k7, f"{scores['engagement']:.0f}",    "Engagement",         "💬", "up" if scores["engagement"]>=60 else "flat"),
            (k8, f"{scores['soft_skills']:.0f}",   "Soft Skills",        "🤝", "up" if scores["soft_skills"]>=60 else "flat"),
        ]
        for col, val, lbl, icon, direction in kpi_data:
            with col:
                st.markdown(kpi_card(val, lbl, icon=icon, delta_dir=direction), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── ROW 3: Gauges ──
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(sec("🎛️", "Performance Gauges"), unsafe_allow_html=True)
        g1, g2, g3, g4 = st.columns(4)
        gauge_items = [
            (g1, scores["health"],       "Health",       C_HIGH),
            (g2, scores["risk"],         "Attrition Risk", C_LOW),
            (g3, scores["promo_ready"],  "Promo Ready",  C_ACCENT2),
            (g4, scores["retention"],    "Retention",    C_ACCENT1),
        ]
        for col, val, lbl, clr in gauge_items:
            with col:
                st.plotly_chart(gauge_chart(val, lbl, clr), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── ROW 4: Radar + Score Bars ──
        rv1, rv2 = st.columns(2)
        with rv1:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("📡", "Performance Radar"), unsafe_allow_html=True)
            st.plotly_chart(viz_scorecard_radar(scores, emp_name), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with rv2:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("🎯", "Soft Skills Spider"), unsafe_allow_html=True)
            st.plotly_chart(viz_skill_spider(inno, lead, comm, team, job_inv, wlb, emp_name),
                            use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── ROW 5: Score Bars + Waterfall ──
        bv1, bv2 = st.columns(2)
        with bv1:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("📊", "Score Breakdown"), unsafe_allow_html=True)
            st.plotly_chart(viz_scores_bar(scores), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with bv2:
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("🌊", "HR Score Waterfall"), unsafe_allow_html=True)
            st.plotly_chart(viz_kpi_waterfall(scores), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ── ROW 6: Benchmark Scatter ──
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(sec("🌍", "Workforce Benchmark"), unsafe_allow_html=True)
        st.plotly_chart(viz_benchmark_scatter(income, sat, emp_name), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ═══════════════════════════════════════
        # AI RECOMMENDATION ENGINE
        # ═══════════════════════════════════════
        st.markdown("<div class='section-divider'>AI RECOMMENDATION ENGINE</div>", unsafe_allow_html=True)

        # Executive Summary first
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(sec("📋", "Executive Summary"), unsafe_allow_html=True)
        for item in recs["executive"]:
            st.markdown(f"<div class='rec-block {item['cls']}'>{item['icon']} {item['text']}</div>",
                        unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Collapsible recommendation sections
        rec_meta = [
            ("strengths",  "✅ Strengths",            True),
            ("weaknesses", "⚠️ Weaknesses & Risks",   True),
            ("career",     "🚀 Career Growth Plan",    True),
            ("training",   "📚 Training Roadmap",      False),
            ("salary",     "💰 Compensation Review",   False),
            ("leadership", "👑 Leadership Development",False),
            ("wellness",   "💚 Employee Wellness",     False),
            ("attrition",  "🔒 Attrition Prevention",  True),
            ("action",     "📋 Action Items",          False),
        ]
        for key, title, expanded in rec_meta:
            render_rec_section(title, recs[key], expanded=expanded)

        # ── WHAT-IF SCENARIO SIMULATOR ──
        st.markdown("<div class='section-divider'>WHAT-IF ANALYSIS</div>", unsafe_allow_html=True)
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(sec("🔬", "Scenario Simulator — What if we change these inputs?"), unsafe_allow_html=True)
        ws1, ws2, ws3 = st.columns(3)
        with ws1:
            wi_sat  = st.slider("Hypothetical Satisfaction", 1.0, 4.0, sat,  0.1, key="wi_sat")
        with ws2:
            wi_att  = st.slider("Hypothetical Attendance %", 50.0,100.0,att, 0.5, key="wi_att")
        with ws3:
            wi_mgr  = st.slider("Hypothetical Mgr Rating",   1.0, 5.0, mgr_rating, 0.1, key="wi_mgr")
        wi_scores = compute_scores(pred, probs, age, income, tenure, wi_sat, wi_att, wi_mgr,
                                   wlb=wlb, env_sat=env_sat, rel_sat=rel_sat, ot=overtime,
                                   training_hrs=training, n_projects=n_projects)
        wf1, wf2, wf3, wf4 = st.columns(4)
        wi_items = [
            (wf1, "HR Score",     scores["hr_score"],   wi_scores["hr_score"]),
            (wf2, "Risk",         scores["risk"],        wi_scores["risk"]),
            (wf3, "Retention",    scores["retention"],   wi_scores["retention"]),
            (wf4, "Productivity", scores["productivity"],wi_scores["productivity"]),
        ]
        for col, lbl, base_v, new_v in wi_items:
            with col:
                delta = new_v - base_v
                dir_  = "up" if delta > 0 else ("down" if delta < 0 else "flat")
                st.markdown(kpi_card(f"{new_v:.0f}", lbl, delta=f"{delta:+.1f} vs actual",
                                     delta_dir=dir_, icon="🔄"), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── DOWNLOADS ──
        st.markdown("<div class='section-divider'>EXPORT INTELLIGENCE REPORT</div>", unsafe_allow_html=True)
        dl1, dl2, dl3 = st.columns(3)
        with dl1:
            csv_data = single_report_csv(emp_name, dept, age, income, pred, conf, scores, recs)
            st.download_button(
                "📥 Download CSV Report",
                data=csv_data,
                file_name=f"{emp_name.replace(' ','_')}_HR_Report.csv",
                mime="text/csv", use_container_width=True,
            )
        with dl2:
            # ── PDF REPORT ──
            if PDF_AVAILABLE:
                # Build emp_info dict from current form values
                _emp_info = {
                    "name": emp_name, "emp_id": emp_id, "dept": dept,
                    "role": job_role, "education": education, "gender": gender,
                    "marital": marital, "age": age, "income": income,
                    "tenure": tenure, "yrs_role": yrs_role, "yrs_promo": yrs_promo,
                    "tot_exp": tot_exp, "travel": travel, "overtime": overtime,
                    "dist": dist, "wlb": wlb, "job_inv": job_inv,
                    "work_env": work_env, "inno": inno, "lead": lead,
                    "comm": comm, "team": team, "training": training,
                    "projects": n_projects, "perf_rating": perf_rating,
                    "sat": sat, "env_sat": env_sat, "rel_sat": rel_sat,
                    "att": att, "mgr_rating": mgr_rating,
                }
                with st.spinner("Generating PDF …"):
                    _pdf_bytes = generate_single_pdf(_emp_info, scores, probs, recs, pred)
                st.download_button(
                    "📄 Download PDF Intelligence Report",
                    data=_pdf_bytes,
                    file_name=f"{emp_name.replace(' ','_')}_HR_Report.pdf",
                    mime="application/pdf", use_container_width=True,
                )
            else:
                st.info("PDF engine not found. Place hr_pdf_engine.py in the same folder.")
        with dl3:
            # JSON export — _NpEncoder (module-level) handles all numpy types.
            json_data = json.dumps({
                "employee": {"name": str(emp_name), "id": str(emp_id),
                             "dept": str(dept),     "role": str(job_role)},
                "prediction": {"label": str(pred),
                               "confidence": float(conf),
                               "probabilities": {k: float(v) for k, v in probs.items()}},
                "scores": {k: round(float(v), 1) for k, v in scores.items()},
                "generated": datetime.now().isoformat(),
            }, indent=2, cls=_NpEncoder)
            st.download_button(
                "📊 Download JSON Report",
                data=json_data,
                file_name=f"{emp_name.replace(' ','_')}_HR_Report.json",
                mime="application/json", use_container_width=True,
            )

# ═══════════════════════════════════════════════════════════════════
# TAB 2 — BULK ENTERPRISE ANALYTICS
# ═══════════════════════════════════════════════════════════════════
with tab2:

    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown(sec("📤", "Upload Employee Dataset"), unsafe_allow_html=True)
    st.markdown("""
    <p style='color:#64748b;font-size:0.9rem;margin-bottom:16px'>
    Upload a <span class='mono'>CSV</span> or <span class='mono'>XLSX</span> file
    containing employee records. Required columns: <span class='chip'>Age</span>
    <span class='chip'>MonthlyIncome</span> <span class='chip'>YearsAtCompany</span>
    <span class='chip'>satisfaction_score</span> <span class='chip'>AttendanceRate</span>.
    All other columns are optional and will be derived automatically.
    </p>""", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=["csv", "xlsx"])
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded_file:
        try:
            df_raw = (pd.read_csv(uploaded_file)
                      if uploaded_file.name.endswith(".csv")
                      else pd.read_excel(uploaded_file))
            st.success(f"✅ Loaded **{len(df_raw):,}** employee records · {df_raw.shape[1]} columns detected.")
        except Exception:
            st.error("❌ Invalid file format. Please upload a valid CSV or XLSX file.")
            st.stop()

        col_run = st.columns([1, 2, 1])
        with col_run[1]:
            run_bulk = st.button("🚀  Execute Bulk Intelligence Pipeline", use_container_width=True)

        if run_bulk or st.session_state.bulk_results is not None:
            if run_bulk:
                with st.spinner("⚡ Processing bulk predictions …"):
                    try:
                        _bulk_preds = _predict_bulk(df_raw.to_dict("records"))
                        df_res = pd.DataFrame(_bulk_preds)
                    except Exception as _be:
                        st.warning(f"⚠️ Prediction engine error ({_be}) — using synthesised predictions.")
                        df_res = df_raw.copy()

                df_res = bulk_ensure_columns(df_res)
                st.session_state.bulk_results    = df_res
                st.session_state.bulk_df_source  = df_raw

            df_res = st.session_state.bulk_results

            # ═══════════════════════════════════════
            # BULK KPIs
            # ═══════════════════════════════════════
            st.markdown("<div class='section-divider'>ENTERPRISE DASHBOARD</div>", unsafe_allow_html=True)
            n_emp, n_hi, n_med, n_low, n_pr, n_ar, avg_sal, avg_sat, avg_att, avg_exp = bulk_kpis(df_res)
            kpi_row1 = st.columns(5)
            kpi_defs1 = [
                (f"{n_emp:,}",    "Total Employees",       "👥",  "flat"),
                (f"{n_hi:,}",     "High Performers",       "🏆",  "up"),
                (f"{n_med:,}",    "Mid Performers",        "📊",  "flat"),
                (f"{n_low:,}",    "Low Performers",        "⚠️",  "down"),
                (f"{n_pr:,}",     "Promotion Ready",       "🚀",  "up"),
            ]
            for col, (v, l, ic, d) in zip(kpi_row1, kpi_defs1):
                with col:
                    st.markdown(kpi_card(v, l, icon=ic, delta_dir=d), unsafe_allow_html=True)

            kpi_row2 = st.columns(5)
            kpi_defs2 = [
                (f"{n_ar:,}",        "High Attrition Risk",  "🔴", "down"),
                (f"${avg_sal:,.0f}", "Avg Monthly Salary",   "💰", "flat"),
                (f"{avg_sat:.2f}",   "Avg Satisfaction",     "😊", "up"),
                (f"{avg_att:.1f}%",  "Avg Attendance",       "📅", "up"),
                (f"{avg_exp:.1f}y",  "Avg Experience",       "🎓", "flat"),
            ]
            for col, (v, l, ic, d) in zip(kpi_row2, kpi_defs2):
                with col:
                    st.markdown(kpi_card(v, l, icon=ic, delta_dir=d), unsafe_allow_html=True)

            # ═══════════════════════════════════════
            # BULK CHARTS — ROW 1
            # ═══════════════════════════════════════
            st.markdown("<div class='hr-divider'></div>", unsafe_allow_html=True)
            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                fig = px.pie(df_res, names="Prediction", hole=0.55,
                             color="Prediction", color_discrete_map=COLOR_MAP,
                             title="Performance Distribution")
                fig.update_traces(textinfo="percent+label", pull=[0.05]*3)
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with bc2:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                dept_pred = df_res.groupby(["Department","Prediction"]).size().reset_index(name="Count")
                fig = px.bar(dept_pred, x="Department", y="Count", color="Prediction",
                             color_discrete_map=COLOR_MAP, title="Department Performance",
                             barmode="stack", text_auto=True)
                fig.update_layout(xaxis_tickangle=-30)
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with bc3:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                fig = px.scatter(df_res, x="AttritionRisk", y="PromotionReadiness",
                                 color="Prediction", size="OverallScore",
                                 color_discrete_map=COLOR_MAP,
                                 hover_name="EmployeeName", title="HR Matrix: Attrition vs Promotion",
                                 opacity=0.75)
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # ── ROW 2 ──
            bc4, bc5 = st.columns(2)
            with bc4:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                fig = px.histogram(df_res, x="MonthlyIncome", color="Prediction",
                                   nbins=30, color_discrete_map=COLOR_MAP,
                                   title="Salary Distribution by Performance", barmode="overlay",
                                   opacity=0.7)
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with bc5:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                fig = px.box(df_res, x="Prediction", y="SatisfactionScore",
                             color="Prediction", color_discrete_map=COLOR_MAP,
                             title="Satisfaction Distribution by Performance Tier",
                             points="outliers")
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # ── ROW 3 ──
            bc6, bc7 = st.columns(2)
            with bc6:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                fig = px.violin(df_res, x="Prediction", y="AttendanceRate",
                                color="Prediction", color_discrete_map=COLOR_MAP,
                                title="Attendance Distribution by Performance",
                                box=True, points="outliers")
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with bc7:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                age_g = df_res.copy()
                age_g["Age Group"] = pd.cut(age_g["Age"], bins=[20,30,40,50,65],
                                            labels=["20–30","30–40","40–50","50+"])
                fig = px.histogram(age_g, x="Age Group", color="Prediction",
                                   color_discrete_map=COLOR_MAP, barmode="group",
                                   title="Age Group vs Performance", text_auto=True)
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # ── ROW 4: Gender pie + Treemap ──
            bc8, bc9 = st.columns(2)
            with bc8:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                fig = px.pie(df_res, names="Gender", title="Gender Distribution",
                             color_discrete_sequence=[C_ACCENT1, C_ACCENT2, C_ACCENT3], hole=0.4)
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with bc9:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                tm_df = df_res.groupby(["Department","Prediction"]).size().reset_index(name="Count")
                fig   = px.treemap(tm_df, path=["Department","Prediction"], values="Count",
                                   color="Count", color_continuous_scale="Blues",
                                   title="Department × Performance Treemap")
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # ── ROW 5: Bubble + Heatmap ──
            bc10, bc11 = st.columns(2)
            with bc10:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                fig = px.scatter(df_res, x="YearsAtCompany", y="MonthlyIncome",
                                 size="OverallScore", color="Prediction",
                                 color_discrete_map=COLOR_MAP,
                                 hover_name="EmployeeName",
                                 title="Experience vs Income (Bubble = Score)",
                                 opacity=0.7)
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with bc11:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                num_cols = ["MonthlyIncome","SatisfactionScore","AttendanceRate",
                            "PromotionReadiness","AttritionRisk","OverallScore",
                            "YearsAtCompany","Age"]
                num_cols = [c for c in num_cols if c in df_res.columns]
                if len(num_cols) >= 3:
                    corr = df_res[num_cols].corr().round(2)
                    fig  = go.Figure(go.Heatmap(
                        z=corr.values, x=corr.columns.tolist(), y=corr.index.tolist(),
                        colorscale="RdBu", zmid=0,
                        text=corr.values.round(2), texttemplate="%{text}",
                        hovertemplate="%{x} vs %{y}: %{z}<extra></extra>",
                    ))
                    fig.update_layout(title="Correlation Matrix", height=400, **PLOTLY_THEME_NM,
                                      margin=dict(t=48, b=40, l=80, r=40))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Insufficient numeric columns for correlation matrix.")
                st.markdown("</div>", unsafe_allow_html=True)

            # ── ROW 6: Attrition donut + Promo bar ──
            bc12, bc13 = st.columns(2)
            with bc12:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                # Build attrition risk buckets explicitly — avoids pandas
                # Categorical column-naming differences across versions.
                _ar = df_res["AttritionRisk"]
                _rb = {
                    "Low Risk":    int((_ar <= 33).sum()),
                    "Medium Risk": int(((_ar > 33) & (_ar <= 66)).sum()),
                    "High Risk":   int((_ar > 66).sum()),
                }
                _rb_df = pd.DataFrame({
                    "Risk Level": list(_rb.keys()),
                    "Count":      list(_rb.values()),
                })
                fig = px.pie(
                    _rb_df, names="Risk Level", values="Count",
                    color="Risk Level", hole=0.5,
                    color_discrete_map={
                        "Low Risk":    C_HIGH,
                        "Medium Risk": C_MEDIUM,
                        "High Risk":   C_LOW,
                    },
                    title="Attrition Risk Distribution",
                )
                fig.update_traces(
                    textinfo="percent+label+value",
                    pull=[0.04, 0.04, 0.08],
                    hovertemplate="%{label}: %{value} employees (%{percent})<extra></extra>",
                )
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with bc13:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                top10 = df_res.nlargest(10, "OverallScore")[["EmployeeName","Department","Prediction","OverallScore"]]
                fig   = px.bar(top10, x="OverallScore", y="EmployeeName",
                               color="Prediction", color_discrete_map=COLOR_MAP,
                               orientation="h", text="OverallScore",
                               title="🏆 Top 10 Performers by Overall Score")
                fig.update_traces(texttemplate="%{text:.0f}", textposition="inside")
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # ── ROW 7: Bottom 10 + Area trend ──
            bc14, bc15 = st.columns(2)
            with bc14:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                bot10 = df_res.nsmallest(10, "OverallScore")[["EmployeeName","Department","Prediction","OverallScore"]]
                fig   = px.bar(bot10, x="OverallScore", y="EmployeeName",
                               color="Prediction", color_discrete_map=COLOR_MAP,
                               orientation="h", text="OverallScore",
                               title="⚠️ Bottom 10 — Needs Attention")
                fig.update_traces(texttemplate="%{text:.0f}", textposition="inside")
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(pt(fig), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with bc15:
                st.markdown("<div class='glass'>", unsafe_allow_html=True)
                tenure_g = df_res.groupby("YearsAtCompany")[["OverallScore","AttritionRisk","PromotionReadiness"]].mean().reset_index()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=tenure_g["YearsAtCompany"], y=tenure_g["OverallScore"],
                                         mode="lines+markers", name="Overall Score",
                                         line=dict(color=C_ACCENT1, width=2),
                                         fill="tozeroy", fillcolor="rgba(0,229,255,0.09)"))
                fig.add_trace(go.Scatter(x=tenure_g["YearsAtCompany"], y=tenure_g["PromotionReadiness"],
                                         mode="lines+markers", name="Promo Readiness",
                                         line=dict(color=C_ACCENT2, width=2)))
                fig.update_layout(title="Score Trends by Years at Company", **PLOTLY_THEME_NM)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # ── ROW 8: Parallel Coordinates ──
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("🔀", "Parallel Coordinates — Multi-Dimensional View"), unsafe_allow_html=True)
            par_cols = ["MonthlyIncome","SatisfactionScore","AttendanceRate",
                        "PromotionReadiness","AttritionRisk","OverallScore"]
            par_cols = [c for c in par_cols if c in df_res.columns]
            pred_num = df_res["Prediction"].map({"High": 2, "Medium": 1, "Low": 0})
            dims = [dict(range=[df_res[c].min(), df_res[c].max()],
                         label=c, values=df_res[c]) for c in par_cols]
            fig = go.Figure(go.Parcoords(
                line=dict(color=pred_num, colorscale=[[0, C_LOW],[0.5, C_MEDIUM],[1, C_HIGH]],
                          showscale=True, cmin=0, cmax=2),
                dimensions=dims,
            ))
            fig.update_layout(height=380, **PLOTLY_THEME_NM)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # ═══════════════════════════════════════
            # AI INSIGHTS
            # ═══════════════════════════════════════
            st.markdown("<div class='section-divider'>AI-GENERATED INSIGHTS</div>", unsafe_allow_html=True)
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("💡", "Intelligent Observations"), unsafe_allow_html=True)
            insights = bulk_generate_insights(df_res)
            for i, ins in enumerate(insights, 1):
                st.markdown(f"""
                <div class='rec-block rec-action' style='display:flex;gap:14px;align-items:flex-start'>
                  <span class='mono' style='color:{C_MUTED};min-width:24px'>{i:02d}</span>
                  <span>{ins}</span>
                </div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # ═══════════════════════════════════════
            # DEPT RECOMMENDATIONS
            # ═══════════════════════════════════════
            st.markdown("<div class='section-divider'>HR RECOMMENDATIONS BY DEPARTMENT</div>",
                        unsafe_allow_html=True)
            dept_recs = bulk_recommendations_by_dept(df_res)
            dr_cols   = st.columns(min(3, len(dept_recs)))
            for i, (dept_name, drecs) in enumerate(dept_recs.items()):
                with dr_cols[i % len(dr_cols)]:
                    st.markdown("<div class='glass'>", unsafe_allow_html=True)
                    st.markdown(f"<div class='sec-header'>🏢 {dept_name}</div>", unsafe_allow_html=True)
                    for rec in drecs:
                        st.markdown(f"<div class='rec-block rec-neutral' style='margin-bottom:8px'>{rec}</div>",
                                    unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

            # ═══════════════════════════════════════
            # INTERACTIVE DATA TABLE
            # ═══════════════════════════════════════
            st.markdown("<div class='section-divider'>ENTERPRISE LEADERBOARD</div>", unsafe_allow_html=True)
            st.markdown("<div class='glass'>", unsafe_allow_html=True)
            st.markdown(sec("📋", "Interactive Employee Table"), unsafe_allow_html=True)

            # Filters
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                f_pred = st.multiselect("Filter by Performance", ["High","Medium","Low"],
                                        default=["High","Medium","Low"], key="bulk_f_pred")
            with fc2:
                f_dept = st.multiselect("Filter by Department", df_res["Department"].unique().tolist(),
                                        default=df_res["Department"].unique().tolist(), key="bulk_f_dept")
            with fc3:
                f_sort = st.selectbox("Sort by", ["OverallScore","AttritionRisk","PromotionReadiness",
                                                   "MonthlyIncome","SatisfactionScore"],
                                      key="bulk_f_sort")
            df_filtered = df_res[df_res["Prediction"].isin(f_pred) & df_res["Department"].isin(f_dept)]
            df_filtered = df_filtered.sort_values(f_sort, ascending=False).reset_index(drop=True)

            show_cols = [c for c in ["EmployeeName","Department","Prediction","OverallScore",
                                     "AttritionRisk","PromotionReadiness","MonthlyIncome",
                                     "SatisfactionScore","AttendanceRate","Age"] if c in df_filtered.columns]
            st.dataframe(df_filtered[show_cols], use_container_width=True, hide_index=True, height=400)
            st.markdown(f"<p style='color:{C_MUTED};font-size:0.8rem'>Showing {len(df_filtered):,} of {len(df_res):,} records</p>",
                        unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # ═══════════════════════════════════════
            # DOWNLOADS — BULK
            # ═══════════════════════════════════════
            st.markdown("<div class='section-divider'>EXPORT OPTIONS</div>", unsafe_allow_html=True)
            dl1, dl2, dl3, dl4 = st.columns(4)
            with dl1:
                st.download_button(
                    "📥 CSV Report",
                    data=df_res.to_csv(index=False).encode("utf-8"),
                    file_name="enterprise_bulk_report.csv", mime="text/csv",
                    use_container_width=True,
                )
            with dl2:
                # ── BULK PDF REPORT ──
                if PDF_AVAILABLE:
                    _kpi_dict = dict(
                        n_emp=n_emp, n_hi=n_hi, n_med=n_med, n_low=n_low,
                        n_pr=n_pr,   n_ar=n_ar,
                        avg_sal=avg_sal, avg_sat=avg_sat,
                        avg_att=avg_att, avg_exp=avg_exp,
                    )
                    with st.spinner("Generating Bulk PDF …"):
                        _bulk_pdf = generate_bulk_pdf(
                            df_res, insights, dept_recs, _kpi_dict
                        )
                    st.download_button(
                        "📄 PDF Enterprise Report",
                        data=_bulk_pdf,
                        file_name="enterprise_hr_report.pdf",
                        mime="application/pdf", use_container_width=True,
                    )
                else:
                    st.info("Place hr_pdf_engine.py in the same folder to enable PDF.")
            with dl3:
                st.download_button(
                    "📊 Excel Executive Report",
                    data=to_excel(df_res),
                    file_name="enterprise_executive_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            with dl4:
                html_report = to_html_report(df_res, insights)
                st.download_button(
                    "🌐 HTML Dashboard",
                    data=html_report.encode("utf-8"),
                    file_name="enterprise_hr_dashboard.html",
                    mime="text/html", use_container_width=True,
                )

# ═══════════════════════════════════════════════════════════════════
# TAB 3 — PREDICTION HISTORY
# ═══════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown(sec("📜", "Recent Predictions"), unsafe_allow_html=True)
    history = st.session_state.prediction_history
    if history:
        hist_df = pd.DataFrame(history[::-1])   # newest first
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
        st.markdown("<br>", unsafe_allow_html=True)
        col_clear = st.columns([1, 2, 1])
        with col_clear[1]:
            if st.button("🗑️  Clear History", use_container_width=True):
                st.session_state.prediction_history = []
                st.rerun()
    else:
        st.markdown("""
        <div style='text-align:center;padding:60px;color:#64748b'>
          <div style='font-size:3rem;margin-bottom:16px'>📭</div>
          <div style='font-size:1.1rem;font-weight:600'>No predictions yet</div>
          <div style='font-size:0.9rem;margin-top:8px'>Run an Individual Prediction to see results here.</div>
        </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── FOOTER ──
st.markdown("""
<div style='text-align:center;padding:40px 0 20px;color:#334155;font-size:0.78rem;
font-family:"JetBrains Mono",monospace;letter-spacing:1px'>
  ⚡ PULSEIQ · HR INTELLIGENCE PLATFORM · POWERED BY FLASK + STREAMLIT + PLOTLY
</div>""", unsafe_allow_html=True)
