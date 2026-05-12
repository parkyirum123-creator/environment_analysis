import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# --- [1. 페이지 기본 설정] ---
st.set_page_config(page_title="환경오염-호흡기 건강 분석", layout="wide")

st.title("🌱 환경오염과 호흡기 건강 상관관계 분석")
st.markdown("""
이 대시보드는 **미세먼지, 자동차등록대수, 그리고 천식환자수** 사이의 복합적인 관계를 분석합니다. 
데이터베이스의 최신 정보를 바탕으로 인터랙티브한 시각화를 제공합니다.
""")

# --- [2. 데이터베이스 연결 및 로드] ---
@st.cache_data
def load_data():
    # SQLite DB 파일 연결
    conn = sqlite3.connect('environment_analysis.db')
    
    # '최종데이터' 테이블 불러오기 (띄어쓰기 없는 컬럼명 기준)
    query = "SELECT * FROM 최종데이터"
    df = pd.read_sql(query, conn)
    
    # 날짜 데이터 처리
    if '날짜' in df.columns:
        df['날짜'] = pd.to_datetime(df['날짜'])
    
    conn.close()
    return df

# 데이터 로드 실행
try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다. DB 파일명과 테이블 컬럼명을 확인해주세요. \n 에러 내용: {e}")
    st.stop()

# --- [3. 사이드바 - 지역 필터] ---
st.sidebar.header("🔍 필터 설정")
all_regions = df['지역'].unique().tolist()
selected_regions = st.sidebar.multiselect(
    "분석할 지역을 선택하세요:",
    options=all_regions,
    default=all_regions
)

# 필터링된 데이터
filtered_df = df[df['지역'].isin(selected_regions)]

# --- [4. 메인 화면 시각화] ---

# 차트 1: 상관관계 히트맵 (Heatmap)
st.subheader("📊 1. 변수 간 상관관계 분석 (Heatmap)")
st.info("각 수치들이 서로 얼마나 밀접하게 움직이는지 보여줍니다. 1에 가까울수록 강한 연관성이 있습니다.")

# 띄어쓰기가 제거된 컬럼명 리스트
numeric_cols = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대수', '천식환자수']
# 데이터에 존재하는 컬럼만 선별하여 상관계수 계산
existing_cols = [col for col in numeric_cols if col in filtered_df.columns]
corr_matrix = filtered_df[existing_cols].corr()

fig1 = px.imshow(
    corr_matrix,
    text_auto='.2f',
    color_continuous_scale='RdBu_r',
    aspect="auto",
    title="환경 요소 및 질환 상관계수 히트맵"
)
st.plotly_chart(fig1, use_container_width=True)


# 차트 2: 지역별 위험도 트리맵 (Treemap)
st.subheader("🗺️ 2. 지역별 천식 위험도 및 미세먼지 현황")
st.markdown("사각형의 **면적은 천식환자수 합계**, **색상은 평균 미세먼지 농도**입니다.")

# 지역별 데이터 집계 (띄어쓰기 없는 버전)
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
    title="지역별 천식환자 규모와 평균 미세먼지 농도"
)
st.plotly_chart(fig2, use_container_width=True)


# 차트 3: 3D 산점도 (3D Scatter Plot)
st.subheader("🧊 3. 자동차 - 미세먼지 - 환자수의 입체적 관계")
st.markdown("마우스를 드래그하여 그래프를 회전시켜보세요. 세 변수의 상관관계를 입체적으로 분석할 수 있습니다.")

fig3 = px.scatter_3d(
    filtered_df,
    x='자동차등록대수',
    y='미세먼지',
    z='천식환자수',
    color='지역',
    opacity=0.7,
    title="자동차-미세먼지-천식환자 3D 상관분석"
)

# 3D 차트 여백 조절
fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
st.plotly_chart(fig3, use_container_width=True)


# --- [5. 데이터 요약 표시] ---
with st.expander("📝 필터링된 원본 데이터 보기"):
    st.write(f"현재 선택된 데이터 행 개수: {len(filtered_df)}개")
    st.dataframe(filtered_df)