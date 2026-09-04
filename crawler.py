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
    print("🚀 전국 한전ON 데이터 크롤링 시작...")
    
    for sido_name, code in sido_codes.items():
        url = f"https://online.kepco.co.kr/ui/ew/service/EWM104D00W.xml?postfix={code}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
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
            
            print(f"✅ [{sido_name}] 데이터 수집 완료")
            time.sleep(1) # 서버 차단 방지용 1초 대기
            
        except Exception as e:
            print(f"❌ [{sido_name}] 수집 실패: {e}")

    df = pd.DataFrame(all_data)
    return df

# ----------------------------------------------------
# 2. 구글 스프레드시트 업데이트 함수
# ----------------------------------------------------
def update_google_sheets(df):
    if df.empty:
        print("⚠️ 수집된 데이터가 없습니다. 한전 API 구조를 확인해야 합니다.")
        return

    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 선생님의 키 파일 이름인 google_key.json 으로 변경 완료!
    creds = ServiceAccountCredentials.from_json_keyfile_name("google_key.json", scope)
    client = gspread.authorize(creds)
    
    # ★★★ 여기에 새로 만든 구글 스프레드시트 주소를 덮어쓰세요 ★★★
    spreadsheet_url = "여기를_지우고_복사한_구글시트_URL을_붙여넣으세요"
    
    try:
        doc = client.open_by_url(spreadsheet_url)
        sheet = doc.worksheet("Sheet1")
        
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        print(f"🎉 총 {len(df)}건 구글 시트 업데이트 완료!")
    except Exception as e:
        print(f"❌ 구글 시트 업데이트 실패. 권한이나 URL을 확인하세요: {e}")

# ----------------------------------------------------
# 3. 메인 실행
# ----------------------------------------------------
if __name__ == "__main__":
    df_kepco = fetch_all_kepco_data()
    update_google_sheets(df_kepco)
