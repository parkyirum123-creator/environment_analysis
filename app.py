import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import re

# --- [1. 페이지 설정] ---
st.set_page_config(page_title="주요도시 환경-건강 분석", layout="wide")

st.title("🏙️ 주요 도시 환경오염과 호흡기 건강 분석")
st.info("날짜 변환 엔진을 업그레이드하여 병합 오류를 해결했습니다.")

# --- [2. 무적의 날짜 변환 함수] ---
def force_parse_date(date_str):
    """어떤 날짜 형식이든 YYYY-MM 형태로 강제 변환합니다."""
    if not date_str: return None
    date_str = str(date_str).strip().upper()
    
    # 영문 월 이름 매핑
    months = {
        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
        'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
    }

    try:
        # 1. '23-NOV' 형식 처리 (하이픈으로 분리)
        if '-' in date_str:
            parts = date_str.split('-')
            # 년도가 앞에 있고 월이 뒤에 있는 경우 (23-NOV)
            if parts[1] in months:
                return f"20{parts[0][-2:]}-{months[parts[1]]}"
            # 월이 앞에 있고 년도가 뒤에 있는 경우 (NOV-23)
            elif parts[0] in months:
                return f"20{parts[1][-2:]}-{months[parts[0]]}"
            # 숫자만 있는 경우 (2023-01-01)
            else:
                dt = pd.to_datetime(date_str)
                return dt.strftime('%Y-%m')
        
        # 2. 하이픈 없이 숫자만 있거나 다른 형식일 때 (예: 20230101)
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y-%m')
    except:
        # 3. 정규식으로 영문 월 이름만이라도 찾아내기
        for m_name, m_num in months.items():
            if m_name in date_str:
                # 숫자(년도) 추출 시도
                year_match = re.search(r'\d{2,4}', date_str)
                year = year_match.group() if year_match else "2023"
                if len(year) == 2: year = "20" + year
                return f"{year}-{m_num}"
        return None

# --- [3. 데이터 로드 및 통합 함수] ---
@st.cache_data
def load_and_merge_data():
    db_path = 'environment_analysis.db'
    if not os.path.exists(db_path):
        st.error("DB 파일을 찾을 수 없습니다.")
        return None

    try:
        conn = sqlite3.connect(db_path)
        df_w = pd.read_sql("SELECT * FROM 날씨", conn)
        df_a = pd.read_sql("SELECT * FROM 대기질", conn)
        df_s = pd.read_sql("SELECT * FROM 배출원", conn)
        df_h = pd.read_sql("SELECT * FROM 보건", conn)
        conn.close()

        def clean_df(df):
            # 지역 이름 통일 (서울, 부산, 인천)
            df['지역'] = df['지역'].astype(str).str.strip()
            for city in ['서울', '부산', '인천']:
                df.loc[df['지역'].str.contains(city), '지역'] = city
            df = df[df['지역'].isin(['서울', '부산', '인천'])].copy()
            
            # 날짜를 무적의 변환기로 처리
            df['날짜_key'] = df['날짜'].apply(force_parse_date)
            return df.drop(columns=['날짜'])

        # 전처리 적용
        df_w, df_a, df_s, df_h = map(clean_df, [df_w, df_a, df_s, df_h])

        # 병합 (날짜_key와 지역 기준)
        merged = pd.merge(df_w, df_a, on=['날짜_key', '지역'], how='inner')
        merged = pd.merge(merged, df_s, on=['날짜_key', '지역'], how='inner')
        merged = pd.merge(merged, df_h, on=['날짜_key', '지역'], how='inner')

        # 수치형 변환
        nums = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대수', '천식환자수']
        for col in nums:
            if col in merged.columns:
                merged[col] = pd.to_numeric(merged[col], errors='coerce')

        merged.rename(columns={'날짜_key': '날짜'}, inplace=True)
        return merged

    except Exception as e:
        st.error(f"오류 발생: {e}")
        return None

# 데이터 로딩
df = load_and_merge_data()

# --- [4. 시각화 출력] ---
if df is not None and not df.empty:
    st.sidebar.header("📍 분석 필터")
    selected = st.sidebar.multiselect("도시 선택", ['서울', '부산', '인천'], default=['서울', '부산', '인천'])
    f_df = df[df['지역'].isin(selected)]

    # 1. 히트맵
    st.subheader("📊 상관관계 분석")
    corr = f_df.select_dtypes(include=['number']).corr()
    st.plotly_chart(px.imshow(corr, text_auto='.2f', color_continuous_scale='RdBu_r'), use_container_width=True)

    # 2. 트리맵
    st.subheader("🗺️ 도시별 환자수 및 미세먼지")
    tree_df = f_df.groupby('지역').agg({'천식환자수':'sum', '미세먼지':'mean'}).reset_index()
    st.plotly_chart(px.treemap(tree_df, path=['지역'], values='천식환자수', color='미세먼지', color_continuous_scale='OrRd'), use_container_width=True)

    # 3. 3D 산점도
    st.subheader("🧊 자동차-미세먼지-환자수 분석")
    st.plotly_chart(px.scatter_3d(f_df, x='자동차등록대수', y='미세먼지', z='천식환자수', color='지역'), use_container_width=True)

    with st.expander("📝 통합 데이터 확인"):
        st.dataframe(f_df)
else:
    st.error("데이터 병합에 실패했습니다.")
    st.write("표시할 수 있는 공통 데이터가 없습니다. DB 안의 '지역'과 '날짜'가 서로 일치하는지 다시 확인해주세요.")