import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# --- [1. 기본 설정 및 페이지 스타일] ---
st.set_page_config(page_title="환경오염-호흡기 건강 분석", layout="wide")

st.title("🌱 환경오염과 호흡기 건강 상관관계 분석")
st.markdown("""
이 대시보드는 **미세먼지, 자동차 등록대 수, 그리고 천식 환자 수** 사이의 복합적인 관계를 분석합니다. 
왼쪽 사이드바에서 지역을 선택하여 데이터를 탐색해 보세요.
""")

# --- [2. 데이터베이스 연결 함수] ---
# DB에서 데이터를 가져오는 함수입니다. 캐시(@st.cache_data)를 사용하여 속도를 높입니다.
@st.cache_data
def load_data():
    # SQLite DB 파일에 연결 (파일명: environment_analysis.db)
    conn = sqlite3.connect('environment_analysis.db')
    
    # '최종데이터' 테이블의 모든 데이터를 불러와서 데이터프레임(df) 형태로 저장
    query = "SELECT * FROM 최종데이터"
    df = pd.read_sql(query, conn)
    
    # 날짜 컬럼이 있다면 시계열 데이터로 변환 (분석 편의성)
    if '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'])
    
    conn.close()
    return df

# 데이터 로드 (파일이 없을 경우를 대비해 예외 처리를 하면 좋지만, 여기서는 기본 흐름에 집중합니다)
try:
    df = load_data()
except Exception as e:
    st.error(f"데이터베이스를 찾을 수 없습니다. 파일명과 테이블명을 확인해주세요. 에러: {e}")
    st.stop()

# --- [3. 사이드바 - 지역 필터링] ---
st.sidebar.header("🔍 필터 설정")
all_regions = df['지역'].unique().tolist()
selected_regions = st.sidebar.multiselect(
    "분석할 지역을 선택하세요:",
    options=all_regions,
    default=all_regions  # 기본값은 전체 선택
)

# 선택된 지역으로 데이터 필터링
filtered_df = df[df['지역'].isin(selected_regions)]

# --- [4. 메인 화면 시각화] ---

# 1번 차트: 상관관계 히트맵 (Heatmap)
st.subheader("📊 1. 변수 간 상관관계 분석 (Heatmap)")
st.info("상관계수가 1에 가까울수록 두 변수는 강한 양의 관계(함께 증가)가 있음을 의미합니다.")

# 수치형 변수만 추출하여 상관계수 계산
numeric_cols = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대 수', '천식환자 수']
# 실제 데이터에 존재하는 컬럼만 선택
existing_cols = [col for col in numeric_cols if col in filtered_df.columns]
corr_matrix = filtered_df[existing_cols].corr()

fig1 = px.imshow(
    corr_matrix,
    text_auto='.2f', # 소수점 둘째자리까지 표시
    color_continuous_scale='RdBu_r', # 빨간색(양의 상관), 파란색(음의 상관)
    aspect="auto",
    title="환경 요소 및 질환 상관계수 히트맵"
)
st.plotly_chart(fig1, use_container_width=True)


# 2번 차트: 지역별 위험도 트리맵 (Treemap)
st.subheader("🗺️ 2. 지역별 천식 위험도 및 미세먼지 현황")
st.markdown("사각형의 **크기는 천식 환자 수**, **색상은 미세먼지 농도**를 의미합니다. (크고 붉을수록 위험)")

# 지역별로 데이터 그룹화(집계)
df_grouped = filtered_df.groupby('지역').agg({
    '천식환자 수': 'sum',
    '미세먼지': 'mean'
}).reset_index()

fig2 = px.treemap(
    df_grouped,
    path=['지역'],
    values='천식환자 수',
    color='미세먼지',
    color_continuous_scale='OrRd', # 주황~빨강 색상 조합
    title="지역별 천식 환자 규모와 평균 미세먼지 농도"
)
st.plotly_chart(fig2, use_container_width=True)


# 3번 차트: 3D 산점도 (3D Scatter Plot)
st.subheader("🧊 3. 자동차 - 미세먼지 - 환자 수의 입체적 관계")
st.markdown("자동차가 많아지면 미세먼지가 늘고, 결국 환자 수도 늘어날까요? 마우스로 그래프를 돌려보며 확인하세요.")

fig3 = px.scatter_3d(
    filtered_df,
    x='자동차등록대 수',
    y='미세먼지',
    z='천식환자 수',
    color='지역',
    opacity=0.7,
    size_max=10,
    title="자동차-미세먼지-천식환자 3D 분석"
)

# 그래프 레이아웃 최적화
fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
st.plotly_chart(fig3, use_container_width=True)

# --- [5. 하단 데이터 요약 정보] ---
with st.expander("📝 필터링된 데이터 상세보기"):
    st.dataframe(filtered_df)