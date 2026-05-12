import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- [1. 페이지 설정 및 제목] ---
st.set_page_config(page_title="환경오염-호흡기 건강 분석", layout="wide")

st.title("🌱 환경오염과 호흡기 건강 상관관계 분석")
st.markdown("""
이 대시보드는 **날씨, 대기질, 자동차 배출원, 보건 데이터**를 통합하여 분석합니다.
각기 다른 서랍(테이블)에 저장된 데이터를 하나로 합쳐서 환경 요인이 우리 건강(천식)에 어떤 영향을 주는지 탐색합니다.
""")

# --- [2. 데이터베이스 로드 및 병합 함수] ---
@st.cache_data
def load_and_merge_data():
    db_path = 'environment_analysis.db'
    
    # DB 파일 존재 여부 확인
    if not os.path.exists(db_path):
        return None

    # SQLite 연결
    conn = sqlite3.connect(db_path)
    
    try:
        # 각 테이블을 데이터프레임으로 읽어오기
        df_weather = pd.read_sql("SELECT * FROM 날씨", conn)
        df_air = pd.read_sql("SELECT * FROM 대기질", conn)
        df_source = pd.read_sql("SELECT * FROM 배출원", conn)
        df_health = pd.read_sql("SELECT * FROM 보건", conn)
        
        # '날짜'와 '지역'을 기준으로 모든 데이터 병합 (수납장의 칸을 맞추는 과정)
        # 여러 테이블을 하나로 합칠 때는 공통된 기준(Key)이 필요합니다.
        df = pd.merge(df_weather, df_air, on=['날짜', '지역'], how='inner')
        df = pd.merge(df, df_source, on=['날짜', '지역'], how='inner')
        df = pd.merge(df, df_health, on=['날짜', '지역'], how='inner')
        
        # 날짜 형식 변환
        df['날짜'] = pd.to_datetime(df['날짜'])
        
        conn.close()
        return df
    except Exception as e:
        st.error(f"데이터 병합 중 오류 발생: {e}")
        return None

# 데이터 불러오기
df = load_and_merge_data()

if df is not None:
    # --- [3. 사이드바: 지역 필터링] ---
    st.sidebar.header("🔍 분석 설정")
    all_regions = sorted(df['지역'].unique())
    selected_regions = st.sidebar.multiselect(
        "분석할 지역을 선택하세요:",
        options=all_regions,
        default=all_regions
    )

    # 필터 적용
    filtered_df = df[df['지역'].isin(selected_regions)]

    # --- [4. 메인 시각화 섹션] ---

    # 차트 1: 상관관계 히트맵 (Heatmap)
    st.subheader("📊 1. 전체 변수 간 상관관계 (Heatmap)")
    st.markdown("어떤 요인이 천식환자수와 가장 밀접할까요? 1에 가까운 진한 색상을 찾아보세요.")
    
    # 수치형 컬럼 선택
    cols_to_corr = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대수', '천식환자수']
    # 실제 존재하는 컬럼만 필터링
    valid_corr_cols = [c for c in cols_to_corr if c in filtered_df.columns]
    corr_matrix = filtered_df[valid_corr_cols].corr()

    fig1 = px.imshow(
        corr_matrix,
        text_auto='.2f',
        color_continuous_scale='RdBu_r',
        aspect="auto",
        title="환경-보건 지표 상관계수"
    )
    st.plotly_chart(fig1, use_container_width=True)


    # 차트 2: 지역별 위험도 트리맵 (Treemap)
    st.subheader("🗺️ 2. 지역별 천식 위험도 및 미세먼지 농도")
    st.markdown("사각형의 **크기는 천식환자수**, **색상은 미세먼지 농도**입니다. (크고 붉을수록 주의 지역)")
    
    # 지역별 평균 및 합계 집계
    df_tree = filtered_df.groupby('지역').agg({
        '천식환자수': 'sum',
        '미세먼지': 'mean'
    }).reset_index()

    fig2 = px.treemap(
        df_tree,
        path=['지역'],
        values='천식환자수',
        color='미세먼지',
        color_continuous_scale='YlOrRd',
        title="지역별 천식 환자 규모와 대기질 위험도"
    )
    st.plotly_chart(fig2, use_container_width=True)


    # 차트 3: 3D 산점도 (3D Scatter Plot)
    st.subheader("🧊 3. 자동차-미세먼지-환자수 3D 상관분석")
    st.markdown("자동차가 많으면(X) 미세먼지가 늘고(Y), 결과적으로 환자가 늘어날까요(Z)? 마우스로 돌려보세요!")

    fig3 = px.scatter_3d(
        filtered_df,
        x='자동차등록대수',
        y='미세먼지',
        z='천식환자수',
        color='지역',
        opacity=0.7,
        size_max=10,
        title="자동차 등록대수 vs 미세먼지 vs 천식환자수 관계"
    )
    # 레이아웃 조정
    fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
    st.plotly_chart(fig3, use_container_width=True)

    # --- [5. 하단 데이터 요약] ---
    with st.expander("📝 통합된 데이터 미리보기"):
        st.write(f"총 {len(filtered_df)}개의 데이터가 분석되었습니다.")
        st.dataframe(filtered_df)

else:
    st.error("❌ 'environment_analysis.db' 파일을 찾을 수 없거나 테이블 구조가 다릅니다.")
    st.info("DB 파일 내에 '날씨', '대기질', '배출원', '보건' 테이블이 있는지 확인해주세요.")