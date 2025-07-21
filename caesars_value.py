import streamlit as st
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Caesar's Valuation", page_icon="💰")

st.title("📊 Caesar's Intrinsic Valuation")

ticker = st.text_input("Enter Stock Ticker (e.g. AAPL, MSFT):", value="AAPL")
cagr = st.slider("Expected CAGR (%):", min_value=0.0, max_value=50.0, value=10.0, step=0.5)

def calculate_intrinsic_value(ticker, cagr):
    try:
        stock = yf.Ticker(ticker)
        cashflow = stock.cashflow
        balance_sheet = stock.balance_sheet
        shares_outstanding = stock.info.get("sharesOutstanding", None)

        if cashflow is None or cashflow.empty or balance_sheet is None or balance_sheet.empty:
            return None, None, "Could not fetch required financial data."

        # Extract the relevant fields
        ocf = None
        capex = None
        ddna = None

        for row in cashflow.index:
            row_str = str(row).lower()
            if 'operating cash flow' in row_str and ocf is None:
                ocf = float(cashflow.loc[row].dropna().values[0])
            elif 'capital expend' in row_str and capex is None:
                capex = float(cashflow.loc[row].dropna().values[0])
            elif 'depreciation' in row_str and ddna is None:
                ddna = float(cashflow.loc[row].dropna().values[0])

        if ocf is None or capex is None or ddna is None:
            return None, None, "Missing required cashflow components."

        capex = -abs(capex)
        ddna = -abs(ddna)
        adjusted_cost = capex if abs(capex) > abs(ddna) else ddna
        fcf = ocf - adjusted_cost  # Owner earnings

        # Forecast and discount each year individually for 10 years
        discount_rate = 0.06
        cagr_rate = cagr / 100
        projected_fcfs = []
        discounted_fcfs = []

        for year in range(1, 11):
            future_fcf = fcf * ((1 + cagr_rate) ** year)
            discounted_fcf = future_fcf / ((1 + discount_rate) ** year)
            projected_fcfs.append(future_fcf)
            discounted_fcfs.append(discounted_fcf)

        # Terminal value = 9 * current FCF
        terminal_value = 9 * fcf
        discounted_terminal = terminal_value / ((1 + discount_rate) ** 10)

        # Add cash and subtract debt
        cash = 0
        short_term_debt = 0
        long_term_debt = 0

        for row in balance_sheet.index:
            row_str = str(row).lower()
            if 'cash and cash equivalents' in row_str and cash == 0:
                cash = float(balance_sheet.loc[row].dropna().values[0])
            elif 'short long term debt' in row_str and short_term_debt == 0:
                short_term_debt = float(balance_sheet.loc[row].dropna().values[0])
            elif 'long term debt' in row_str and long_term_debt == 0:
                long_term_debt = float(balance_sheet.loc[row].dropna().values[0])

        # Adjust for sign
        if short_term_debt > 0:
            debt_adjustment = -short_term_debt
        else:
            debt_adjustment = abs(short_term_debt)

        if long_term_debt > 0:
            debt_adjustment -= long_term_debt
        else:
            debt_adjustment += abs(long_term_debt)

        intrinsic_value_total = sum(discounted_fcfs) + discounted_terminal + cash + debt_adjustment
        margin_of_safety = 0.30
        intrinsic_value_total_mos = intrinsic_value_total * (1 - margin_of_safety)

        if shares_outstanding and shares_outstanding > 0:
            per_share = intrinsic_value_total_mos / shares_outstanding
        else:
            per_share = None

        return per_share, intrinsic_value_total_mos, None
    except Exception as e:
        return None, None, f"Exception occurred: {e}"

if st.button("Calculate Caesar's Value"):
    per_share_value, total_value, error = calculate_intrinsic_value(ticker, cagr)
    if error:
        st.error(f"❌ {error}")
    elif per_share_value:
        st.success(f"✅ Caesar's Value Estimate (with 30% margin of safety): ${per_share_value:,.2f} per share")
        st.info(f"📈 Total Caesar's Value (with MoS): ${total_value:,.2f}")
    else:
        st.warning("⚠️ Unable to calculate value.")
