import streamlit as st
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Caesars Valuation", page_icon="💰")

st.title("📊 Caesars Intrinsic Valuation")

ticker = st.text_input("Enter Stock Ticker (e.g. AAPL, MSFT):", value="AAPL")
cagr = st.slider("Expected CAGR (%):", min_value=0.0, max_value=20.0, value=10.0, step=0.5)
discount_rate = st.slider("Discount Rate (%):", min_value=0.0, max_value=15.0, value=10.0, step=0.5)

def calculate_intrinsic_value(ticker, cagr, discount_rate):
    try:
        stock = yf.Ticker(ticker)
        cashflow = stock.cashflow
        shares_outstanding = stock.info.get("sharesOutstanding", None)

        if cashflow is None or cashflow.empty:
            return None, "Could not fetch cashflow data."

        # Extract the relevant fields
        ocf = None
        capex = None
        ddna = None

        for row in cashflow.index:
            row_str = str(row).lower()
            if 'operating cash flow' in row_str and ocf is None:
                ocf = cashflow.loc[row].dropna().values[0]
            elif 'capital expend' in row_str and capex is None:
                capex = cashflow.loc[row].dropna().values[0]
            elif 'depreciation' in row_str and ddna is None:
                ddna = cashflow.loc[row].dropna().values[0]

        if ocf is None or capex is None or ddna is None:
            return None, "Missing required cashflow components."

        # Apply the rule: use max(capex, ddna) (both are negative values)
        adjusted_capex = capex if abs(capex) > abs(ddna) else ddna

        fcf = ocf - adjusted_capex

        # DCF valuation with 5-year projection and terminal value
        years = 5
        cagr_rate = cagr / 100
        discount = discount_rate / 100

        projected_fcfs = [fcf * ((1 + cagr_rate) ** year) for year in range(1, years + 1)]
        discounted_fcfs = [fcf_ / ((1 + discount) ** year) for year, fcf_ in enumerate(projected_fcfs, start=1)]

        terminal_value = projected_fcfs[-1] * (1 + cagr_rate) / (discount - cagr_rate)
        discounted_terminal = terminal_value / ((1 + discount) ** years)

        intrinsic_value_total = sum(discounted_fcfs) + discounted_terminal

        if shares_outstanding:
            per_share = intrinsic_value_total / shares_outstanding
        else:
            per_share = None

        return per_share, None
    except Exception as e:
        return None, f"Exception occurred: {e}"

if st.button("Calculate Caesars Value"):
    value, error = calculate_intrinsic_value(ticker, cagr, discount_rate)
    if error:
        st.error(f"❌ {error}")
    elif value:
        st.success(f"✅ Caesars Value Estimate: ${value:,.2f} per share")
    else:
        st.warning("⚠️ Unable to calculate value.")
