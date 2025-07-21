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

        if cashflow is None or cashflow.empty or balance_sheet is None or balance_sheet.empty or financials is None or financials.empty:
            return None, None, None, None, None, None, None, "Could not fetch required financial data."

        net_income = capex = ddna = dividends = equity = lt_debt = st_debt = cash = leases = minority_interest = None

        for row in financials.index:
            row_str = str(row).lower()
            if 'net income' in row_str and net_income is None:
                net_income = float(financials.loc[row].dropna().values[0])

        for row in cashflow.index:
            row_str = str(row).lower()
            if 'capital expend' in row_str and capex is None:
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

        required = {
            'Net Income': net_income,
            'Capital Expenditures': capex,
            'Depreciation & Amortization': ddna,
            'Shareholder Equity': equity
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            return None, None, None, None, None, None, None, f"Missing required financial components: {', '.join(missing)}"

        capex = -abs(capex)
        ddna = -abs(ddna)
        adjusted_cost = capex if abs(capex) > abs(ddna) else ddna
        fcf = net_income - adjusted_cost

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

        total_debt = 0
        if st_debt is not None:
            total_debt -= st_debt if st_debt > 0 else -st_debt
        if lt_debt is not None:
            total_debt -= lt_debt if lt_debt > 0 else -lt_debt

        intrinsic_value_total = sum(discounted_fcfs) + discounted_terminal + (cash or 0) + total_debt
        intrinsic_value_total_mos = intrinsic_value_total * (1 - 0.30)

        per_share = intrinsic_value_total_mos / shares_outstanding if shares_outstanding else None

        roe = fcf / equity if equity else None
        invested_capital = (equity or 0) + (lt_debt or 0) + (st_debt or 0) + (leases or 0) + (minority_interest or 0) - (cash or 0)
        retained_earnings = fcf - (dividends if dividends and dividends < 0 else 0)
        roic = retained_earnings / invested_capital if invested_capital else None

        return per_share, intrinsic_value_total_mos, roe, roic, fcf, discounted_fcfs, terminal_value, {
            'Net Income': net_income,
            'Capital Expenditures': capex,
            'Depreciation & Amortization': ddna,
            'Dividends Paid': dividends,
            'Shareholder Equity': equity,
            'Cash & Equivalents': cash,
            'Long-Term Debt': lt_debt,
            'Short-Term Debt': st_debt,
            'Capital Leases': leases,
            'Minority Interest': minority_interest
        }

    except Exception as e:
        return None, None, None, None, None, None, None, f"Exception occurred: {e}"

if st.button("Calculate Caesar's Value"):
    per_share_value, total_value, roe, roic, fcf, discounted_fcfs, terminal_value, extra = calculate_intrinsic_value(ticker, cagr)
    if isinstance(extra, str):
        st.error(f"❌ {extra}")
    elif per_share_value:
        st.success(f"✅ Caesar's Value Estimate (with 30% margin of safety): ${per_share_value:,.2f} per share")
        st.info(f"📈 Total Caesar's Value (with MoS): ${total_value:,.2f}")
        st.write("### Calculation Details")
        st.write(f"- Free Cash Flow (Owner Earnings): ${fcf:,.2f}")
        st.write(f"- Discounted FCFs (10 yrs): {[f'${v:,.2f}' for v in discounted_fcfs]}")
        st.write(f"- Terminal Value (undiscounted): ${terminal_value:,.2f}")
        if roe is not None:
            st.metric(label="📊 Return on Equity (ROE)", value=f"{roe:.2%}")
        if roic is not None:
            st.metric(label="🏗️ Return on Invested Capital (ROIC)", value=f"{roic:.2%}")

        st.write("### Components Used for FCF Calculation")
        for k, v in extra.items():
            st.write(f"- {k}: ${v:,.2f}" if v is not None else f"- {k}: Not Found")
    else:
        st.warning("⚠️ Unable to calculate value.")
