import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

# 1. .env 파일에서 API 키 안전하게 불러오기
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2. Gemini AI 모델 세팅 (보안 적용)
genai.configure(api_key=GEMINI_API_KEY)
# 모델 이름은 현재 사용 가능한 안정 버전으로 유지합니다.
model = genai.GenerativeModel('gemini-1.5-flash') 

# 3. FastAPI 서버 앱 생성
app = FastAPI()

# 프론트엔드 접근 허용 (CORS 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 규격 정의
class ChatRequest(BaseModel):
    user_message: str

@app.get("/")
def read_root():
    return {"message": "🚀 TRIPLY AI 서버가 보안 모드로 작동 중입니다!"}

@app.post("/api/recommend")
def get_ai_recommendation(request: ChatRequest):
    try:
        user_input = request.user_message 
        prompt = f"너는 여행 추천 AI 챗봇 'TRIPLY'야. 사용자의 질문에 맞춰서 다양한 국내 여행지를 추천해줘. 질문: {user_input}"
        
        response = model.generate_content(prompt)
        return {"status": "success", "ai_reply": response.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 🛑 [주의] 이 아래에 더 이상 키를 적는 코드가 있으면 안 됩니다! 🛑