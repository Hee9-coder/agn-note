import streamlit as st
import openai
import os
import base64
import time
import requests
import json
import sys
import hashlib
import hmac

# 💡 시크릿 키 설정
openai.api_key = st.secrets["OPENAI_API_KEY"]
NAVER_OCR_CLIENT_ID = st.secrets["NAVER_OCR_CLIENT_ID"]
NAVER_OCR_CLIENT_SECRET = st.secrets["NAVER_OCR_CLIENT_SECRET"]

# 📝 페이지 제목
st.title("📗 나의 알・궁・나 노트")

# 📌 설명 문구
st.markdown("""
**🧠노트가 자동으로 쌓인다!**

오늘 배운 내용을 기록만 해 주세요.
질문 수준을 높여드릴게요.
(복습 문제 제공은 업데이트 예정)

이미 손글씨로 쓴 노트가 있다면 사진을 찍어 업로드하면
자동으로 대신 써 드릴게요.
*"이미지 자동 입력"으로 잘 인식되지 않으면 직접 입력해 주세요!*
""")

# ✨ 입력 방식 선택
mode = st.radio("✍️ 입력 방식 선택", ["🖼️ OCR 자동 입력", "⌨️ 수동 입력"], horizontal=True)

알, 궁, 나 = "", "", ""

# ✅ OCR 입력 처리
if mode == "🖼️ OCR 자동 입력":
    uploaded_file = st.file_uploader(
        "노트 사진을 올려 주세요.", type=["png", "jpg", "jpeg"])
    result_text = ""

    # 사용자 설정
access_key = st.secrets["NAVER_OCR_CLIENT_ID"]
secret_key = st.secrets["NAVER_OCR_CLIENT_SECRET"]

OCR_REQUEST_URL = "https://YOUR_API_GATEWAY_ID.apigw.ntruss.com/custom/v1/XXXXX"  # 발급받은 endpoint
OCR_URI = "/custom/v1/XXXXX"

def make_signature():
    timestamp = str(int(time.time() * 1000))
    method = "POST"
    message = method + " " + OCR_URI + "\n" + timestamp + "\n" + access_key
    message = bytes(message, 'UTF-8')
    signingKey = base64.b64encode(hmac.new(bytes(secret_key, 'UTF-8'), message, digestmod=hashlib.sha256).digest())
    return signingKey.decode('utf-8'), timestamp


st.title("📗 나의 알・궁・나 노트 - OCR 자동 변환")

uploaded_file = st.file_uploader("노트 이미지를 업로드하세요", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    image_data = base64.b64encode(uploaded_file.read()).decode('utf-8')

    payload = {
        "version": "V2",
        "requestId": "sample_id",
        "timestamp": int(time.time() * 1000),
        "images": [{
            "name": "note",
            "format": "jpg",
            "data": image_data
        }]
    }

    signature, timestamp = make_signature()

    headers = {
        "Content-Type": "application/json",
        "x-ncp-apigw-timestamp": timestamp,
        "x-ncp-iam-access-key": access_key,
        "x-ncp-apigw-signature-v2": signature
    }

    response = requests.post(OCR_REQUEST_URL, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        st.success("OCR 분석 완료")
        st.json(response.json())
    else:
        st.error("OCR 분석 실패")
        st.write("응답 코드:", response.status_code)
        st.text(response.text)

with st.form("ocr_note_form"):
        알 = st.text_area("1️⃣ 알게 된 점", value=result_text, key="ocr_알")
        궁 = st.text_area("2️⃣ 궁금한 점", key="ocr_궁")
        나 = st.text_area("3️⃣ 나의 생각", key="ocr_나")
        ocr_submitted = st.form_submit_button("✏️ 분석하기")

if ocr_submitted:
    analyze = True

# ✅ 수동 입력 처리
elif mode == "⌨️ 수동 입력":
    with st.form("manual_form"):
        알 = st.text_area("1️⃣ 알게 된 점", key="수동_알", placeholder="예: 지구의 자전 때문에 낮과 밤이 생긴다.")
        궁 = st.text_area("2️⃣ 궁금한 점", key="수동_궁", placeholder="예: 지구가 자전하지 않으면 어떻게 될까?")
        나 = st.text_area("3️⃣ 나의 생각", key="수동_나", placeholder="예: 밤하늘의 별이 자전과 관련 있다는 걸 새롭게 알게 되었어.")
        manual_submitted = st.form_submit_button("✏️ 분석하기")

    if manual_submitted:
        analyze = True

# ✅ GPT 분석 로직 공통 실행
if "analyze" in locals() and analyze:
    with st.spinner("인공지능이 노트 분석 중입니다..."):
        SYSTEM_PROMPT = """
        너는 초등학생의 질문을 평가하는 전문가야.
        학생이 입력한 질문이 블룸의 인지적 수준 중 어디에 해당하는지를 판단하고,
        그 이유와 질문을 더 깊이 있는 수준으로 바꿀 수 있는 제안을 해 줘.

        블룸의 6단계는 다음과 같아:
        1 기억하기 (사실, 용어 나열)
        2 이해하기 (설명, 요약)
        3 적용하기 (실생활 사례)
        4 분석하기 (비교, 관계 파악)
        5 평가하기 (판단, 근거 제시)
        6 창조하기 (새로운 질문 만들기, 가정하기)

        또한 학생이 쓴 ‘알게 된 점’에서 핵심 키워드 3개를 뽑고,
‘궁금한 점’에서 질문 의도를 분석해줘. (예: 사실 확인, 원인 파악, 감정 표현 등)
‘나의 생각’에는 감정이나 태도가 드러나 있는지 알려줘.

아래와 같은 JSON 형식으로만 정확히 응답해 줘.

{
    "keyword": ["핵심", "키워드", "3개"],
    "question_intent": "질문 의도",
    "attitude_emotion": "감정 또는 태도",
    "level": 4,
    "level_name": "분석하기",
    "rationale": "해당 수준으로 판단한 이유",
    "improvement": "더 높은 수준으로 질문을 바꾸는 방법"
            "level": 3,
            "level_name": "적용하기",
            "rationale": "실제 상황을 들어 설명하려 했기 때문입니다.",
            "improvement": "이 질문을 더 높은 수준으로 바꾸려면, 문제 상황 속 원인이나 결과를 분석하는 방향으로 바꿔 보세요."
}
        """

        prompt = f"""
        아래는 한 초등학생이 쓴 알・궁・나 학습 노트입니다.

        [알게 된 점]  
        {알}

        [궁금한 점]  
        {궁}

        [나의 생각]  
        {나}

        위의 내용을 요약해서 다음 항목으로 구분해줘:
        1. 알게 된 점의 핵심 키워드 3개
        2. 궁금한 점의 질문 의도 (예: 사실 확인, 원인 파악, 감정 표현 등)
        3. 나의 생각에서 드러난 학생의 태도나 감정
        """

    try:
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            result = response.choices[0].message.content
            st.success("✅ 분석 결과")
            st.markdown(result)

    except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
