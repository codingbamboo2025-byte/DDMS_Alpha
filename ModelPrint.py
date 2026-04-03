import google.generativeai as genai
import streamlit as st

# 1. API 키 설정 (직접 넣거나 secrets 사용)
try:
    # secrets.toml에 설정했다면 아래 줄 사용
    key = st.secrets["DB"]
except:
    # 에러가 나면 아래에 실제 키를 따옴표 안에 넣으세요
    key = "AIzaSy..." 

genai.configure(api_key=key)

print("--- 사용 가능한 모델 목록 ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"이름: {m.name}")
except Exception as e:
    print(f"오류 발생: {e}")