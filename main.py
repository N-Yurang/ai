from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # 👈 [추가 1] 문지기 불러오기
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. .env 파일에서 숨겨둔 API 키 안전하게 불러오기
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 2. Gemini AI 모델 세팅
genai.configure(api_key=GEMINI_API_KEY)
# 괄호 안의 이름을 2.5 버전으로 바꿔줍니다!
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. FastAPI 서버 앱 생성
app = FastAPI()

# 👇 [추가 2] 프론트엔드(Next.js)가 마음껏 접근할 수 있게 허락해 주는 코드
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 모든 도메인 허용 (나중에 배포할 때 바꿀 예정)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프론트엔드가 보낼 데이터(질문)의 규칙 정하기
class ChatRequest(BaseModel):
    user_message: str

# 4. 서버가 잘 켜졌는지 확인하는 기본 주소 (http://localhost:8000/)
@app.get("/")
def read_root():
    return {"message": "🚀 TRIPLY AI 서버가 완벽하게 작동 중입니다!"}

# 5. 실제로 AI가 대답을 생성해 주는 핵심 API 주소
@app.post("/api/recommend")
def get_ai_recommendation(request: ChatRequest):
    try:
        # 1. 팀장님이 프론트에서 친 질문(user_message)을 변수에 담습니다.
        user_input = request.user_message 
        
        # 2. AI에게 역할과 '진짜 질문'을 섞어서 명령을 내립니다.
        prompt = f"너는 여행 추천 AI 챗봇 'TRIPLY'야. 사용자의 질문에 맞춰서 다양한 국내 여행지를 추천해줘. 질문: {user_input}"
        
        # 3. AI가 이 질문을 읽고 답변을 생성하게 합니다.
        response = model.generate_content(prompt)
        
        # 4. AI가 만든 답변을 프론트엔드로 보내줍니다.
        return {"status": "success", "ai_reply": response.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

        # load_dotenv()  <-- 앞에 # 붙여서 끄기
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  <-- 앞에 # 붙여서 끄기

# 👇 여기에 복사한 키를 직접 붙여넣습니다! (양옆 큰따옴표 "" 필수)
GEMINI_API_KEY = "AIzaSyA_k1xWjLAYKhXG-gpo89j1pBqC8rjRxHA"

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
# ... 아래 코드는 그대로 두기 ...

