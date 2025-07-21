import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Set default darker theme colors
st.markdown("""
    <style>
        body {
            background-color: #1e1e1e;
            color: white;
        }
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input {
            color: white;
        }
        .stSelectbox > div > div > div > div {
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# Display logo and YouTube icon with link
st.markdown("""
<div style="display: flex; justify-content: center; align-items: center; gap: 10px;">
    <a href="https://www.youtube.com/@CaesarFM-h9z" target="_blank">
        <img src="https://i.postimg.cc/JzBzfxws/Chat-GPT-Image-Jul-10-2025-06-34-37-PM.png" width="90" alt="Logo">
        <img src="https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png" width="60" alt="YouTube">
    </a>
</div>
""", unsafe_allow_html=True)

# App input and layout
st.title("Caesar's Stock Valuation App")
ticker = st.text_input("Enter Stock Ticker (e.g. AAPL, MSFT):", "AAPL")
cagr_input = st.number_input("Expected CAGR (%):", min_value=0.0, max_value=50.0, value=10.0)

if ticker:
    stock = yf.Ticker(ticker)
    info = stock.info
    cashflow = stock.cashflow
    financials = stock.financials
    balance_sheet = stock.balance_sheet

    try:
        # Extract key values
        operating_cash_flow = cashflow.loc["Total Cash From Operating Activities"].iloc[0]
        capex = cashflow.loc["Capital Expenditures"].iloc[0]
        ddna = financials.loc["Depreciation"].iloc[0]
        shares_outstanding = info.get("sharesOutstanding", 0)
        price = info.get("currentPrice", 0)
        dividends_per_share = info.get("dividendRate", 0)
        treasury = balance_sheet.loc["Treasury Stock"].iloc[0] if "Treasury Stock" in balance_sheet.index else 0
        market_cap = price * shares_outstanding

        # Calculate FCF and Caesars Value
        fcf = operating_cash_flow - capex + ddna
        cagr = cagr_input / 100
        intrinsic_value = fcf * (1 + cagr)**10
        caesar_value = intrinsic_value / shares_outstanding

        # Determine valuation
        margin = 0.10 * caesar_value
        if price > caesar_value + margin:
            valuation_label = "overvalued"
            valuation_color = "red"
        elif price < caesar_value - margin:
            valuation_label = "undervalued"
            valuation_color = "green"
        else:
            valuation_label = "fairly valued"
            valuation_color = "yellow"

        # Display results
        df = pd.DataFrame({
            "Metric": ["Price", "Market Cap", "Caesar's Value", "Margin of Safety", "Dividends/share", "Treasury"],
            "Value": [
                f"${price:,.2f}",
                f"${market_cap:,.0f}",
                f"${caesar_value:,.2f}",
                f"${margin:,.2f}",
                f"${dividends_per_share:,.2f}" if dividends_per_share > 0 else "$0.00",
                f"${treasury:,.0f}" if treasury != 0 else "$0"
            ]
        })
        st.table(df)

        # Display Caesar's conclusion
        st.markdown(f"""
        <h3 style='text-align: center; color: black;'>According to Caesar, this stock is 
            <span style='color: {valuation_color};'>{valuation_label}</span>.</h3>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
