import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# 1. 화면 기본 설정
st.set_page_config(page_title="환경오염 대시보드", layout="wide")
st.title("🌱 환경오염과 호흡기 건강 대시보드")
st.markdown("DB 내 4개의 테이블을 실시간으로 결합하여 분석하는 대시보드입니다.")

# 2. 4개의 테이블을 불러와서 하나로 합치기
@st.cache_data
def load_data():
    conn = sqlite3.connect('environment_analysis.db')

    try:
        # 사용자님이 만드신 4개의 테이블을 각각 불러옵니다
        df_air = pd.read_sql("SELECT * FROM 대기질", conn)
        df_weather = pd.read_sql("SELECT * FROM 날씨", conn)
        df_emission = pd.read_sql("SELECT * FROM 배출원", conn)
        df_health = pd.read_sql("SELECT * FROM 보건", conn)
    except Exception as e:
        st.error(f"테이블을 불러오는 중 문제가 발생했습니다: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

    # '날짜'와 '지역'을 기준으로 4개 테이블 하나로 합치기 (Merge)
    df_merged1 = pd.merge(df_air, df_weather, on=['날짜', '지역'], how='inner')
    df_merged2 = pd.merge(df_merged1, df_health, on=['날짜', '지역'], how='inner')
    df_final = pd.merge(df_merged2, df_emission, on=['날짜', '지역'], how='inner')

    return df_final

df = load_data()

# 3. 데이터가 잘 합쳐졌다면 차트 그리기
if not df.empty:
    st.sidebar.header("🔍 분석 필터")

    지역목록 = df['지역'].unique()
    선택된지역 = st.sidebar.multiselect('지역을 선택하세요', 지역목록, default=지역목록)
    filtered_df = df[df['지역'].isin(선택된지역)]

    st.markdown("### 1. 지역별 위험도 분석 (트리맵)")
    fig1 = px.treemap(filtered_df, path=['지역', '날짜'], values='천식환자수', color='미세먼지',
                      color_continuous_scale='RdBu_r', title='면적: 환자수 / 색상: 미세먼지 농도')
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("### 2. 모든 요인의 상관관계 (히트맵)")
    numeric_df = filtered_df.select_dtypes(include=['number'])
    상관관계 = numeric_df.corr()
    fig2 = px.imshow(상관관계, text_auto=True, aspect="auto", title='숫자가 1에 가까울수록 관련성이 높음')
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 3. 자동차-미세먼지-환자수 3D 분석")
    fig3 = px.scatter_3d(filtered_df, x='자동차등록대수', y='미세먼지', z='천식환자수', 
                         color='지역', size='천식환자수', opacity=0.7, title='마우스로 돌려보며 확인하세요')
    fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.error("데이터를 병합하지 못했습니다. 테이블 구조를 확인해주세요.")
