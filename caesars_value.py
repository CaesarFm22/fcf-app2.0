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
        financials = stock.financials
        info = stock.info
        shares_outstanding = info.get("sharesOutstanding", None)

        if cashflow is None or cashflow.empty or balance_sheet is None or balance_sheet.empty:
            return None, None, None, None, "Could not fetch required financial data."

        # Extract the relevant fields
        ocf = capex = ddna = dividends = equity = lt_debt = st_debt = cash = leases = minority_interest = None

        for row in cashflow.index:
            row_str = str(row).lower()
            if 'operating cash flow' in row_str and ocf is None:
                ocf = float(cashflow.loc[row].dropna().values[0])
            elif 'capital expend' in row_str and capex is None:
                capex = float(cashflow.loc[row].dropna().values[0])
            elif ('depreciation' in row_str or 'amortization' in row_str) and ddna is None:
                ddna = float(cashflow.loc[row].dropna().values[0])
            elif 'dividends paid' in row_str and dividends is None:
                dividends = float(cashflow.loc[row].dropna().values[0])

        for row in balance_sheet.index:
            row_str = str(row).lower()
            if 'stockholder' in row_str and 'equity' in row_str and equity is None:
                equity = float(balance_sheet.loc[row].dropna().values[0])
            elif 'long term debt' in row_str and lt_debt is None:
                lt_debt = float(balance_sheet.loc[row].dropna().values[0])
            elif 'short long term debt' in row_str and st_debt is None:
                st_debt = float(balance_sheet.loc[row].dropna().values[0])
            elif 'cash and cash' in row_str and cash is None:
                cash = float(balance_sheet.loc[row].dropna().values[0])
            elif 'capital lease' in row_str and leases is None:
                leases = float(balance_sheet.loc[row].dropna().values[0])
            elif 'minority interest' in row_str and minority_interest is None:
                minority_interest = float(balance_sheet.loc[row].dropna().values[0])

        if ocf is None or capex is None or ddna is None or equity is None:
            missing = []
            if ocf is None: missing.append("Operating Cash Flow")
            if capex is None: missing.append("Capital Expenditures")
            if ddna is None: missing.append("Depreciation & Amortization")
            if equity is None: missing.append("Shareholder Equity")
            return None, None, None, None, f"Missing required financial components: {', '.join(missing)}"

        capex = -abs(capex)
        ddna = -abs(ddna)
        adjusted_cost = capex if abs(capex) > abs(ddna) else ddna
        fcf = ocf - adjusted_cost  # Owner earnings

        discount_rate = 0.06
        cagr_rate = cagr / 100
        projected_fcfs = []
        discounted_fcfs = []

        for year in range(1, 11):
            future_fcf = fcf * ((1 + cagr_rate) ** year)
            discounted_fcf = future_fcf / ((1 + discount_rate) ** year)
            projected_fcfs.append(future_fcf)
            discounted_fcfs.append(discounted_fcf)

        terminal_value = 9 * fcf
        discounted_terminal = terminal_value / ((1 + discount_rate) ** 10)

        # Debt sign correction
        total_debt = 0
        if st_debt is not None:
            total_debt -= st_debt if st_debt > 0 else -st_debt
        if lt_debt is not None:
            total_debt -= lt_debt if lt_debt > 0 else -lt_debt

        intrinsic_value_total = sum(discounted_fcfs) + discounted_terminal + (cash or 0) + total_debt
        intrinsic_value_total_mos = intrinsic_value_total * (1 - 0.30)

        per_share = intrinsic_value_total_mos / shares_outstanding if shares_outstanding else None

        # ROE = Owner Earnings / Equity
        roe = fcf / equity if equity else None

        # ROIC
        invested_capital = (equity or 0) + (lt_debt or 0) + (st_debt or 0) + (leases or 0) + (minority_interest or 0) - (cash or 0)
        retained_earnings = fcf - (dividends if dividends and dividends < 0 else 0)
        roic = retained_earnings / invested_capital if invested_capital else None

        return per_share, intrinsic_value_total_mos, roe, roic, None

    except Exception as e:
        return None, None, None, None, f"Exception occurred: {e}"

if st.button("Calculate Caesar's Value"):
    per_share_value, total_value, roe, roic, error = calculate_intrinsic_value(ticker, cagr)
    if error:
        st.error(f"❌ {error}")
    elif per_share_value:
        st.success(f"✅ Caesar's Value Estimate (with 30% margin of safety): ${per_share_value:,.2f} per share")
        st.info(f"📈 Total Caesar's Value (with MoS): ${total_value:,.2f}")
        if roe is not None:
            st.metric(label="📊 Return on Equity (ROE)", value=f"{roe:.2%}")
        if roic is not None:
            st.metric(label="🏗️ Return on Invested Capital (ROIC)", value=f"{roic:.2%}")
    else:
        st.warning("⚠️ Unable to calculate value.")
