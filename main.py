import os
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json

# 1. .env 파일을 읽어옵니다. (파일이 바로 옆에 있어서 이 한 줄이면 충분해요)
load_dotenv()

# 2. 키가 잘 들어왔는지 터미널에 바로 출력해봅니다. (보안상 앞 4자리만 출력)
raw_key = os.getenv("GOOGLE_API_KEY")

if raw_key:
    print(f"✅ [DEBUG] API 키를 찾았습니다! (앞부분: {raw_key[:4]}...)")
    genai.configure(api_key=raw_key)
else:
    print("❌ [DEBUG] .env 파일에서 GOOGLE_API_KEY를 읽지 못했습니다.")
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

@app.get("/")
def read_root():
    return {"status": "success", "message": "🚀 TRIPLY AI 서버가 작동 중입니다!"}

# ... 이후 하단 코드 (api/recommend 등) ...

from pydantic import BaseModel

# 1. 프론트엔드에서 보내는 데이터 형식을 정의합니다.
class ChatRequest(BaseModel):
    user_message: str

# 2. 드디어 진짜 'AI 추천' 문을 만듭니다!
@app.post("/api/recommend")
async def get_recommendation(request: ChatRequest):
    try:
        print(f"📩 [DEBUG] 요청 발생: {request.user_message}")

        # 시스템 프롬프트
        system_instruction = """
        """
        
        # Gemini 모델 설정
        model = genai.GenerativeModel('gemini-flash-latest')
        
        # 프론트엔드에서 보낸 메시지를 AI에게 전달
        response = model.generate_content(request.user_message)
        
        # 💡 response.text 사용 전 안전하게 체크
        if response and response.text:
            ai_reply = json.loads(response.text)
            print(f"✅ [DEBUG] AI 응답 성공")
            return {
                "status": "success",
                "ai_reply": ai_reply
            }
        else:
            raise Exception("AI 응답에서 텍스트를 찾을 수 없습니다.")
        
    except Exception as e:
        print(f"❌ [ERROR] AI 생성 중 에러 발생: {e}")
        # 💡 사용자에게는 깔끔한 메시지를 보여주되, 원인은 로그에 남깁니다.
        error_msg = "AI가 대답하는 중에 문제가 생겼어요. (API 할당량 초과일 수 있습니다)"
        if "429" in str(e):
             error_msg = "AI 서비스 사용량이 초과되었습니다. 잠시 후 다시 시도해 주세요!"
             
        return {
            "status": "error",
            "message": error_msg
        }
