# %%
from wallstreet import Stock
import streamlit as st
import pandas as pd
import plotly.express as px

c1, c2, c3 = st.columns(3)
with c1:
    look_back = st.text_input('Look back (Days)', '600')
with c2:
    ticker1 = st.text_input('Long Ticker', 'AMD') # long
with c3:
    ticker2 = st.text_input('Short Ticker', 'INTC')  # short

c4,c5 = st.columns([1,3])
with c4:
    fixed_weight = st.checkbox('Fixed Weights')
with c5:
    long_weight = st.text_input('Long Weight', value='0.5', disabled=not fixed_weight)
    long_weight = float(long_weight)

keep_cols = ['Date','Price','PctChange','PctVolatility']

s1 = Stock(ticker1).historical(int(look_back))
s1['Price'] = s1['Adj Close']
s1['PrevPrice'] = s1.Price.shift(1)
s1['PctVolatility'] = s1.eval('(High-Low)/Price').shift(1)
s1['PctChange'] = s1.eval('(Price-PrevPrice)/PrevPrice')
s1 = s1[keep_cols]

s2 = Stock(ticker2).historical(int(look_back))
s2['Price'] = s2['Adj Close']
s2['PrevPrice'] = s2.Price.shift(1)
s2['PctVolatility'] = s2.eval('(High-Low)/Price').shift(1)
s2['PctChange'] = s2.eval('(Price-PrevPrice)/PrevPrice')
s2 = s2[keep_cols]

df =s1.set_index('Date').join(s2.set_index('Date'),lsuffix='1',rsuffix='2')

if not fixed_weight:
    pair_returns=df.eval('1+ (PctVolatility2 * PctChange1 - PctVolatility1* PctChange2)/ (PctVolatility1+PctVolatility2)').cumprod().rename('Pair Returns')-1
else:
    pair_returns=df.eval('1+ (@long_weight * PctChange1 - (1-@long_weight)* PctChange2)').cumprod().rename('Pair Returns')-1
t1_returns = df.eval('1+PctChange1').cumprod().rename(f'{ticker1} Returns')-1
t2_returns = df.eval('1+PctChange2').cumprod().rename(f'{ticker2} Returns')-1
returns_df = pd.concat([pair_returns,t1_returns,t2_returns],axis=1)

fig1=px.line(returns_df,title=f'Pair (+{ticker1} -{ticker2})')
st.plotly_chart(fig1)

if not fixed_weight:
    t1_weights = df.eval('PctVolatility2 / (PctVolatility1+PctVolatility2)').rename(f'{ticker1} Weight')
    t2_weights = df.eval('PctVolatility1 / (PctVolatility1+PctVolatility2)').rename(f'{ticker2} Weight')
    weights_df = pd.concat([t1_weights,t2_weights],axis=1)
    fig2=px.line(weights_df,title=f'Dollar Weights (+{ticker1} -{ticker2})')
    st.plotly_chart(fig2)
