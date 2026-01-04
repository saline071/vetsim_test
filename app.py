import streamlit as st
import time
import os

# ==========================================
# 1. 페이지 설정
# ==========================================
st.set_page_config(
    page_title="VetSim: 수의 임상 진단 시뮬레이터",
    page_icon="🩺",
    layout="wide"
)

st.markdown("""
    <style>
        /* 1. 툴팁 위치 및 애니메이션 정의 */
        .sidebar-tooltip {
            position: fixed;
            top: 60px;        /* 헤더 바로 아래 */
            left: 10px;       /* 왼쪽 여백 */
            z-index: 99999;   /* 맨 위에 표시 */
            pointer-events: none; /* 이걸 넣어야 툴팁 뒤에 있는 버튼도 클릭 가능함 */
            animation: bounce 2s infinite;
        }

        /* 2. 말풍선 디자인 */
        .tooltip-box {
            background-color: #ff4b4b; /* 스트림릿 레드 컬러 */
            color: white;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.3);
            position: relative;
        }

        /* 3. 말풍선 꼬리 (위쪽을 가리킴) */
        .tooltip-box::after {
            content: "";
            position: absolute;
            bottom: 100%;       /* 말풍선 윗변 */
            left: 15px;         /* 꼬리 위치 */
            margin-left: -5px;
            border-width: 8px;
            border-style: solid;
            border-color: transparent transparent #ff4b4b transparent;
        }

        /* 4. 둥둥 떠다니는 애니메이션 */
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        
        /* (선택) PC화면(너비 768px 이상)에서는 숨기기 - 모바일에서만 보이게 하려면 주석 해제하세요 */
        /* @media (min-width: 768px) { .sidebar-tooltip { display: none; } } */
        
    </style>

    <div class="sidebar-tooltip">
        <div class="tooltip-box">
            ↖ 메뉴를 열어보세요!
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 환자 데이터 (이미지 경로 포함)
# ==========================================
# 팁: images 폴더에 실제 사진 파일이 있어야 작동합니다.
case_data = {
    "name": "초코",
    "info": "3살 / 중성화 수컷 / 푸들",
    "cc": "구토 (5회 이상), 식욕 부진",
    "image_path": "images/choco.jpeg",
    "tests": {
        "CBC (혈액검사)": {
            "cost": 30000, 
            "result": "✅ [CBC] WBC, RBC, HCT 정상. 염증 수치 낮음.",
            "type": "text"
        },
        "X-ray (방사선)": {
            "cost": 40000, 
            "result": "⚠️ [X-ray] 복부 방사선 상 장 내 이물 음영 확인.",
            "type": "image", 
            "image_path": "images/xray.jpeg",  # 여기에 실제 파일 경로를 넣으세요
            "caption": "RL abd rad"
        },
        "US (초음파)": {
            "cost": 70000, 
            "result": "⚠️ [US] 위 내 강한 음향 음영(Acoustic Shadowing) 확인.",
            "type": "text" # 사진 있으면 'image'로 바꾸고 path 추가하면 됨
        },
        "S Chem": {
            "cost": 50000, 
            "result": "✅ [Chem] 간/신장 수치 정상. 전해질 불균형 경미함.",
            "type": "text"},

        "Parvo Kit": {
            "cost": 25000, 
            "result": "✅ [Parvo] Negative (음성).",
            "type": "text"},
    },
    "answer_keywords": ["이물", "Foreign", "FB", "Gastric foriegn body", "위내이물"],
    "diagnosis_full": "위 내 이물 (Gastric Foreign Body)"
}

# ==========================================
# 3. 세션 상태 관리 (기억장치)
# ==========================================
if 'cost' not in st.session_state:
    st.session_state['cost'] = 0
if 'logs' not in st.session_state:
    st.session_state['logs'] = [] # 검사 결과들이 쌓이는 리스트
if 'done_tests' not in st.session_state:
    st.session_state['done_tests'] = []
if 'game_over' not in st.session_state:
    st.session_state['game_over'] = False

# ==========================================
# 4. 화면 구성 (레이아웃)
# ==========================================

# [사이드바] 상태창
with st.sidebar:
    # ▼▼▼ [새로 추가해야 할 코드] ▼▼▼
    # 파일이 진짜로 있는지 확인하고 보여주는 안전한 코드입니다
    if "image_path" in case_data and os.path.exists(case_data['image_path']):
        st.image(case_data['image_path'], caption=case_data['name'])
    else:
        # 사진이 없거나 경로가 틀렸으면 텍스트만 보여주기
        st.warning("⚠️ 프로필 사진을 찾을 수 없습니다.")
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    st.header(f"환자: {case_data['name']}")
    st.info(case_data['info'])
    st.divider()
    st.metric(label="현재 누적 병원비", value=f"{st.session_state['cost']:,} 원")
    
    if st.button("🔄 처음부터 다시 하기"):
        st.session_state.clear()
        st.rerun()
# [메인 화면]
st.title("🩺 우리 애가 아파요 엉엉")
st.markdown("### Case 1. 구토하는 강아지")
st.warning(f"주증상: {case_data['cc']}")
st.markdown("---")

# ------------------------------------------
# (A) 검사 오더 내리기
# ------------------------------------------
st.subheader("1️⃣ 검사 선택 (Diagnostic Plan)")
col1, col2, col3, col4 = st.columns(4)
test_keys = list(case_data['tests'].keys())

# 버튼 배치 로직
if not st.session_state['game_over']:
    for i, test_name in enumerate(test_keys):
        # 4개의 컬럼에 순서대로 버튼 배치
        col = [col1, col2, col3, col4][i % 4]
        
        if col.button(test_name):
            if test_name in st.session_state['done_tests']:
                st.toast("이미 시행한 검사입니다!", icon="⚠️")
            else:
                # 검사 수행 처리
                test_info = case_data['tests'][test_name]
                st.session_state['cost'] += test_info['cost']
                st.session_state['done_tests'].append(test_name)
                
                # 로그에 결과 저장 (텍스트인지 이미지인지 구분해서 저장)
                log_entry = {
                    "name": test_name,
                    "result_text": test_info['result'],
                    "type": test_info['type']
                }
                
                # 이미지가 있는 경우 경로도 같이 저장
                if test_info['type'] == 'image':
                    log_entry["image_path"] = test_info.get("image_path")
                    log_entry["caption"] = test_info.get("caption")
                
                st.session_state['logs'].append(log_entry)
                st.rerun()

# ------------------------------------------
# (B) 결과 차트 (여기에 사진이 뜹니다)
# ------------------------------------------
st.markdown("---")
st.subheader("2️⃣ 검사 결과 리포트")
result_area = st.container(border=True)

if not st.session_state['logs']:
    result_area.write("아직 시행된 검사가 없습니다. 위에서 검사를 선택하세요.")
else:
    for log in st.session_state['logs']:
        # 검사명 출력
        result_area.markdown(f"**[{log['name']}]**")
        
        # 텍스트 결과 출력
        result_area.write(log['result_text'])
        
        # 이미지 결과 출력 (이미지 타입인 경우)
        if log['type'] == 'image':
            img_path = log['image_path']
            # 파일이 실제로 있는지 확인 후 출력 (에러 방지)
            if os.path.exists(img_path):
                result_area.image(img_path, caption=log.get('caption'), width=400)
            else:
                result_area.error(f"❌ 이미지 파일을 찾을 수 없습니다: {img_path}")
                result_area.info("images 폴더에 사진 파일을 넣어주세요.")
        
        result_area.divider()

# ------------------------------------------
# (C) 최종 진단
# ------------------------------------------
st.markdown("---")
st.subheader("3️⃣ 최종 진단 (Diagnosis)")

with st.form("dx_form"):
    user_dx = st.text_input("진단명을 입력하세요 (예: 위내 이물):")
    submit = st.form_submit_button("진단 제출")
    
    if submit:
        if not user_dx:
            st.warning("진단명을 입력해주세요!")
        else:
            # ========================================================
            # [핵심 로직] 대소문자 구분 없이 & 띄어쓰기 무시하기
            # ========================================================
            
            # 1. 사용자 입력을 소문자로 바꾸고(.lower), 공백을 전부 삭제(.replace)
            normalized_input = user_dx.lower().replace(" ", "")
            
            # 2. 정답 키워드도 똑같이 바꿔서 포함되어 있는지 확인
            # (이렇게 하면 'Foreign Body'나 'foreignbody'나 똑같이 'foreignbody'가 됩니다)
            is_correct = any(
                k.lower().replace(" ", "") in normalized_input 
                for k in case_data['answer_keywords']
            )
            
            if is_correct:
                st.balloons()
                st.success(f"정답입니다! 👏 (진단명: {case_data['diagnosis_full']})")
                st.write(f"총 검사 비용: {st.session_state['cost']:,} 원")
                st.session_state['game_over'] = True
            else:
                st.error(f"오진입니다. '{user_dx}'은(는) 정답이 아닙니다.")

                st.info("힌트: 핵심 키워드(예: 이물, 파보 등)가 포함되어야 합니다.")

