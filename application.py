import json
import logging
import os
import threading
import time

import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for
from peewee import SQL

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
    # 데이터베이스에서 모든 Stock 레코드 가져오기
    # 데이터베이스에서 모든 Stock 레코드를 db1 필드를 정수로 변환하여 내림차순 정렬하여 가져오기
    stocks = (Stock
              .select()
              .order_by(SQL('CAST(db1 AS INTEGER)').desc())
              .dicts())    # main.html 템플릿으로 렌더링
    return render_template('main.html', stocks=stocks)


def update_scores():
    # 데이터베이스에서 모든 Stock 레코드 가져오기
    stocks = Stock.select()

    # 각 주식 데이터의 점수를 계산하여 db1 필드에 업데이트
    for stock in stocks:
        try:
            data = get_stock_data_from_json(stock.itmsNm)  # 주식 데이터 DataFrame 가져오기
            score = data["score"]  # DataFrame에서 score의 평균을 계산

            # 점수를 db1 컬럼에 업데이트
            stock.db1 = score
            stock.save()  # 데이터베이스에 저장
            print(f"종목 : {stock.itmsNm} / Score : {score:.2f}")
        except Exception as e:

            # 점수를 db1 컬럼에 업데이트
            stock.db1 = 0
            stock.save()  # 데이터베이스에 저장
            print(f"종목에러 : {stock.itmsNm} / Error: {str(e)}")


    print("Scores updated successfully.")


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

    # 최소값 보정 후 누적 합 다시 계산
    for i in range(11):
        min_value = min(accumulated_tradevals_list[f'TradeValSum{i}'])
        accumulated_tradevals_list[f'TradeValSum{i}'] = [x - min_value for x in accumulated_tradevals_list[f'TradeValSum{i}']]

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


def calculate_FRVp(data, start_date, end_date):
    # Convert date strings to datetime objects
    dates = pd.to_datetime(data["dates"])

    # Create a DataFrame with the necessary data
    df = pd.DataFrame({
        'trd_dd': dates,
        'clsprc': data['closing_prices'],
        **{f'tradeval{i}': data[f'TradeVal{i}'] for i in range(11)},
        **{f'tradecnt{i}': data[f'TradeCnt{i}'] for i in range(11)},
    })

    # Filter the DataFrame for the given date range
    df = df[(df['trd_dd'] >= start_date) & (df['trd_dd'] <= end_date)]

    # Print the filtered DataFrame for debugging
    print("Filtered DataFrame:")
    print(df)

    # Initialize the volume profile dictionary
    volume_profile = {}

    # Calculate the average cost for each trade value and count pair
    for i in range(11):
        df[f"avg_cost{i}"] = df[f'tradeval{i}'] / df[f'tradecnt{i}'].replace(0, np.nan)

    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        for i in range(11):
            avg_cost = row[f"avg_cost{i}"]
            if pd.isna(avg_cost) or avg_cost == 0:
                continue

            # Find the closest closing price to the average cost
            closest_closing_price = min(df['clsprc'], key=lambda x: abs(x - avg_cost))

            # Convert the closest closing price to a string to use as a key
            closest_closing_price_str = str(int(closest_closing_price))

            # Add the trade value to the volume profile using the closest closing price as the key
            if closest_closing_price_str not in volume_profile:
                volume_profile[closest_closing_price_str] = 0

            volume_profile[closest_closing_price_str] += row[f'tradeval{i}']

    # Extract the keys and values from the volume profile
    profile_key = list(volume_profile.keys())
    profile_values = list(volume_profile.values())

    # Return the calculated data
    return {
        "dates": df['trd_dd'].dt.strftime('%Y-%m-%d').tolist(),
        "closing_prices": df['clsprc'].tolist(),
        "profile_key": profile_key,
        "profile_values": profile_values
    }


@app.route('/GetFRPVChartView', methods=['POST'])
def GetFRPVChartView():
    StockName = request.form.get('StockName')
    startDT = request.form.get("startDT")
    endDT = request.form.get("endDT")

    print(StockName , startDT , endDT)

    df = get_stock_data_from_json(StockName)
    frvp_data = calculate_FRVp(df, startDT, endDT)

    if frvp_data:
        return jsonify(frvp_data)
    else:
        return jsonify({"error": "Stock code not found"}), 404


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
        # threads = []
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 1)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 2)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 3)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 4)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 5)))
        #
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 6)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 7)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 8)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 9)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 10)))
        #
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 11)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 12)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 13)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 14)))
        # threads.append(threading.Thread(target=GetStockDetailData, args=( 200, 15)))
        #
        # for thread in threads:
        #     thread.start()
        #     time.sleep(1)
        #
        # for thread in threads:
        #     thread.join()

    # update_scores()


    app.run(debug=True, port=5500)
