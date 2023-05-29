# %%
from wallstreet import Stock
import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px

from datetime import date, timedelta

# ===== UI =====
c1, c2, c3 = st.columns([1,1,2])
with c1:
    start_date = st.date_input('Start Date', date.today()-timedelta(days=360))
with c2:
    end_date = st.date_input('End Date')
with c3:
    tickers = st.text_input('Pair (separate by comma)', 'WM,SRCL') 
    ticker1,ticker2 = [t.strip() for t in tickers.split(',')[:2]]

c4,c5,c6 = st.columns([1,1,1])
with c4:
    iv_weight = st.checkbox('IV Weights')
with c5:
    long_weight = st.text_input('Long Weight', value='0.5', disabled=iv_weight)
    long_weight = float(long_weight) 
with c6:
    rebalance_freq = st.text_input('Rebalance Frequency (Business Days)', value='60')
    rebalance_freq = int(rebalance_freq)
# ===========

# ===== Grab Data =====
keep_cols = ['Price','PctChange','PctVolatility','Position','Dollars']
look_back = int((date.today()-start_date).days)

dfs = []
fixed_weight = long_weight*2
for t in tickers.split(',')[:2]:
    s = Stock(t.strip()).historical(look_back)
    s['Date'] = pd.to_datetime(s['Date'])
    s.set_index('Date',inplace=True)
    s['Price'] = s['Adj Close']
    s['PrevPrice'] = s.Price.shift(1)
    s['PctVolatility'] = s.eval('(High-Low)/Price').shift(1).rolling(rebalance_freq, min_periods=1).mean()
    s['PctChange'] = s.eval('(Price-PrevPrice)/PrevPrice')
    s.dropna(inplace=True)
    s['Position'] = np.nan
    s['Dollars'] = 1 if iv_weight else fixed_weight
    fixed_weight = 2-fixed_weight
    s = s[keep_cols]
    dfs.append(s)

df = dfs[0].join(dfs[-1],lsuffix='1',rsuffix='2')[start_date:end_date]
# ==========

# ===== Rebalance Logic =====

rebalance_dates = pd.date_range(df.index.min(),df.index.max(),freq=f'{rebalance_freq}B',inclusive='left')

for i, d in enumerate(rebalance_dates):
    next_d = rebalance_dates[i+1] if i < len(rebalance_dates)-1 else df.index.max()

    if iv_weight:
        long_weight = df.eval('PctVolatility2/(PctVolatility1+PctVolatility2)').loc[d]
    total_dollars = df.loc[d].Dollars1+df.loc[d].Dollars2
    df.loc[d:next_d,'EntryPrice1'] = df.loc[d].Price1
    df.loc[d:next_d,'EntryPrice2'] = df.loc[d].Price2
    df.loc[d:next_d,'Position1'] = long_weight*total_dollars/df.loc[d].Price1
    df.loc[d:next_d,'Position2'] = (1-long_weight)*total_dollars/df.loc[d].Price2

    df.loc[d:next_d,'Dollars1'] = df.loc[d:next_d].eval('Position1*(Price1-EntryPrice1)+Position1*EntryPrice1')
    df.loc[d:next_d,'Dollars2'] = df.loc[d:next_d].eval('Position2*(EntryPrice2-Price2)+Position2*EntryPrice2')

# st.dataframe(df)
# ==========

# ===== Plots =====

pair_returns=df.eval('(Dollars1 + Dollars2)/2').rename('Pair Returns')-1
t1_returns = df.eval('1+PctChange1').cumprod().rename(f'{ticker1} Returns')-1
t2_returns = df.eval('1+PctChange2').cumprod().rename(f'{ticker2} Returns')-1
returns_df = pd.concat([pair_returns,t1_returns,t2_returns],axis=1)

fig1=px.line(returns_df,title=f'Cumulative Returns (+{ticker1} -{ticker2})')
st.plotly_chart(fig1)

pos_df = df[['Position1','Position2']]*1_000
pos_df.columns = [ticker1,ticker2]
fig2=px.line(pos_df,title=f'Position Size (Number of shares / $1k capital) (+{ticker1} -{ticker2})')
st.plotly_chart(fig2)
# if not fixed_weight:
#     t1_weights = df.eval('PctVolatility2 / (PctVolatility1+PctVolatility2)').rename(f'{ticker1} Weight')
#     t2_weights = df.eval('PctVolatility1 / (PctVolatility1+PctVolatility2)').rename(f'{ticker2} Weight')
#     weights_df = pd.concat([t1_weights,t2_weights],axis=1)

# ==========