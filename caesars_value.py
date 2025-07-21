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

def format_value(val, metric):
    if val is None:
        return ""
    if metric in ["Caesar Value", "Caesar Value per Share", "Price", "Preferred Stock", "Treasury Stock", "Market Cap", "Dividends per Share"]:
        return f"${val:,.2f}"
    elif metric in ["ROE", "ROIC", "SGR", "Retained Earnings %", "Debt to Equity", "Cash to Debt"]:
        return f"{val * 100:.2f}%"
    return val

def colorize(val, metric, thresholds, caesar_value, dividends_per_share, treasury_stock):
    if val is None:
        return ""
    green, red = "background-color: #d4edda", "background-color: #f8d7da"
    if metric == "Caesar Value":
        return green if val > price else red
    elif metric == "Price":
        return green if val < caesar_value else red
    elif metric == "ROE":
        return green if val > thresholds else red
    elif metric == "ROIC":
        return green if val > thresholds else red
    elif metric == "SGR":
        return green if val > thresholds else red
    elif metric == "Retained Earnings %":
        return green if val > thresholds else red
    elif metric == "Preferred Stock":
        return red if val and val > 0 else green
    elif metric == "Treasury Stock":
        return green if val and val > 0 or (dividends_per_share and dividends_per_share > 0) else red
    elif metric == "Debt to Equity":
        return green if val < thresholds else red
    elif metric == "Cash to Debt":
        return green if val > thresholds else red
    elif metric == "Market Cap":
        return green if val < caesar_value * 0.9 else red if val > caesar_value * 1.1 else "background-color: #fff3cd"
    elif metric == "Dividends per Share":
        return green if val > 0 or (treasury_stock and treasury_stock > 0) else red
    return ""

def calculate_intrinsic_value(ticker, cagr):
    try:
        stock = yf.Ticker(ticker)
        cashflow = stock.cashflow
        balance_sheet = stock.balance_sheet
        financials = stock.financials
        info = stock.info
        shares_outstanding = info.get("sharesOutstanding", None)
        market_cap = info.get("marketCap", None)
        dividends_per_share = info.get("dividendRate", 0.0)

        if cashflow.empty or balance_sheet.empty or financials.empty:
            return [None]*15 + ["Could not fetch required financial data."]

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
                ddna = (ddna or 0) + float(cashflow.loc[row].dropna().values[0])
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

        capex = -abs(capex)
        ddna = -abs(ddna)
        adjusted_cost = capex if abs(capex) > abs(ddna) else ddna
        fcf = net_income - adjusted_cost

        discount_rate = 0.06
        cagr_rate = cagr / 100
        discounted_fcfs = [fcf * ((1 + cagr_rate) ** i) / ((1 + discount_rate) ** i) for i in range(1, 11)]

        terminal_value = 9 * fcf
        discounted_terminal = terminal_value / ((1 + discount_rate) ** 10)

        total_debt = (lt_debt or 0) + (st_debt or 0)
        caesar_value = sum(discounted_fcfs) + discounted_terminal + (cash or 0) - total_debt
        caesar_value *= 0.70

        caesar_value_per_share = caesar_value / shares_outstanding if shares_outstanding else None
        roe = fcf / equity if equity else None
        invested_capital = (equity or 0) + (lt_debt or 0) + (st_debt or 0) + (leases or 0) + (minority_interest or 0) - (cash or 0)
        retained_earnings = fcf - (dividends if dividends and dividends < 0 else 0)
        roic = retained_earnings / invested_capital if invested_capital else None
        sgr = roic * ((fcf + (dividends or 0)) / fcf) if roic and roic > 0 else None
        retained_rate = (fcf + (dividends or 0)) / (fcf - (dividends if dividends and dividends < 0 else 0))
        debt_to_equity = total_debt / equity if equity else None
        cash_to_debt = cash / total_debt if total_debt else None

        return caesar_value, caesar_value_per_share, roe, roic, sgr, retained_rate, price, preferred_stock, treasury_stock, debt_to_equity, cash_to_debt, market_cap, dividends_per_share, None

    except Exception as e:
        return [None]*15 + [str(e)]

results = calculate_intrinsic_value(ticker, cagr)

if results[-1]:
    st.error(results[-1])
else:
    labels = ["Caesar Value", "Caesar Value per Share", "ROE", "ROIC", "SGR", "Retained Earnings %", "Price", "Preferred Stock", "Treasury Stock", "Debt to Equity", "Cash to Debt", "Market Cap", "Dividends per Share"]
    df = pd.DataFrame([[results[i] for i in range(len(labels))]], columns=labels).T
    df.columns = ["Value"]
    df.index.name = "Metric"

    caesar_value = results[0]
    dividends_per_share = results[12]
    treasury_stock = results[8]

    def highlight(val, metric):
        thresholds = {
            "ROE": 0.18,
            "ROIC": 0.18,
            "SGR": 0.18,
            "Retained Earnings %": 0.7,
            "Debt to Equity": 0.8,
            "Cash to Debt": 0.9,
        }
        return colorize(val, metric, thresholds.get(metric, 0), caesar_value, dividends_per_share, treasury_stock)

    df["Formatted"] = [format_value(val, idx) for val, idx in zip(df["Value"], df.index)]
    styled = df[["Formatted"]].style.set_table_styles([
        {"selector": "th", "props": [("background-color", "#dbefff"), ("font-weight", "bold")]},
        {"selector": "thead th", "props": [("background-color", "#a8d0ff")]} 
    ]).apply(lambda col: [highlight(val, idx) for val, idx in zip(df["Value"], df.index)], axis=0)

    st.dataframe(styled, use_container_width=True)

    current_price = results[6]
    caesar_value_per_share = results[1]
    valuation_status = "undervalued" if current_price < caesar_value_per_share * 0.9 else "overvalued" if current_price > caesar_value_per_share * 1.1 else "fairly valued"
    st.markdown(f"### 🏷️ According to Caesar, this stock is **{valuation_status}**.")

    st.markdown("""
    ---
    ⚠️ **This is just Caesar's opinion, not financial advice. Always do your own research before investing.**
    """)
