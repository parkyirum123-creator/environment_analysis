import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- [1. 기본 설정] ---
st.set_page_config(page_title="환경오염 분석 대시보드", layout="wide")
st.title("🏙️ 주요 도시 환경오염과 호흡기 건강 분석")

# --- [2. 데이터 통합 함수] ---
@st.cache_data
def load_data():
    db_path = 'environment_analysis.db'
    if not os.path.exists(db_path): return None

    conn = sqlite3.connect(db_path)
    # 각 테이블 읽기
    df_w = pd.read_sql("SELECT * FROM 날씨", conn)
    df_a = pd.read_sql("SELECT * FROM 대기질", conn)
    df_s = pd.read_sql("SELECT * FROM 배출원", conn)
    df_h = pd.read_sql("SELECT * FROM 보건", conn)
    conn.close()

    # 날짜 및 지역 정리 함수
    def clean(df):
        # 지역 이름 통일
        df['지역'] = df['지역'].astype(str).str.strip()
        for city in ['서울', '부산', '인천']:
            df.loc[df['지역'].str.contains(city), '지역'] = city
        df = df[df['지역'].isin(['서울', '부산', '인천'])].copy()

        # 날짜 형식(23-Nov) 변환
        # 오류 방지를 위해 대소문자 구분 없이 처리
        df['날짜'] = df['날짜'].astype(str).str.strip()
        df['날짜_dt'] = pd.to_datetime(df['날짜'], format='%y-%b', errors='coerce')
        return df.drop(columns=['날짜'])

    # 데이터 정리 적용
    df_w, df_a, df_s, df_h = map(clean, [df_w, df_a, df_s, df_h])

    # 데이터 병합 (날짜와 지역 기준)
    m = pd.merge(df_w, df_a, on=['날짜_dt', '지역'], how='inner')
    m = pd.merge(m, df_s, on=['날짜_dt', '지역'], how='inner')
    df_final = pd.merge(m, df_h, on=['날짜_dt', '지역'], how='inner')

    df_final.rename(columns={'날짜_dt': '날짜'}, inplace=True)
    return df_final

df = load_data()

# --- [3. 메인 화면 구성] ---
if df is not None and not df.empty:
    # 사이드바 필터
    st.sidebar.header("📍 필터")
    cities = st.sidebar.multiselect("도시 선택", ['서울', '부산', '인천'], default=['서울', '부산', '인천'])
    f_df = df[df['지역'].isin(cities)].sort_values('날짜')

    # --- 차트 1: 산점도 (미세먼지 vs 환자수) ---
    st.header("1. 미세먼지가 높으면 환자도 많을까?")
    
    with st.expander("🔍 SQL 쿼리 보기"):
        st.code("SELECT 미세먼지, 천식환자수 FROM 통합데이터", language='sql')

    fig1 = px.scatter(f_df, x="미세먼지", y="천식환자수", color="지역", trendline="ols",
                     title="미세먼지 농도와 천식 환자수 상관관계")
    st.plotly_chart(fig1, use_container_width=True)
    
    st.info("**인사이트:** 점들이 우상향(오른쪽 위로) 모여있다면 미세먼지가 많을수록 환자도 많아진다는 논리적 근거가 됩니다.")

    st.divider()

    # --- 차트 2: 막대그래프 (지역별 미세먼지 비교) ---
    st.header("2. 어느 지역이 가장 미세먼지가 심할까?")

    with st.expander("🔍 SQL 쿼리 보기"):
        st.code("SELECT 지역, AVG(미세먼지) FROM 통합데이터 GROUP BY 지역", language='sql')

    avg_df = f_df.groupby('지역')['미세먼지'].mean().reset_index()
    fig2 = px.bar(avg_df, x="지역", y="미세먼지", color="지역", title="지역별 평균 미세먼지 농도")
    st.plotly_chart(fig2, use_container_width=True)

    st.info("**인사이트:** 각 도시의 미세먼지 수준을 한눈에 비교하여 어느 지역의 공기질 관리가 가장 시급한지 보여줍니다.")

    st.divider()

    # --- 차트 3: 선 그래프 (시간에 따른 환자수 변화) ---
    st.header("3. 시간이 지날수록 어떻게 변할까?")

    with st.expander("🔍 SQL 쿼리 보기"):
        st.code("SELECT 날짜, SUM(천식환자수) FROM 통합데이터 GROUP BY 날짜 ORDER BY 날짜", language='sql')

    trend_df = f_df.groupby(['날짜', '지역'])['천식환자수'].sum().reset_index()
    fig3 = px.line(trend_df, x="날짜", y="천식환자수", color="지역", title="월별 천식 환자수 추이")
    st.plotly_chart(fig3, use_container_width=True)

    st.info("**인사이트:** 계절적 요인이나 시간 흐름에 따라 환자수가 증가하거나 감소하는 패턴을 확인할 수 있습니다.")

    # 원본 데이터 확인
    with st.expander("📝 전체 데이터 보기"):
        st.dataframe(f_df)

else:
    st.error("데이터를 합치지 못했습니다. DB의 날짜(예: 23-Nov)와 지역명(서울, 부산, 인천)이 일치하는지 확인해주세요.")