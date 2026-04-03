import streamlit as st
import google.generativeai as genai
import pandas as pd
import olefile
import zipfile
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader
import os
import datetime # 날짜 기능을 위해 추가
import time # 재시도를 위해 추가

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

if "global_context" not in st.session_state:
    st.session_state["global_context"] = load_data()

# API 설정 (가장 안정적인 1.5-flash 권장하지만, 일단 현재 설정 유지)
genai.configure(api_key=st.secrets["DB"])
# 팁: 429 에러가 너무 잦다면 'gemini-1.5-flash'로 바꾸는 것이 훨씬 안정적입니다.
model = genai.GenerativeModel('models/gemma-3-1b-it')

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
                    st.session_state["global_context"] = new_context
                    save_data(new_context) 
                    st.success("✅ 서버에 안전하게 저장되었습니다!")
            except Exception as e:
                st.error(f"오류: {e}")
    elif password != "":
        st.error("비밀번호가 틀렸습니다.")

else:
    # --- 학생 모드 ---
    st.header("🤖 우리반 보조봇")
    
    # 오늘 날짜 정보 생성
    now = datetime.datetime.now()
    weekday_list = ['월', '화', '수', '목', '금', '토', '일']
    current_date = now.strftime(f"%Y년 %m월 %d일({weekday_list[now.weekday()]})")
    
    st.info(f"📅 오늘은 **{current_date}** 입니다.")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages: st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("질문하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        # 시스템 프롬프트 구성 (날짜 정보 주입)
        full_prompt = f"""
        너는 우리반 학생들을 돕는 친절한 안내봇이야.
        오늘은 {current_date}이야.
        제공된 [정보]를 바탕으로 질문에 친절하게 답해줘. 정보에 없는 내용은 선생님께 여쭤보라고 안내해줘.

        [정보]: {st.session_state['global_context']}
        [질문]: {prompt}
        """
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            # 429 에러 대응을 위한 재시도 로직
            success = False
            for i in range(3): # 최대 3번 시도
                try:
                    response = model.generate_content(full_prompt)
                    full_response = response.text
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    success = True
                    break
                except Exception as e:
                    if "429" in str(e):
                        message_placeholder.warning(f"⚠️ 사용자가 많아 대기 중입니다... ({i+1}/3)")
                        time.sleep(3) # 3초 대기 후 재시도
                    else:
                        st.error(f"오류가 발생했습니다: {e}")
                        break
            
            if not success:
                st.error("🤖: 미안해! 지금 질문이 너무 많아서 대답하기 힘들어. 10초 뒤에 다시 물어봐 줄래?")