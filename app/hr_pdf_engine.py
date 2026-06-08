"""
hr_pdf_engine.py
════════════════════════════════════════════════════════════
PulseIQ · Premium HR PDF Report Engine
Generates impressive, HR-ready PDF reports using ReportLab.
No Chrome / kaleido required — all charts use matplotlib.

Public API
──────────
  generate_single_pdf(emp_info, scores, probs, recs, inputs) → bytes
  generate_bulk_pdf(df, insights, dept_recs, kpi_dict)       → bytes
════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import io, math
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

# ── ReportLab ──────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether, PageBreak,
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas as pdfcanvas

# ─────────────────────────────────────────────
# DESIGN PALETTE
# ─────────────────────────────────────────────
P_NAVY      = colors.HexColor("#0a1628")
P_DARK      = colors.HexColor("#0f1117")
P_CARD      = colors.HexColor("#141820")
P_BORDER    = colors.HexColor("#1e2535")
P_CYAN      = colors.HexColor("#00e5ff")
P_VIOLET    = colors.HexColor("#a855f7")
P_ORANGE    = colors.HexColor("#f97316")
P_GREEN     = colors.HexColor("#22c55e")
P_YELLOW    = colors.HexColor("#eab308")
P_RED       = colors.HexColor("#ef4444")
P_TEXT      = colors.HexColor("#e2e8f0")
P_MUTED     = colors.HexColor("#64748b")
P_WHITE     = colors.white
P_LIGHTGRAY = colors.HexColor("#1e293b")   # kept for reference only

# ── Light/print-safe palette (used in all tables & text) ──
P_BLACK      = colors.HexColor("#111111")   # primary text
P_DARK_TEXT  = colors.HexColor("#1e293b")   # secondary text / labels
P_ROW_EVEN   = colors.HexColor("#f1f5f9")   # alternating row light
P_ROW_ODD    = colors.white                 # alternating row white
P_HDR_BG     = colors.HexColor("#0a1628")   # table header — navy (white text on top)
P_HDR_ALT    = colors.HexColor("#1e40af")   # section sub-header — blue
P_CELL_BG    = colors.white                 # default cell background
P_ACCENT_BG  = colors.HexColor("#e0f2fe")   # light cyan tint for highlights
P_REC_STR    = colors.HexColor("#f0fdf4")   # strength rec background (light green)
P_REC_WARN   = colors.HexColor("#fef2f2")   # warning rec background (light red)
P_REC_ACT    = colors.HexColor("#eff6ff")   # action rec background (light blue)
P_REC_GRW    = colors.HexColor("#faf5ff")   # growth rec background (light violet)
P_REC_NEU    = colors.HexColor("#f8fafc")   # neutral rec background (off-white)

# matplotlib color strings
M_CYAN   = "#00e5ff"
M_VIOLET = "#a855f7"
M_ORANGE = "#f97316"
M_GREEN  = "#22c55e"
M_YELLOW = "#eab308"
M_RED    = "#ef4444"
M_DARK   = "#0f1117"
M_CARD   = "#141820"
M_BORDER = "#1e2535"
M_TEXT   = "#e2e8f0"
M_MUTED  = "#64748b"

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm

# ─────────────────────────────────────────────
# PARAGRAPH STYLES
# ─────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    def s(name, **kw):
        return ParagraphStyle(name, **kw)

    return {
        "title": s("RPTitle",
            fontSize=26, textColor=P_CYAN, alignment=TA_CENTER,
            fontName="Helvetica-Bold", spaceAfter=4, leading=30),
        "subtitle": s("RPSub",
            fontSize=10, textColor=P_MUTED, alignment=TA_CENTER,
            fontName="Helvetica", spaceAfter=2),
        "section": s("RPSection",
            fontSize=13, textColor=P_CYAN, fontName="Helvetica-Bold",
            spaceBefore=14, spaceAfter=6, leading=16),
        "subsection": s("RPSubsec",
            fontSize=10, textColor=P_VIOLET, fontName="Helvetica-Bold",
            spaceBefore=8, spaceAfter=4),
        "body": s("RPBody",
            fontSize=9, textColor=P_TEXT, fontName="Helvetica",
            spaceAfter=4, leading=14, alignment=TA_JUSTIFY),
        "body_left": s("RPBodyL",
            fontSize=9, textColor=P_TEXT, fontName="Helvetica",
            spaceAfter=4, leading=14),
        "small": s("RPSmall",
            fontSize=8, textColor=P_MUTED, fontName="Helvetica",
            spaceAfter=2, leading=12),
        "kpi_val": s("RPKpi",
            fontSize=22, textColor=P_CYAN, fontName="Helvetica-Bold",
            alignment=TA_CENTER, leading=26),
        "kpi_lbl": s("RPKpiL",
            fontSize=7, textColor=P_MUTED, fontName="Helvetica-Bold",
            alignment=TA_CENTER, spaceAfter=0, leading=9),
        "pred_high": s("RPPredH",
            fontSize=30, textColor=P_GREEN, fontName="Helvetica-Bold",
            alignment=TA_CENTER, leading=34),
        "pred_medium": s("RPPredM",
            fontSize=30, textColor=P_YELLOW, fontName="Helvetica-Bold",
            alignment=TA_CENTER, leading=34),
        "pred_low": s("RPPredL",
            fontSize=30, textColor=P_RED, fontName="Helvetica-Bold",
            alignment=TA_CENTER, leading=34),
        "rec_title": s("RPRecT",
            fontSize=9, textColor=P_CYAN, fontName="Helvetica-Bold",
            spaceAfter=2),
        "rec_body": s("RPRecB",
            fontSize=8.5, textColor=P_TEXT, fontName="Helvetica",
            spaceAfter=3, leading=13),
        "footer": s("RPFtr",
            fontSize=7, textColor=P_MUTED, fontName="Helvetica",
            alignment=TA_CENTER),
        "tbl_header": s("RPTblH",
            fontSize=8, textColor=P_WHITE, fontName="Helvetica-Bold",
            alignment=TA_CENTER),
        "tbl_cell": s("RPTblC",
            fontSize=8, textColor=P_TEXT, fontName="Helvetica",
            alignment=TA_CENTER),
        "insight": s("RPIns",
            fontSize=8.5, textColor=P_TEXT, fontName="Helvetica",
            spaceAfter=4, leading=13, leftIndent=8),
        "exec_summary": s("RPExec",
            fontSize=9.5, textColor=P_TEXT, fontName="Helvetica",
            spaceAfter=6, leading=15, alignment=TA_JUSTIFY),
    }

# ─────────────────────────────────────────────
# CANVAS CALLBACKS — header / footer on every page
# ─────────────────────────────────────────────
class _PageTemplate:
    def __init__(self, report_title: str, emp_name: str = ""):
        self.report_title = report_title
        self.emp_name     = emp_name

    def __call__(self, canv: pdfcanvas.Canvas, doc):
        canv.saveState()
        w, h = A4

        # ── Header bar ──
        canv.setFillColor(P_NAVY)
        canv.rect(0, h - 2.2*cm, w, 2.2*cm, fill=1, stroke=0)
        # Cyan accent line
        canv.setFillColor(P_CYAN)
        canv.rect(0, h - 2.22*cm, w, 2*mm, fill=1, stroke=0)
        # Logo text
        canv.setFont("Helvetica-Bold", 13)
        canv.setFillColor(P_CYAN)
        canv.drawString(MARGIN, h - 1.4*cm, "⚡ PulseIQ")
        canv.setFont("Helvetica", 9)
        canv.setFillColor(P_MUTED)
        canv.drawString(MARGIN + 2.6*cm, h - 1.4*cm, "HR Intelligence Platform")
        # Right side — report title + date
        canv.setFont("Helvetica-Bold", 8)
        canv.setFillColor(P_TEXT)
        canv.drawRightString(w - MARGIN, h - 1.1*cm, self.report_title)
        canv.setFont("Helvetica", 7)
        canv.setFillColor(P_MUTED)
        canv.drawRightString(w - MARGIN, h - 1.55*cm,
                             f"Generated: {datetime.now().strftime('%d %b %Y · %H:%M')}")

        # ── Footer bar ──
        canv.setFillColor(P_NAVY)
        canv.rect(0, 0, w, 1.3*cm, fill=1, stroke=0)
        canv.setFillColor(P_CYAN)
        canv.rect(0, 1.28*cm, w, 1.5*mm, fill=1, stroke=0)
        canv.setFont("Helvetica", 7)
        canv.setFillColor(P_MUTED)
        canv.drawString(MARGIN, 0.55*cm,
                        "CONFIDENTIAL — For authorised HR personnel only. "
                        "PulseIQ AI Platform · Powered by Machine Learning")
        canv.drawRightString(w - MARGIN, 0.55*cm, f"Page {doc.page}")

        canv.restoreState()

# ─────────────────────────────────────────────
# DIVIDER FLOWABLE
# ─────────────────────────────────────────────
def _divider(color=P_BORDER, thickness=0.5):
    return HRFlowable(width="100%", thickness=thickness,
                      color=color, spaceAfter=6, spaceBefore=6)

# ─────────────────────────────────────────────
# MATPLOTLIB CHART → ReportLab Image
# ─────────────────────────────────────────────
def _fig_to_rl_image(fig, width_cm=16, height_cm=7) -> Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight",
                facecolor=M_CARD, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_cm*cm, height=height_cm*cm)

# ─────────────────────────────────────────────
# CHART HELPERS (matplotlib, dark theme)
# ─────────────────────────────────────────────
def _mpl_setup(fig, axes=None):
    """Apply dark theme to a figure and optional axes list."""
    fig.patch.set_facecolor(M_CARD)
    for ax in (axes or []):
        ax.set_facecolor(M_CARD)
        ax.tick_params(colors=M_MUTED, labelsize=7)
        ax.spines[:].set_color(M_BORDER)
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)
        ax.xaxis.label.set_color(M_MUTED)
        ax.yaxis.label.set_color(M_MUTED)
        ax.title.set_color(M_TEXT)

def chart_gauge(value: float, label: str, color: str,
                w_cm=7, h_cm=5.5) -> Image:
    """Half-donut gauge chart."""
    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54),
                           subplot_kw=dict(aspect="equal"))
    fig.patch.set_facecolor(M_CARD)
    ax.set_facecolor(M_CARD)
    ax.axis("off")

    v    = max(0, min(100, float(value)))
    ang  = 180 * (v / 100)  # degrees filled

    # Background arc
    theta = np.linspace(0, np.pi, 200)
    ax.plot(np.cos(theta), np.sin(theta), color=M_BORDER, lw=10, solid_capstyle="round")
    # Zone arcs
    for lo, hi, c in [(0,.4,M_RED),(0.4,.7,M_YELLOW),(.7,1,M_GREEN)]:
        th = np.linspace(lo*np.pi, hi*np.pi, 100)
        ax.plot(np.cos(th), np.sin(th), color=c, lw=10, alpha=0.18, solid_capstyle="butt")
    # Value arc
    if v > 0:
        th_v = np.linspace(0, ang/180*np.pi, 200)
        ax.plot(np.cos(th_v), np.sin(th_v), color=color, lw=10, solid_capstyle="round")

    # Needle
    ang_r = ang / 180 * np.pi
    ax.annotate("", xy=(0.6*np.cos(ang_r), 0.6*np.sin(ang_r)),
                xytext=(0, 0),
                arrowprops=dict(arrowstyle="-|>", color=M_TEXT, lw=1.5))
    ax.add_patch(plt.Circle((0, 0), 0.08, color=M_TEXT, zorder=5))

    ax.text(0, -0.15, f"{v:.0f}", ha="center", va="center",
            fontsize=14, fontweight="bold", color=color)
    ax.text(0, -0.38, label, ha="center", va="center",
            fontsize=6.5, color=M_MUTED)
    ax.set_xlim(-1.2, 1.2); ax.set_ylim(-0.5, 1.2)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight",
                facecolor=M_CARD, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w_cm*cm, height=h_cm*cm)

def chart_radar(categories: list, values: list, color: str,
                title: str, w_cm=8, h_cm=7) -> Image:
    """Spider/radar chart."""
    N    = len(categories)
    angs = [n / N * 2 * np.pi for n in range(N)]
    angs += angs[:1]
    vals = [float(v)/100 for v in values] + [float(values[0])/100]

    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54),
                           subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(M_CARD)
    ax.set_facecolor(M_CARD)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(0)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["25","50","75","100"], color=M_MUTED, fontsize=5)
    ax.set_xticks(angs[:-1])
    ax.set_xticklabels(categories, color=M_TEXT, fontsize=6.5)
    ax.spines["polar"].set_color(M_BORDER)
    ax.grid(color=M_BORDER, linewidth=0.5)
    ax.plot(angs, vals, color=color, lw=2)
    ax.fill(angs, vals, color=color, alpha=0.15)
    ax.set_title(title, color=M_TEXT, fontsize=8, pad=12)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight",
                facecolor=M_CARD, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w_cm*cm, height=h_cm*cm)

def chart_hbar(labels: list, values: list, colors_list: list,
               title: str, w_cm=16, h_cm=6) -> Image:
    """Horizontal bar chart."""
    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    _mpl_setup(fig, [ax])
    y = range(len(labels))
    bars = ax.barh(list(y), values, color=colors_list, edgecolor="none",
                   height=0.55)
    # Value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height()/2,
                f"{val:.0f}", va="center", ha="left", color=M_TEXT, fontsize=7)
    ax.set_yticks(list(y)); ax.set_yticklabels(labels, color=M_TEXT, fontsize=7)
    ax.set_xlim(0, max(values)*1.18 if values else 110)
    ax.set_title(title, color=M_TEXT, fontsize=8, pad=8)
    ax.set_xlabel("Score", color=M_MUTED, fontsize=7)
    ax.invert_yaxis()
    ax.axvline(0, color=M_BORDER, lw=0.5)
    fig.tight_layout()
    return _fig_to_rl_image(fig, w_cm, h_cm)

def chart_prob_bar(probs: dict, w_cm=9, h_cm=4.5) -> Image:
    """Prediction probability bar chart."""
    labels = list(probs.keys())
    values = [v*100 for v in probs.values()]
    clr_map = {"High": M_GREEN, "Medium": M_YELLOW, "Low": M_RED}
    bar_colors = [clr_map.get(l, M_CYAN) for l in labels]

    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    _mpl_setup(fig, [ax])
    bars = ax.bar(labels, values, color=bar_colors, edgecolor="none", width=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{val:.1f}%", ha="center", va="bottom", color=M_TEXT, fontsize=8,
                fontweight="bold")
    ax.set_ylim(0, 115); ax.set_title("Prediction Confidence", color=M_TEXT, fontsize=8)
    ax.set_ylabel("Probability %", color=M_MUTED, fontsize=7)
    fig.tight_layout()
    return _fig_to_rl_image(fig, w_cm, h_cm)

def chart_perf_dist(pred_counts: dict, w_cm=7, h_cm=5) -> Image:
    """Donut chart for performance distribution."""
    labels = list(pred_counts.keys())
    sizes  = list(pred_counts.values())
    clr_map = {"High": M_GREEN, "Medium": M_YELLOW, "Low": M_RED}
    clrs   = [clr_map.get(l, M_CYAN) for l in labels]

    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    fig.patch.set_facecolor(M_CARD)
    ax.set_facecolor(M_CARD)
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%",
        colors=clrs, startangle=90,
        wedgeprops=dict(width=0.55, edgecolor=M_CARD),
        pctdistance=0.75,
    )
    for t in texts:      t.set_color(M_TEXT);  t.set_fontsize(7)
    for t in autotexts:  t.set_color(M_DARK);  t.set_fontsize(6.5); t.set_fontweight("bold")
    ax.set_title("Performance Distribution", color=M_TEXT, fontsize=8, pad=8)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight",
                facecolor=M_CARD, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w_cm*cm, height=h_cm*cm)

def chart_dept_bar(dept_data: pd.DataFrame, w_cm=16, h_cm=6) -> Image:
    """Stacked bar: department × performance."""
    if dept_data.empty:
        return Spacer(1, 1)
    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    _mpl_setup(fig, [ax])
    depts = dept_data["Department"].unique()
    x     = np.arange(len(depts))
    bottom = np.zeros(len(depts))
    for tier, color in [("High", M_GREEN), ("Medium", M_YELLOW), ("Low", M_RED)]:
        vals = [dept_data[(dept_data["Department"]==d) &
                          (dept_data["Prediction"]==tier)]["Count"].sum() for d in depts]
        ax.bar(x, vals, bottom=bottom, color=color, label=tier,
               edgecolor="none", width=0.6)
        bottom += np.array(vals, dtype=float)
    ax.set_xticks(x); ax.set_xticklabels(depts, color=M_TEXT, fontsize=6.5, rotation=20, ha="right")
    ax.set_title("Department Performance Distribution", color=M_TEXT, fontsize=8)
    ax.set_ylabel("Employees", color=M_MUTED, fontsize=7)
    ax.legend(fontsize=6.5, facecolor=M_CARD, edgecolor=M_BORDER,
              labelcolor=M_TEXT, loc="upper right")
    fig.tight_layout()
    return _fig_to_rl_image(fig, w_cm, h_cm)

def chart_scatter(df: pd.DataFrame, xcol: str, ycol: str,
                  title: str, w_cm=16, h_cm=6) -> Image:
    """Scatter plot coloured by Prediction."""
    clr_map = {"High": M_GREEN, "Medium": M_YELLOW, "Low": M_RED}
    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    _mpl_setup(fig, [ax])
    for tier, color in clr_map.items():
        sub = df[df["Prediction"]==tier]
        if sub.empty: continue
        ax.scatter(sub[xcol], sub[ycol], c=color, s=18, alpha=0.65,
                   edgecolors="none", label=tier)
    ax.set_xlabel(xcol, color=M_MUTED, fontsize=7)
    ax.set_ylabel(ycol, color=M_MUTED, fontsize=7)
    ax.set_title(title, color=M_TEXT, fontsize=8)
    ax.legend(fontsize=6.5, facecolor=M_CARD, edgecolor=M_BORDER, labelcolor=M_TEXT)
    fig.tight_layout()
    return _fig_to_rl_image(fig, w_cm, h_cm)

def chart_top10(df: pd.DataFrame, col: str, title: str,
                ascending=False, color=M_CYAN, w_cm=16, h_cm=5.5) -> Image:
    """Top/Bottom 10 horizontal bar chart."""
    sub = df.nlargest(10, col) if not ascending else df.nsmallest(10, col)
    sub = sub.head(10)
    if "EmployeeName" not in sub.columns:
        return Spacer(1, 1)
    labels = sub["EmployeeName"].tolist()
    values = sub[col].tolist()
    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    _mpl_setup(fig, [ax])
    clr_map = {"High": M_GREEN, "Medium": M_YELLOW, "Low": M_RED}
    bar_colors = [clr_map.get(p, color) for p in sub["Prediction"].tolist()] \
                  if "Prediction" in sub.columns else [color]*len(labels)
    bars = ax.barh(range(len(labels)), values, color=bar_colors, edgecolor="none", height=0.55)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2,
                f"{val:.0f}", va="center", ha="left", color=M_TEXT, fontsize=6.5)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, color=M_TEXT, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_title(title, color=M_TEXT, fontsize=8)
    ax.set_xlabel(col, color=M_MUTED, fontsize=7)
    fig.tight_layout()
    return _fig_to_rl_image(fig, w_cm, h_cm)

def chart_corr_heatmap(df: pd.DataFrame, cols: list, w_cm=16, h_cm=7) -> Image:
    """Correlation heatmap."""
    available = [c for c in cols if c in df.columns]
    if len(available) < 3:
        return Spacer(1, 1)
    corr = df[available].corr().round(2)
    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    _mpl_setup(fig, [ax])
    im = ax.imshow(corr.values, cmap="RdBu", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(available))); ax.set_xticklabels(available, rotation=30, ha="right",
                                                              color=M_TEXT, fontsize=6)
    ax.set_yticks(range(len(available))); ax.set_yticklabels(available, color=M_TEXT, fontsize=6)
    for i in range(len(available)):
        for j in range(len(available)):
            ax.text(j, i, f"{corr.values[i,j]:.2f}", ha="center", va="center",
                    color=M_DARK if abs(corr.values[i,j]) > 0.5 else M_TEXT, fontsize=5.5)
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04).ax.tick_params(labelcolor=M_MUTED, labelsize=6)
    ax.set_title("Correlation Matrix", color=M_TEXT, fontsize=8)
    fig.tight_layout()
    return _fig_to_rl_image(fig, w_cm, h_cm)

def chart_salary_hist(df: pd.DataFrame, w_cm=16, h_cm=5.5) -> Image:
    """Salary histogram by performance tier."""
    clr_map = {"High": M_GREEN, "Medium": M_YELLOW, "Low": M_RED}
    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    _mpl_setup(fig, [ax])
    for tier, color in clr_map.items():
        sub = df[df["Prediction"]==tier]["MonthlyIncome"].dropna()
        if sub.empty: continue
        ax.hist(sub, bins=20, alpha=0.6, color=color, label=tier, edgecolor="none")
    ax.set_xlabel("Monthly Income ($)", color=M_MUTED, fontsize=7)
    ax.set_ylabel("Employees", color=M_MUTED, fontsize=7)
    ax.set_title("Salary Distribution by Performance", color=M_TEXT, fontsize=8)
    ax.legend(fontsize=6.5, facecolor=M_CARD, edgecolor=M_BORDER, labelcolor=M_TEXT)
    fig.tight_layout()
    return _fig_to_rl_image(fig, w_cm, h_cm)

def chart_age_dist(df: pd.DataFrame, w_cm=8, h_cm=5) -> Image:
    """Age group distribution."""
    if "Age" not in df.columns: return Spacer(1,1)
    bins   = [20, 30, 40, 50, 65]
    labels = ["20-30","30-40","40-50","50+"]
    df2 = df.copy()
    df2["AgeGroup"] = pd.cut(df2["Age"], bins=bins, labels=labels, right=False)
    counts = df2["AgeGroup"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    _mpl_setup(fig, [ax])
    ax.bar(counts.index.astype(str), counts.values,
           color=[M_CYAN, M_VIOLET, M_ORANGE, M_GREEN], edgecolor="none", width=0.55)
    for i, v in enumerate(counts.values):
        ax.text(i, v+0.3, str(v), ha="center", va="bottom", color=M_TEXT, fontsize=7)
    ax.set_title("Age Distribution", color=M_TEXT, fontsize=8)
    ax.set_xlabel("Age Group", color=M_MUTED, fontsize=7)
    ax.set_ylabel("Employees", color=M_MUTED, fontsize=7)
    fig.tight_layout()
    return _fig_to_rl_image(fig, w_cm, h_cm)

def chart_gender_pie(df: pd.DataFrame, w_cm=7, h_cm=5) -> Image:
    """Gender distribution pie."""
    if "Gender" not in df.columns: return Spacer(1,1)
    counts = df["Gender"].value_counts()
    fig, ax = plt.subplots(figsize=(w_cm/2.54, h_cm/2.54))
    fig.patch.set_facecolor(M_CARD); ax.set_facecolor(M_CARD)
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=counts.index,
        autopct="%1.0f%%",
        colors=[M_CYAN, M_VIOLET, M_ORANGE, M_GREEN][:len(counts)],
        wedgeprops=dict(edgecolor=M_CARD),
        startangle=90,
    )
    for t in texts:     t.set_color(M_TEXT); t.set_fontsize(7)
    for t in autotexts: t.set_color(M_DARK); t.set_fontsize(6.5); t.set_fontweight("bold")
    ax.set_title("Gender Distribution", color=M_TEXT, fontsize=8)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight",
                facecolor=M_CARD, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=w_cm*cm, height=h_cm*cm)

def chart_attrition_gauge_bulk(pct: float, w_cm=7, h_cm=5) -> Image:
    """Single big gauge for attrition risk %."""
    return chart_gauge(pct, "Avg Attrition Risk %", M_RED, w_cm, h_cm)

# ─────────────────────────────────────────────
# TABLE BUILDER HELPERS
# ─────────────────────────────────────────────
def _kpi_table(kpi_items: list, st: dict, col_count=4) -> Table:
    """
    kpi_items: list of (value, label, color_hex) tuples
    Renders in a 2-row grid of col_count per row.
    """
    rows = []
    for i in range(0, len(kpi_items), col_count):
        chunk = kpi_items[i:i+col_count]
        while len(chunk) < col_count:
            chunk.append(("", "", M_MUTED))

        val_row = []
        lbl_row = []
        for val, lbl, clr in chunk:
            val_style = ParagraphStyle("kv", fontSize=18, textColor=colors.HexColor(clr),
                                       fontName="Helvetica-Bold", alignment=TA_CENTER, leading=22)
            lbl_style = ParagraphStyle("kl", fontSize=7, textColor=P_DARK_TEXT,
                                       fontName="Helvetica-Bold", alignment=TA_CENTER, leading=10)
            val_row.append(Paragraph(str(val), val_style))
            lbl_row.append(Paragraph(lbl.upper(), lbl_style))
        rows.append(val_row)
        rows.append(lbl_row)

    col_w = (PAGE_W - 2*MARGIN) / col_count
    tbl   = Table(rows, colWidths=[col_w]*col_count, repeatRows=0)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), P_CELL_BG),       # white background
        ("BOX",           (0,0), (-1,-1), 0.8, P_CYAN),     # cyan outer border
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#cbd5e1")),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ("RIGHTPADDING",  (0,0), (-1,-1), 4),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    return tbl

def _data_table(headers: list, rows_data: list, st: dict,
                col_widths=None) -> Table:
    """Styled data table with dark header."""
    header_row = [Paragraph(h, ParagraphStyle("th", fontSize=7.5, textColor=P_WHITE,
                                               fontName="Helvetica-Bold", alignment=TA_CENTER))
                  for h in headers]
    body_rows  = []
    for i, row in enumerate(rows_data):
        body_rows.append([
            Paragraph(str(cell), ParagraphStyle("td", fontSize=7, textColor=P_BLACK,
                                                 fontName="Helvetica", alignment=TA_CENTER,
                                                 leading=10))
            for cell in row
        ])

    all_rows = [header_row] + body_rows
    tbl = Table(all_rows, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND",    (0,0), (-1,0),   P_HDR_BG),       # navy header
        ("TEXTCOLOR",     (0,0), (-1,0),   P_WHITE),         # white header text
        ("FONTNAME",      (0,0), (-1,0),   "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0),   7.5),
        ("BACKGROUND",    (0,1), (-1,-1),  P_CELL_BG),       # white body
        ("TEXTCOLOR",     (0,1), (-1,-1),  P_BLACK),         # black body text
        ("TOPPADDING",    (0,0), (-1,-1),  5),
        ("BOTTOMPADDING", (0,0), (-1,-1),  5),
        ("LEFTPADDING",   (0,0), (-1,-1),  4),
        ("RIGHTPADDING",  (0,0), (-1,-1),  4),
        ("GRID",          (0,0), (-1,-1),  0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN",        (0,0), (-1,-1),  "MIDDLE"),
        ("ROWBACKGROUND", (0,1), (-1,-1),  [P_ROW_ODD, P_ROW_EVEN]),  # white / light-gray
    ]
    # Conditional colour for Prediction column
    for i, row in enumerate(rows_data, 1):
        for j, cell in enumerate(row):
            cell_s = str(cell)
            if cell_s == "High":
                style.append(("TEXTCOLOR",(j,i),(j,i), P_GREEN))
                style.append(("FONTNAME", (j,i),(j,i), "Helvetica-Bold"))
            elif cell_s == "Medium":
                style.append(("TEXTCOLOR",(j,i),(j,i), P_YELLOW))
                style.append(("FONTNAME", (j,i),(j,i), "Helvetica-Bold"))
            elif cell_s == "Low":
                style.append(("TEXTCOLOR",(j,i),(j,i), P_RED))
                style.append(("FONTNAME", (j,i),(j,i), "Helvetica-Bold"))
    tbl.setStyle(TableStyle(style))
    return tbl

def _rec_block(items: list, bg_hex: str, border_hex: str, st: dict) -> Table:
    """Render a list of recommendation items as a styled block."""
    rows = []
    for item in items:
        text = item.get("text","")
        rows.append([
            Paragraph(f"• {text}",
                      ParagraphStyle("ri", fontSize=8, textColor=P_BLACK,
                                     fontName="Helvetica", leading=12, spaceAfter=2,
                                     leftIndent=4))
        ])
    if not rows:
        return Spacer(1, 0.1*cm)
    tbl = Table(rows, colWidths=[PAGE_W - 2*MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor(bg_hex)),
        ("LEFTPADDING",  (0,0),(-1,-1), 10),
        ("RIGHTPADDING", (0,0),(-1,-1), 10),
        ("TOPPADDING",   (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LINEAFTER",    (0,0),(0,-1),  2, colors.HexColor(border_hex)),
        ("BOX",          (0,0),(-1,-1), 0.3, P_BORDER),
        ("ROWBACKGROUND",(0,0),(-1,-1), [colors.HexColor(bg_hex)]),
    ]))
    return tbl

# ─────────────────────────────────────────────
# COVER PAGE BUILDER
# ─────────────────────────────────────────────
def _cover_page(title: str, subtitle: str, name: str, extra_lines: list, st: dict) -> list:
    elems = []
    elems.append(Spacer(1, 3*cm))

    # Main title
    elems.append(Paragraph("⚡ PulseIQ", ParagraphStyle("ct",
        fontSize=36, textColor=P_CYAN, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4)))
    elems.append(Paragraph("HR Intelligence Platform",
        ParagraphStyle("cs", fontSize=13, textColor=P_MUTED,
                       fontName="Helvetica", alignment=TA_CENTER, spaceAfter=24)))

    # Divider
    elems.append(HRFlowable(width="60%", thickness=1.5, color=P_CYAN,
                             spaceAfter=20, spaceBefore=0, hAlign="CENTER"))

    elems.append(Paragraph(title, ParagraphStyle("rpt",
        fontSize=22, textColor=P_TEXT, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=8, leading=26)))
    elems.append(Paragraph(subtitle, ParagraphStyle("rps",
        fontSize=11, textColor=P_MUTED, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=30)))

    # Employee / report name box
    box_data = [[Paragraph(name, ParagraphStyle("bn",
        fontSize=16, textColor=P_CYAN, fontName="Helvetica-Bold",
        alignment=TA_CENTER, leading=20))]]
    for line in extra_lines:
        box_data.append([Paragraph(line, ParagraphStyle("bl",
            fontSize=9, textColor=P_MUTED, fontName="Helvetica",
            alignment=TA_CENTER, spaceAfter=2))])
    box_tbl = Table(box_data, colWidths=[PAGE_W - 4*cm])
    box_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), P_CELL_BG),
        ("BOX",        (0,0),(-1,-1), 2, P_CYAN),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
    ]))
    elems.append(box_tbl)
    elems.append(Spacer(1, 2*cm))

    elems.append(Paragraph(
        f"Report Generated: {datetime.now().strftime('%d %B %Y · %H:%M')}",
        ParagraphStyle("rd", fontSize=9, textColor=P_MUTED, fontName="Helvetica",
                       alignment=TA_CENTER)))
    elems.append(Paragraph(
        "CONFIDENTIAL — Authorised HR Personnel Only",
        ParagraphStyle("rc", fontSize=8, textColor=P_RED, fontName="Helvetica-Bold",
                       alignment=TA_CENTER, spaceBefore=6)))
    elems.append(PageBreak())
    return elems

# ═══════════════════════════════════════════════════════════════════
#  SINGLE EMPLOYEE PDF GENERATOR
# ═══════════════════════════════════════════════════════════════════
def generate_single_pdf(
    emp_info:  dict,   # name, emp_id, dept, role, education, gender, marital,
                        # age, income, tenure, yrs_role, yrs_promo, tot_exp,
                        # travel, overtime, dist, wlb, job_inv, work_env,
                        # inno, lead, comm, team, training, projects, perf_rating,
                        # sat, env_sat, rel_sat, att, mgr_rating
    scores:    dict,   # output of compute_scores()
    probs:     dict,   # {"High":0.7, "Medium":0.2, "Low":0.1}
    recs:      dict,   # output of generate_recommendations()
    pred:      str,    # "High" | "Medium" | "Low"
) -> bytes:

    buf = io.BytesIO()
    st  = _styles()
    pred_color = {"High": M_GREEN, "Medium": M_YELLOW, "Low": M_RED}.get(pred, M_CYAN)
    pred_rl    = {"High": P_GREEN,  "Medium": P_YELLOW,  "Low": P_RED }.get(pred, P_CYAN)

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.8*cm, bottomMargin=1.8*cm,
        title=f"HR Intelligence Report — {emp_info.get('name','Employee')}",
        author="PulseIQ HR Platform",
        subject="Employee Performance Report",
    )

    tmpl = _PageTemplate(
        f"Intelligence Report · {emp_info.get('name','')}",
        emp_info.get("name",""),
    )

    # ── Collect story ──────────────────────────────────────────────
    story = []

    # ── COVER PAGE ──
    story += _cover_page(
        "Employee Intelligence Report",
        "AI-Powered Performance & Career Analytics",
        emp_info.get("name", "Employee"),
        [
            f"Employee ID: {emp_info.get('emp_id','-')}   ·   "
            f"Department: {emp_info.get('dept','-')}   ·   "
            f"Role: {emp_info.get('role','-')}",
            f"AI Prediction: {pred} Performer   ·   "
            f"Confidence: {max(probs.values())*100:.1f}%   ·   "
            f"Overall HR Score: {scores['hr_score']:.0f}/100",
        ], st,
    )

    # ── SECTION 1: PREDICTION RESULT ──────────────────────────────
    story.append(Paragraph("01 · AI Prediction Result", st["section"]))
    story.append(_divider(P_CYAN))

    # Prediction box
    pred_style = ParagraphStyle("predv", fontSize=42, fontName="Helvetica-Bold",
                                 alignment=TA_CENTER, textColor=pred_rl, leading=48)
    sub_style  = ParagraphStyle("preds", fontSize=11, fontName="Helvetica",
                                 alignment=TA_CENTER, textColor=P_DARK_TEXT, leading=14)
    pred_tbl = Table([
        [Paragraph(f"{pred.upper()} PERFORMER", pred_style)],
        [Paragraph(f"Prediction Confidence: {max(probs.values())*100:.1f}%", sub_style)],
        [Paragraph(f"Overall HR Score: {scores['hr_score']:.0f} / 100", sub_style)],
    ], colWidths=[PAGE_W - 2*MARGIN])
    pred_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), P_CELL_BG),
        ("BOX",        (0,0),(-1,-1), 2, pred_rl),
        ("TOPPADDING",    (0,0),(-1,-1), 16),
        ("BOTTOMPADDING", (0,0),(-1,-1), 16),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
    ]))
    story.append(pred_tbl)
    story.append(Spacer(1, 0.4*cm))

    # ── EXECUTIVE SUMMARY ──
    story.append(Paragraph("Executive Summary", st["subsection"]))
    for item in recs.get("executive", []):
        story.append(Paragraph(item["text"], st["exec_summary"]))
    story.append(Spacer(1, 0.3*cm))

    # ── KPI SCORECARD ──
    story.append(Paragraph("Intelligence Scorecard", st["subsection"]))
    kpi_items = [
        (f"{scores['health']:.0f}",      "Health Score",        M_GREEN),
        (f"{scores['risk']:.0f}",         "Attrition Risk",      M_RED),
        (f"{scores['growth']:.0f}",       "Growth Score",        M_CYAN),
        (f"{scores['promo_ready']:.0f}",  "Promo Readiness",     M_VIOLET),
        (f"{scores['retention']:.0f}",    "Retention Prob",      M_GREEN),
        (f"{scores['productivity']:.0f}", "Productivity",        M_CYAN),
        (f"{scores['engagement']:.0f}",   "Engagement",          M_VIOLET),
        (f"{scores['soft_skills']:.0f}",  "Soft Skills",         M_ORANGE),
    ]
    story.append(_kpi_table(kpi_items, st, col_count=4))
    story.append(Spacer(1, 0.4*cm))

    # ── PROBABILITY CHART + GAUGES side-by-side ──
    g1 = chart_gauge(scores["health"],      "Health",       M_GREEN,  w_cm=4.2, h_cm=4.2)
    g2 = chart_gauge(scores["risk"],        "Attrition",    M_RED,    w_cm=4.2, h_cm=4.2)
    g3 = chart_gauge(scores["promo_ready"],"Promo Ready",  M_VIOLET, w_cm=4.2, h_cm=4.2)
    g4 = chart_gauge(scores["retention"],   "Retention",    M_CYAN,   w_cm=4.2, h_cm=4.2)
    gauge_tbl = Table([[g1, g2, g3, g4]],
                      colWidths=[(PAGE_W-2*MARGIN)/4]*4)
    gauge_tbl.setStyle(TableStyle([
        ("VALIGN",  (0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",   (0,0),(-1,-1),"CENTER"),
        ("LEFTPADDING",  (0,0),(-1,-1), 2),
        ("RIGHTPADDING", (0,0),(-1,-1), 2),
    ]))
    story.append(gauge_tbl)
    story.append(Spacer(1, 0.3*cm))

    # Prob bar chart
    story.append(chart_prob_bar(probs, w_cm=PAGE_W/cm - 2*MARGIN/cm, h_cm=4.5))
    story.append(Spacer(1, 0.3*cm))

    # ── SECTION 2: EMPLOYEE DETAILS ───────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("02 · Employee Profile", st["section"]))
    story.append(_divider(P_CYAN))

    # Personal Info table
    pi_data = [
        ["Full Name",       emp_info.get("name","-"),
         "Employee ID",     emp_info.get("emp_id","-")],
        ["Age",             str(emp_info.get("age","-")),
         "Gender",          emp_info.get("gender","-")],
        ["Department",      emp_info.get("dept","-"),
         "Job Role",        emp_info.get("role","-")],
        ["Education",       emp_info.get("education","-"),
         "Marital Status",  emp_info.get("marital","-")],
        ["Business Travel", emp_info.get("travel","-"),
         "Overtime",        "Yes" if emp_info.get("overtime") else "No"],
        ["Distance (km)",   str(emp_info.get("dist","-")),
         "Total Experience",f"{emp_info.get('tot_exp','-')} yrs"],
    ]
    lbl_style = ParagraphStyle("pl", fontSize=7.5, textColor=P_DARK_TEXT,
                                fontName="Helvetica-Bold")
    val_style = ParagraphStyle("pv", fontSize=8.5, textColor=P_BLACK,
                                fontName="Helvetica")
    pi_rows = [[Paragraph(r[0],lbl_style), Paragraph(r[1],val_style),
                Paragraph(r[2],lbl_style), Paragraph(r[3],val_style)]
               for r in pi_data]
    cw = (PAGE_W-2*MARGIN)/4
    pi_tbl = Table(pi_rows, colWidths=[cw*0.9, cw*1.1, cw*0.9, cw*1.1])
    pi_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), P_CELL_BG),
        ("BACKGROUND",    (0,0),(0,-1),  P_ACCENT_BG),
        ("BACKGROUND",    (2,0),(2,-1),  P_ACCENT_BG),
        ("TEXTCOLOR",     (0,0),(-1,-1), P_BLACK),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#cbd5e1")),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(pi_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Job Info + Performance Metrics table
    story.append(Paragraph("Job & Performance Data", st["subsection"]))
    jm_data = [
        ["Monthly Income",    f"${emp_info.get('income',0):,}",
         "Years at Company",  str(emp_info.get("tenure","-"))],
        ["Yrs in Current Role", str(emp_info.get("yrs_role","-")),
         "Yrs Since Promo",   str(emp_info.get("yrs_promo","-"))],
        ["Training Hours/yr", str(emp_info.get("training","-")),
         "No. of Projects",   str(emp_info.get("projects","-"))],
        ["Job Satisfaction",  f"{emp_info.get('sat','-')}/4",
         "Env Satisfaction",  f"{emp_info.get('env_sat','-')}/4"],
        ["Relationship Sat.", f"{emp_info.get('rel_sat','-')}/4",
         "Work-Life Balance", f"{emp_info.get('wlb','-')}/4"],
        ["Attendance Rate",   f"{emp_info.get('att','-')}%",
         "Manager Rating",    f"{emp_info.get('mgr_rating','-')}/5"],
        ["Job Involvement",   f"{emp_info.get('job_inv','-')}/4",
         "Perf. Self-Rating", f"{emp_info.get('perf_rating','-')}/4"],
    ]
    jm_rows = [[Paragraph(r[0],lbl_style), Paragraph(r[1],val_style),
                Paragraph(r[2],lbl_style), Paragraph(r[3],val_style)]
               for r in jm_data]
    jm_tbl = Table(jm_rows, colWidths=[cw*0.9, cw*1.1, cw*0.9, cw*1.1])
    jm_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), P_CELL_BG),
        ("BACKGROUND",    (0,0),(0,-1),  P_ACCENT_BG),
        ("BACKGROUND",    (2,0),(2,-1),  P_ACCENT_BG),
        ("TEXTCOLOR",     (0,0),(-1,-1), P_BLACK),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#cbd5e1")),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(jm_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Behavioural scores
    story.append(Paragraph("Behavioural Assessment", st["subsection"]))
    beh_data = [
        ["Innovation Score", f"{emp_info.get('inno','-')}/100",
         "Leadership Score", f"{emp_info.get('lead','-')}/100"],
        ["Communication",    f"{emp_info.get('comm','-')}/100",
         "Team Collab.",     f"{emp_info.get('team','-')}/100"],
        ["Work Env Score",   f"{emp_info.get('work_env','-')}/100",
         "",                 ""],
    ]
    bh_rows = [[Paragraph(r[0],lbl_style), Paragraph(r[1],val_style),
                Paragraph(r[2],lbl_style), Paragraph(r[3],val_style)]
               for r in beh_data]
    bh_tbl = Table(bh_rows, colWidths=[cw*0.9, cw*1.1, cw*0.9, cw*1.1])
    bh_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), P_CELL_BG),
        ("BACKGROUND",    (0,0),(0,-1),  P_ACCENT_BG),
        ("BACKGROUND",    (2,0),(2,-1),  P_ACCENT_BG),
        ("TEXTCOLOR",     (0,0),(-1,-1), P_BLACK),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#cbd5e1")),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(bh_tbl)

    # ── SECTION 3: VISUALISATIONS ─────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("03 · Performance Visualisations", st["section"]))
    story.append(_divider(P_CYAN))

    # Radar charts side by side
    story.append(Paragraph("Performance Radar & Soft Skills Spider", st["subsection"]))
    r1 = chart_radar(
        ["Performance","Health","Retention","Productivity","Engagement","Soft Skills"],
        [scores["performance"], scores["health"], scores["retention"],
         scores["productivity"], scores["engagement"], scores["soft_skills"]],
        M_CYAN, "Performance Radar", w_cm=8.5, h_cm=7,
    )
    r2 = chart_radar(
        ["Innovation","Leadership","Communication","Team Collab","Job Involvement","Work-Life Balance"],
        [emp_info.get("inno",50), emp_info.get("lead",50),
         emp_info.get("comm",50), emp_info.get("team",50),
         emp_info.get("job_inv",3)*25, emp_info.get("wlb",3)*25],
        M_VIOLET, "Soft Skills Spider", w_cm=8.5, h_cm=7,
    )
    radar_tbl = Table([[r1, r2]], colWidths=[(PAGE_W-2*MARGIN)/2]*2)
    radar_tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN", (0,0),(-1,-1),"CENTER"),
        ("LEFTPADDING",(0,0),(-1,-1),2),
        ("RIGHTPADDING",(0,0),(-1,-1),2),
    ]))
    story.append(radar_tbl)
    story.append(Spacer(1, 0.3*cm))

    # Score breakdown horizontal bar
    story.append(Paragraph("Score Breakdown", st["subsection"]))
    score_labels = ["HR Score","Performance","Health","Retention",
                    "Productivity","Engagement","Growth","Risk"]
    score_values = [float(scores["hr_score"]), float(scores["performance"]),
                    float(scores["health"]),    float(scores["retention"]),
                    float(scores["productivity"]),float(scores["engagement"]),
                    float(scores["growth"]),    float(scores["risk"])]
    score_colors = [M_CYAN, M_GREEN, M_VIOLET, M_GREEN,
                    M_CYAN, M_VIOLET, M_ORANGE, M_RED]
    story.append(chart_hbar(score_labels, score_values, score_colors,
                             "All Intelligence Scores (0–100)", w_cm=16, h_cm=5.5))
    story.append(Spacer(1, 0.3*cm))

    # Waterfall chart for HR score
    story.append(Paragraph("HR Score Decomposition", st["subsection"]))
    wf_labels = ["Base","Attendance","Satisfaction","Manager","Experience","Soft Skills","HR Score"]
    wf_values = [40,
                 (scores["productivity"]-50)*0.15,
                 (scores["health"]-50)*0.12,
                 (scores["growth"]-50)*0.10,
                 (scores["retention"]-50)*0.10,
                 (scores["soft_skills"]-50)*0.08,
                 float(scores["hr_score"])]

    fig, ax = plt.subplots(figsize=(16/2.54, 5/2.54))
    _mpl_setup(fig, [ax])
    running = 40.0
    bottoms = [0]
    bar_vals = [40]
    bar_cols = [M_CYAN]
    for v in wf_values[1:-1]:
        bottoms.append(running if v >= 0 else running + v)
        bar_vals.append(abs(v))
        bar_cols.append(M_GREEN if v >= 0 else M_RED)
        running += v
    bottoms.append(0)
    bar_vals.append(float(scores["hr_score"]))
    bar_cols.append(M_VIOLET)

    for i, (lbl, btm, bval, col) in enumerate(zip(wf_labels, bottoms, bar_vals, bar_cols)):
        ax.bar(i, bval, bottom=btm, color=col, edgecolor="none", width=0.55)
        ax.text(i, btm + bval + 0.5, f"{bval:.1f}", ha="center", va="bottom",
                color=M_TEXT, fontsize=6.5)
        # connector lines
        if 0 < i < len(wf_labels)-1:
            ax.plot([i-0.27, i+0.27], [btm+bval, btm+bval], color=M_BORDER, lw=0.7)

    ax.set_xticks(range(len(wf_labels)))
    ax.set_xticklabels(wf_labels, color=M_TEXT, fontsize=6.5)
    ax.set_title("HR Score Waterfall Decomposition", color=M_TEXT, fontsize=8)
    ax.set_ylabel("Score", color=M_MUTED, fontsize=7)
    story.append(_fig_to_rl_image(fig, 16, 5))

    # ── SECTION 4: RECOMMENDATIONS ────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("04 · AI Recommendation Engine", st["section"]))
    story.append(_divider(P_CYAN))

    rec_sections = [
        ("strengths",  "Strengths",              "#f0fdf4", "#22c55e"),
        ("weaknesses", "Weaknesses & Risk Areas", "#fef2f2", "#ef4444"),
        ("career",     "Career Growth Plan",      "#eff6ff", "#a855f7"),
        ("training",   "Training Roadmap",        "#ecfeff","#00e5ff"),
        ("salary",     "Compensation Review",     "#fff7ed", "#f97316"),
        ("leadership", "Leadership Development",  "#faf5ff", "#a855f7"),
        ("wellness",   "Employee Wellness",       "#f0fdf4", "#22c55e"),
        ("attrition",  "Attrition Prevention",    "#fef2f2", "#ef4444"),
        ("action",     "Action Items",            "#eff6ff", "#00e5ff"),
    ]
    for key, title, bg, border in rec_sections:
        items = recs.get(key, [])
        if not items:
            continue
        story.append(Paragraph(title, st["subsection"]))
        story.append(_rec_block(items, bg.strip(), border, st))
        story.append(Spacer(1, 0.15*cm))

    # ── SECTION 5: KPI SUMMARY TABLE ──────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("05 · KPI Summary Table", st["section"]))
    story.append(_divider(P_CYAN))

    kpi_headers = ["KPI Metric", "Score", "Benchmark", "Status"]
    benchmarks  = {"HR Score":70, "Health Score":65, "Risk Score":40,
                   "Growth Score":60, "Promo Readiness":60, "Retention Prob":65,
                   "Productivity":65, "Engagement":65, "Soft Skills":60}
    kpi_rows_data = []
    kpi_mapping = [
        ("HR Score",       scores["hr_score"]),
        ("Health Score",   scores["health"]),
        ("Risk Score",     scores["risk"]),
        ("Growth Score",   scores["growth"]),
        ("Promo Readiness",scores["promo_ready"]),
        ("Retention Prob", scores["retention"]),
        ("Productivity",   scores["productivity"]),
        ("Engagement",     scores["engagement"]),
        ("Soft Skills",    scores["soft_skills"]),
    ]
    for metric, val in kpi_mapping:
        bench    = benchmarks.get(metric, 60)
        above    = float(val) >= bench
        status   = "Above" if above else "Below"
        kpi_rows_data.append([metric, f"{float(val):.0f}/100",
                               f"{bench}/100", status])
    cw_kpi = [(PAGE_W-2*MARGIN)/4] * 4
    story.append(_data_table(kpi_headers, kpi_rows_data, st, col_widths=cw_kpi))
    story.append(Spacer(1, 0.5*cm))

    # Benchmark context note
    story.append(Paragraph(
        "Note: Benchmark values represent company-average thresholds derived from "
        "historical HR data. Scores above benchmark indicate above-average performance "
        "in that dimension. Risk Score is inverse — lower is better.",
        st["small"]))

    # Build PDF
    doc.build(story, onFirstPage=tmpl, onLaterPages=tmpl)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════
#  BULK ENTERPRISE PDF GENERATOR
# ═══════════════════════════════════════════════════════════════════
def generate_bulk_pdf(
    df:        pd.DataFrame,
    insights:  list,           # list of str from bulk_generate_insights()
    dept_recs: dict,           # dict from bulk_recommendations_by_dept()
    kpi_dict:  dict,           # n_emp,n_hi,n_med,n_low,n_pr,n_ar,avg_sal,avg_sat,avg_att,avg_exp
) -> bytes:

    buf = io.BytesIO()
    st  = _styles()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=2.8*cm, bottomMargin=1.8*cm,
        title="Enterprise HR Analytics Report",
        author="PulseIQ HR Platform",
        subject="Bulk Employee Performance Report",
    )
    tmpl = _PageTemplate("Enterprise HR Analytics Report")

    story = []

    # ── COVER ──
    story += _cover_page(
        "Enterprise HR Analytics Report",
        "Bulk Employee Performance Intelligence",
        f"Workforce Analysis · {kpi_dict.get('n_emp',len(df)):,} Employees",
        [
            f"High Performers: {kpi_dict.get('n_hi',0):,}   ·   "
            f"Promotion Ready: {kpi_dict.get('n_pr',0):,}   ·   "
            f"High Attrition Risk: {kpi_dict.get('n_ar',0):,}",
            f"Avg Salary: ${kpi_dict.get('avg_sal',0):,.0f}/mo   ·   "
            f"Avg Satisfaction: {kpi_dict.get('avg_sat',0):.2f}/4   ·   "
            f"Avg Attendance: {kpi_dict.get('avg_att',0):.1f}%",
        ], st,
    )

    # ── SECTION 1: ENTERPRISE KPIs ─────────────────────────────────
    story.append(Paragraph("01 · Enterprise KPI Dashboard", st["section"]))
    story.append(_divider(P_CYAN))

    kpi_items = [
        (f"{kpi_dict.get('n_emp',len(df)):,}",       "Total Employees",    M_CYAN),
        (f"{kpi_dict.get('n_hi',0):,}",              "High Performers",    M_GREEN),
        (f"{kpi_dict.get('n_med',0):,}",             "Mid Performers",     M_YELLOW),
        (f"{kpi_dict.get('n_low',0):,}",             "Low Performers",     M_RED),
        (f"{kpi_dict.get('n_pr',0):,}",              "Promotion Ready",    M_VIOLET),
        (f"{kpi_dict.get('n_ar',0):,}",              "High Attrition Risk",M_RED),
        (f"${kpi_dict.get('avg_sal',0):,.0f}",       "Avg Monthly Salary", M_ORANGE),
        (f"{kpi_dict.get('avg_sat',0):.2f}/4",       "Avg Satisfaction",   M_CYAN),
        (f"{kpi_dict.get('avg_att',0):.1f}%",        "Avg Attendance",     M_GREEN),
        (f"{kpi_dict.get('avg_exp',0):.1f} yrs",     "Avg Experience",     M_VIOLET),
    ]
    story.append(_kpi_table(kpi_items, st, col_count=5))
    story.append(Spacer(1, 0.4*cm))

    # ── SECTION 2: PERFORMANCE VISUALISATIONS ─────────────────────
    story.append(Paragraph("02 · Performance Distribution Analytics", st["section"]))
    story.append(_divider(P_CYAN))

    # Donut + dept bar side by side
    pred_counts = df["Prediction"].value_counts().to_dict()
    donut = chart_perf_dist(pred_counts, w_cm=7.5, h_cm=5.5)

    dept_pred = df.groupby(["Department","Prediction"]).size().reset_index(name="Count")
    dept_bar  = chart_dept_bar(dept_pred, w_cm=9, h_cm=5.5)

    row1 = Table([[donut, dept_bar]],
                 colWidths=[(PAGE_W-2*MARGIN)*0.42, (PAGE_W-2*MARGIN)*0.58])
    row1.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN", (0,0),(-1,-1),"CENTER"),
        ("LEFTPADDING",(0,0),(-1,-1),2),
        ("RIGHTPADDING",(0,0),(-1,-1),2),
    ]))
    story.append(row1)
    story.append(Spacer(1, 0.3*cm))

    # Salary distribution
    story.append(Paragraph("Salary Distribution by Performance", st["subsection"]))
    story.append(chart_salary_hist(df, w_cm=16, h_cm=5))
    story.append(Spacer(1, 0.3*cm))

    # Scatter: experience vs income
    story.append(Paragraph("Experience vs. Monthly Income", st["subsection"]))
    story.append(chart_scatter(df, "YearsAtCompany", "MonthlyIncome",
                               "Experience vs. Income (coloured by Performance Tier)",
                               w_cm=16, h_cm=5.5))
    story.append(Spacer(1, 0.3*cm))

    # Age dist + Gender pie side by side
    age_img    = chart_age_dist(df, w_cm=8.5, h_cm=5)
    gender_img = chart_gender_pie(df, w_cm=7, h_cm=5)
    ag_tbl = Table([[age_img, gender_img]],
                   colWidths=[(PAGE_W-2*MARGIN)*0.55, (PAGE_W-2*MARGIN)*0.45])
    ag_tbl.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                                 ("ALIGN", (0,0),(-1,-1),"CENTER"),
                                 ("LEFTPADDING",(0,0),(-1,-1),2),
                                 ("RIGHTPADDING",(0,0),(-1,-1),2)]))
    story.append(ag_tbl)

    # ── SECTION 3: ATTRITION & PROMOTION ──────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("03 · Attrition Risk & Promotion Pipeline", st["section"]))
    story.append(_divider(P_CYAN))

    avg_risk = float(df["AttritionRisk"].mean()) if "AttritionRisk" in df.columns else 30.0
    avg_promo= float(df["PromotionReadiness"].mean()) if "PromotionReadiness" in df.columns else 50.0
    g_risk   = chart_gauge(avg_risk,  "Avg Attrition Risk",    M_RED,    w_cm=6.5, h_cm=5.5)
    g_promo  = chart_gauge(avg_promo, "Avg Promo Readiness",   M_VIOLET, w_cm=6.5, h_cm=5.5)
    g_sat    = chart_gauge(float(df["SatisfactionScore"].mean()*25) if "SatisfactionScore" in df.columns else 50,
                           "Avg Satisfaction",  M_GREEN,  w_cm=6.5, h_cm=5.5)
    gauge2_tbl = Table([[g_risk, g_promo, g_sat]],
                       colWidths=[(PAGE_W-2*MARGIN)/3]*3)
    gauge2_tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN", (0,0),(-1,-1),"CENTER"),
        ("LEFTPADDING",(0,0),(-1,-1),2),
        ("RIGHTPADDING",(0,0),(-1,-1),2),
    ]))
    story.append(gauge2_tbl)
    story.append(Spacer(1, 0.3*cm))

    # Scatter: attrition vs promotion
    if "AttritionRisk" in df.columns and "PromotionReadiness" in df.columns:
        story.append(Paragraph("HR Matrix: Attrition Risk vs Promotion Readiness", st["subsection"]))
        story.append(chart_scatter(df, "AttritionRisk", "PromotionReadiness",
                                   "Attrition Risk vs Promotion Readiness",
                                   w_cm=16, h_cm=5.5))
        story.append(Spacer(1, 0.3*cm))

    # ── SECTION 4: TOP & BOTTOM PERFORMERS ────────────────────────
    story.append(Paragraph("04 · Top & Bottom Performers", st["section"]))
    story.append(_divider(P_CYAN))

    if "OverallScore" in df.columns:
        t10 = chart_top10(df, "OverallScore", "Top 10 Performers — Overall Score",
                          ascending=False, color=M_GREEN, w_cm=16, h_cm=5.5)
        b10 = chart_top10(df, "OverallScore", "Bottom 10 — Needs Attention",
                          ascending=True, color=M_RED, w_cm=16, h_cm=5.5)
        story.append(t10)
        story.append(Spacer(1, 0.3*cm))
        story.append(b10)
        story.append(Spacer(1, 0.3*cm))

    # ── SECTION 5: CORRELATION MATRIX ─────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("05 · Statistical Correlation Matrix", st["section"]))
    story.append(_divider(P_CYAN))
    corr_cols = ["MonthlyIncome","SatisfactionScore","AttendanceRate",
                 "PromotionReadiness","AttritionRisk","OverallScore",
                 "YearsAtCompany","Age"]
    story.append(chart_corr_heatmap(df, corr_cols, w_cm=16, h_cm=7.5))
    story.append(Spacer(1, 0.3*cm))

    # ── SECTION 6: AI INSIGHTS ─────────────────────────────────────
    story.append(Paragraph("06 · AI-Generated Workforce Insights", st["section"]))
    story.append(_divider(P_CYAN))

    for i, ins in enumerate(insights, 1):
        # Strip markdown bold markers for PDF
        clean = ins.replace("**", "")
        story.append(Paragraph(
            f"<b>{i:02d}.</b> {clean}",
            ParagraphStyle("ins", fontSize=8.5, textColor=P_BLACK,
                           fontName="Helvetica", leading=13,
                           spaceAfter=5, leftIndent=6,
                           borderPad=4)
        ))
    story.append(Spacer(1, 0.3*cm))

    # ── SECTION 7: DEPARTMENT RECOMMENDATIONS ─────────────────────
    story.append(PageBreak())
    story.append(Paragraph("07 · Department-Wise HR Recommendations", st["section"]))
    story.append(_divider(P_CYAN))

    for dept_name, drecs in dept_recs.items():
        story.append(Paragraph(f"🏢  {dept_name}", st["subsection"]))
        for rec in drecs:
            clean_rec = rec.replace("**","")
            story.append(Paragraph(
                f"• {clean_rec}",
                ParagraphStyle("dr", fontSize=8, textColor=P_BLACK,
                               fontName="Helvetica", leading=12, spaceAfter=3,
                               leftIndent=10)
            ))
        story.append(Spacer(1, 0.15*cm))
        story.append(_divider(P_BORDER, 0.3))

    # ── SECTION 8: EMPLOYEE LEADERBOARD TABLE ─────────────────────
    story.append(PageBreak())
    story.append(Paragraph("08 · Employee Leaderboard", st["section"]))
    story.append(_divider(P_CYAN))

    show_cols = ["EmployeeName","Department","Prediction","OverallScore",
                 "AttritionRisk","PromotionReadiness","MonthlyIncome",
                 "SatisfactionScore","AttendanceRate"]
    show_cols = [c for c in show_cols if c in df.columns]
    headers   = [c.replace("EmployeeName","Name").replace("MonthlyIncome","Income ($)")
                  .replace("SatisfactionScore","Satisf.").replace("AttendanceRate","Attend.%")
                  .replace("PromotionReadiness","Promo")
                  .replace("AttritionRisk","AtrRisk")
                  for c in show_cols]

    # Show top 50 sorted by OverallScore
    sort_col = "OverallScore" if "OverallScore" in df.columns else show_cols[0]
    top50    = df.sort_values(sort_col, ascending=False).head(50)
    tbl_data = []
    for _, row in top50.iterrows():
        tbl_data.append([
            str(row[c])[:18] if isinstance(row[c], str) else
            (f"${row[c]:,.0f}" if c == "MonthlyIncome" else f"{float(row[c]):.1f}")
            for c in show_cols
        ])

    total_w = PAGE_W - 2*MARGIN
    col_ratios = {"EmployeeName":1.6,"Department":1.3,"Prediction":0.9,
                  "OverallScore":0.7,"AttritionRisk":0.7,"PromotionReadiness":0.7,
                  "MonthlyIncome":0.9,"SatisfactionScore":0.7,"AttendanceRate":0.7}
    raw_ws = [col_ratios.get(c, 1.0) for c in show_cols]
    ws_sum = sum(raw_ws)
    col_ws = [total_w * w / ws_sum for w in raw_ws]

    story.append(_data_table(headers, tbl_data, st, col_widths=col_ws))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        f"Showing top 50 of {len(df):,} employees sorted by Overall Score. "
        "Download the Excel report for the full dataset.",
        st["small"]))

    # Build PDF
    doc.build(story, onFirstPage=tmpl, onLaterPages=tmpl)
    return buf.getvalue()