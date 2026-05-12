import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# 1. 화면 기본 설정
st.set_page_config(page_title="환경오염 대시보드", layout="wide")
st.title("🌱 환경오염과 호흡기 건강 대시보드")
st.markdown("사용자님이 직접 구축한 DB를 활용한 고급 시각화 대시보드입니다.")

# 2. 사용자님의 DB 불러오기 (자동화)
@st.cache_data
def load_data():
    # ★ 사용자님의 파일 이름으로 정확히 연결!
    conn = sqlite3.connect('environment_analysis.db')

    # DB 안에 있는 표(Table) 이름 자동으로 찾아내기
    query = "SELECT name FROM sqlite_master WHERE type='table';"
    tables = pd.read_sql(query, conn)

    if tables.empty:
        st.error("DB 파일은 찾았는데, 안에 데이터(표)가 없습니다. DB를 만들 때 데이터가 안 들어간 것 같습니다.")
        return pd.DataFrame()

    # 첫 번째 표 이름 가져오기
    table_name = tables.iloc[0]['name']

    # 데이터 불러오기
    df = pd.read_sql(f"SELECT * FROM '{table_name}'", conn)
    conn.close()

    # 영어가 섞여 있어도 알아서 한글로 바꿔주는 똑똑한 처리
    rename_dict = {
        'Date': '날짜', 'Region': '지역', 'PM10': '미세먼지', 'PM25': '초미세먼지',
        'Avg_Temp': '평균기온', 'Rainfall': '강수량', 
        'Asthma_Patients': '천식환자수', 'Registered_Vehicles': '자동차등록대수'
    }
    df.rename(columns=rename_dict, inplace=True)

    # 띄어쓰기가 있는 경우도 안전하게 붙여주기
    df.columns = df.columns.str.replace(' ', '')

    return df

# 데이터 로딩
df = load_data()

# 데이터가 정상적으로 불러와졌을 때만 차트 그리기
if not df.empty:
    # 3. 사이드바 (지역 필터링)
    st.sidebar.header("🔍 분석 필터")

    # '지역' 컬럼이 혹시 없으면 에러 안 나게 처리
    if '지역' in df.columns:
        지역목록 = df['지역'].unique()
        선택된지역 = st.sidebar.multiselect('지역을 선택하세요', 지역목록, default=지역목록)
        filtered_df = df[df['지역'].isin(선택된지역)]
    else:
        st.warning("데이터에 '지역' 컬럼이 없어서 전체 데이터를 보여줍니다.")
        filtered_df = df.copy()

    # 4. 차트 그리기 (고급 차트 3종)
    st.markdown("### 1. 지역별 위험도 분석 (트리맵)")
    try:
        fig1 = px.treemap(filtered_df, path=['지역', '날짜'], values='천식환자수', color='미세먼지',
                          color_continuous_scale='RdBu_r', title='면적: 환자수 / 색상: 미세먼지 농도')
        st.plotly_chart(fig1, use_container_width=True)
    except Exception as e:
        st.info("트리맵을 그리기 위한 데이터(지역, 날짜, 환자수, 미세먼지)가 부족합니다.")

    st.markdown("### 2. 모든 요인의 상관관계 (히트맵)")
    try:
        numeric_df = filtered_df.select_dtypes(include=['number'])
        상관관계 = numeric_df.corr()
        fig2 = px.imshow(상관관계, text_auto=True, aspect="auto", title='숫자가 1에 가까울수록 관련성이 높음')
        st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.info("히트맵을 그리기 위한 숫자 데이터가 부족합니다.")

    st.markdown("### 3. 자동차-미세먼지-환자수 3D 분석")
    try:
        fig3 = px.scatter_3d(filtered_df, x='자동차등록대수', y='미세먼지', z='천식환자수', 
                             color='지역', size='천식환자수', opacity=0.7, title='마우스로 돌려보며 확인하세요')
        fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
        st.plotly_chart(fig3, use_container_width=True)
    except Exception as e:
        st.info("3D 차트를 그리기 위한 데이터가 부족합니다.")
