import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- [1. 페이지 기본 설정] ---
st.set_page_config(page_title="주요도시 환경-건강 분석", layout="wide")

st.title("🏙️ 주요 도시 환경오염과 호흡기 건강 분석")
st.markdown("""
이 대시보드는 **서울, 부산, 인천**의 데이터를 바탕으로 **미세먼지, 자동차, 천식 환자수**의 관계를 분석합니다.  
특이한 날짜 형식(`23-Nov`)을 분석 가능한 데이터로 변환하여 4개의 테이블을 통합했습니다.
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

        # 2. 데이터 클리닝 함수 (날짜 변환 및 지역 필터링)
        def clean_and_filter(df):
            # 지역 공백 제거 및 필터링 (서울, 부산, 인천 포함 여부 확인)
            df['지역'] = df['지역'].astype(str).str.strip()
            # '서울'이 포함된 경우 '서울'로 통일 (서울특별시 등 처리)
            df.loc[df['지역'].str.contains('서울'), '지역'] = '서울'
            df.loc[df['지역'].str.contains('부산'), '지역'] = '부산'
            df.loc[df['지역'].str.contains('인천'), '지역'] = '인천'
            
            # 서울, 부산, 인천만 남기기
            df = df[df['지역'].isin(['서울', '부산', '인천'])].copy()

            # 날짜 형식(23-Nov) 변환
            # %y: 23(년도), %b: Nov(월 영어 약어)
            df['날짜_dt'] = pd.to_datetime(df['날짜'], format='%y-%b', errors='coerce')
            return df

        # 모든 데이터프레임 전처리
        df_w = clean_and_filter(df_w)
        df_a = clean_and_filter(df_a)
        df_s = clean_and_filter(df_s)
        df_h = clean_and_filter(df_h)

        # 3. 데이터 병합 (날짜_dt와 지역 기준)
        # inner join: 모든 테이블에 공통으로 존재하는 날짜/지역만 합침
        m1 = pd.merge(df_w, df_a, on=['날짜_dt', '지역'], how='inner')
        m2 = pd.merge(m1, df_s, on=['날짜_dt', '지역'], how='inner')
        final_df = pd.merge(m2, df_h, on=['날짜_dt', '지역'], how='inner')

        # 불필요한 날짜 컬럼 정리
        final_df = final_df.drop(columns=[col for col in final_df.columns if '날짜' in col and col != '날짜_dt'])
        final_df.rename(columns={'날짜_dt': '날짜'}, inplace=True)

        return final_df

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
        return None

# 데이터 실행
df = load_and_merge_data()

# --- [3. 결과 확인 및 시각화] ---
if df is not None and not df.empty:
    
    # 사이드바: 주요 도시 선택
    st.sidebar.header("📍 분석 도시 선택")
    target_cities = ['서울', '부산', '인천']
    selected_cities = st.sidebar.multiselect(
        "확인하고 싶은 도시를 선택하세요:",
        options=target_cities,
        default=target_cities
    )
    
    # 선택된 도시로 데이터 필터링
    f_df = df[df['지역'].isin(selected_cities)]

    # --- 차트 1: 상관관계 히트맵 ---
    st.subheader("📊 1. 주요 지표 상관관계 분석 (Heatmap)")
    st.markdown("수치가 **1에 가까운 빨간색**일수록 두 지표가 함께 증가한다는 뜻입니다.")
    
    num_cols = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대수', '천식환자수']
    valid_cols = [c for c in num_cols if c in f_df.columns]
    
    if len(valid_cols) > 1:
        corr = f_df[valid_cols].corr()
        fig1 = px.imshow(corr, text_auto='.2f', color_continuous_scale='RdBu_r', 
                         title=f"{', '.join(selected_cities)} 통합 상관관계")
        st.plotly_chart(fig1, use_container_width=True)

    # --- 차트 2: 지역별 위험도 트리맵 ---
    st.subheader("🗺️ 2. 도시별 천식 위험도 및 대기질")
    st.markdown("사각형의 **크기는 천식환자수**, **색상은 미세먼지 농도**입니다.")
    
    df_tree = f_df.groupby('지역').agg({'천식환자수': 'sum', '미세먼지': 'mean'}).reset_index()
    fig2 = px.treemap(
        df_tree, 
        path=['지역'], 
        values='천식환자수', 
        color='미세먼지',
        color_continuous_scale='OrRd',
        title="서울/부산/인천 환자 규모 및 미세먼지 비교"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # --- 차트 3: 3D 산점도 ---
    st.subheader("🧊 3. 자동차-미세먼지-환자수의 3차원 분석")
    st.markdown("자동차가 많으면 미세먼지가 늘고, 결과적으로 환자수도 늘어나는지 입체적으로 확인해보세요.")
    
    fig3 = px.scatter_3d(
        f_df, 
        x='자동차등록대수', 
        y='미세먼지', 
        z='천식환자수', 
        color='지역',
        color_discrete_map={'서울':'#EF553B', '부산':'#00CC96', '인천':'#636EFA'}, # 도시별 고정 색상
        opacity=0.8,
        title="자동차 vs 미세먼지 vs 천식환자수"
    )
    fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
    st.plotly_chart(fig3, use_container_width=True)

    # 데이터 미리보기
    with st.expander("📝 필터링된 통합 데이터 보기"):
        st.dataframe(f_df.sort_values('날짜'))

else:
    st.error("❗ 분석할 데이터를 찾지 못했습니다.")
    st.warning("""
    **확인 사항:**
    1. DB의 '지역' 컬럼에 '서울', '부산', '인천' 중 하나라도 포함된 이름이 있는지 확인하세요.
    2. 날짜가 '23-Nov' 형식이 맞는지 다시 한번 확인하세요. (예: 23-nov 혹은 2023-Nov 등 미세한 차이)
    """)