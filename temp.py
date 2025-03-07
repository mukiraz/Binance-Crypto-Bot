# -*- coding: utf-8 -*-
"""
Created on Tue Jun 21 09:39:18 2022

@author: Murat Ugur KIRAZ
"""


#from constant import Source

#source = Ind(HCcandles).source(Source.OHLC4)
#atrBands = Ind(HCcandles).getATRBands(atrPeriod=3, atrMultiplierUpper = 1.4, srcUpper = Source.OHLC4, atrMultiplierLower = 1.4, srcLower = Source.CLOSE)
#macd = Ind(HCcandles).getMACD()

from Connection import BinanceConnection as BC
#from Indicators import Indicators as Ind
from Strategy import Strategy as ST
import pandas as pd



start_cash = 1000
parameters = {
    "total_cash":0,
    "interval":"5m",
    "symbol":"avaxusdt",
    "cash":start_cash,
    "risk_percentage":0.01,
    "risk_reward_ratio":1.2,
    "operation_time":"",
    "has_coin":False,
    "has_cash":True,
    "position":"",
    "coin_amount":0,
    "stop_price":0,
    "sell_price":0,
    "comission":0,
    "comission_fee":0,
    "before_comission_calculated_coin_amount":0,
    "after_comission_calculated_coin_amount":0,
    "buy_price":0
    }

df_transactions = pd.DataFrame(columns = [
    "operation_time", 
    "symbol", 
    "operation_type", 
    "position",
    "coin_amount", 
    "price", 
    "fee", 
    "comission",
    "comission_fee",
    "after_comission_calculated_coin_amount",
    "total_cash",
    "stop_price",
    "sell_price",
    "explanation"])

macd_volume = {"MACD" : 0.0,
                   'Volume': 0.0,
                   "Result": 3}

df_macd_volume = pd.DataFrame(columns = [
    "MACD", 
    "Volume", 
    "Result"])


Binance = BC("","")

#CandleData = Binance.get_candles(parameters["symbol"],parameters["interval"], 1200)
print("Getting candlestick data. Please wait...")

CandleData = Binance.get_historic_candles(parameters["symbol"], parameters["interval"], "20 Jul, 2022")

print("Candlestick data was taken.")

candles = ST(CandleData).MACDS_RSI_EMA_Strategy()

def toggle_has():
    if parameters["has_cash"]:
        parameters["has_cash"] = False
        parameters["has_coin"] = True
    else:
        parameters["has_cash"] = True
        parameters["has_coin"] = False
        
def calculate_risk_amount(cash:float, risk_percentage:float):
    return cash * risk_percentage

def calculate_coin_amount(position:str, operation :str, symbol:str, buy_price:int, stop_price:int, cash:float, risk_percentage:float):
    risk_amount = calculate_risk_amount(cash, risk_percentage)
    
    if position == "Long":        
        delta = buy_price - stop_price        
    if position == "Short":
        delta = stop_price - buy_price
        
    coin_amount = risk_amount / delta
    coin_amount = Binance.normalize_coin(symbol, coin_amount, operation)
    cash_amount_buy_coin = coin_amount * buy_price
    if cash_amount_buy_coin >= cash:
        coin_amount = cash / buy_price
        coin_amount = Binance.normalize_coin(symbol, coin_amount, operation)
    return coin_amount

def calculate_hour_for_interest(start_time, end_time):
    start_time =  pd.Timestamp(start_time)
    start_time = start_time - pd.DateOffset(minutes=start_time.minute)
    end_time =  pd.Timestamp(end_time)
    end_time = end_time - pd.DateOffset(minutes=end_time.minute)
    end_time = end_time + pd.DateOffset(minutes = 60)
    time_delta = end_time - start_time
    time_delta = time_delta.seconds//3600
    return time_delta
    
    
def calculate_interest_hourly(borrowed_money, buy_time, sell_time, interest_rate):
    #https://www.binance.com/en/support/faq/360030157812
    hours = calculate_hour_for_interest(buy_time, sell_time)
    return  borrowed_money * (interest_rate / 24) * int(hours)
        

def calculate_sell_price(position, buy_price, stop_price, risk_reward_ratio):
     if position == "Long":
         delta = buy_price - stop_price
         return buy_price + delta * risk_reward_ratio
     if position == "Short":
         delta = stop_price - buy_price
         return buy_price - delta * risk_reward_ratio

def calculate_comission(coin_amount, comission_rate):
    parameters["comission"] = coin_amount * Binance.CONST_COMISSION_RATE
    parameters["before_comission_calculated_coin_amount"] = coin_amount
    parameters["after_comission_calculated_coin_amount"] = coin_amount - parameters["comission"]
    parameters["coin_amount"] = parameters["after_comission_calculated_coin_amount"]
    
def insert_transaction(operation_time,  operation_type, position, coin_amount, price, 
                       comission, comission_fee, after_comission_calculated_coin_amount, 
                       fee, stop_price, sell_price, total_cash, explanation = ""):
    
    data ={
                "operation_time": operation_time ,
                "symbol": parameters["symbol"], 
                "operation_type" : operation_type,
                "position": position,
                "coin_amount" : coin_amount,
                "price" : price,
                "comission": comission,
                "comission_fee":comission_fee,
                "after_comission_calculated_coin_amount" : after_comission_calculated_coin_amount,
                "fee" : fee ,                 
                "stop_price":stop_price,
                "sell_price":sell_price,
                "total_cash": total_cash,
                "explanation": explanation          
                }
    return data

def buy_coin(decision:str, candles, i):
    if decision == "Long":
        parameters["position"] = "Long"
        parameters["stop_price"] = candles["atrlower"][i]
    
    elif decision == "Short":
        parameters["position"] = "Short"
        parameters["stop_price"] = candles["atrupper"][i]
    
    macd_volume.clear()
    parameters["operation"] = "Buy"    
    parameters["buy_price"] = candles["Close"][i]    
    parameters["coin_amount"] = calculate_coin_amount(parameters["position"], parameters["operation"], parameters["symbol"],  parameters["buy_price"], parameters["stop_price"], parameters["cash"], parameters["risk_percentage"])    
    parameters["sell_price"] = calculate_sell_price(parameters["position"], parameters["buy_price"], parameters["stop_price"], parameters["risk_reward_ratio"])
    parameters["sell_price"] = calculate_sell_price(parameters["position"], parameters["buy_price"], parameters["stop_price"], parameters["risk_reward_ratio"])
    calculate_comission(parameters["coin_amount"], Binance.CONST_COMISSION_RATE)
    parameters["comission_fee"] = parameters["buy_price"] * parameters["comission"]    
    fee = parameters["before_comission_calculated_coin_amount"] * parameters["buy_price"]
    parameters["cash"] -= fee        
    toggle_has()    
    parameters["total_cash"] = parameters["cash"] + parameters["coin_amount"] * parameters["buy_price"]
    parameters["operation_time"] = candles["Id"][i+1]
    macd_volume["MACD"] = candles["MACD"][i]
    macd_volume["Volume"] = candles["Volume"][i]
    if decision == "Long":
        print("Long bought",parameters["total_cash"])
    elif decision == "Short":
        print("Short bought",parameters["total_cash"])
    
    data = insert_transaction(parameters["operation_time"], parameters["operation"], parameters["position"], 
                               parameters["before_comission_calculated_coin_amount"], parameters["buy_price"],
                               parameters["comission"], parameters["comission_fee"], parameters["after_comission_calculated_coin_amount"],
                               fee, parameters["stop_price"], parameters["sell_price"], parameters["total_cash"]
                               )
        
    return (data,0)


def sell_long(candles, i):
    parameters["operation"] = "Sell"
    toggle_has()
    calculate_comission(parameters["coin_amount"], Binance.CONST_COMISSION_RATE)
    fee = 0.0
    price = 0.0
    if candles["High"][i] >= parameters["sell_price"]:
        parameters["comission_fee"] = parameters["sell_price"] * parameters["comission"]
        fee = parameters["sell_price"] * parameters["coin_amount"]
        price = parameters["sell_price"]
        explanation = "Profit!"
        macd_volume["Result"] = 1
        print("Long sold. Profit!", parameters["total_cash"])
    elif candles["Low"][i] <= parameters["stop_price"]:
        parameters["comission_fee"] = parameters["stop_price"] * parameters["comission"]
        fee = parameters["stop_price"] * parameters["coin_amount"]
        price = parameters["stop_price"]
        explanation = "Loss!"
        macd_volume["Result"] = 0
        print("Long sold. Loss!", parameters["total_cash"])
        
    parameters["cash"] += fee
    parameters["total_cash"] = parameters["cash"]

    
    
    data = insert_transaction(candles["Id"][i], parameters["operation"], parameters["position"], 
                               parameters["before_comission_calculated_coin_amount"], price,
                               parameters["comission"], parameters["comission_fee"], parameters["after_comission_calculated_coin_amount"],
                               fee, "-", "-",parameters["total_cash"], explanation
                               )
    return (data, macd_volume)

def sell_short(candles, i):
    parameters["operation"] = "Sell"
    toggle_has()
    calculate_comission(parameters["coin_amount"], Binance.CONST_COMISSION_RATE)
    margin_cost = calculate_interest_hourly(parameters["buy_price"],parameters["operation_time"], candles["Id"][i], Binance.CONST_DAILY_INTEREST_RATE)
    price = 0.0
    explanation = 0.0
    if candles["High"][i] >= parameters["stop_price"]:
        parameters["comission_fee"] = parameters["stop_price"] * parameters["comission"]
        net_loss = (parameters["stop_price"] - parameters["buy_price"]) * parameters["coin_amount"] + margin_cost
        parameters["total_cash"] -= net_loss
        price = parameters["stop_price"]
        explanation = "Loss!"
        macd_volume["Result"] = 0
        print("Short sold. Loss!", parameters["total_cash"])
    elif candles["Low"][i] <= parameters["sell_price"]:
        parameters["comission_fee"] = parameters["sell_price"] * parameters["comission"]
        net_profit = (parameters["buy_price"] - parameters["sell_price"]) * parameters["coin_amount"] - margin_cost
        parameters["total_cash"] += net_profit
        price = parameters["sell_price"]
        explanation = "Profit!"
        macd_volume["Result"] = 0
        print("Short sold. Profit!", parameters["total_cash"])
    
    parameters["cash"] = parameters["total_cash"]
    fee = parameters["sell_price"] * parameters["coin_amount"]
    
   
    
    data = insert_transaction(candles["Id"][i], parameters["operation"], parameters["position"], 
                   parameters["before_comission_calculated_coin_amount"], price,
                   parameters["comission"], parameters["comission_fee"], parameters["after_comission_calculated_coin_amount"],
                   fee, "-", "-", parameters["total_cash"], explanation
                   )
    
    return (data, macd_volume)
    
    
    
    
    
for i in range(len(candles)):
    if parameters["has_cash"]:
        if candles["Decision"][i] == "Long":
            data = buy_coin(candles["Decision"][i], candles, i)            
            df_transactions = df_transactions.append(data[0], ignore_index = True)
            continue
        elif candles["Decision"][i] == "Short":
            data = buy_coin(candles["Decision"][i], candles, i)            
            df_transactions = df_transactions.append(data[0], ignore_index = True)
            continue
        else:
            continue
    if parameters["has_coin"]:
        if parameters["position"] == "Long":
            if  candles["High"][i] >= parameters["sell_price"]:                
                #profit
                data = sell_long(candles, i)                
                df_transactions = df_transactions.append(data[0], ignore_index = True) 
                df_macd_volume = df_macd_volume.append(data[1], ignore_index = True)
                continue
            elif candles["Low"][i] <= parameters["stop_price"]:                
                #loss
                data = sell_long(candles, i)                
                df_transactions = df_transactions.append(data[0], ignore_index = True)
                df_macd_volume = df_macd_volume.append(data[1], ignore_index = True)
                continue
        elif parameters["position"] == "Short":
            if candles["High"][i] >= parameters["stop_price"]:                
                #loss
                data = sell_short(candles, i)
                df_transactions = df_transactions.append(data[0], ignore_index = True)        
                df_macd_volume = df_macd_volume.append(data[1], ignore_index = True)
                continue
            elif candles["Low"][i] <= parameters["sell_price"]:                
                #profit
                data = sell_short(candles, i)
                df_transactions = df_transactions.append(data[0], ignore_index = True)
                df_macd_volume = df_macd_volume.append(data[1], ignore_index = True)
                print("Short sold. Profit!", parameters["total_cash"])
                continue
                
            
profit = df_transactions['explanation'].value_counts()['Profit!']
loss = df_transactions['explanation'].value_counts()['Loss!']

win_rate = profit / (profit + loss)

print(win_rate)

from sklearn.preprocessing import StandardScaler
sc=StandardScaler()

df_macd_volume_scaled = sc.fit_transform(df_macd_volume.iloc[:,0:2])
result = df_macd_volume["Result"].to_numpy()

import matplotlib.pyplot as plt

#plt.scatter(df_macd_volume_scaled[:,0], df_macd_volume_scaled[:,1], c=df_macd_volume["Result"].to_numpy())
plt.scatter(df_macd_volume["MACD"].to_numpy(), df_macd_volume["Volume"].to_numpy(), c=df_macd_volume["Result"].to_numpy())
plt.show()



