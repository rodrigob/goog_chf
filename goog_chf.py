#!/bin/bash
''':'
# This part is read by Bash
"$(dirname "$0")/streamlit_venv/bin/streamlit" run "$0" "$@" ; exit $?
'''

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="GOOG & CHF Tracker", layout="wide")

# Sidebar for controls
st.sidebar.title("Configuration")
timeframe = st.sidebar.radio(
    "Select Time Range:",
    options=["1 Week", "1 Month", "1 Year", "10 Years"],
    index=1
)

# Configuration mapping for periodicity
mapping = {
    "1 Week": ("5d", "1h"), 
    "1 Month": ("1mo", "1d"), 
    "1 Year": ("1y", "1wk"), 
    "10 Years": ("10y", "1mo")
}
period, interval = mapping[timeframe]

st.title("GOOG & CHF dashboard")

@st.cache_data(ttl=600)
def get_data(p, i):
    goog = yf.download("GOOG", period=p, interval=i)
    fx = yf.download("USDCHF=X", period=p, interval=i)
    
    # Fallback logic for empty results
    if goog.empty or fx.empty:
        goog = yf.download("GOOG", period=p, interval="1d")
        fx = yf.download("USDCHF=X", period=p, interval="1d")

    # Handle Multi-Index columns from modern yfinance
    if isinstance(goog.columns, pd.MultiIndex):
        goog.columns = goog.columns.get_level_values(0)
    if isinstance(fx.columns, pd.MultiIndex):
        fx.columns = fx.columns.get_level_values(0)

    g_c = goog[['Close']].rename(columns={'Close': 'GOOG_USD'})
    f_c = fx[['Close']].rename(columns={'Close': 'USD_CHF'})
    
    # Outer join + forward fill to align stock & 24/5 FX data
    df = pd.merge(g_c, f_c, left_index=True, right_index=True, how='outer').sort_index()
    df = df.ffill().dropna()
    
    df['GOOG_CHF'] = df['GOOG_USD'] * df['USD_CHF']
    return df

def create_styled_chart(df, column, title, color, unit=""):
    series = df[column]
    val_max, val_min, val_latest = series.max(), series.min(), series.iloc[-1]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series, mode='lines',
        line=dict(color=color, width=4), name=title
    ))

    # Reference lines
    for val, label in [(val_max, "MAX"), (val_min, "MIN")]:
        fig.add_hline(y=val, line_dash="dash", line_color="rgba(128,128,128,0.5)", line_width=1,
                      annotation_text=f"{label}: {val:.2f}{unit}", annotation_position="top right")

    # Callout for latest value
    fig.add_annotation(
        x=series.index[-1], y=val_latest,
        text=f"Latest: {val_latest:.2f}{unit}",
        showarrow=True, arrowhead=2, arrowcolor=color,
        ax=-40, ay=-30, font=dict(size=12, color="white"),
        bgcolor=color, bordercolor=color, borderwidth=1
    )

    fig.update_layout(
        height=350, margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(200,200,200,0.2)')
    )
    return fig

try:
    df = get_data(period, interval)
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Current GOOG (CHF)", f"{df['GOOG_CHF'].iloc[-1]:.2f} CHF")
        c2.metric("Current GOOG (USD)", f"${df['GOOG_USD'].iloc[-1]:.2f}")
        c3.metric("Current USD/CHF", f"{df['USD_CHF'].iloc[-1]:.4f}")

        st.divider()

        st.subheader("I. GOOG Investment Value in Swiss Francs (CHF)")
        # Updated width parameter for 2026 Streamlit compatibility
        st.plotly_chart(create_styled_chart(df, 'GOOG_CHF', "CHF Value", "#2E7D32", " CHF"), on_select="ignore", selection_mode="box", width="stretch")

        st.subheader("II. GOOG Stock Market Price (USD)")
        st.plotly_chart(create_styled_chart(df, 'GOOG_USD', "USD Price", "#1565C0", " $"), on_select="ignore", selection_mode="box", width="stretch")

        st.subheader("III. USD to CHF Exchange Rate")
        st.plotly_chart(create_styled_chart(df, 'USD_CHF', "FX Rate", "#C62828"), on_select="ignore", selection_mode="box", width="stretch")
    else:
        st.warning("Data fetch returned empty.")
except Exception as e:
    st.error(f"Unexpected error: {e}")
