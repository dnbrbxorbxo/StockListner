import logging
import os
import threading
import time

import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import Stock
from GetData import GetStockData , GetStockDetailData , calculate_technical_indicators , calculate_scores

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# 디버깅을 위한 로그 설정
logging.basicConfig(level=logging.INFO)

@app.route('/')
def home():
    return redirect(url_for('main'))

# Define the 'main' endpoint
@app.route('/main')
def main():
    stocks = Stock.select().dicts()
    return render_template('main.html', stocks=stocks)


import pandas as pd
from datetime import datetime, timedelta


def get_stock_data_from_db(stock, frequency='daily'):
    # query = (StockDetail
    #          .select()
    #          .where(StockDetail.srtnCd == stock)
    #          .group_by(StockDetail.trd_dd)
    #          .order_by(StockDetail.trd_dd.asc()))

    query = None

    if query.exists():
        data = [{
            'date': record.trd_dd,
            'opnprc': float(record.tdd_opnprc.replace(',', '')) if record.tdd_opnprc else 0,
            'clsprc': float(record.tdd_clsprc.replace(',', '')) if record.tdd_clsprc else 0,
            'lwprc': float(record.tdd_lwprc.replace(',', '')) if record.tdd_lwprc else 0,
            'hgprc': float(record.tdd_hgprc.replace(',', '')) if record.tdd_hgprc else 0,
            **{f'tradeval{i}': int(getattr(record, f'trdval{i + 1}').replace(',', '')) for i in range(11)},
            **{f'tradecnt{i}': int(getattr(record, f'trdcnt{i + 1}').replace(',', '')) for i in range(11)}
        } for record in query]

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])

        if frequency == 'weekly':
            df = df.resample('W-MON', on='date').agg({
                'opnprc': 'first',
                'clsprc': 'last',
                'lwprc': 'min',
                'hgprc': 'max',
                **{f'tradeval{i}': 'sum' for i in range(11)},
                **{f'tradecnt{i}': 'sum' for i in range(11)}
            }).dropna().reset_index()
        elif frequency == 'monthly':
            df = df.resample('M', on='date').agg({
                'opnprc': 'first',
                'clsprc': 'last',
                'lwprc': 'min',
                'hgprc': 'max',
                **{f'tradeval{i}': 'sum' for i in range(11)},
                **{f'tradecnt{i}': 'sum' for i in range(11)}
            }).dropna().reset_index()
        elif frequency == 'quarterly':
            df = df.resample('Q', on='date').agg({
                'opnprc': 'first',
                'clsprc': 'last',
                'lwprc': 'min',
                'hgprc': 'max',
                **{f'tradeval{i}': 'sum' for i in range(11)},
                **{f'tradecnt{i}': 'sum' for i in range(11)}
            }).dropna().reset_index()
        elif frequency == 'yearly':
            df = df.resample('Y', on='date').agg({
                'opnprc': 'first',
                'clsprc': 'last',
                'lwprc': 'min',
                'hgprc': 'max',
                **{f'tradeval{i}': 'sum' for i in range(11)},
                **{f'tradecnt{i}': 'sum' for i in range(11)}
            }).dropna().reset_index()

        dates = df['date'].dt.strftime('%Y-%m-%d').tolist()
        candlestick_data = df[['opnprc', 'clsprc', 'lwprc', 'hgprc']].values.tolist()

        # 누적 합 계산
        accumulated_tradevals_list = {f'TradeValSum{i}': df[f'tradeval{i}'].cumsum().tolist() for i in range(11)}
        tradevals = {f'TradeVal{i}': df[f'tradeval{i}'].tolist() for i in range(11)}
        tradeCnts = {f'TradeCnt{i}': df[f'tradecnt{i}'].tolist() for i in range(11)}

        closing_prices = df['clsprc'].tolist()

        # 기술적 지표 계산
        df = calculate_technical_indicators(df)

        # 종목별 점수 계산
        score, reasons = calculate_scores(df)

        return {
            "dates": dates,
            "candlestickData": candlestick_data,
            **accumulated_tradevals_list,
            **tradevals,
            **tradeCnts,
            "closing_prices": closing_prices,
            "score": int(score),
            "reasons": reasons
        }
    else:
        return None

@app.route('/GetStockDetailView', methods=['POST'])
def GetStockDetailView():
    stock_code = request.form.get('srtnCd')
    ViewType = request.form.get("ViewType")
    print(stock_code , ViewType)
    data = get_stock_data_from_db(stock_code , ViewType)
    print(data)
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Stock code not found"}), 404

@app.route('/GetStockReport', methods=['POST'])
def GetStockReport():
    StockCode = request.form.get('StockCode')
    data = get_stock_data_from_db(StockCode)

    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Stock code not found"}), 404



if __name__ == '__main__':
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":

        #   GetStockData_Thread = threading.Thread(target=GetStockData)
        #  GetStockData_Thread.start()

        threads = []
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 1)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 2)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 3)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 4)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 5)))

        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 6)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 7)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 8)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 9)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 10)))

        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 11)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 12)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 13)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 14)))
        threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 15)))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


    app.run(debug=True, port=5500)
