import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd

st.set_page_config(page_title="Caesar's Valuation", page_icon="💰")

st.title("📊 Caesar's Intrinsic Valuation")

ticker = st.text_input("Enter Stock Ticker (e.g. AAPL, MSFT):", value="AAPL")
stock = yf.Ticker(ticker)
price = stock.info.get("currentPrice", None)
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
            return [None]*13 + ["Could not fetch required financial data."]

        net_income = capex = ddna = dividends = equity = lt_debt = st_debt = cash = leases = minority_interest = preferred_stock = treasury_stock = None

        for row in financials.index:
            row_str = str(row).lower()
            if 'net income' in row_str and net_income is None:
                net_income = float(financials.loc[row].dropna().values[0])

        for row in cashflow.index:
            row_str = str(row).lower()
            if 'capital expend' in row_str and capex is None:
                capex = float(cashflow.loc[row].dropna().values[0])
            elif any(term in row_str for term in ['depreciation', 'amortization', 'depletion']):
                value = float(cashflow.loc[row].dropna().values[0])
                ddna = (ddna or 0) + value
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
            elif 'preferred stock' in row_str and preferred_stock is None:
                preferred_stock = float(balance_sheet.loc[row].dropna().values[0])
            elif 'treasury stock' in row_str and treasury_stock is None:
                treasury_stock = float(balance_sheet.loc[row].dropna().values[0])

        required = {
            'Net Income': net_income,
            'Capital Expenditures': capex,
            'Depreciation & Amortization': ddna,
            'Shareholder Equity': equity
        }
        missing = [k for k, v in required.items() if v is None]
        if missing:
            return [None]*13 + [f"Missing required financial components: {', '.join(missing)}"]

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

        total_debt = (lt_debt or 0) + (st_debt or 0)
        intrinsic_value_total = sum(discounted_fcfs) + discounted_terminal + (cash or 0) - total_debt
        intrinsic_value_total_mos = intrinsic_value_total * 0.70
        per_share = intrinsic_value_total_mos / shares_outstanding if shares_outstanding else None

        roe = fcf / equity if equity else None
        invested_capital = (equity or 0) + (lt_debt or 0) + (st_debt or 0) + (leases or 0) + (minority_interest or 0) - (cash or 0)
        retained_earnings = fcf - (dividends if dividends and dividends < 0 else 0)
        roic = retained_earnings / invested_capital if invested_capital else None

        sgr = None
        if roic and roic > 0:
            sgr = roic * ((fcf + (dividends if dividends else 0)) / fcf)

        retained_rate = (fcf + (dividends if dividends else 0)) / (fcf - (dividends if dividends and dividends < 0 else 0))

        debt_to_equity = total_debt / equity if equity else None
        cash_to_debt = cash / total_debt if total_debt else None

        return per_share, intrinsic_value_total_mos, roe, roic, sgr, retained_rate, price, preferred_stock, treasury_stock, debt_to_equity, cash_to_debt, None

    except Exception as e:
        return [None]*13 + [f"Exception occurred: {e}"]

if st.button("Calculate Caesar's Value"):
    result = calculate_intrinsic_value(ticker, cagr)

    if isinstance(result[-1], str):
        st.error(f"❌ {result[-1]}")
    else:
        per_share_value, total_value, roe, roic, sgr, retained_rate, price, preferred, treasury, dte, ctd, _ = result

        st.subheader("📊 Valuation Summary")

        def highlight(val, metric):
            if metric in ["Caesar's Value (per share)", "Total Caesar's Value", "Stock Price"]:
                return 'background-color: lightgreen' if per_share_value > price else 'background-color: lightcoral'
            elif metric == "Return on Equity (ROE)":
                return 'background-color: lightgreen' if roe and roe > 0.18 else 'background-color: lightcoral'
            elif metric == "Return on Invested Capital (ROIC)":
                return 'background-color: lightgreen' if roic and roic > 0.18 else 'background-color: lightcoral'
            elif metric == "Sustainable Growth Rate (SGR)":
                return 'background-color: lightgreen' if sgr and sgr > 0.18 else 'background-color: lightcoral'
            elif metric == "Retained Earnings Rate":
                return 'background-color: lightgreen' if retained_rate and retained_rate > 0.70 else 'background-color: lightcoral'
            elif metric == "Preferred Stock":
                return 'background-color: lightcoral' if preferred and preferred > 0 else 'background-color: lightgreen'
            elif metric == "Treasury Stock":
                return 'background-color: lightgreen' if treasury and treasury > 0 else 'background-color: lightcoral'
            elif metric == "Debt to Equity":
                return 'background-color: lightgreen' if dte and dte < 0.8 else 'background-color: lightcoral'
            elif metric == "Cash to Debt":
                return 'background-color: lightgreen' if ctd and ctd > 0.9 else 'background-color: lightcoral'
            return ''

        df = pd.DataFrame({
            "Metric": [
                "Caesar's Value (per share)",
                "Stock Price",
                "Total Caesar's Value",
                "Return on Equity (ROE)",
                "Return on Invested Capital (ROIC)",
                "Sustainable Growth Rate (SGR)",
                "Retained Earnings Rate",
                "Preferred Stock",
                "Treasury Stock",
                "Debt to Equity",
                "Cash to Debt"
            ],
            "Value": [
                f"${per_share_value:,.2f}",
                f"${price:,.2f}" if price else "N/A",
                f"${total_value:,.2f}",
                f"{roe:.2%}" if roe is not None else "N/A",
                f"{roic:.2%}" if roic is not None else "N/A",
                f"{sgr:.2%}" if sgr is not None else "N/A",
                f"{retained_rate:.2%}" if retained_rate is not None else "N/A",
                f"${preferred:,.2f}" if preferred else "$0.00",
                f"${treasury:,.2f}" if treasury else "$0.00",
                f"{dte:.2f}" if dte is not None else "N/A",
                f"{ctd:.2f}" if ctd is not None else "N/A"
            ]
        })

        st.dataframe(
            df.style.apply(lambda row: ["background-color: #D6EAF8"] + [highlight(row['Value'], row['Metric'])], axis=1)
                     .set_table_styles([
                         {'selector': 'th', 'props': [('background-color', '#AED6F1'), ('color', 'black'), ('font-size', '14px')]},
                         {'selector': 'td', 'props': [('font-size', '13px')]}
                     ])
        )

        if per_share_value and price:
            if price > per_share_value * 1.1:
                verdict = "🚨 Overvalued"
            elif per_share_value * 0.9 <= price <= per_share_value * 1.1:
                verdict = "✅ Fairly Valued"
            else:
                verdict = "💎 Undervalued"
            st.subheader(f"Market Verdict: {verdict}")

        st.markdown("---")
        st.markdown("### 🧠 Disclaimer")
        st.markdown("This tool represents **Caesar's personal valuation opinion** based on publicly available data and does **not constitute financial advice**. Caesar believes spreadsheets are mightier than swords – but don't take his word to the bank.")
