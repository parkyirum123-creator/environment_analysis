import streamlit as st
import pandas as pd
import plotly.express as px

# --- [1. 페이지 기본 설정] ---
st.set_page_config(page_title="환경오염-호흡기 건강 대시보드", layout="wide")

st.title("🌱 환경오염과 호흡기 건강 상관관계 분석")
st.markdown("""
이 대시보드는 공공데이터를 활용하여 **미세먼지, 날씨, 자동차 등록 현황**이 **천식 환자수**에 미치는 영향을 분석합니다.
각 차트를 통해 환경 요인과 건강 사이의 밀접한 관계를 확인해 보세요.
""")

# --- [2. 데이터 로드 및 병합 함수] ---
@st.cache_data
def load_data():
    try:
        # 4개의 CSV 파일 읽기 (파일명이 정확해야 합니다)
        대기질 = pd.read_csv('대기질.csv')
        날씨 = pd.read_csv('날씨.csv')
        보건 = pd.read_csv('보건.csv')
        배출원 = pd.read_csv('배출원.csv')

        # 컬럼명 통일 및 띄어쓰기 제거 (사용자 요청 반영)
        대기질.rename(columns={'Date': '날짜', 'Region': '지역', 'PM10': '미세먼지', 'PM25': '초미세먼지'}, inplace=True)
        날씨.rename(columns={'Date': '날짜', 'Region': '지역', 'Avg_Temp': '평균기온', 'Rainfall': '강수량'}, inplace=True)
        보건.rename(columns={'Date': '날짜', 'Region': '지역', 'Asthma_Patients': '천식환자수'}, inplace=True)
        배출원.rename(columns={'Date': '날짜', 'Region': '지역', 'Registered_Vehicles': '자동차등록대수'}, inplace=True)

        # 데이터 병합 (날짜와 지역을 기준으로 하나로 합침)
        # inner merge를 통해 모든 데이터가 존재하는 날짜/지역만 남깁니다.
        합침1 = pd.merge(대기질, 날씨, on=['날짜', '지역'], how='inner')
        합침2 = pd.merge(합침1, 보건, on=['날짜', '지역'], how='inner')
        최종데이터 = pd.merge(합침2, 배출원, on=['날짜', '지역'], how='inner')
        
        # 날짜 형식 변환
        최종데이터['날짜'] = pd.to_datetime(최종데이터['날짜'])
        
        return 최종데이터
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다. CSV 파일명과 컬럼명을 확인해주세요: {e}")
        return pd.DataFrame()

# 데이터 로딩 실행
df = load_data()

# 데이터가 비어있지 않을 때만 화면을 그립니다.
if not df.empty:
    # --- [3. 사이드바 - 지역 필터] ---
    st.sidebar.header("🔍 분석 필터")
    지역목록 = sorted(df['지역'].unique())
    선택된지역 = st.sidebar.multiselect(
        '분석할 지역을 선택하세요 (다중 선택 가능)', 
        options=지역목록, 
        default=지역목록
    )

    # 필터 적용
    filtered_df = df[df['지역'].isin(선택된지역)]

    # --- [4. 메인 시각화 영역] ---

    # 첫 번째 섹션: 상관관계 히트맵
    st.subheader("📊 1. 모든 요인의 상관관계 (Heatmap)")
    st.markdown("> 수치가 **1에 가까울수록(진한 빨강)** 두 요소는 강한 상관관계가 있음을 의미합니다.")
    
    numeric_cols = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대수', '천식환자수']
    # 실제 존재하는 컬럼만 선택
    valid_cols = [c for c in numeric_cols if c in filtered_df.columns]
    상관관계 = filtered_df[valid_cols].corr()

    fig1 = px.imshow(
        상관관계, 
        text_auto='.2f', 
        aspect="auto", 
        color_continuous_scale='RdBu_r',
        title='환경 요소-천식환자 상관계수'
    )
    st.plotly_chart(fig1, use_container_width=True)


    # 두 번째 섹션: 지역별 위험도 트리맵
    st.subheader("🗺️ 2. 지역별 위험도 분석 (Treemap)")
    st.markdown("> 사각형의 **크기는 천식환자수**, **색상은 미세먼지 농도**입니다. (붉고 클수록 위험)")
    
    # 지역별로 데이터 집계
    df_grouped = filtered_df.groupby('지역').agg({
        '천식환자수': 'sum',
        '미세먼지': 'mean'
    }).reset_index()

    fig2 = px.treemap(
        df_grouped, 
        path=['지역'], 
        values='천식환자수', 
        color='미세먼지',
        color_continuous_scale='OrRd',
        title='지역별 천식 환자 규모 및 평균 미세먼지 농도'
    )
    st.plotly_chart(fig2, use_container_width=True)


    # 세 번째 섹션: 3D 산점도 분석
    st.subheader("🧊 3. 자동차-미세먼지-환자수 3D 분석")
    st.markdown("> 자동차가 많으면 미세먼지가 늘고, 환자수도 늘어날까요? 입체적으로 확인해보세요.")
    
    fig3 = px.scatter_3d(
        filtered_df, 
        x='자동차등록대수', 
        y='미세먼지', 
        z='천식환자수', 
        color='지역', 
        opacity=0.7,
        size='천식환자수', # 환자수에 따라 점의 크기도 다르게 표시
        size_max=15,
        title='자동차 대수 vs 미세먼지 농도 vs 천식환자수 관계'
    )
    # 그래프 초기 각도 및 여백 설정
    fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
    st.plotly_chart(fig3, use_container_width=True)

    # --- [5. 하단 원본 데이터 미리보기] ---
    with st.expander("📝 필터링된 원본 데이터 상세 보기"):
        st.dataframe(filtered_df.sort_values(by='날짜', ascending=False))

else:
    st.warning("데이터를 불러올 수 없습니다. CSV 파일이 app.py와 같은 경로에 있는지 확인해 주세요.")