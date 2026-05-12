import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- [1. 기본 설정] ---
st.set_page_config(page_title="환경 오염과 건강 대시보드", layout="wide")
st.title("🌱 환경 오염과 건강에 해로운 관계 대시보드")

# --- [2. 데이터 로드 및 확실한 병합 함수] ---
@st.cache_data
def load_and_merge_data():
    db_path = 'environment_analysis.db'
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    # 각 테이블 로드
    df_w = pd.read_sql("SELECT * FROM 날씨", conn)
    df_a = pd.read_sql("SELECT * FROM 대기질", conn)
    df_s = pd.read_sql("SELECT * FROM 배출원", conn)
    df_h = pd.read_sql("SELECT * FROM 보건", conn)
    conn.close()

    # 영문 월 이름을 숫자로 바꾸는 사전 (23-Nov 형식 해결용)
    month_map = {
        'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
        'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }

    def clean(df):
        # 1. 지역 이름 공백 제거 및 주요 도시 통일
        df['지역'] = df['지역'].astype(str).str.strip()
        df.loc[df['지역'].str.contains('서울'), '지역'] = '서울'
        df.loc[df['지역'].str.contains('부산'), '지역'] = '부산'
        df.loc[df['지역'].str.contains('인천'), '지역'] = '인천'
        df = df[df['지역'].isin(['서울', '부산', '인천'])].copy()

        # 2. 날짜 '23-Nov' -> '2023-11' 형식으로 강제 변환
        def convert_date(d):
            try:
                parts = d.split('-') # ['23', 'Nov']
                year = "20" + parts[0]
                month = month_map[parts[1].capitalize()]
                return f"{year}-{month}"
            except:
                return None
        
        df['날짜_key'] = df['날짜'].apply(convert_date)
        return df.drop(columns=['날짜'])

    # 모든 테이블 전처리
    df_w, df_a, df_s, df_h = map(clean, [df_w, df_a, df_s, df_h])

    # 3. 데이터 병합 (날짜_key와 지역 기준)
    # 하나씩 순차적으로 합쳐서 누락 방지
    try:
        merged = pd.merge(df_w, df_a, on=['날짜_key', '지역'], how='inner')
        merged = pd.merge(merged, df_s, on=['날짜_key', '지역'], how='inner')
        merged = pd.merge(merged, df_h, on=['날짜_key', '지역'], how='inner')
        
        merged.rename(columns={'날짜_key': '날짜'}, inplace=True)
        merged['날짜'] = pd.to_datetime(merged['날짜'])
        return merged
    except:
        return pd.DataFrame()

# 데이터 실행
df = load_and_merge_data()

# --- [3. 메인 화면 구성] ---
if df is not None and not df.empty:
    # 사이드바 필터
    st.sidebar.header("📍 필터 설정")
    selected_cities = st.sidebar.multiselect("도시 선택", ['서울', '부산', '인천'], default=['서울', '부산', '인천'])
    f_df = df[df['지역'].isin(selected_cities)].sort_values('날짜')

    # --- 차트 1: 산점도 ---
    st.header("1. 미세먼지 농도와 천식 환자수 관계")
    with st.expander("🖥️ SQL 쿼리 원리"):
        st.code("""
SELECT A.미세먼지, H.천식환자수 
FROM 대기질 A 
JOIN 보건 H ON A.날짜 = H.날짜 AND A.지역 = H.지역
        """, language='sql')

    fig1 = px.scatter(f_df, x="미세먼지", y="천식환자수", color="지역", trendline="ols",
                     title="미세먼지가 높아지면 환자수도 늘어날까?")
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("**💡 인사이트:** 산점도의 점들이 우상향 추세를 보인다면, 미세먼지 농도가 호흡기 질환 발생의 주요 원인임을 논리적으로 뒷받침합니다.")

    st.divider()

    # --- 차트 2: 막대그래프 ---
    st.header("2. 도시별 평균 미세먼지 농도 비교")
    with st.expander("🖥️ SQL 쿼리 원리"):
        st.code("""
SELECT 지역, AVG(미세먼지) as 평균농도 
FROM 대기질 
GROUP BY 지역
        """, language='sql')

    avg_df = f_df.groupby('지역')['미세먼지'].mean().reset_index()
    fig2 = px.bar(avg_df, x="지역", y="미세먼지", color="지역", text_auto='.1f',
                  title="어느 도시의 미세먼지가 가장 심각할까?")
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("**💡 인사이트:** 서울, 부산, 인천 중 평균 오염도가 가장 높은 지역을 파악하여 환경 규제가 우선적으로 필요한 도시를 선별할 수 있습니다.")

    st.divider()

    # --- 차트 3: 선 그래프 ---
    st.header("3. 월별 천식 환자수 변화 추이")
    with st.expander("🖥️ SQL 쿼리 원리"):
        st.code("""
SELECT 날짜, 지역, 천식환자수 
FROM 보건 
ORDER BY 날짜
        """, language='sql')

    fig3 = px.line(f_df, x="날짜", y="천식환자수", color="지역", markers=True,
                  title="시간에 따라 환자수는 어떻게 변하고 있을까?")
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown("**💡 인사이트:** 특정 계절에 환자수가 급증하는지 확인하여, 시기별로 주의보를 발령하거나 보건 대책을 마련하는 근거로 활용합니다.")

else:
    st.error("데이터를 합치지 못했습니다. DB의 날짜(예: 23-Nov)와 지역명(서울, 부산, 인천)이 모든 테이블에서 일치하는지 확인해주세요.")