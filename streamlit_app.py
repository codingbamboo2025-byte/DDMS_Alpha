import streamlit as st
import google.generativeai as genai
import pandas as pd
import olefile
import zipfile
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader
import os

# 1. 파일 기반 저장소 설정
DB_FILE = "school_db.txt"

def save_data(text):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        f.write(text)

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "아직 등록된 학교 정보가 없습니다."

# 2. 페이지 설정 및 초기 데이터 로드
st.set_page_config(page_title="우리반 AI 보조", page_icon="🏫")

# 앱이 시작될 때 파일에서 데이터를 읽어옵니다.
if "global_context" not in st.session_state:
    st.session_state["global_context"] = load_data()

# [중요] API 설정 (1.5-flash 권장)
genai.configure(api_key=st.secrets["DB"])
model = genai.GenerativeModel('models/gemini-2.5-flash')

# 3. 사이드바 메뉴
mode = st.sidebar.radio("모드 선택", ["학생 모드", "선생님 모드"])

if mode == "선생님 모드":
    st.header("🔐 관리자 페이지")
    password = st.text_input("관리자 비밀번호", type="password")
    
    if password == "20260403":
        uploaded_file = st.file_uploader("파일 업로드 (xlsx, hwp, hwpx, pdf)", type=["xlsx", "hwp", "hwpx", "pdf"])
        
        if uploaded_file:
            new_context = ""
            file_type = uploaded_file.name.split('.')[-1].lower()
            
            try:
                # (기존 파일 처리 로직 동일...)
                if file_type == "hwpx":
                    with zipfile.ZipFile(uploaded_file) as z:
                        xml_files = [f for f in z.namelist() if 'Contents/section' in f]
                        for xml_file in xml_files:
                            with z.open(xml_file) as f:
                                root = ET.parse(f).getroot()
                                for txt in root.iter():
                                    if txt.text: new_context += txt.text + " "
                elif file_type == "hwp":
                    f = olefile.OleFileIO(uploaded_file)
                    if f.exists('PrvText'):
                        new_context = f.openstream('PrvText').read().decode('utf-16')
                elif file_type == "xlsx":
                    new_context = pd.read_excel(uploaded_file).to_string()
                elif file_type == "pdf":
                    reader = PdfReader(uploaded_file)
                    for page in reader.pages:
                        new_context += page.extract_text()

                if new_context:
                    # [핵심] 세션에도 저장하고, 파일에도 저장합니다!
                    st.session_state["global_context"] = new_context
                    save_data(new_context) 
                    st.success("✅ 서버에 안전하게 저장되었습니다. 이제 웹을 꺼도 유지됩니다!")
            except Exception as e:
                st.error(f"오류: {e}")

else:
    # 학생 모드
    st.header("🤖 우리반 보조봇")
    st.info("💡 선생님이 등록하신 최신 정보를 바탕으로 대답합니다.")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages: st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("질문하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        # 현재 로드된 데이터를 기반으로 답변
        full_prompt = f"정보: {st.session_state['global_context']}\n질문: {prompt}\n친절하게 답해줘."
        
        try:
            response = model.generate_content(full_prompt)
            st.chat_message("assistant").write(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error("잠시 후 다시 시도해주세요. (API 사용량 초과 가능성)")