import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- [1. 페이지 설정] ---
st.set_page_config(page_title="환경오염-호흡기 건강 분석", layout="wide")

st.title("🌱 환경오염과 호흡기 건강 상관관계 분석")
st.markdown("""
**데이터 진단 완료:** 날짜 형식(`23-Nov`)을 분석하여 데이터를 통합했습니다.  
각기 다른 테이블의 데이터를 '월' 단위로 매칭하여 시각화합니다.
""")

# --- [2. 데이터 로드 및 변환 함수] ---
def load_and_merge_data():
    db_path = 'environment_analysis.db'
    if not os.path.exists(db_path):
        st.error(f"❌ '{db_path}' 파일을 찾을 수 없습니다.")
        return None

    try:
        conn = sqlite3.connect(db_path)
        # 테이블 읽기
        df_w = pd.read_sql("SELECT * FROM 날씨", conn)
        df_a = pd.read_sql("SELECT * FROM 대기질", conn)
        df_s = pd.read_sql("SELECT * FROM 배출원", conn)
        df_h = pd.read_sql("SELECT * FROM 보건", conn)
        conn.close()

        # 데이터 전처리 함수 (중요!)
        def preprocess(df):
            # 1. 앞뒤 공백 제거
            df['날짜'] = df['날짜'].astype(str).str.strip()
            df['지역'] = df['지역'].astype(str).str.strip()
            
            # 2. '23-Nov' 형식을 실제 날짜로 변환 (%y:년도2자리, %b:월이름3자리)
            # errors='coerce'를 써서 변환 안되는 건 NaT로 처리
            df['날짜_dt'] = pd.to_datetime(df['날짜'], format='%y-%b', errors='coerce')
            return df

        # 모든 테이블에 전처리 적용
        df_w = preprocess(df_w)
        df_a = preprocess(df_a)
        df_s = preprocess(df_s)
        df_h = preprocess(df_h)

        # 3. 데이터 병합 (날짜_dt와 지역을 기준으로 합침)
        # 4개의 퍼즐 조각을 하나로 맞추는 과정입니다.
        m1 = pd.merge(df_w, df_a, on=['날짜_dt', '지역'], how='inner')
        m2 = pd.merge(m1, df_s, on=['날짜_dt', '지역'], how='inner')
        final_df = pd.merge(m2, df_h, on=['날짜_dt', '지역'], how='inner')

        # 분석에 필요 없는 중복된 날짜 컬럼 정리
        if '날짜_x' in final_df.columns:
            final_df = final_df.drop(columns=[col for col in final_df.columns if '날짜_' in col and col != '날짜_dt'])
            final_df.rename(columns={'날짜_dt': '날짜'}, inplace=True)

        return final_df

    except Exception as e:
        st.error(f"데이터 통합 중 오류 발생: {e}")
        return None

# 데이터 로드 실행
df = load_and_merge_data()

# --- [3. 결과 확인 및 시각화] ---
if df is not None and not df.empty:
    # 사이드바 설정
    st.sidebar.header("🔍 지역 필터")
    all_regions = sorted(df['지역'].unique())
    selected_regions = st.sidebar.multiselect("분석할 지역을 선택하세요:", all_regions, default=all_regions)
    
    # 필터 적용
    f_df = df[df['지역'].isin(selected_regions)]

    # [차트 1] 상관관계 히트맵
    st.subheader("📊 1. 변수 간 상관관계 분석 (Heatmap)")
    st.info("빨간색이 진할수록 천식 환자수 증가와 밀접한 관련이 있는 요인입니다.")
    target_cols = ['미세먼지', '초미세먼지', '평균기온', '강수량', '자동차등록대수', '천식환자수']
    valid_cols = [c for c in target_cols if c in f_df.columns]
    
    if len(valid_cols) > 1:
        corr = f_df[valid_cols].corr()
        fig1 = px.imshow(corr, text_auto='.2f', color_continuous_scale='RdBu_r', 
                         labels=dict(color="상관계수"), title="환경-보건 지표 간 상관성")
        st.plotly_chart(fig1, use_container_width=True)

    # [차트 2] 지역별 위험도 트리맵
    st.subheader("🗺️ 2. 지역별 위험도 트리맵 (Treemap)")
    st.markdown("사각형 **크기: 천식환자수 합계** / **색상: 평균 미세먼지 농도**")
    df_tree = f_df.groupby('지역').agg({'천식환자수': 'sum', '미세먼지': 'mean'}).reset_index()
    fig2 = px.treemap(df_tree, path=['지역'], values='천식환자수', color='미세먼지',
                      color_continuous_scale='OrRd', title="지역별 천식 환자 및 대기질 위험도")
    st.plotly_chart(fig2, use_container_width=True)

    # [차트 3] 3D 산점도
    st.subheader("🧊 3. 자동차-미세먼지-환자수 3D 분석")
    st.markdown("마우스로 회전하여 자동차 대수와 미세먼지, 환자수의 입체적 관계를 확인하세요.")
    fig3 = px.scatter_3d(f_df, x='자동차등록대수', y='미세먼지', z='천식환자수', 
                         color='지역', opacity=0.8, size_max=10,
                         title="원인(자동차)-현상(미세먼지)-결과(천식)의 입체적 분포")
    fig3.update_layout(margin=dict(l=0, r=0, b=0, t=40))
    st.plotly_chart(fig3, use_container_width=True)

    # 데이터 미리보기
    with st.expander("📝 통합 데이터 상세보기 (전체 행 수: {})".format(len(f_df))):
        st.dataframe(f_df.sort_values('날짜'))

else:
    st.error("❗ 데이터를 합치지 못했습니다.")
    st.info("""
    **원인 진단:** 
    사용하신 `23-Nov` 형식을 파이썬이 해석하도록 설정했습니다. 그럼에도 데이터가 없다면:
    1. **지역 이름 불일치**: 한 테이블엔 '서울', 다른 테이블엔 '서울 ' (공백)이나 '서울특별시'로 되어 있는지 확인하세요.
    2. **데이터 시점 불일치**: 날씨는 23년인데 보건은 22년 데이터만 있는 경우 합쳐지지 않습니다.
    """)