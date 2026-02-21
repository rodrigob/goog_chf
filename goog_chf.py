
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="GOOG & CHF Tracker", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    </style>
""", unsafe_allow_html=True)

st.title("GOOG & CHF dashboard")

timeframe = st.radio(
    "Select Time Range:",
    options=["1 Week", "1 Month", "1 Year", "10 Years"],
    index=1,
    horizontal=True
)

# ─── Data loading ─────────────────────────────────────────────────────────────

INTERVAL_MAP = {
    "1 Week":   ("7d",  "1h",  "1d"),   # (period, interval, fallback interval)
    "1 Month":  ("1mo", "1d",  "1d"),
    "1 Year":   ("1y",  "1wk", "1d"),
    "10 Years": ("10y", "1mo", "1d"),
}

@st.cache_data(ttl=600)
def get_data(tf_name):
    period, interval, fallback = INTERVAL_MAP[tf_name]
    kwargs    = {"period": period, "interval": interval}
    fb_kwargs = {"period": period, "interval": fallback}

    goog = yf.download("GOOG", **kwargs)
    fx   = yf.download("USDCHF=X", **kwargs)

    if goog.empty or fx.empty:
        goog = yf.download("GOOG", **fb_kwargs)
        fx   = yf.download("USDCHF=X", **fb_kwargs)

    # Modern yfinance returns MultiIndex columns — flatten them
    for frame in (goog, fx):
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)

    g_c = goog[["Close"]].rename(columns={"Close": "GOOG_USD"})
    f_c = fx[["Close"]].rename(columns={"Close": "USD_CHF"})

    # Outer join + forward-fill to align 5-day stock data with 24/5 FX data
    df = pd.merge(g_c, f_c, left_index=True, right_index=True, how="outer").sort_index()
    df = df.ffill().dropna()
    df["GOOG_CHF"] = df["GOOG_USD"] * df["USD_CHF"]
    return df


@st.cache_data(ttl=86400)
def load_freeze_periods():
    """Fetch GOOG earnings dates and derive employee trading blackout windows."""
    QUARTER_STARTS = {
        (1, 2):   lambda y: datetime(y - 1, 12, 10).date(),  # Q4 closes → Dec 10 lock
        (4, 5):   lambda y: datetime(y,     3,  10).date(),  # Q1 closes → Mar 10 lock
        (7, 8):   lambda y: datetime(y,     6,  10).date(),  # Q2 closes → Jun 10 lock
        (10, 11): lambda y: datetime(y,     9,  10).date(),  # Q3 closes → Sep 10 lock
    }
    try:
        dates_df = yf.Ticker("GOOG").earnings_dates.head(20)
        if dates_df is None or dates_df.empty:
            return []

        periods = []
        for date_idx in dates_df.index:
            earn_date = date_idx.to_pydatetime().date()
            month, year = earn_date.month, earn_date.year
            start_date = next(
                (fn(year) for months, fn in QUARTER_STARTS.items() if month in months),
                earn_date - timedelta(days=45),
            )
            periods.append({
                "start": start_date.strftime("%Y-%m-%d"),
                "end":   (earn_date + timedelta(days=3)).strftime("%Y-%m-%d"),
            })
        return periods
    except Exception as e:
        print(f"Failed to fetch earnings dates: {e}")
        return []


# ─── Chart creation ───────────────────────────────────────────────────────────

def build_xaxis(tf_name, series):
    """Return the Plotly xaxis config dict for the given timeframe."""
    x_min, x_max = series.index.min(), series.index.max()
    if tf_name == "1 Week":
        # Anchor to last real data point to avoid blank weekend gap on the right
        return {"showgrid": False, "range": [x_max - timedelta(days=7), x_max], "dtick": 86400000}
    if tf_name == "1 Month":
        return {"showgrid": False, "range": [x_min, x_max], "dtick": 86400000 * 3}
    return {"showgrid": False, "range": [x_min, x_max]}


def create_styled_chart(df, column, title, color, unit="", freeze_periods=None, tf_name=None):
    series = df[column]
    val_max, val_min, val_latest = series.max(), series.min(), series.iloc[-1]
    pct_of_max = (val_latest / val_max) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series, mode="lines",
        line=dict(color=color, width=4), name=title
    ))

    # MIN / MAX reference lines (left-anchored to avoid occluding the callout)
    fig.add_hline(y=val_max, line_dash="dash", line_color="rgba(128,128,128,0.5)", line_width=1,
                  annotation_text=f"MAX: {val_max:.2f}{unit}", annotation_position="top left")
    fig.add_hline(y=val_min, line_dash="dash", line_color="rgba(128,128,128,0.5)", line_width=1,
                  annotation_text=f"MIN: {val_min:.2f}{unit}", annotation_position="bottom left")

    # Latest value callout with % of MAX
    fig.add_annotation(
        x=series.index[-1], y=val_latest,
        text=f"Latest: {val_latest:.2f}{unit}<br>{pct_of_max:.1f}% of MAX",
        showarrow=True, arrowhead=2, arrowcolor=color,
        ax=-40, ay=-40, font=dict(size=12, color="white"),
        bgcolor=color, bordercolor=color, borderwidth=1
    )

    # Trading freeze periods (semi-transparent red bands)
    if freeze_periods:
        tz = series.index.min().tz
        for p in freeze_periods:
            p_start = pd.to_datetime(p["start"]).tz_localize(tz)
            p_end   = pd.to_datetime(p["end"]).tz_localize(tz)
            if p_end >= series.index.min() and p_start <= series.index.max():
                fig.add_vrect(x0=p["start"], x1=p["end"],
                              fillcolor="rgba(220,50,50,0.08)", layer="below", line_width=0)

    val_range = (val_max - val_min) or val_max * 0.1
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=build_xaxis(tf_name, series),
        yaxis={
            "showgrid": True,
            "gridcolor": "rgba(200,200,200,0.2)",
            "range": [val_min - val_range * 0.05, val_max + val_range * 0.15],
        },
    )
    return fig


# ─── Main layout ──────────────────────────────────────────────────────────────

try:
    df             = get_data(timeframe)
    freeze_periods = load_freeze_periods()

    if df.empty:
        st.warning("Data fetch returned empty.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Current GOOG (CHF)", f"{df['GOOG_CHF'].iloc[-1]:.2f} CHF")
        c2.metric("Current GOOG (USD)", f"${df['GOOG_USD'].iloc[-1]:.2f}")
        c3.metric("Current USD/CHF",    f"{df['USD_CHF'].iloc[-1]:.4f}")

        st.divider()

        charts = [
            ("I. GOOG Investment Value in Swiss Francs (CHF)", "GOOG_CHF", "#2E7D32", " CHF"),
            ("II. GOOG Stock Market Price (USD)",              "GOOG_USD", "#1565C0", " $"),
            ("III. USD to CHF Exchange Rate",                  "USD_CHF",  "#C62828", ""),
        ]
        for subtitle, col, color, unit in charts:
            st.subheader(subtitle)
            st.plotly_chart(
                create_styled_chart(df, col, subtitle, color, unit, freeze_periods, timeframe),
                on_select="ignore", selection_mode="box", width="stretch"
            )

except Exception as e:
    st.error(f"Unexpected error: {e}")
