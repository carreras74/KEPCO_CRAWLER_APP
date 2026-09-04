import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------------------------------------------
# 1. 페이지 기본 설정
# ----------------------------------------------------
st.set_page_config(
    page_title="전국 송전여유용량 실시간 파악 APP",
    page_icon="⚡",
    layout="wide"
)

# ----------------------------------------------------
# 2. 구글 시트에서 데이터 로드
# ----------------------------------------------------
@st.cache_data(ttl=600) # 10분마다 새로고침
def load_data_from_gsheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # 선생님의 키 파일 이름인 google_key.json 으로 변경 완료!
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_key.json", scope)
        client = gspread.authorize(creds)
        
        # ★★★ 여기에 crawler.py와 똑같은 구글 스프레드시트 주소를 덮어쓰세요 ★★★
        sheet_url = "여기를_지우고_복사한_구글시트_URL을_붙여넣으세요"
        
        doc = client.open_by_url(sheet_url)
        sheet = doc.worksheet("Sheet1")
        
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"구글 시트 연동 실패: {e}\n(google_key.json 파일이 없거나 URL이 잘못되었을 수 있습니다.)")
        return pd.DataFrame()

df = load_data_from_gsheets()

# ----------------------------------------------------
# 3. UI 및 내림차순 정렬 기능
# ----------------------------------------------------
st.title("⚡ 전국 송전 및 배전 여유용량 실시간 모니터링")
st.markdown("매일 자동으로 한전ON 데이터를 수집하여 시도별/읍면동별 여유용량을 제공합니다.")
st.markdown("---")

if not df.empty:
    st.sidebar.header("🔍 지역 검색")
    
    sido_list = sorted(df['시도'].unique().tolist())
    sido_list.insert(0, "전체")
    
    selected_sido = st.sidebar.selectbox("시/도를 선택하세요", sido_list)
    
    if selected_sido == "전체":
        filtered_df = df.copy()
    else:
        filtered_df = df[df['시도'] == selected_sido]
        
    # 여유용량이 가장 많은 곳부터 내림차순 정렬 (요구사항 4번 완벽 적용)
    filtered_df['여유용량(MW)'] = pd.to_numeric(filtered_df['여유용량(MW)'], errors='coerce').fillna(0)
    filtered_df = filtered_df.sort_values(by='여유용량(MW)', ascending=False).reset_index(drop=True)
    
    if selected_sido != "전체":
        st.subheader(f"📍 {selected_sido} 여유용량 현황")
    else:
        st.subheader("📍 전국 여유용량 현황")
        
    if not filtered_df.empty:
        top_region = filtered_df.iloc[0]
        st.success(f"💡 현재 **{selected_sido}**에서 여유용량이 가장 많은 곳은 **{top_region['시군구']} {top_region['읍면동']} ({top_region['여유용량(MW)']}MW)** 입니다.")
    
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "여유용량(MW)": st.column_config.NumberColumn(
                "여유용량(MW)",
                format="%.1f MW"
            )
        }
    )
    st.caption(f"최종 업데이트 일시: {df['업데이트일시'].iloc[0] if '업데이트일시' in df.columns else '알 수 없음'}")
else:
    st.warning("데이터를 불러오는 중이거나 크롤러가 아직 실행되지 않았습니다.")
