import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import re

# --- [1. 페이지 기본 설정] ---
st.set_page_config(page_title="환경오염-호흡기 건강 분석", layout="wide")

st.title("🌱 환경오염과 호흡기 건강 상관관계 대시보드")
st.markdown("""
이 대시보드는 **날씨, 대기질, 자동차 배출원, 보건(천식)** 데이터를 통합하여 환경 오염이 인간의 건강에 미치는 영향을 분석합니다.
각 시각화 아래에는 해당 데이터를 추출하기 위한 **SQL 쿼리**와 분석가가 발견한 **인사이트**가 포함되어 있습니다.
""")

# --- [2. 데이터베이스 지식 창고] ---
with st.expander("📝 초보자를 위한 DB 교육: 테이블을 합치는 방법 (JOIN)"):
    st.write("""
    데이터베이스는 여러 개의 서랍이 있는 수납장과 같아요. 이번 분석에서는 4개의 서랍(테이블)을 사용합니다.
    1. **날씨**: 온도와 비 정보가 있어요.
    2. **대기질**: 미세먼지 농도가 있어요.
    3. **배출원**: 자동차 등록 대수가 있어요.
    4. **보건**: 천식 환자 수가 있어요.
    
    이 데이터들은 **'날짜'**와 **'지역'**이라는 공통 열쇠를 가지고 있어서, 이 열쇠들을 맞춰서 하나로 합치는 작업을 **JOIN(조인)** 또는 **Merge(병합)**라고 부릅니다.
    """)

# --- [3. 무적의 날짜 변환 함수] ---
def force_parse_date(date_str):
    if not date_str: return None
    date_str = str(date_str).strip().upper()
    months = {
        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
        'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
    }
    try:
        if '-' in date_str:
            parts = date_str.split('-')
            if parts[1] in months: return f"20{parts[0][-2:]}-{months[parts[1]]}"
            elif parts[0] in months: return f"20{parts[1][-2:]}-{months[parts[0]]}"
        dt = pd.to_datetime(date_str)
        return dt.strftime('%Y-%m')
    except:
        for m_name, m_num in months.items():
            if m_name in date_str:
                year_match = re.search(r'\d{2,4}', date_str)
                year = year_match.group() if year_match else "2023"
                if len(year) == 2: year = "20" + year
                return f"{year}-{m_num}"
        return None

# --- [4. 데이터 통합 및 로드] ---
@st.cache_data
def get_integrated_data():
    db_path = 'environment_analysis.db'
    if not os.path.exists(db_path): return None
    
    conn = sqlite3.connect(db_path)
    df_w = pd.read_sql("SELECT * FROM 날씨", conn)
    df_a = pd.read_sql("SELECT * FROM 대기질", conn)
    df_s = pd.read_sql("SELECT * FROM 배출원", conn)
    df_h = pd.read_sql("SELECT * FROM 보건", conn)
    conn.close()

    def clean_df(df):
        df['지역'] = df['지역'].astype(str).str.strip()
        for city in ['서울', '부산', '인천']:
            df.loc[df['지역'].str.contains(city), '지역'] = city
        df = df[df['지역'].isin(['서울', '부산', '인천'])].copy()
        df['날짜_key'] = df['날짜'].apply(force_parse_date)
        return df.drop(columns=['날짜'])

    df_w, df_a, df_s, df_h = map(clean_df, [df_w, df_a, df_s, df_h])
    merged = pd.merge(df_w, df_a, on=['날짜_key', '지역'], how='inner')
    merged = pd.merge(merged, df_s, on=['날짜_key', '지역'], how='inner')
    merged = pd.merge(merged, df_h, on=['날짜_key', '지역'], how='inner')
    
    num_cols = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대수', '천식환자수']
    for col in num_cols:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce')
    
    merged.rename(columns={'날짜_key': '날짜'}, inplace=True)
    return merged

df = get_integrated_data()

# --- [5. 메인 대시보드 화면] ---
if df is not None and not df.empty:
    # 사이드바 필터
    st.sidebar.header("📍 분석 필터")
    selected_cities = st.sidebar.multiselect("도시 선택", ['서울', '부산', '인천'], default=['서울', '부산', '인천'])
    f_df = df[df['지역'].isin(selected_cities)]

    # ---------------------------------------------------------
    # 차트 1: 상관관계 히트맵
    # ---------------------------------------------------------
    st.header("📊 1. 변수 간 상관관계 분석")
    
    # SQL 쿼리 설명
    with st.expander("🖥️ 이 차트를 만들기 위한 SQL 쿼리"):
        st.code("""
SELECT 
    A.미세먼지, A.초미세먼지, 
    W.평균기온, W.강수량, 
    S.자동차등록대수, 
    H.천식환자수
FROM 날씨 W
JOIN 대기질 A ON W.날짜 = A.날짜 AND W.지역 = A.지역
JOIN 배출원 S ON W.날짜 = S.날짜 AND W.지역 = S.지역
JOIN 보건 H ON W.날짜 = H.날짜 AND W.지역 = H.지역
        """, language='sql')

    corr = f_df.select_dtypes(include=['number']).corr()
    fig1 = px.imshow(corr, text_auto='.2f', color_continuous_scale='RdBu_r', 
                     aspect="auto", title="환경-보건 지표 상관관계")
    st.plotly_chart(fig1, use_container_width=True)

    st.success("""
    **💡 데이터 인사이트:**
    * **천식환자수**와 가장 강한 상관관계를 보이는 변수가 무엇인지 확인해보세요. 
    * 보통 **미세먼지** 농도가 높아질수록 환자 수도 증가하는 양(+)의 상관관계가 나타납니다. 
    * 상관계수가 **0.7 이상**이면 두 변수는 매우 밀접하게 움직인다는 뜻입니다.
    """)

    st.divider()

    # ---------------------------------------------------------
    # 차트 2: 지역별 위험도 트리맵
    # ---------------------------------------------------------
    st.header("🗺️ 2. 도시별 천식 위험도와 대기질 현황")

    with st.expander("🖥️ 이 차트를 만들기 위한 SQL 쿼리"):
        st.code("""
SELECT 
    지역, 
    SUM(천식환자수) AS 총환자수, 
    AVG(미세먼지) AS 평균미세먼지
FROM 통합데이터
GROUP BY 지역
ORDER BY 총환자수 DESC
        """, language='sql')

    tree_df = f_df.groupby('지역').agg({'천식환자수':'sum', '미세먼지':'mean'}).reset_index()
    fig2 = px.treemap(tree_df, path=['지역'], values='천식환자수', color='미세먼지', 
                      color_continuous_scale='OrRd', title="도시별 환자 규모(면적)와 미세먼지 농도(색상)")
    st.plotly_chart(fig2, use_container_width=True)

    st.success("""
    **💡 데이터 인사이트:**
    * 사각형의 **면적이 클수록** 해당 도시에 천식 환자가 더 많이 거주하고 있음을 나타냅니다.
    * 사각형의 **색상이 붉을수록** 해당 도시의 평균 미세먼지 농도가 높다는 뜻입니다.
    * 면적도 크고 색도 붉은 도시는 환경 개선과 보건 서비스 지원이 가장 시급한 곳입니다.
    """)

    st.divider()

    # ---------------------------------------------------------
    # 차트 3: 3D 산점도 분석
    # ---------------------------------------------------------
    st.header("🧊 3. 자동차 - 미세먼지 - 천식환자의 3D 관계")

    with st.expander("🖥️ 이 차트를 만들기 위한 SQL 쿼리"):
        st.code("""
-- 원인(자동차), 현상(미세먼지), 결과(질환)의 인과관계를 3축으로 시각화합니다.
SELECT 자동차등록대수, 미세먼지, 천식환자수, 지역
FROM 통합데이터
        """, language='sql')

    fig3 = px.scatter_3d(f_df, x='자동차등록대수', y='미세먼지', z='천식환자수', color='지역',
                         title="자동차 등록대수와 오염물질, 환자수의 입체적 분포",
                         opacity=0.8, size_max=18)
    fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
    st.plotly_chart(fig3, use_container_width=True)

    st.success("""
    **💡 데이터 인사이트:**
    * **원인-현상-결과** 분석: 자동차가 많은 지역(X축)에서 미세먼지가 높게 나타나고(Y축), 그 결과 천식 환자수(Z축)가 늘어나는지 입체적으로 확인하세요.
    * 데이터 점들이 우상향 대각선 방향으로 모여있다면, 자동차 배기가스가 호흡기 건강에 실질적인 영향을 준다는 강력한 시각적 증거가 됩니다.
    """)

    # 데이터 테이블
    with st.expander("📝 통합 데이터셋 미리보기"):
        st.dataframe(f_df)

else:
    st.error("데이터 병합에 실패했습니다. DB 내 지역명(서울, 부산, 인천)과 날짜(23-Nov 등) 일치 여부를 확인해주세요.")