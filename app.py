import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- [1. 페이지 설정] ---
st.set_page_config(page_title="주요도시 환경-건강 분석", layout="wide")

st.title("🏙️ 주요 도시 환경오염-건강 분석 (데이터 추적 모드)")
st.info("데이터가 보이지 않는 원인을 찾기 위해 각 테이블의 데이터를 하나씩 검사합니다.")

# --- [2. 데이터 로드 및 전처리 함수] ---
def load_and_merge_data():
    db_path = 'environment_analysis.db'
    if not os.path.exists(db_path):
        st.error(f"❌ DB 파일을 찾을 수 없습니다: {db_path}")
        return None

    try:
        conn = sqlite3.connect(db_path)
        # 1. 4개 테이블 각각 로드
        df_w = pd.read_sql("SELECT * FROM 날씨", conn)
        df_a = pd.read_sql("SELECT * FROM 대기질", conn)
        df_s = pd.read_sql("SELECT * FROM 배출원", conn)
        df_h = pd.read_sql("SELECT * FROM 보건", conn)
        conn.close()

        # 영문 월 매핑 사전 (대문자 처리)
        month_map = {
            'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
            'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
        }

        # 전처리 함수
        def clean(df, name):
            # 지역 전처리: '서울', '부산', '인천' 글자가 포함되어 있으면 통일
            df['지역'] = df['지역'].astype(str).str.strip()
            df.loc[df['지역'].str.contains('서울'), '지역'] = '서울'
            df.loc[df['지역'].str.contains('부산'), '지역'] = '부산'
            df.loc[df['지역'].str.contains('인천'), '지역'] = '인천'
            
            # 날짜 전처리: '23-Nov' -> '2023-11'
            def parse_date(d):
                try:
                    p = d.split('-')
                    yr = "20" + p[0]
                    mn = month_map[p[1].upper()]
                    return f"{yr}-{mn}"
                except:
                    return None
            
            df['날짜_key'] = df['날짜'].apply(parse_date)
            # 서울, 부산, 인천만 필터링
            df = df[df['지역'].isin(['서울', '부산', '인천'])].copy()
            # 원본 날짜 컬럼 삭제
            df = df.drop(columns=['날짜'])
            return df

        # 각 테이블 청소
        df_w = clean(df_w, "날씨")
        df_a = clean(df_a, "대기질")
        df_s = clean(df_s, "배출원")
        df_h = clean_df_h = clean(df_h, "보건")

        # [진단 기능] 각 단계별 병합 데이터 개수 확인
        with st.expander("🔍 데이터 병합 과정 진단 보기"):
            st.write(f"1. 날씨 데이터 (서울/부산/인천): {len(df_w)}건")
            st.write(f"2. 대기질 데이터 (서울/부산/인천): {len(df_a)}건")
            st.write(f"3. 배출원 데이터 (서울/부산/인천): {len(df_s)}건")
            st.write(f"4. 보건 데이터 (서울/부산/인천): {len(df_h)}건")

            # 단계별 병합 시도
            m1 = pd.merge(df_w, df_a, on=['날짜_key', '지역'], how='inner')
            st.write(f"➡ 날씨 + 대기질 합친 결과: {len(m1)}건")
            
            m2 = pd.merge(m1, df_s, on=['날짜_key', '지역'], how='inner')
            st.write(f"➡ 위 결과 + 배출원 합친 결과: {len(m2)}건")
            
            final_df = pd.merge(m2, df_h, on=['날짜_key', '지역'], how='inner')
            st.write(f"➡ 최종(위 결과 + 보건) 합친 결과: {len(final_df)}건")

        if final_df.empty:
            st.warning("데이터가 최종적으로 0건입니다. 테이블 중 하나라도 날짜나 지역이 매칭되지 않으면 이 현상이 발생합니다.")
            # 어떤 테이블의 날짜가 다른지 예시 출력
            st.write("각 테이블의 날짜(날짜_key) 예시:")
            st.write(f"날씨: {df_w['날짜_key'].iloc[0] if not df_w.empty else '없음'}")
            st.write(f"보건: {df_h['날짜_key'].iloc[0] if not df_h.empty else '없음'}")

        final_df.rename(columns={'날짜_key': '날짜'}, inplace=True)
        return final_df

    except Exception as e:
        st.error(f"처리 도중 에러 발생: {e}")
        return None

# 데이터 로드
df = load_and_merge_data()

# --- [3. 시각화 화면] ---
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
    st.warning("데이터 병합에 실패했습니다. 상단의 [🔍 데이터 병합 과정 진단 보기]를 열어 숫자를 확인해주세요.")