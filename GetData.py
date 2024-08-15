import json
import os

import numpy as np
import requests
from datetime import datetime, timedelta
from models import Stock , db
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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


def GetStockData():
    while True:
        # 현재 시간 확인
        current_time = datetime.now().strftime('%H:%M')

        # 현재 시간이 오후 8시이면 데이터 수집 시작
        if current_time == '03:17':
            url = "https://apis.data.go.kr/1160100/service/GetKrxListedInfoService/getItemInfo"
            current_date = datetime.now().strftime('%Y%m%d')
            current_date = "20240723"

            params = {
                "serviceKey": "kC7MdG1iVeZvHxVf3e8MRXeWRnkNnf9+0AVQRkwCC5dxcRk90iZn1ULrlKk2b2lH8rdYzbBtEIG/FMUSBAQbOw==",
                "resultType": "json",
                "numOfRows": 1000,
                "pageNo": 1,
                "basDt": current_date
            }
            print(params)

            try:
                # 첫 번째 호출로 totalCount 가져오기
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                totalCount = data.get('response', {}).get('body', {}).get('totalCount', 0)
                numOfRows = params["numOfRows"]
                total_pages = (totalCount // numOfRows) + (1 if totalCount % numOfRows != 0 else 0)

                print(f"총 {totalCount}개의 데이터를 {total_pages} 페이지에 걸쳐 가져옵니다.")

                for page in range(1, total_pages + 1):
                    params["pageNo"] = page

                    # 완전한 URL 출력
                    request = requests.Request('GET', url, params=params).prepare()
                    print(f"API 호출 URL: {request.url}")

                    response = requests.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                    items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])

                    print(f"{page}/{total_pages} 페이지 처리 중... {len(items)}개의 항목을 가져왔습니다.")

                    parsed_items = []
                    for item in items:
                        parsed_item = {
                            "basDt": item.get("basDt"),
                            "srtnCd": item.get("srtnCd"),
                            "isinCd": item.get("isinCd"),
                            "mrktCtg": item.get("mrktCtg"),
                            "itmsNm": item.get("itmsNm"),
                            "crno": item.get("crno"),
                            "corpNm": item.get("corpNm") ,

                            "db1": "N" ,
                            "db2": "N" ,
                            "db3": "N" ,
                            "db4": "N" ,
                            "db5": "N" ,
                            "db6": "N" ,
                            "db7": "N" ,
                            "db8": "N" ,
                            "db9": "N" ,
                            "db10": "N" ,
                            "db11": "N" ,
                        }
                        # 중복 확인 및 삽입
                        if not Stock.select().where(Stock.isinCd == parsed_item["isinCd"]).exists():
                            parsed_items.append(parsed_item)

                    # 데이터베이스에 데이터 삽입
                    with db.atomic():
                        for item in parsed_items:
                            Stock.create(**item)

                    # 로그 출력
                    print(f"{page}/{total_pages} 페이지 데이터베이스에 삽입 완료.")

                    # API 호출 간격 두기 (1초)
                    time.sleep(1)

            except Exception as e:
                print(f"Error occurred: {e}")
        else:
            print("종목 정보 게더링 쓰레드 실행중 - 현재시간 : " + current_time)
        # 60초마다 현재 시간 확인
        time.sleep(30)


def generate_date_ranges(start_date, end_date):
    """start_date부터 end_date까지 1년 단위로 날짜 범위를 생성합니다."""
    start_date = datetime.strptime(start_date, "%Y%m%d")
    end_date = datetime.strptime(end_date, "%Y%m%d")

    date_ranges = []
    current_start = start_date

    while current_start < end_date:
        current_end = current_start + timedelta(days=( 365 * 2) )
        if current_end > end_date:
            current_end = end_date
        date_ranges.append((current_start.strftime("%Y%m%d"), current_end.strftime("%Y%m%d")))
        current_start = current_end + timedelta(days=1)

    return date_ranges


def insert_or_update(DetailDB , data):
    """데이터베이스에 삽입 또는 업데이트"""
    attempt = 0
    max_retries = 5
    retry_delay = 0.3

    while attempt < max_retries:
        try :
            query = DetailDB.select().where((DetailDB.srtnCd == data['srtnCd']) & (DetailDB.trd_dd == data['trd_dd']))
            if query.exists():
                query = DetailDB.update(data).where((DetailDB.srtnCd == data['srtnCd']) & (DetailDB.trd_dd == data['trd_dd']))
                query.execute()
            else:
                DetailDB.create(**data)
        except Exception as e:
            if "database is locked" in str(e):
                attempt += 1
                print(f"Database is locked. Retrying {attempt}/{max_retries} after {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Error: {e}")
                break


# JSON 파일에 데이터를 저장하는 함수
def savejson(filename, data, directory=None):
    if directory is None:
        directory = os.path.join(os.path.dirname(__file__), 'StockData')

    # 디렉토리가 존재하지 않으면 생성
    if not os.path.exists(directory):
        os.makedirs(directory)

    filepath = os.path.join(directory, filename)

    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    existing_data.append(data)

    with open(filepath, 'w') as f:
        json.dump(existing_data, f, indent=4, default=str)

    # print(f"Data saved to {filepath}")

def update_db_field(stock, db_field):
    setattr(stock, db_field, 'Y')
    stock.save()
    print(f"Updated {db_field} to 'Y' for stock {stock.isinCd}")


# JSON 파일에서 이미 저장된 종목과 기간을 로드하는 함수
def load_existing_data(directory=None):
    if directory is None:
        directory = os.path.join(os.path.dirname(__file__), 'StockData')

    existing_data = {}

    if not os.path.exists(directory):
        return existing_data

    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            parts = filename.split('_')
            if len(parts) == 4:
                stock_name = parts[1]
                start_date = parts[2]
                end_date = parts[3].replace('.json', '')
                key = (stock_name, start_date, end_date)
                existing_data[key] = True

    return existing_data


def GetStockDetailData( Limit , Page):

    try:

        existing_data = load_existing_data()

        # Stock 테이블에서 isinCd가 subquery에 없는 항목 선택하고 페이징 처리
        stocks = (Stock
                  .select().order_by(Stock.id.desc()).limit(Limit).offset(Limit * (Page - 1)))
        print(stocks)

        total_start_date = "20240701"
        total_end_date = datetime.now().strftime("%Y%m%d")

        date_ranges = generate_date_ranges(total_start_date, total_end_date)

        for stock in stocks:

            driver = webdriver.Chrome(options=chrome_options)
            driver.get("http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020302")
            time.sleep(3)  # 페이지 로딩 대기

            for idx, (start_date, end_date) in enumerate(date_ranges, start=1):
                db_field = f'db{idx}'

                key = (stock.itmsNm, start_date, end_date)
                if key in existing_data:
                    print("이미 존재 하는 데이터" + stock.itmsNm + " " + start_date+ "~"+end_date)
                    continue

                record = {}
                # 종목 데이터 정의
                ISU_CD = stock.isinCd
                ISU_SRT_CD = stock.srtnCd
                ISU_NM = stock.itmsNm
                ISU_NICK = stock.srtnCd + "/" + stock.itmsNm

                ##########################################
                # 종목 투자자별 데이터 준비
                ##########################################
                print(f"종목 {stock.isinCd} ({stock.itmsNm}) 데이터 가져오는 중... 기간: {start_date} ~ {end_date}")
                filename = f"투자금액_{stock.itmsNm}_{start_date}_{end_date}.json"

                script = f"""
                    var xhr = new XMLHttpRequest();
                    xhr.open('POST', 'http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd', true);
                    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
                    xhr.onreadystatechange = function() {{
                        if (xhr.readyState == 4 && xhr.status == 200) {{
                            console.log(xhr.responseText);
                            window.responseData = xhr.responseText;
                        }} else if (xhr.readyState == 4) {{
                            window.responseData = 'error';
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
                time.sleep(4)  # AJAX 요청 대기

                # JavaScript에서 설정한 데이터를 가져옴
                response = driver.execute_script("return window.responseData;")
                if response is None or response == 'error':
                    print(f"종목 {stock.isinCd} ({stock.itmsNm}) 데이터 요청 실패")
                    continue

                try:
                    data = json.loads(response)
                except json.JSONDecodeError:
                    print(f"종목 {stock.isinCd} ({stock.itmsNm}) 데이터 파싱 실패")
                    continue

                print(f"종목 {stock.isinCd} ({stock.itmsNm}) 데이터:")
                # JSON 데이터 파싱 및 데이터베이스에 기록
                for item in data.get('output', []):
                    record = {
                        'isinCd': ISU_CD,
                        'srtnCd': ISU_SRT_CD,
                        'itmsNm': ISU_NM,
                        'trd_dd': datetime.strptime(item['TRD_DD'], '%Y/%m/%d').date(),
                        'trdval1': item['TRDVAL1'],
                        'trdval2': item['TRDVAL2'],
                        'trdval3': item['TRDVAL3'],
                        'trdval4': item['TRDVAL4'],
                        'trdval5': item['TRDVAL5'],
                        'trdval6': item['TRDVAL6'],
                        'trdval7': item['TRDVAL7'],
                        'trdval8': item['TRDVAL8'],
                        'trdval9': item['TRDVAL9'],
                        'trdval10': item['TRDVAL10'],
                        'trdval11': item['TRDVAL11'],
                        'trdval_tot': item['TRDVAL_TOT'],
                        'current_datetime': datetime.now()
                    }
                    savejson(filename , record)
                print(record)

                if len(record) == 0 :
                    savejson(filename, record)
                    print(f"종목 {stock.isinCd} ({stock.itmsNm}) 기간: {start_date} ~ {end_date} 데이터 없음")
                    continue

                ##########################################
                # 종목 투자자별 거래수량 데이터 준비
                ##########################################
                print(f"종목 {stock.isinCd} ({stock.itmsNm}) 거래수량 데이터 가져오는 중... 기간: {start_date} ~ {end_date}")

                filename = f"투자수량_{stock.itmsNm}_{start_date}_{end_date}.json"

                script = f"""
                    var xhr = new XMLHttpRequest();
                    xhr.open('POST', 'http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd', true);
                    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
                    xhr.onreadystatechange = function() {{
                        if (xhr.readyState == 4 && xhr.status == 200) {{
                            console.log(xhr.responseText);
                            window.responseData = xhr.responseText;
                        }} else if (xhr.readyState == 4) {{
                            window.responseData = 'error';
                        }}
                    }};
                    var params = [
                        'bld=dbms/MDC/STAT/standard/MDCSTAT02303',
                        'locale=ko_KR',
                        'inqTpCd=2',
                        'trdVolVal=1',
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
                time.sleep(4)  # AJAX 요청 대기

                # JavaScript에서 설정한 데이터를 가져옴
                response = driver.execute_script("return window.responseData;")
                if response is None or response == 'error':
                    print(f"종목 {stock.isinCd} ({stock.itmsNm}) 거래수량 데이터 요청 실패")
                    continue

                try:
                    data = json.loads(response)
                except json.JSONDecodeError:
                    print(f"종목 {stock.isinCd} ({stock.itmsNm}) 거래수량 데이터 파싱 실패")
                    continue

                print(f"종목 {stock.isinCd} ({stock.itmsNm}) 거래수량 데이터:")


                # JSON 데이터 파싱 및 데이터베이스에 기록
                for item in data.get('output', []):
                    record = {
                        'isinCd': ISU_CD,
                        'srtnCd': ISU_SRT_CD,
                        'itmsNm': ISU_NM,
                        'trd_dd': datetime.strptime(item['TRD_DD'], '%Y/%m/%d').date(),
                        'trdcnt1': item['TRDVAL1'],
                        'trdcnt2': item['TRDVAL2'],
                        'trdcnt3': item['TRDVAL3'],
                        'trdcnt4': item['TRDVAL4'],
                        'trdcnt5': item['TRDVAL5'],
                        'trdcnt6': item['TRDVAL6'],
                        'trdcnt7': item['TRDVAL7'],
                        'trdcnt8': item['TRDVAL8'],
                        'trdcnt9': item['TRDVAL9'],
                        'trdcnt10': item['TRDVAL10'],
                        'trdcnt11': item['TRDVAL11'],
                        'trdcnt_tot': item['TRDVAL_TOT'],
                        'current_datetime': datetime.now()
                    }
                    savejson(filename , record)
                print(record)

                ##########################################
                # 종목 시세 데이터 준비
                ##########################################
                print(f"종목 {stock.isinCd} ({stock.itmsNm}) 시세 데이터 가져오는 중... 기간: {start_date} ~ {end_date}")
                filename = f"시세_{stock.itmsNm}_{start_date}_{end_date}.json"
                script = f"""
                                    var xhr = new XMLHttpRequest();
                                    xhr.open('POST', 'http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd', true);
                                    xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8');
                                    xhr.onreadystatechange = function() {{
                                        if (xhr.readyState == 4 && xhr.status == 200) {{
                                            console.log(xhr.responseText);
                                            window.responseData = xhr.responseText;
                                        }} else if (xhr.readyState == 4) {{
                                            window.responseData = 'error';
                                        }}
                                    }};
                                    var params = [
                                        'bld=dbms/MDC/STAT/standard/MDCSTAT01701',
                                        'locale=ko_KR',
                                        'adjStkPrc=2',
                                        'adjStkPrc_check=Y',
                                        'isuCd={ISU_CD}',
                                        'isuCd2={ISU_SRT_CD}',
                                        'strtDd={start_date}',
                                        'endDd={end_date}',
                                        'tboxisuCd_finder_stkisu0_0={ISU_NICK}',
                                        'codeNmisuCd_finder_stkisu0_0={ISU_NM}',
                                        'param1isuCd_finder_stkisu0_0=ALL',
                                        'share=1',
                                        'money=1',
                                        'csvxls_isNo=false'
                                    ];
                                    xhr.send(params.join('&'));
                                    """
                driver.execute_script(script)
                time.sleep(4)  # AJAX 요청 대기

                # JavaScript에서 설정한 데이터를 가져옴
                response = driver.execute_script("return window.responseData;")
                if response is None or response == 'error':
                    print(f"종목 {stock.isinCd} ({stock.itmsNm}) 시세 데이터 요청 실패")
                    continue

                try:
                    data = json.loads(response)
                except json.JSONDecodeError:
                    print(f"종목 {stock.isinCd} ({stock.itmsNm}) 시세 데이터 파싱 실패")
                    continue

                print(f"종목 {stock.isinCd} ({stock.itmsNm}) 시세 데이터:")
                # print(response)  # 데이터 출력

                # JSON 데이터 파싱 및 데이터베이스에 기록
                for item in data.get('output', []):
                    record = {
                        'isinCd': ISU_CD,
                        'srtnCd': ISU_SRT_CD,
                        'itmsNm': ISU_NM,
                        'trd_dd': datetime.strptime(item['TRD_DD'], '%Y/%m/%d').date(),
                        'acc_trdval': item['ACC_TRDVAL'],
                        'acc_trdvol': item['ACC_TRDVOL'],
                        'cmpprvdd_prc': item['CMPPREVDD_PRC'],
                        'fluc_rt': item['FLUC_RT'],
                        'fluc_tp_cd': item['FLUC_TP_CD'],
                        'list_shrs': item['LIST_SHRS'],
                        'mktcap': item['MKTCAP'],
                        'tdd_clsprc': item['TDD_CLSPRC'],
                        'tdd_hgprc': item['TDD_HGPRC'],
                        'tdd_lwprc': item['TDD_LWPRC'],
                        'tdd_opnprc': item['TDD_OPNPRC'],
                        'current_datetime': datetime.now()
                    }
                    savejson(filename , record)

                print(record)

            driver.quit()  # 각 종목이 끝나면 드라이버를 종료하고 새 드라이버를 시작합니다.

    except Exception as e:
        print(f"Error occurred: {e}")


def calculate_technical_indicators(df):
    # 이동 평균 계산
    df['MA20'] = df['clsprc'].rolling(window=20).mean()
    df['MA60'] = df['clsprc'].rolling(window=60).mean()
    df['MA33'] = df['clsprc'].rolling(window=33).mean()  # 33일 이동평균선

    # RSI 계산
    delta = df['clsprc'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD 계산
    exp12 = df['clsprc'].ewm(span=12, adjust=False).mean()
    exp26 = df['clsprc'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # 볼린저 밴드 계산
    df['stddev'] = df['clsprc'].rolling(window=20).std()
    df['upper_band'] = df['MA20'] + (df['stddev'] * 2)
    df['lower_band'] = df['MA20'] - (df['stddev'] * 2)

    return df


def calculate_scores(df, accumulated_tradecnts_list):
    score = 0
    reasons = []

    def add_reason(condition, points, reason_text):
        nonlocal score
        if condition.sum() > 0:
            score_change = condition.sum() * points
            score += score_change
            reasons.append(f"{reason_text}: {score_change}점")

    # 이동 평균선 골든 크로스, 데드 크로스 점수 계산
    df['golden_cross'] = np.where((df['MA20'] > df['MA60']) & (df['MA20'].shift(1) <= df['MA60'].shift(1)), -1, 0)
    df['dead_cross'] = np.where((df['MA20'] < df['MA60']) & (df['MA20'].shift(1) >= df['MA60'].shift(1)), 1, 0)
    add_reason(df['golden_cross'], -1, "골든 크로스 발생")
    add_reason(df['dead_cross'], 1, "데드 크로스 발생")

    # RSI 점수 계산
    df['rsi_overbought'] = np.where(df['RSI'] > 70, -1, 0)
    df['rsi_oversold'] = np.where(df['RSI'] < 30, 1, 0)
    add_reason(df['rsi_overbought'], -1, "RSI 과매수")
    add_reason(df['rsi_oversold'], 1, "RSI 과매도")

    # MACD 점수 계산
    df['macd_golden_cross'] = np.where((df['MACD'] > df['Signal']) & (df['MACD'].shift(1) <= df['Signal'].shift(1)), -1, 0)
    df['macd_dead_cross'] = np.where((df['MACD'] < df['Signal']) & (df['MACD'].shift(1) >= df['Signal'].shift(1)), 1, 0)
    add_reason(df['macd_golden_cross'], -1, "MACD 골든 크로스")
    add_reason(df['macd_dead_cross'], 1, "MACD 데드 크로스")

    # 볼린저 밴드 점수 계산
    df['band_expand'] = np.where(df['clsprc'] >= df['upper_band'], -1, 0)
    df['band_contract'] = np.where(
        (df['clsprc'] > df['lower_band']) & (df['clsprc'].shift(1) <= df['lower_band'].shift(1)), 1, 0)
    add_reason(df['band_expand'], -1, "볼린저 밴드 확장")
    add_reason(df['band_contract'], 1, "볼린저 밴드 수축 후 돌파")

    # 수급 분석 점수 계산
    #    df['foreign_buy_increase'] = np.where(accumulated_tradecnts_list['TradeCntSum9'] > accumulated_tradecnts_list['TradeCntSum9'].shift(1), 1, 0)
    #   df['foreign_sell_increase'] = np.where(accumulated_tradecnts_list['TradeCntSum9'] < accumulated_tradecnts_list['TradeCntSum9'].shift(1), -1, 0)
    #   add_reason(df['foreign_buy_increase'], 1, "외국인 순매수량 증가")
    #   add_reason(df['foreign_sell_increase'], -1, "외국인 순매도량 증가")

    # Calculate the ratio of TradeCntSum8 to the sum of TradeCntSum0 to TradeCntSum10
    #    accumulated_total = accumulated_tradecnts_list[[f'TradeCntSum{i}' for i in range(11)]].sum(axis=1)
    #   trade_ratio = accumulated_tradecnts_list['TradeCntSum8'] / accumulated_total

    # 개인 순매도량 분석 점수 계산 및 Grade 설정
    grade = "Fail"


    # Check each condition separately and set grade if any condition is met
    #if ((trade_ratio.shift(10) >= 15) & (trade_ratio.shift(10) <= 60)).any():
    #    grade = "A 조건 만족"
    #    add_reason(trade_ratio.shift(10), 1, "A 조건 만족 - 개인 순매도량 조건 만족")

    #if ((trade_ratio.shift(20) >= 15) & (trade_ratio.shift(20) <= 60)).any():
    #    grade = "B 조건 만족"
    #    add_reason(trade_ratio.shift(20), 1, "B 조건 만족 - 개인 순매도량 조건 만족")

    #if ((trade_ratio.shift(40) >= 15) & (trade_ratio.shift(40) <= 60)).any():
    #    grade = "C 조건 만족"
    #    add_reason(trade_ratio.shift(40), 1, "C 조건 만족 - 개인 순매도량 조건 만족")

    #if ((trade_ratio.shift(60) >= 15) & (trade_ratio.shift(60) <= 60)).any():
    #    grade = "D 조건 만족"
    #    add_reason(trade_ratio.shift(60), 1, "D 조건 만족 - 개인 순매도량 조건 만족")

    #if ((trade_ratio.shift(120) >= 15) & (trade_ratio.shift(120) <= 70)).any():
    #    grade = "E 조건 만족"
    #    add_reason(trade_ratio.shift(120), 1, "E 조건 만족 - 개인 순매도량 조건 만족")

    #if ((trade_ratio.shift(240) >= 20) & (trade_ratio.shift(240) <= 70)).any():
    #    grade = "F 조건 만족"
    #    add_reason(trade_ratio.shift(240), 1, "F 조건 만족 - 개인 순매도량 조건 만족")

    #if ((trade_ratio.shift(480) >= 30) & (trade_ratio.shift(480) <= 70)).any():
    #    grade = "G 조건 만족"
    #    add_reason(trade_ratio.shift(480), 1, "G 조건 만족 - 개인 순매도량 조건 만족")

    # 기타 지표 점수 계산
    df['below_33ma'] = np.where(df['clsprc'] < df['MA33'], 1, 0)
    add_reason(df['below_33ma'], 1, "33일 이동 평균선 밑")

    # 주가 변동에 따른 점수 계산
    df['price_rebound'] = np.where(df['clsprc'] > df['clsprc'].shift(1), 1, 0)
    df['price_fall'] = np.where(df['clsprc'] < df['clsprc'].shift(1), 1, 0)
    add_reason(df['price_rebound'], 1, "주가 반등")
    add_reason(df['price_fall'], 1, "주가 하락")

    return score, grade, reasons