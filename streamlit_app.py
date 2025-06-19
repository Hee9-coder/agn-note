import streamlit as st
import requests
import json
import base64
import time
import openai

st.title("🎈 나의 알・궁・나 노트")

st.markdown("""
학생이 손글씨로 쓴 노트를 업로드하면 자동 인식해드려요.  
또는 직접 입력해서 분석할 수도 있어요!
""")

# 입력 방식 선택
mode = st.radio("✍ 입력 방식 선택", ["🖼 OCR 자동 입력", "⌨️ 수동 입력"], horizontal=True)

# 초기 변수
알, 궁, 나 = "", "", ""

# OCR 모드
if mode == "🖼 OCR 자동 입력":
    uploaded_file = st.file_uploader("이미지 업로드 (JPG/PNG)", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        st.info("🔍 글자 인식 중입니다...")
        image_bytes = uploaded_file.read()
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')

        # 네이버 OCR API 호출
        headers = {
            "X-NCP-APIGW-API-KEY-ID": st.secrets["NAVER_OCR_CLIENT_ID"],
            "X-NCP-APIGW-API-KEY": st.secrets["NAVER_OCR_CLIENT_SECRET"],
            "Content-Type": "application/json"
        }
        payload = {
            "images": [{"format": "jpg", "data": encoded_image, "name": "note"}],
            "requestId": "note-ocr",
            "version": "V1",
            "timestamp": int(time.time() * 1000)
        }

        try:
            res = requests.post("https://naveropenapi.apigw.ntruss.com/vision/v1/ocr", headers=headers, data=json.dumps(payload))
            result = res.json()
            fields = result["images"][0]["fields"]
            full_text = "\n".join([f["inferText"] for f in fields])
            st.text_area("🧾 인식된 전체 텍스트", value=full_text, height=150)

            # 간단한 구분 추출
            lower = full_text.lower()
            if "알" in lower and "궁" in lower and "나" in lower:
                parts = lower.split("알")[1].split("궁")
                알 = parts[0].strip()
                궁 = parts[1].split("나")[0].strip()
                나 = parts[1].split("나")[1].strip()
            else:
                st.warning("⚠️ '알・궁・나' 구분이 어렵습니다. 제목을 또렷하게 써 주세요.")
        except Exception as e:
            st.error(f"OCR 오류: {e}")

    # 자동 입력 + 수정 가능
    알 = st.text_area("1️⃣ 알게 된 점", value=알)
    궁 = st.text_area("2️⃣ 궁금한 점", value=궁)
    나 = st.text_area("3️⃣ 나의 생각", value=나)

    if st.button("🤖 분석하기"):
        with st.spinner("GPT가 분석 중입니다..."):
            prompt = f"""
            아래는 한 초등학생이 쓴 알·궁·나 학습 노트입니다.

            [알게 된 점]
            {알}

            [궁금한 점]
            {궁}

            [나의 생각]
            {나}

            위의 내용을 요약해서 다음 항목으로 구분해줘:
            1. 알게 된 점의 핵심 키워드 3개
            2. 궁금한 점의 질문 의도 (예: 사실 확인, 확장 사고, 감정 표현 등)
            3. 나의 생각에서 드러난 학생의 태도나 감정
            """
            try:
                client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
                result = response.choices[0].message.content
                st.success("✅ 분석 결과")
                st.markdown(result)
            except Exception as e:
                st.error(f"GPT 오류: {e}")

# 수동 입력 모드
else:
    with st.form("note_form"):
        알 = st.text_area("1️⃣ 알게 된 점", placeholder="예: 지구의 자전 때문에 낮과 밤이 생긴다.")
        궁 = st.text_area("2️⃣ 궁금한 점", placeholder="예: 그럼 지구가 자전하지 않으면 어떻게 될까?")
        나 = st.text_area("3️⃣ 나의 생각", placeholder="예: 나는 별과 자전이 연결된다는 걸 알게 되었다.")
        submitted = st.form_submit_button("✍ 분석하기")

    if submitted:
        with st.spinner("GPT가 분석 중입니다..."):
            prompt = f"""
            아래는 한 초등학생이 쓴 알·궁·나 학습 노트입니다.

            [알게 된 점]
            {알}

            [궁금한 점]
            {궁}

            [나의 생각]
            {나}

            위의 내용을 요약해서 다음 항목으로 구분해줘:
            1. 알게 된 점의 핵심 키워드 3개
            2. 궁금한 점의 질문 의도 (예: 사실 확인, 확장 사고, 감정 표현 등)
            3. 나의 생각에서 드러난 학생의 태도나 감정
            """
            try:
                client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
                result = response.choices[0].message.content
                st.success("✅ 분석 결과")
                st.markdown(result)
            except Exception as e:
                st.error(f"GPT 오류: {e}")
