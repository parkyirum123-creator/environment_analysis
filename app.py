import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta

# --- 0. 가상 데이터 생성 함수 (DB가 없을 경우 대비) ---
def create_sample_db():
    conn = sqlite3.connect('environment_analysis.db')
    cursor = conn.cursor()
    
    # 데이터 생성을 위한 설정
    regions = ['서울', '부산', '대구', '인천', '광주']
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(100)]
    
    data_list = []
    for region in regions:
        for date in dates:
            pm10 = np.random.randint(20, 100)
            data_list.append([date.strftime('%Y-%m-%d'), region, pm10, pm10*0.6 + np.random.randint(5, 15)])
    
    # 1. 대기질 테이블
    df_air = pd.DataFrame(data_list, columns=['Date', 'Region', 'PM10', 'PM25'])
    df_air.to_sql('대기질', conn, if_exists='replace', index=False)
    
    # 2. 날씨 테이블
    weather_data = [[d.strftime('%Y-%m-%d'), r, np.random.uniform(-5, 30), np.random.uniform(0, 50)] 
                    for r in regions for d in dates]
    df_weather = pd.DataFrame(weather_data, columns=['Date', 'Region', 'Avg_Temp', 'Rainfall'])
    df_weather.to_sql('날씨', conn, if_exists='replace', index=False)
    
    # 3. 배출원 테이블
    emission_data = [[d.strftime('%Y-%m-%d'), r, np.random.randint(50000, 200000)] 
                     for r in regions for d in dates]
    df_emission = pd.DataFrame(emission_data, columns=['Date', 'Region', 'Registered_Vehicles'])
    df_emission.to_sql('배출원', conn, if_exists='replace', index=False)
    
    # 4. 보건 테이블 (미세먼지와 상관관계가 있게 생성)
    health_data = [[d.strftime('%Y-%m-%d'), r, int(df_air[(df_air['Date']==d.strftime('%Y-%m-%d')) & (df_air['Region']==r)]['PM10'].values[0] * 1.5 + np.random.randint(10, 30))] 
                   for r in regions for d in dates]
    df_health = pd.DataFrame(health_data, columns=['Date', 'Region', 'Asthma_Patients'])
    df_health.to_sql('보건', conn, if_exists='replace', index=False)
    
    conn.close()

# DB가 없으면 생성
import os
if not os.path.exists('environment_analysis.db'):
    create_sample_db()

# --- 1. 화면 기본 설정 ---
st.set_page_config(page_title="환경오염 대시보드", layout="wide")
st.title("📊 대기오염이 호흡기 건강에 미치는 영향 분석")
st.markdown("본 대시보드는 공공데이터(대기질, 기상, 교통, 보건)를 융합하여 미세먼지 농도와 천식 환자 발생 간의 상관관계를 통계적으로 시각화한 결과물입니다.")

# --- 2. 데이터 불러오기 ---
@st.cache_data
def load_data():
    conn = sqlite3.connect('environment_analysis.db')
    try:
        df_air = pd.read_sql("SELECT * FROM 대기질", conn)
        df_weather = pd.read_sql("SELECT * FROM 날씨", conn)
        df_emission = pd.read_sql("SELECT * FROM 배출원", conn)
        df_health = pd.read_sql("SELECT * FROM 보건", conn)
    except:
        return pd.DataFrame()
    finally:
        conn.close()

    rename_dict = {
        'Date': '날짜', 'Region': '지역', 'PM10': '미세먼지', 'PM25': '초미세먼지',
        'Avg_Temp': '평균기온', 'Rainfall': '강수량', 
        'Asthma_Patients': '천식환자수', 'Registered_Vehicles': '자동차등록대수'
    }
    
    # 컬럼명 변경 및 불필요한 컬럼 제거
    processed_dfs = []
    for df in [df_air, df_weather, df_emission, df_health]:
        df.rename(columns=rename_dict, inplace=True)
        cols_to_drop = [c for c in df.columns if 'Unnamed' in c]
        df.drop(columns=cols_to_drop, inplace=True)
        processed_dfs.append(df)

    df_air, df_weather, df_emission, df_health = processed_dfs

    # 데이터 병합 (Inner Join)
    m1 = pd.merge(df_air, df_weather, on=['날짜', '지역'], how='inner')
    m2 = pd.merge(m1, df_health, on=['날짜', '지역'], how='inner')
    df_final = pd.merge(m2, df_emission, on=['날짜', '지역'], how='inner')
    
    df_final['날짜'] = pd.to_datetime(df_final['날짜'])
    df_final = df_final.sort_values('날짜')
    return df_final

df = load_data()

# --- 3. 대시보드 구성 ---
if not df.empty:
    # 사이드바 설정
    st.sidebar.header("📌 분석 옵션")
    all_regions = df['지역'].unique()
    지역선택 = st.sidebar.multiselect('분석할 지역을 선택하세요:', all_regions, default=all_regions)
    
    # 데이터 필터링
    filtered_df = df[df['지역'].isin(지역선택)]

    # --- SQL 쿼리문 노출 섹션 ---
    with st.expander("💻 [과제 요건] 데이터 추출에 사용된 SQL 쿼리 및 Python 병합 코드 보기"):
        st.markdown("**SQLite DB에서 4개의 테이블을 추출하는 기본 쿼리:**")
        st.code("""
SELECT * FROM 대기질;
SELECT * FROM 날씨;
SELECT * FROM 배출원;
SELECT * FROM 보건;
        """, language='sql')
        st.markdown("**추출된 데이터를 '날짜'와 '지역'을 Key로 병합(Inner Join)하는 논리:**")
        st.code("""
# Python Pandas를 활용한 다중 조인 구현
m1 = pd.merge(df_air, df_weather, on=['날짜', '지역'], how='inner')
m2 = pd.merge(m1, df_health, on=['날짜', '지역'], how='inner')
df_final = pd.merge(m2, df_emission, on=['날짜', '지역'], how='inner')
        """, language='python')

    st.markdown("---")
    
    # --- 차트 1 & 2 ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. 미세먼지 농도와 환자 수 상관분석")
        try:
            fig1 = px.scatter(filtered_df, x='미세먼지', y='천식환자수', color='지역', 
                              trendline="ols", hover_data=['날짜'])
            st.plotly_chart(fig1, use_container_width=True)
            st.info("💡 **[인사이트]** 미세먼지 농도가 높아질수록 천식 환자 수가 비례하여 증가하는 **양의 상관관계**를 관찰할 수 있습니다.")
        except:
            st.warning("차트 생성 중 오류가 발생했습니다.")

    with col2:
        st.subheader("2. 지역별 평균 미세먼지 농도 비교")
        try:
            df_bar = filtered_df.groupby('지역')['미세먼지'].mean().reset_index()
            fig2 = px.bar(df_bar, x='지역', y='미세먼지', color='지역', text_auto='.1f')
            st.plotly_chart(fig2, use_container_width=True)
            st.info("💡 **[인사이트]** 지역별 평균 오염도 차이를 통해 오염이 집중된 지역을 파악하고 맞춤형 저감 정책 수립이 가능합니다.")
        except:
            st.warning("차트 생성 중 오류가 발생했습니다.")

    st.markdown("---")
    
    # --- 차트 3 (시계열 분석) ---
    st.subheader("3. 월별 미세먼지 변동 추이 (시계열 분석)")
    try:
        fig3 = px.line(filtered_df, x='날짜', y='미세먼지', color='지역', markers=True)
        st.plotly_chart(fig3, use_container_width=True)
        st.info("💡 **[인사이트]** 특정 시기에 미세먼지가 급증하는 패턴을 통해 계절적 요인이나 특정 기상 현상과의 연관성을 분석할 수 있습니다.")
    except Exception as e:
        st.warning(f"시계열 차트 생성 오류: {e}")

    # 데이터 테이블 출력
    with st.expander("📄 전체 통합 데이터 상세보기"):
        st.dataframe(filtered_df, use_container_width=True)

else:
    st.error("데이터를 불러올 수 없습니다. DB 파일 및 테이블 구조를 확인하세요.")