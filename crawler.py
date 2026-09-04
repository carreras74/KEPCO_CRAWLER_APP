import requests
import xml.etree.ElementTree as ET
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import time

# ----------------------------------------------------
# 1. 한전ON 전국 데이터 크롤링 함수
# ----------------------------------------------------
def fetch_all_kepco_data():
    # 전국 시도 코드 목록 (한전ON 시스템 기준 맵핑 필요, 예시로 주요 지역 코드 구성)
    # 실제 한전ON의 시도별 postfix 코드가 다르다면 이 리스트를 수정해야 합니다.
    sido_codes = {
        "서울": "11", "부산": "26", "대구": "27", "인천": "28", "광주": "29", 
        "대전": "30", "울산": "31", "세종": "36", "경기": "41", "강원": "42", 
        "충북": "43", "충남": "44", "전북": "45", "전남": "46", "경북": "47", 
        "경남": "48", "제주": "50"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "sec-ch-ua-platform": '"Windows"',
        "Referer": "https://online.kepco.co.kr/EWM098D00",
    }

    all_data = []

    print("전국 한전ON 데이터 크롤링 시작...")
    
    for sido_name, code in sido_codes.items():
        # 시도별 파라미터 적용 (URL 구조는 테스트하신 기반으로 구성)
        url = f"https://online.kepco.co.kr/ui/ew/service/EWM104D00W.xml?postfix={code}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # XML 파싱
            root = ET.fromstring(response.content)
            
            # 주의: 실제 한전 XML 응답의 태그명으로 변경해야 합니다. (아래는 범용 예시)
            for item in root.findall('.//record'): 
                sigungu = item.findtext('SIGUNGU_NM', default='')
                dong = item.findtext('DONG_NM', default='')
                
                try:
                    capacity = float(item.findtext('CAPACITY', default='0'))
                except ValueError:
                    capacity = 0.0
                    
                all_data.append({
                    '시도': sido_name,
                    '시군구': sigungu,
                    '읍면동': dong,
                    '여유용량(MW)': capacity,
                    '업데이트일시': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                })
            
            print(f"[{sido_name}] 수집 완료")
            time.sleep(1) # 서버 부하 방지를 위한 1초 대기
            
        except Exception as e:
            print(f"[{sido_name}] 수집 실패: {e}")

    df = pd.DataFrame(all_data)
    return df

# ----------------------------------------------------
# 2. 구글 스프레드시트 업데이트 함수
# ----------------------------------------------------
def update_google_sheets(df):
    if df.empty:
        print("업데이트할 데이터가 없습니다.")
        return

    # 구글 API 인증 (기존 ETF 앱에서 쓰시는 credentials.json 파일 사용)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    
    # [수정 필요] 새로 만드신 구글 스프레드시트의 URL 또는 키값 입력
    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1QsHxBwA40ElWl9AAMf1HrKXjXRI_QyhHdgTOqWnZQQk/edit?hl=ko&pli=1&gid=0#gid=0"
    doc = client.open_by_url(spreadsheet_url)
    sheet = doc.worksheet("Sheet1")
    
    # 기존 데이터 지우고 최신 데이터로 덮어쓰기
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    print(f"총 {len(df)}건 구글 시트 업데이트 완료!")

# ----------------------------------------------------
# 3. 메인 실행 블록
# ----------------------------------------------------
if __name__ == "__main__":
    df_kepco = fetch_all_kepco_data()
    update_google_sheets(df_kepco)