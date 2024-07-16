import logging
import os
import threading
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# 디버깅을 위한 로그 설정
logging.basicConfig(level=logging.INFO)

# 크롬 드라이버 옵션 설정
chrome_options = Options()
chrome_options.add_argument("--headless")  # 백그라운드에서 실행
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")  # GPU 비활성화
chrome_options.add_argument("window-size=1920x1080")  # 화면 크기 설정
chrome_options.add_argument("--disable-extensions")  # 확장 프로그램 비활성화
chrome_options.add_argument("--proxy-server='direct://'")  # 프록시 서버 비활성화
chrome_options.add_argument("--proxy-bypass-list=*")  # 프록시 서버 비활성화
chrome_options.add_argument("--start-maximized")  # 화면 최대화
chrome_options.add_argument("--enable-automation")  # 자동화 플래그 설정
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

data = {}

# 크롤링 함수
def crawl_krx_data(stock , start_date, end_date):
    global data
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(
            "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020302")  # 실제 KRX 데이터 URL로 변경
        time.sleep(10)  # 페이지 로딩 대기

        # JavaScript를 사용하여 AJAX 요청을 전송
        # - inqTpCd = 1 : 기간합계 / 2 : 일별 추이
        # - trdVolVal = 1 : 거래량 / 2 : 거래대금
        # - askBid = 1 : 매도 / 2 : 매수 / 3 : 순매수

        ISU_CD = stock["ISU_CD"]
        ISU_SRT_CD = stock["ISU_SRT_CD"]
        ISU_NM = stock["ISU_NM"]
        ISU_NICK = stock["ISU_SRT_CD"]+"/"+stock["ISU_NM"]

        script = f"""
        var xhr = new XMLHttpRequest();
        xhr.open('POST', 'http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd', true);
        xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
        xhr.onreadystatechange = function() {{
            if (xhr.readyState == 4 && xhr.status == 200) {{
                console.log(xhr.responseText);
                window.responseData = xhr.responseText;
            }}
        }};
        var params = [
            'bld=dbms/MDC/STAT/standard/MDCSTAT02303',
            'locale=ko_KR',
            'inqTpCd=2',
            'trdVolVal=2',
            'askBid=3',
            'isuCd={ISU_CD}',
            'isuCd2={ISU_SRT_CD}',
            'strtDd={start_date}',
            'endDd={end_date}',
            'tboxisuCd_finder_stkisu0_0={ISU_NICK}',
            'codeNmisuCd_finder_stkisu0_0={ISU_NM}',
            'param1isuCd_finder_stkisu0_0=ALL',
            'share=1',
            'money=1',
            'detailView=1',
            'csvxls_isNo=false'
        ];
        xhr.send(params.join('&'));
        """
        driver.execute_script(script)
        time.sleep(5)  # AJAX 요청 대기

        # JavaScript에서 설정한 데이터를 가져옴
        response = driver.execute_script("return window.responseData;")
        data['response'] = response

        print(response)  # 데이터 출력
        driver.quit()
    except Exception as e:
        print(f"Error occurred: {e}")

# 백그라운드에서 크롤링 함수 실행
def start_crawling_thread(stock , start_date, end_date):
    thread = threading.Thread(target=crawl_krx_data, args=(stock , start_date, end_date))
    thread.daemon = True
    thread.start()

@app.route('/')
def home():
    return redirect(url_for('main'))

# Define the 'main' endpoint
@app.route('/main')
def main():
    return render_template('main.html')

def StockData():
    url = "https://data-dbg.krx.co.kr/svc/sample/apis/sto/ksq_isu_base_info.json"
    params = {
        "AUTH_KEY": "74D1B99DFBF345BBA3FB4476510A4BED4C78D13A",
        "basDd": "20240712"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json().get('OutBlock_1', [])
    except Exception as e:
        print(f"Error occurred: {e}")
        data = []

    return data

@app.route('/StockList')
def StockList():
    data = StockData()
    return jsonify(data)

if __name__ == '__main__':
    stock_data = StockData()
    print(stock_data)

    for stock in stock_data:
        ISU_CD = stock['ISU_CD']
        list_date = stock['LIST_DD']
        start_date = list_date
        end_date = (datetime.strptime(list_date, '%Y%m%d') + timedelta(days=365)).strftime('%Y%m%d')

        print(f"Stock Code: {ISU_CD}, Start Date: {start_date}, End Date: {end_date}")
        start_crawling_thread( stock , start_date, end_date)
        time.sleep(10)  # 각 요청 간에 약간의 딜레이를 둠

    app.run(debug=True)
