import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- [1. 페이지 설정] ---
st.set_page_config(page_title="주요도시 환경-건강 분석", layout="wide")

st.title("🏙️ 주요 도시 환경오염과 호흡기 건강 분석")
st.markdown("""
**에러 해결 완료:** 데이터 병합 시 발생하는 컬럼 충돌 문제를 수정했습니다.  
서울, 부산, 인천의 데이터를 통합하여 시각화합니다.
""")

# --- [2. 데이터 로드 및 전처리 함수] ---
@st.cache_data
def load_and_merge_data():
    db_path = 'environment_analysis.db'
    if not os.path.exists(db_path):
        st.error(f"❌ '{db_path}' 파일을 찾을 수 없습니다.")
        return None

    try:
        conn = sqlite3.connect(db_path)
        # 1. 4개 테이블 읽기
        df_w = pd.read_sql("SELECT * FROM 날씨", conn)
        df_a = pd.read_sql("SELECT * FROM 대기질", conn)
        df_s = pd.read_sql("SELECT * FROM 배출원", conn)
        df_h = pd.read_sql("SELECT * FROM 보건", conn)
        conn.close()

        # 2. 데이터 클리닝 함수
        def clean_and_filter(df):
            # 지역 공백 제거 및 통일
            df['지역'] = df['지역'].astype(str).str.strip()
            df.loc[df['지역'].str.contains('서울'), '지역'] = '서울'
            df.loc[df['지역'].str.contains('부산'), '지역'] = '부산'
            df.loc[df['지역'].str.contains('인천'), '지역'] = '인천'
            
            # 서울, 부산, 인천만 필터링
            df = df[df['지역'].isin(['서울', '부산', '인천'])].copy()

            # 날짜 형식(23-Nov) 변환 후 새로운 컬럼 생성
            df['날짜_dt'] = pd.to_datetime(df['날짜'], format='%y-%b', errors='coerce')
            
            # [중요] 병합 시 충돌을 막기 위해 원래 문자열 '날짜' 컬럼은 삭제합니다.
            df = df.drop(columns=['날짜'])
            return df

        # 모든 데이터프레임 전처리
        df_w = clean_and_filter(df_w)
        df_a = clean_and_filter(df_a)
        df_s = clean_and_filter(df_s)
        df_h = clean_and_filter(df_h)

        # 3. 데이터 병합 (날짜_dt와 지역을 기준으로 합침)
        # 이제 각 테이블에는 '날짜'라는 이름의 컬럼이 없고 '날짜_dt'만 있으므로 충돌이 없습니다.
        m1 = pd.merge(df_w, df_a, on=['날짜_dt', '지역'], how='inner')
        m2 = pd.merge(m1, df_s, on=['날짜_dt', '지역'], how='inner')
        final_df = pd.merge(m2, df_h, on=['날짜_dt', '지역'], how='inner')

        # 분석용 컬럼명 정리
        final_df.rename(columns={'날짜_dt': '날짜'}, inplace=True)

        return final_df

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
        return None

# 데이터 로드 실행
df = load_and_merge_data()

# --- [3. 시각화 영역] ---
if df is not None and not df.empty:
    # 사이드바
    st.sidebar.header("📍 분석 도시 선택")
    target_cities = ['서울', '부산', '인천']
    selected_cities = st.sidebar.multiselect("도시 선택:", target_cities, default=target_cities)
    
    f_df = df[df['지역'].isin(selected_cities)]

    # 차트 1: 히트맵
    st.subheader("📊 1. 주요 지표 상관관계 (Heatmap)")
    num_cols = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대수', '천식환자수']
    valid_cols = [c for c in num_cols if c in f_df.columns]
    
    if len(valid_cols) > 1:
        corr = f_df[valid_cols].corr()
        fig1 = px.imshow(corr, text_auto='.2f', color_continuous_scale='RdBu_r')
        st.plotly_chart(fig1, use_container_width=True)

    # 차트 2: 트리맵
    st.subheader("🗺️ 2. 도시별 천식 위험도 및 미세먼지")
    df_tree = f_df.groupby('지역').agg({'천식환자수': 'sum', '미세먼지': 'mean'}).reset_index()
    fig2 = px.treemap(df_tree, path=['지역'], values='천식환자수', color='미세먼지', color_continuous_scale='OrRd')
    st.plotly_chart(fig2, use_container_width=True)

    # 차트 3: 3D 산점도
    st.subheader("🧊 3. 자동차-미세먼지-환자수 3D 분석")
    fig3 = px.scatter_3d(f_df, x='자동차등록대수', y='미세먼지', z='천식환자수', color='지역', opacity=0.8)
    fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("📝 통합 데이터 상세보기"):
        st.dataframe(f_df.sort_values('날짜'))
else:
    st.error("분석할 데이터를 불러오지 못했습니다. DB의 날짜와 지역명을 확인해주세요.")