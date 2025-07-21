import streamlit as st
import yfinance as yf
import pandas as pd

# Function to calculate intrinsic value using Free Cash Flow to Firm (FCFF) method
def calculate_intrinsic_value(ticker: str, cagr: float):
    try:
        ticker = ticker.upper()
        stock = yf.Ticker(ticker)
        cashflow = stock.cashflow

        if cashflow.empty:
            st.error("Cashflow data is empty.")
            return None

        # Attempt to find appropriate row labels for OCF and CapEx
        ocf_row = next((label for label in cashflow.index if 'Operating Cash Flow' in label or 'Total Cash From Operating Activities' in label), None)
        capex_row = next((label for label in cashflow.index if 'Capital Expenditure' in label), None)

        if not ocf_row or not capex_row:
            st.error("Could not find required fields in cashflow.")
            return None

        ocf = cashflow.loc[ocf_row]
        capex = cashflow.loc[capex_row]

        fcf = ocf - capex
        fcf = fcf[fcf.notnull()].astype(float)

        if fcf.empty:
            st.error("Free Cash Flow data is not available.")
            return None

        avg_fcf = fcf.mean()

        discount_rate = 0.10
        years = 5

        # Project future FCFs and calculate terminal value
        projected_fcfs = [avg_fcf * ((1 + cagr/100) ** i) for i in range(1, years + 1)]
        terminal_value = projected_fcfs[-1] * (1 + cagr/100) / (discount_rate - cagr/100)

        # Discount FCFs and terminal value to present value
        discounted_fcfs = [fcf / ((1 + discount_rate) ** i) for i, fcf in enumerate(projected_fcfs, start=1)]
        discounted_terminal = terminal_value / ((1 + discount_rate) ** years)

        intrinsic_value = sum(discounted_fcfs) + discounted_terminal
        return intrinsic_value

    except Exception as e:
        st.error(f"Exception occurred: {e}")
        return None

# Streamlit frontend
st.title("📊 Free Cash Flow Valuation Tool")
st.write("Estimate the intrinsic value of a stock using its Free Cash Flow (FCF).")

ticker = st.text_input("Enter Stock Ticker (e.g., AAPL):")
cagr = st.slider("Expected CAGR (%):", min_value=1.0, max_value=20.0, value=10.0, step=0.5)

if st.button("Calculate Valuation"):
    if not ticker:
        st.warning("Please enter a stock ticker.")
    else:
        valuation = calculate_intrinsic_value(ticker, cagr)
        if valuation:
            st.success(f"✅ Intrinsic Value Estimate: ${valuation:,.2f}")
