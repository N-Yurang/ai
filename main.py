import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from pydantic import BaseModel
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 1. .env 파일을 읽어옵니다. (파일이 바로 옆에 있어서 이 한 줄이면 충분해요)
load_dotenv()

# 2. 키가 잘 들어왔는지 터미널에 바로 출력해봅니다. (보안상 앞 4자리만 출력)
raw_key = os.getenv("GOOGLE_API_KEY")

if raw_key:
    print(f"✅ [DEBUG] API 키를 찾았습니다! (앞부분: {raw_key[:4]}...)")
    client = genai.Client(api_key=raw_key)
else:
    print("❌ [DEBUG] .env 파일에서 GOOGLE_API_KEY를 읽지 못했습니다.")
    client = None
    # .env 파일 안의 글자가 GOOGLE_API_KEY=... 가 맞는지 다시 확인해주세요!

app = FastAPI()

# CORS 설정 (이것도 팀원들이랑 작업하면서 꼬였을 수 있으니 다시 체크!)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 프론트엔드에서 보내는 데이터 형식을 정의합니다.
class ChatRequest(BaseModel):
    user_message: str

@app.get("/")
def read_root():
    return {"status": "success", "message": "🚀 TRIPLY AI 서버가 작동 중입니다!"}

# ... 이후 하단 코드 (api/recommend 등) ...

#테스트용 임시 DB
places_db = [
    {"name": "제주 협재 해수욕장", "tags": "부모님과 바다뷰 조용한"},
    {"name": "부산 광안리", "tags": "커플 바다뷰 야경명소"},
    {"name": "강릉 정동진", "tags": "아이와함께 바다뷰 웅장한"},
    {"name": "속초 중앙시장", "tags": "가족 걷기좋은 사진맛집"},
    {"name": "서울 남산타워", "tags": "커플 야경명소 감성적인"}
]

# 2. 드디어 진짜 'AI 추천' 문을 만듭니다!
@app.post("/api/recommend")
async def get_recommendation(request: ChatRequest):
    if not client:
        return {"status": "error", "message": "API 키 설정이 되어있지 않습니다."}

    try:
        print(f"📩 [DEBUG] 요청 발생: {request.user_message}")

        # 시스템 프롬프트
        # 키워드 뽑아내기
        system_instruction_1 = """ ...
        너는 여행지 태그 추출기야. 사용자의 문장에서 아래 허용된 태그만 추출해서 JSON으로 출력해.
        
        [허용 태그]
        분위기: 조용한, 감성적인, 웅장한, 야경명소
        누구와: 부모님과, 아이와함께, 커플, 혼자
        특징: 바다뷰, 걷기좋은, 사진맛집

        출력 형식: {"keywords": ["태그1", "태그2"]}
        
        """
        
        # Gemini 모델 설정
        response1 = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=request.user_message,
            config = {"system_instruction": system_instruction_1, "response_mime_type": "application/json"}
        )

        user_tags = json.loads(response1.text).get("keywords", [])
        user_tags_str = ", ".join(user_tags)

        if not user_tags:
            return {"status": "success", "ai_reply": "어떤 분위기의 장소를 찾으시는지 조금 더 자세히 말씀해 주시겠어요?"}
        
        #코사인 유사도
        db_tags = [place["tags"] for place in places_db]
        all_texts = [user_tags_str] +db_tags

        vectorizer = CountVectorizer().fit_transform(all_texts)
        vectors = vectorizer.toarray()
        
        cosine_sim = cosine_similarity([vectors[0]], vectors[1:])[0]
        top_indices = cosine_sim.argsort()[-3:][::-1]
        
        final_places_info = []
        for i in top_indices:
            if cosine_sim[i] > 0:
                final_places_info.append(places_db[i])

        if not final_places_info:
            return {"status": "success", "ai_reply": "앗, 입력하신 키워드에 딱 맞는 장소를 아직 찾지 못했어요."}

        #답변 깔끔하게
        places_str = "\n".join([f"- {p['name']} (특징: {p['tags']})" for p in final_places_info])
        
        prompt_2 = f"""
        너는 다정하고 센스 있는 여행 가이드야.
        사용자가 처음에 이렇게 말했어: "{request.user_message}"
        
        우리 시스템이 사용자의 취향에 맞춰 아래 3곳을 찾았어:
        {places_str}
        
        이 장소들을 사용자에게 추천해 줘. 
        질문의 의도와 장소의 특징(태그)을 자연스럽게 엮어서 설명하되, 
        가독성을 위해 반드시 아래 형식을 그대로 복사해서 대답해줘. 
        각 장소 설명이 끝날 때마다 반드시 빈 줄(Enter 두 번)을 넣어서 문단을 확실히 나눠야 해.

        [출력 형식]
        (반갑고 다정한 인사말 및 공감 1~2문장)

        📍 [장소 이름 1]
        - (왜 추천하는지 이유 1~2문장)

        📍 [장소 이름 2]
        - (왜 추천하는지 이유 1~2문장)

        📍 [장소 이름 3]
        - (왜 추천하는지 이유 1~2문장)

        (기대감을 높이는 마무리 인사 1문장)
        """
        
        response2 = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_2
        )
        
        ai_reply_text = response2.text

        return {"status": "success", "ai_reply": ai_reply_text}

    except Exception as e:
        print(f"❌ [ERROR] AI 생성 중 에러 발생: {e}")

        # 💡 사용자에게는 깔끔한 메시지를 보여주되, 원인은 로그에 남깁니다.
        error_msg = "AI가 대답하는 중에 문제가 생겼어요."
        
        if "429" in str(e):
             error_msg = "AI 서비스 사용량이 초과되었습니다. 잠시 후 다시 시도해 주세요!"
        elif "quota" in str(e).lower():
            error_msg = "API 할당량이 부족합니다."     

        return {
            "status": "error",
            "message": error_msg
        }