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
import base64 # 👈 [중요] 이 줄을 맨 위에 꼭 추가하세요!

# 1. 파일 기반 저장소 설정
DB_FILE = "school_db.txt"

# 2. 페이지 설정 및 초기 데이터 로드
st.set_page_config(
    page_title="DDAI",          # 브라우저 탭에 표시될 이름
    page_icon="DD (8).png",               # 브라우저 탭에 표시될 아이콘 파일 (또는 이모지)
    layout="wide"                         # 화면 레이아웃
)

def save_data(text):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        f.write(text)

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "아직 등록된 학교 정보가 없습니다."


if "global_context" not in st.session_state:
    st.session_state["global_context"] = load_data()

# API 설정
try:
    genai.configure(api_key=st.secrets["DB"])
    # 팁: 429 에러가 너무 잦다면 'gemini-1.5-flash'로 바꾸는 것이 훨씬 안정적입니다.
    model = genai.GenerativeModel('models/gemma-3-27b-it') 
except:
    st.error("API 키 설정이 필요합니다.")

# ==========================================
# --- [DESIGN UPDATE] 통합 로고 섹션 (크기 확대 버전) ---
# ==========================================

# ==========================================
# --- [DESIGN UPDATE] 테마 대응 로고 섹션 (버그 수정 완벽판) ---
# ==========================================

# 1. 이미지를 HTML에 직접 넣기 위해 Base64로 변환하는 함수
def get_image_base64(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

img_dark = get_image_base64("DD (5).png")
img_light = get_image_base64("DD (6).png")

# 2. CSS 스타일 적용 (완벽한 테마 전환 및 여백 제거)
st.markdown(
    """
    <style>
    /* 상단 여백 최소화 */
    .block-container {
        padding-top: 1rem !important;
    }
    
    /* 로고 래퍼 설정 */
    .logo-wrapper {
        display: flex;
        justify-content: center;
        width: 100%;
    }
    
    /* 이미지 기본 설정 (위아래 여백을 여기서 줄임) */
    .theme-logo {
        max-width: 100%;
        margin-top: -20px;
        margin-bottom: -20px;
    }

    /* 다크 모드일 때: 라이트 로고 숨김, 다크 로고 표시 */
    @media (prefers-color-scheme: dark) {
        .light-logo { display: none !important; }
        .dark-logo { display: block !important; }
    }
    
    /* 라이트 모드일 때: 다크 로고 숨김, 라이트 로고 표시 */
    @media (prefers-color-scheme: light) {
        .dark-logo { display: none !important; }
        .light-logo { display: block !important; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. 로고 배치 (HTML <img> 태그 직접 사용)
col1, col2, col3 = st.columns([1, 1, 1]) 

with col2:
    if img_dark and img_light:
        st.markdown(
            f"""
            <div class="logo-wrapper">
                <img class="theme-logo dark-logo" src="data:image/png;base64,{img_dark}">
                <img class="theme-logo light-logo" src="data:image/png;base64,{img_light}">
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.error("파일을 찾을 수 없습니다. 'DD (5).png'와 'DD (6).png' 파일이 올바르게 있는지 확인해주세요.")



# 구분선 (너무 바짝 붙어있다면 여백용으로 사용)
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
# ==========================================
# 3. 사이드바 메뉴
st.sidebar.markdown("### DDAI 메뉴 ver 1.0")
mode = st.sidebar.radio("모드 선택", ["학생 모드 (질문하기)", "선생님 모드 (관리자)"])

if "선생님 모드" in mode:
    st.header("🔐 관리자 페이지")
    st.markdown("---")
    password = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if password == "20260403":
        st.subheader("📁 데이터 업로드")
        uploaded_file = st.file_uploader("학교 정보 파일 (xlsx, hwp, hwpx, pdf)", type=["xlsx", "hwp", "hwpx", "pdf"])
        
        if uploaded_file:
            new_context = ""
            file_type = uploaded_file.name.split('.')[-1].lower()
            
            with st.spinner("파일을 분석하는 중입니다..."):
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

                    # ... (파일 변환하는 코드들 생략) ...

                    if new_context:
                        # [수정된 부분] 기존 데이터에 새 데이터를 이어 붙입니다!
                        if st.session_state["global_context"] == "아직 등록된 학교 정보가 없습니다.":
                            # 처음 데이터를 넣을 때는 기본 안내 멘트를 지우고 새 데이터만 넣음
                            combined_context = new_context
                        else:
                            # 이미 데이터가 있다면 기존 내용 아래에 새 내용을 추가함
                            combined_context = st.session_state["global_context"] + "\n\n--- [새로 추가된 정보] ---\n\n" + new_context
                        
                        # 합쳐진 전체 데이터를 세션과 파일에 저장
                        st.session_state["global_context"] = combined_context
                        save_data(combined_context) 
                        
                        st.balloons() # 성공 축하 효과
                        st.success("✅ 기존 데이터에 새 학교 정보가 안전하게 추가되었습니다!")
                except Exception as e:
                    st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
    elif password != "":
        st.error("비밀번호가 틀렸습니다.")

else:
    # --- 학생 모드 ---
    # st.header("🤖 우리반 보조봇") # 상단 디자인으로 대체하므로 제거
    
    # 오늘 날짜 정보 생성
    now = datetime.datetime.now()
    weekday_list = ['월', '화', '수', '목', '금', '토', '일']
    current_date = now.strftime(f"%Y년 %m월 %d일({weekday_list[now.weekday()]})")
    
    #st.markdown(f"#### 📅 오늘은 **{current_date}** 입니다.")
    #st.caption("💡 시간표, 급식, 시험 범위 등 학교 생활에 대해 무엇이든 물어보세요!")
    st.markdown("---")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages: st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("질문을 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)

        # 시스템 프롬프트 구성 (날짜 정보 주입)
        full_prompt = f"""
        너는 둔덕중학교 학생들을 돕는 친절한 안내봇 DDAI야.
        학생들은 너를 줄여서 DD 또는 디디라고 부를거야.
        오늘은 {current_date}이야.
        오늘 날짜를 정확히 기억하고 대화에 반영하기.
        제공된 [학교 정보]를 바탕으로 질문에 친절하고 정중하게 답해줘. 학교 관련 질문을 했을 때, 정보에 없는 내용은 '선생님께 여쭤보는 게 좋겠어'라고 안내해줘.
        학생들의 여러 이야기를 들어주고 재밌고 재치있게 답변하는 것도 좋아.
        만일 너는 누가 만들었어 같은 질문을 안 받으면 절대 말하지 말고, 받으면 2026년 기준 3학년 박유찬, 김도윤이 공동개발한 Ai라고 소개해줘. 박유찬은 ai모델 연결과 디자인, 김도윤은 데이터 베이스 관리와 웹 디자인 담당이라고 해줘.
        '안녕하세요! 저는 둔덕중학교 학생들을 돕는 친절한 안내봇 DDMS이고, 학생들은 저를 줄여서 디디 또는 DD라고 부를 수 있습니다.' 같은 말은 말하지 말아줘.
        모든 말에 높임말을 사용해줘.
        {current_date}에 맞는 시간표만 알려주고, 날짜에 맞는 시간표가 없으면 오늘 시간표가 올라오지 않았다고 하고 선생님께 여쭤보라고 안내하기, 다른 시간표는 언급하지 않기.
        날짜가 적혀있지 않은 시간표나 급식은 무시하기.
        사용자와 나눈 모든 대화를 기억하고, 답변에 사용하기.
        학교관련 일이 아니라도, 요청한 일은 적극적으로 도와주기.
        [학교 정보]: {st.session_state['global_context']}
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
                        message_placeholder.warning(f"⚠️ 현재 질문자가 많아 대기 중입니다. 잠시만 기다려주세요. ({i+1}/3)")
                        time.sleep(3) # 3초 대기 후 재시도
                    else:
                        st.error(f"오류가 발생했습니다. 개발자에게 문의하세요: {e}")
                        break
            
            if not success:
                st.error("🤖 DDMS: 미안해! 지금 질문이 너무 많아서 대답하기 힘들어. 10초 뒤에 다시 물어봐 줄래?")