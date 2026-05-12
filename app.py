import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- [1. 페이지 설정] ---
st.set_page_config(page_title="주요도시 환경-건강 분석", layout="wide")

st.title("🏙️ 주요 도시 환경오염과 호흡기 건강 분석")
st.markdown("날짜 형식(`23-Nov`) 문제를 해결하고 서울, 부산, 인천 데이터를 통합합니다.")

# --- [2. 데이터 로드 및 수동 날짜 변환 함수] ---
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

        # 영문 월 이름을 숫자로 바꾸는 사전
        month_map = {
            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
            'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
        }

        # 2. 데이터 클리닝 및 날짜 수동 변환 함수
        def clean_data(df):
            # 지역 전처리
            df['지역'] = df['지역'].astype(str).str.strip()
            df.loc[df['지역'].str.contains('서울'), '지역'] = '서울'
            df.loc[df['지역'].str.contains('부산'), '지역'] = '부산'
            df.loc[df['지역'].str.contains('인천'), '지역'] = '인천'
            df = df[df['지역'].isin(['서울', '부산', '인천'])].copy()

            # 날짜 수동 변환 (예: '23-Nov' -> '2023-11-01')
            def parse_custom_date(date_str):
                try:
                    parts = date_str.split('-') # '23', 'Nov'로 분리
                    year = "20" + parts[0]
                    month = month_map[parts[1].capitalize()] # 'Nov' -> '11'
                    return f"{year}-{month}-01"
                except:
                    return None

            df['날짜_dt'] = df['날짜'].apply(parse_custom_date)
            # 병합 충돌 방지를 위해 원래 '날짜' 컬럼 삭제
            df = df.drop(columns=['날짜'])
            return df

        # 모든 테이블에 전처리 적용
        df_w = clean_data(df_w)
        df_a = clean_data(df_a)
        df_s = clean_data(df_s)
        df_h = clean_data(df_h)

        # 3. 데이터 병합 (날짜_dt와 지역 기준)
        m1 = pd.merge(df_w, df_a, on=['날짜_dt', '지역'], how='inner')
        m2 = pd.merge(m1, df_s, on=['날짜_dt', '지역'], how='inner')
        final_df = pd.merge(m2, df_h, on=['날짜_dt', '지역'], how='inner')

        # 날짜 컬럼 이름 복구 및 데이터 타입 변환
        final_df.rename(columns={'날짜_dt': '날짜'}, inplace=True)
        final_df['날짜'] = pd.to_datetime(final_df['날짜'])

        # 수치 데이터 강제 형변환
        num_cols = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대수', '천식환자수']
        for col in num_cols:
            if col in final_df.columns:
                final_df[col] = pd.to_numeric(final_df[col], errors='coerce')

        return final_df

    except Exception as e:
        st.error(f"데이터 처리 중 오류 발생: {e}")
        return None

# 데이터 로드
df = load_and_merge_data()

# --- [3. 화면 표시 영역] ---
if df is not None and not df.empty:
    st.sidebar.header("📍 분석 설정")
    selected_cities = st.sidebar.multiselect("도시 선택:", ['서울', '부산', '인천'], default=['서울', '부산', '인천'])
    
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
    st.subheader("🗺️ 2. 도시별 천식 환자 규모 및 미세먼지")
    df_tree = f_df.groupby('지역').agg({'천식환자수': 'sum', '미세먼지': 'mean'}).reset_index()
    fig2 = px.treemap(df_tree, path=['지역'], values='천식환자수', color='미세먼지', color_continuous_scale='OrRd')
    st.plotly_chart(fig2, use_container_width=True)

    # 차트 3: 3D 산점도
    st.subheader("🧊 3. 자동차-미세먼지-환자수 3D 분석")
    fig3 = px.scatter_3d(f_df, x='자동차등록대수', y='미세먼지', z='천식환자수', color='지역', opacity=0.8)
    fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
    st.plotly_chart(fig3, use_container_width=True)

    with st.expander("📝 합쳐진 데이터 미리보기"):
        st.dataframe(f_df)

else:
    st.error("데이터 병합에 실패했습니다. 다음 사항을 확인해주세요.")
    st.warning("""
    1. **지역 이름 확인**: DB에 '서울', '부산', '인천'이라는 글자가 포함되어 있나요?
    2. **날짜 형식 확인**: '23-Nov' 형식이 맞나요? (대소문자 상관없음)
    3. **데이터 매칭**: 4개의 테이블에 동일한 '날짜'와 '지역'의 데이터가 모두 들어있나요? 하나라도 빠지면 합쳐지지 않습니다.
    """)
    
    # 디버깅용 정보 출력
    if st.checkbox("디버깅 정보 보기 (테이블별 샘플 데이터)"):
        conn = sqlite3.connect('environment_analysis.db')
        for table in ['날씨', '대기질', '배출원', '보건']:
            st.write(f"--- {table} 테이블 샘플 ---")
            st.dataframe(pd.read_sql(f"SELECT * FROM {table} LIMIT 3", conn))
        conn.close()