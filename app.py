import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- [1. 기본 설정] ---
st.set_page_config(page_title="환경 오염과 건강 대시보드", layout="wide")
st.title("🌱 환경 오염과 건강 분석 대시보드")

# --- [2. 데이터 로드 및 정밀 진단 함수] ---
def load_and_diagnostic():
    db_path = 'environment_analysis.db'
    if not os.path.exists(db_path):
        st.error("DB 파일을 찾을 수 없습니다.")
        return None

    conn = sqlite3.connect(db_path)
    # 4개 테이블 각각 로드
    df_w = pd.read_sql("SELECT * FROM 날씨", conn)
    df_a = pd.read_sql("SELECT * FROM 대기질", conn)
    df_s = pd.read_sql("SELECT * FROM 배출원", conn)
    df_h = pd.read_sql("SELECT * FROM 보건", conn)
    conn.close()

    # 영문 월 변환 사전 (대소문자 무시를 위해 모두 대문자로 처리)
    m_map = {'JAN':'01','FEB':'02','MAR':'03','APR':'04','MAY':'05','JUN':'06',
             'JUL':'07','AUG':'08','SEP':'09','OCT':'10','NOV':'11','DEC':'12'}

    def clean_process(df, name):
        # 1. 지역명에서 '서울', '부산', '인천' 단어만 추출 (오타 방지)
        df['지역'] = df['지역'].astype(str).str.strip()
        df.loc[df['지역'].str.contains('서울'), '지역'] = '서울'
        df.loc[df['지역'].str.contains('부산'), '지역'] = '부산'
        df.loc[df['지역'].str.contains('인천'), '지역'] = '인천'
        df = df[df['지역'].isin(['서울', '부산', '인천'])].copy()

        # 2. 날짜 '23-Nov' 형식을 '2023-11'로 강제 변환
        def to_key(d):
            try:
                p = str(d).split('-')
                year = "20" + p[0].strip()[-2:] # '23' -> '2023'
                month = m_map[p[1].strip().upper()[:3]] # 'Nov' -> '11'
                return f"{year}-{month}"
            except:
                return None
        
        df['날짜_key'] = df['날짜'].apply(to_key)
        return df.drop(columns=['날짜'])

    # 전처리 적용
    df_w = clean_process(df_w, "날씨")
    df_a = clean_process(df_a, "대기질")
    df_s = clean_process(df_s, "배출원")
    df_h = clean_process(df_h, "보건")

    # [진단 섹션] 병합이 왜 안되는지 단계별로 보여줌
    with st.expander("🔍 데이터 병합 진단 결과 (안 보일 때 클릭)"):
        st.write(f"각 테이블 데이터 건수: 날씨({len(df_w)}), 대기질({len(df_a)}), 배출원({len(df_s)}), 보건({len(df_h)})")
        m1 = pd.merge(df_w, df_a, on=['날짜_key', '지역'], how='inner')
        st.write(f"1단계 병합(날씨+대기질): {len(m1)}건")
        m2 = pd.merge(m1, df_s, on=['날짜_key', '지역'], how='inner')
        st.write(f"2단계 병합(+배출원): {len(m2)}건")
        final = pd.merge(m2, df_h, on=['날짜_key', '지역'], how='inner')
        st.write(f"최종 병합(+보건): {len(final)}건")
        
        if len(final) == 0:
            st.warning("데이터가 0건인 이유: 날짜(23-Nov)나 지역(서울/부산/인천) 형식이 테이블마다 다릅니다.")
            st.write("샘플 날짜_key 비교:", "날씨:", df_w['날짜_key'].iloc[0] if not df_w.empty else "없음", 
                     " / 보건:", df_h['날짜_key'].iloc[0] if not df_h.empty else "없음")

    if not final.empty:
        final.rename(columns={'날짜_key': '날짜'}, inplace=True)
        final['날짜'] = pd.to_datetime(final['날짜'] + "-01")
        return final
    return pd.DataFrame()

df = load_and_diagnostic()

# --- [3. 메인 시각화] ---
if not df.empty:
    st.sidebar.header("📍 필터")
    selected = st.sidebar.multiselect("도시 선택", ['서울', '부산', '인천'], default=['서울', '부산', '인천'])
    f_df = df[df['지역'].isin(selected)].sort_values('날짜')

    # 차트 1: 산점도
    st.subheader("1. 미세먼지가 높으면 환자가 많을까?")
    with st.expander("🖥️ SQL 쿼리"):
        st.code("SELECT 미세먼지, 천식환자수 FROM 통합데이터", language='sql')
    fig1 = px.scatter(f_df, x="미세먼지", y="천식환자수", color="지역", trendline="ols")
    st.plotly_chart(fig1, use_container_width=True)
    st.info("**논리적 인사이트:** 미세먼지가 호흡기에 미치는 직접적인 영향을 점의 분포로 확인합니다. 우상향할수록 상관관계가 높습니다.")

    # 차트 2: 막대그래프
    st.subheader("2. 어느 지역이 가장 미세먼지가 심할까?")
    with st.expander("🖥️ SQL 쿼리"):
        st.code("SELECT 지역, AVG(미세먼지) FROM 통합데이터 GROUP BY 지역", language='sql')
    avg_df = f_df.groupby('지역')['미세먼지'].mean().reset_index()
    fig2 = px.bar(avg_df, x="지역", y="미세먼지", color="지역", text_auto='.1f')
    st.plotly_chart(fig2, use_container_width=True)
    st.info("**논리적 인사이트:** 서울, 부산, 인천의 평균 오염도를 비교하여 대기질 개선이 가장 시급한 도시를 찾습니다.")

    # 차트 3: 선 그래프
    st.subheader("3. 시간이 지날수록 어떻게 변할까?")
    with st.expander("🖥️ SQL 쿼리"):
        st.code("SELECT 날짜, 지역, 천식환자수 FROM 통합데이터 ORDER BY 날짜", language='sql')
    fig3 = px.line(f_df, x="날짜", y="천식환자수", color="지역", markers=True)
    st.plotly_chart(fig3, use_container_width=True)
    st.info("**논리적 인사이트:** 환자수의 증가/감소 추세를 통해 계절적 요인이나 정책의 효과를 분석합니다.")

else:
    st.error("데이터를 합치지 못했습니다. 상단의 [🔍 데이터 병합 진단 결과]를 열어 숫자가 어디서 0이 되는지 확인해주세요.")