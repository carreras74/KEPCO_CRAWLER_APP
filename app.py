import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ----------------------------------------------------
# 1. 페이지 설정
# ----------------------------------------------------
st.set_page_config(
    page_title="경북 송전망 여유용량 모니터링",
    page_icon="⚡",
    layout="wide"
)

# ----------------------------------------------------
# 2. 구글 스프레드시트 데이터 연동
# ----------------------------------------------------
@st.cache_data(ttl=600)  # 10분 캐시
def load_substation_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_key.json", scope)
        client = gspread.authorize(creds)
        
        # ★★★ 본인의 구글 시트 URL 입력 ★★★
        sheet_url = "https://docs.google.com/spreadsheets/d/1QsHxBwA40ElWl9AAMf1HrKXjXRI_QyhHdgTOqWnZQQk/edit?gid=942113142#gid=942113142"
        
        doc = client.open_by_url(sheet_url)
        sheet = doc.get_worksheet(0)
        
        # 5행부터 실제 데이터 헤더 및 내용 로드 (또는 전체 데이터 로드)
        all_values = sheet.get_all_values()
        
        # 헤더: 순위, 변전소, 2026년, 2027년, 2028년, 2029년, 2030년, 2031년, 2032년, 발전허가 신청용량, 접속예정 사업자
        header = ["순위", "변전소", "2026년", "2027년", "2028년", "2029년", "2030년", "2031년", "2032년", "발전허가신청용량", "접속예정사업자"]
        
        # 5행(인덱스 5) 이후 실제 데이터 행 추출 (합계/평균 행 제외)
        rows = []
        for r in all_values[5:]:
            if not r or r[0] in ["합계", "평균", ""]:
                continue
            rows.append(r[:11])
            
        df = pd.DataFrame(rows, columns=header)
        
        # 숫자형 컬럼 형변환
        num_cols = ["2026년", "2027년", "2028년", "2029년", "2030년", "2031년", "2032년", "발전허가신청용량", "접속예정사업자"]
        for col in num_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "").str.strip(), errors="coerce").fillna(0)
            
        return df
    except Exception as e:
        st.error(f"구글 시트 연동 실패: {e}\n(google_key.json 위치와 시트 URL, 공유 권한을 확인하세요)")
        return pd.DataFrame()

df = load_substation_data()

# ----------------------------------------------------
# 3. 사이드바 검색 및 필터 옵션
# ----------------------------------------------------
st.title("⚡ 경상북도 송전망 여유용량 실시간 현황")
st.caption("한전ON 분산전원 연계정보 기반 | 경북 관할 변전소 여유용량 분석")
st.markdown("---")

if not df.empty:
    st.sidebar.header("🔍 정렬 및 필터 설정")
    
    # 기준 연도 선택 (기본: 2026년)
    year_options = ["2026년", "2027년", "2028년", "2029년", "2030년", "2031년", "2032년"]
    selected_year = st.sidebar.selectbox("기준 연도 선택", year_options, index=0)
    
    # 0 MW 제외 필터
    hide_zero = st.sidebar.checkbox("여유용량 0 MW 변전소 제외", value=True)
    
    # 변전소 검색
    search_keyword = st.sidebar.text_input("변전소 이름 검색", "")
    
    # ----------------------------------------------------
    # 4. 내림차순 정렬 및 데이터 가공 (요구사항 4번 완벽 반영)
    # ----------------------------------------------------
    filtered_df = df.copy()
    
    if hide_zero:
        filtered_df = filtered_df[filtered_df[selected_year] > 0]
        
    if search_keyword:
        filtered_df = filtered_df[filtered_df["변전소"].str.contains(search_keyword)]
        
    # 선택 연도 기준 최대 여유용량 내림차순 정렬
    filtered_df = filtered_df.sort_values(by=selected_year, ascending=False).reset_index(drop=True)
    filtered_df["순위"] = range(1, len(filtered_df) + 1)

    # ----------------------------------------------------
    # 5. 핵심 지표 카드 (KPI)
    # ----------------------------------------------------
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    top_station = filtered_df.iloc[0] if not filtered_df.empty else None
    
    with kpi1:
        st.metric(f"{selected_year} 최대 여유 변전소", f"{top_station['변전소'] if top_station is not None else '-'}", f"{top_station[selected_year] if top_station is not None else 0:,.0f} MW")
    with kpi2:
        st.metric("분석 대상 변전소", f"{len(df)}개소")
    with kpi3:
        valid_cnt = len(df[df[selected_year] > 0])
        st.metric(f"{selected_year} 여유 가능 변전소", f"{valid_cnt}개소")
    with kpi4:
        total_mw = filtered_df[selected_year].sum() if not filtered_df.empty else 0
        st.metric(f"{selected_year} 경북 총 여유용량", f"{total_mw:,.0f} MW")
        
    st.markdown("---")

    # ----------------------------------------------------
    # 6. 상위 변전소 순위 차트 & 상세 테이블
    # ----------------------------------------------------
    st.subheader(f"📊 {selected_year} 송전망 여유용량 TOP 15 변전소 (내림차순)")
    
    chart_df = filtered_df.head(15)[["변전소", selected_year]].set_index("변전소")
    st.bar_chart(chart_df)
    
    st.subheader("📋 전체 변전소 연계 여유 현황 목록")
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "순위": st.column_config.NumberColumn("순위", format="%d위"),
            "변전소": st.column_config.TextColumn("변전소"),
            "2026년": st.column_config.NumberColumn("2026년(MW)", format="%,.0f MW"),
            "2027년": st.column_config.NumberColumn("2027년(MW)", format="%,.0f MW"),
            "2028년": st.column_config.NumberColumn("2028년(MW)", format="%,.0f MW"),
            "2029년": st.column_config.NumberColumn("2029년(MW)", format="%,.0f MW"),
            "2030년": st.column_config.NumberColumn("2030년(MW)", format="%,.0f MW"),
            "2031년": st.column_config.NumberColumn("2031년(MW)", format="%,.0f MW"),
            "2032년": st.column_config.NumberColumn("2032년(MW)", format="%,.0f MW"),
            "발전허가신청용량": st.column_config.NumberColumn("신청용량(MW)", format="%,.1f MW"),
            "접속예정사업자": st.column_config.NumberColumn("접속사업자", format="%d명")
        }
    )
else:
    st.warning("데이터를 불러오는 중입니다. 구글 시트 연동 설정을 확인해 주세요.")
