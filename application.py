import json
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


def load_data_from_json(stock, data_type, directory=None):
    if directory is None:
        directory = os.path.join(os.path.dirname(__file__), 'StockData')

    all_data = []

    if not os.path.exists(directory):
        return None

    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            parts = filename.split('_')
            if len(parts) == 4 and parts[1] == stock and parts[0] == data_type:
                filepath = os.path.join(directory, filename)
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    all_data.extend(data)

    if not all_data:
        return None

    return all_data


def merge_stock_data(stock, directory=None):
    data_types = ['시세', '투자금액', '투자수량']
    merged_data = {}

    # 모든 열을 추적하기 위해 빈 집합을 생성
    all_columns = set()

    for data_type in data_types:
        data = load_data_from_json(stock, data_type, directory)
        if data:
            for item in data:
                key = (item['srtnCd'], item['trd_dd'])
                if key not in merged_data:
                    merged_data[key] = {}
                merged_data[key].update(item)
                all_columns.update(item.keys())

    if not merged_data:
        return None

    df = pd.DataFrame.from_dict(merged_data, orient='index').reset_index(drop=True)

    # DataFrame에 모든 열이 포함되어 있는지 확인하고, 누락된 열은 NaN으로 채움
    for col in all_columns:
        if col not in df.columns:
            df[col] = 0

    # 필요한 열을 자동으로 추가
    df = df.reindex(columns=sorted(all_columns))

    # 날짜 열을 먼저 처리

    info_columns = ['isinCd', 'srtnCd' , 'itmsNm']
    date_columns = ['trd_dd', 'current_datetime']
    for date_col in date_columns:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    # 숫자형 데이터 전처리: 쉼표 제거 및 NaN 처리
    for col in df.columns:
        if (col not in date_columns) and \
            (df[col].dtype == object) and \
            (col not in info_columns) :
            df[col] = df[col].str.replace(',', '')
            df[col] = pd.to_numeric(df[col], errors='coerce')

    pd.set_option('display.float_format', '{:.2f}'.format)

    return df

def get_stock_data_from_json(stock, frequency='daily'):

    df = merge_stock_data(stock)

    df['trd_dd'] = pd.to_datetime(df['trd_dd'], errors='coerce')
    df = df.dropna(subset=['trd_dd'])
    df = df.sort_values(by='trd_dd')

    for i in range(11):
        print(i)
        print(f'trdval{i + 1}')
        print(df[f'trdval{i + 1}'])

        df[f'trdval{i + 1}'] = df[f'trdval{i + 1}'].fillna(0).astype(float)
        df[f'trdcnt{i + 1}'] = df[f'trdcnt{i + 1}'].fillna(0).astype(float)

        df[f'tradeval{i}'] = df[f'trdval{i + 1}'].replace(',', '').astype(float)
        df[f'tradecnt{i}'] = df[f'trdcnt{i + 1}'].replace(',', '').astype(float)


    df['opnprc'] = df['tdd_opnprc'].replace(',', '').astype(float)
    df['clsprc'] = df['tdd_clsprc'].replace(',', '').astype(float)
    df['lwprc'] = df['tdd_lwprc'].replace(',', '').astype(float)
    df['hgprc'] = df['tdd_hgprc'].replace(',', '').astype(float)

    if frequency == 'weekly':
        df = df.resample('W-MON', on='trd_dd').agg({
            'opnprc': 'first',
            'clsprc': 'last',
            'lwprc': 'min',
            'hgprc': 'max',
            **{f'tradeval{i}': 'sum' for i in range(11)},
            **{f'tradecnt{i}': 'sum' for i in range(11)}
        }).dropna().reset_index()
    elif frequency == 'monthly':
        df = df.resample('M', on='trd_dd').agg({
            'opnprc': 'first',
            'clsprc': 'last',
            'lwprc': 'min',
            'hgprc': 'max',
            **{f'tradeval{i}': 'sum' for i in range(11)},
            **{f'tradecnt{i}': 'sum' for i in range(11)}
        }).dropna().reset_index()
    elif frequency == 'quarterly':
        df = df.resample('Q', on='trd_dd').agg({
            'opnprc': 'first',
            'clsprc': 'last',
            'lwprc': 'min',
            'hgprc': 'max',
            **{f'tradeval{i}': 'sum' for i in range(11)},
            **{f'tradecnt{i}': 'sum' for i in range(11)}
        }).dropna().reset_index()
    elif frequency == 'yearly':
        df = df.resample('Y', on='trd_dd').agg({
            'opnprc': 'first',
            'clsprc': 'last',
            'lwprc': 'min',
            'hgprc': 'max',
            **{f'tradeval{i}': 'sum' for i in range(11)},
            **{f'tradecnt{i}': 'sum' for i in range(11)}
        }).dropna().reset_index()

    dates = df['trd_dd'].dt.strftime('%Y-%m-%d').tolist()
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

@app.route('/GetStockDetailView', methods=['POST'])
def GetStockDetailView():
    StockName = request.form.get('StockName')
    ViewType = request.form.get("ViewType")
    print(StockName , ViewType)
    data = get_stock_data_from_json(StockName , ViewType)
    print(data)
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Stock code not found"}), 404

@app.route('/GetStockReport', methods=['POST'])
def GetStockReport():
    StockCode = request.form.get('StockCode')
    data = get_stock_data_from_json(StockCode)

    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "Stock code not found"}), 404



if __name__ == '__main__':
    # if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    #
    #     #GetStockData_Thread = threading.Thread(target=GetStockData)
    #     #GetStockData_Thread.start()
    #
    #     threads = []
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 1)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 2)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 3)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 4)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 5)))
    #
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 6)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 7)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 8)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 9)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 10)))
    #
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 11)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 12)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 13)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 14)))
    #     threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 15)))
    #
    #     for thread in threads:
    #         thread.start()
    #
    #     for thread in threads:
    #         thread.join()


    app.run(debug=True, port=5500)
