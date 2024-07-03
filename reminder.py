import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
import pandas_market_calendars as mcal
from datetime import datetime, timedelta
from LineNotifyReminder import *
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def GetOpenPrice(Stockcode):
    try:           
                
        url = 'https://tw.stock.yahoo.com/quote/' + Stockcode
        web = requests.get(url)
        soup = BeautifulSoup(web.text, "html.parser")

        a = soup.select('.Fz\(32px\)')[0]  # 即時股價
        b = soup.select('.Fz\(20px\)')[0]  # 漲跌幅
        c = soup.select('#main-2-QuoteOverview-Proxy')[0].select('.Fw\(600\)')[4]  # 當日均價
        d = soup.select('#main-2-QuoteOverview-Proxy')[0].select('.Fw\(600\)')[1]  # 開盤價
        e = soup.select('#main-2-QuoteOverview-Proxy')[0].select('.Fw\(n\)')[0]  # 內盤
        f = soup.select('#main-2-QuoteOverview-Proxy')[0].select('.Fw\(n\)')[1]  # 外盤
        print(d.get_text())        
        return d.get_text()    
    except:
        print("Failed")
            
# 股票代號列表及其名稱
#stocks = {
#    '1514.TW': '亞力',
#    '4967.TW': '十銓',
#    '3374.TWO': '精材',
#    '3450.TW': '聯鈞',
#    '2351.TW': '順德',
#    '5347.TWO': '世界',
#    '4958.TW': '臻鼎-KY',
#    '3163.TWO': '波若威',
#    '2359.TW': '所羅門',
#    '2486.TW': '一詮',    
#    '3376.TW': '新日興'
#}
# Google Sheets 认证并连接
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(./stocksheet-427808-fc8909da447f.json', scope)
client = gspread.authorize(creds)

# 读取Google Sheets中的股票代号和名称
spreadsheet = client.open('StockSheet')
sheet = spreadsheet.sheet1
data = sheet.get_all_records()
stocks = {row['股票代號']: row['名稱'] for row in data}

# 获取交易所日历 (使用台湾交易所)
tw_cal = mcal.get_calendar('XTAI')  # 台湾证券交易所

# 检查日期是否为交易日
def is_trading_day(date, calendar):
    schedule = calendar.schedule(start_date=date.strftime('%Y-%m-%d'), end_date=date.strftime('%Y-%m-%d'))
    return not schedule.empty

# 获取前一个交易日
def get_previous_trading_day(date, calendar):
    while True:
        date -= timedelta(days=1)
        if is_trading_day(date, calendar):
            return date

today = datetime.today()
if not is_trading_day(today, tw_cal):
    print("Today is not a trading day. Exiting.")
else:
    yesterday = get_previous_trading_day(today, tw_cal)
    start_date_yesterday = yesterday.strftime('%Y-%m-%d')
    end_date_yesterday = today.strftime('%Y-%m-%d')

    for ticker, stock_name in stocks.items():
        try:
            # 下载前一天的 5 分钟 K 线数据
            data_yesterday = yf.download(ticker, start=start_date_yesterday, end=end_date_yesterday, interval='5m')

            # 获取今天的开盘价
            data_today = GetOpenPrice(ticker)

            today_open_price = float(data_today)

            # 过滤出 9:00 到 13:30 的数据
            data_yesterday = data_yesterday.between_time('09:00', '13:30')

            # 确保有足够的昨天数据点来计算布林通道
            if len(data_yesterday) >= 19:
                # 取昨天的最后19个数据点
                data_combined = data_yesterday.iloc[-19:].copy()

                # 模拟今天开盘价的数据点
                last_row = data_combined.iloc[-1].copy()
                last_row.name = pd.Timestamp(today)
                last_row['Close'] = today_open_price
                data_combined = pd.concat([data_combined, last_row.to_frame().T])

                # 计算布林通道
                window = 20
                data_combined['middle_band'] = data_combined['Close'].rolling(window=window).mean()
                data_combined['std_dev'] = data_combined['Close'].rolling(window=window).std()
                data_combined['upper_band'] = data_combined['middle_band'] + (2 * data_combined['std_dev'])
                data_combined['lower_band'] = data_combined['middle_band'] - (2 * data_combined['std_dev'])

                # 取今天开盘的布林通道值
                first_row_today = data_combined.iloc[-1]

                if first_row_today['Close'] > first_row_today['upper_band']:
                    SendMessage(stock_name + "\n開盤價:" + str(first_row_today['Close']) + "上軌:" + str(round(float(first_row_today['upper_band']),2)) + "\n價差:" + str(round(float(first_row_today['Close']) - float(first_row_today['upper_band']),2)))

                # 打印今天开盘价的布林通道
                print(f"\nTicker: {ticker}")
                print(f"Stock Name: {stock_name}")
                print("Today's opening price based on yesterday's and today's data:")
                print(f"Time: {first_row_today.name}")
                print(f"Open: {first_row_today['Close']}")
                print(f"Upper Band: {first_row_today['upper_band']}")
                print(f"Middle Band: {first_row_today['middle_band']}")
                print(f"Lower Band: {first_row_today['lower_band']}")
            else:
                print(f"\nTicker: {ticker}")
                print(f"Stock Name: {stock_name}")
                print("Not enough data points to calculate Bollinger Bands.")
        except Exception as e:
            SendMessage(stock_name + " Fail to get")
            print(f"\nTicker: {ticker}")
            print(f"Stock Name: {stock_name}")
            print("An error occurred:")
            print(f"Error: {e}")
