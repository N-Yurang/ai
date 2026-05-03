import os
import json
import random
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from geopy.distance import geodesic

load_dotenv()

# ==========================================
# 1. 초기 설정 및 클라이언트 셋팅
# ==========================================
raw_key = os.getenv("GOOGLE_API_KEY")

if raw_key:
    print(f"✅ [DEBUG] API 키를 찾았습니다! (앞부분: {raw_key[:4]}...)")
    client = genai.Client(api_key=raw_key)
else:
    print("❌ [DEBUG] .env 파일에서 GOOGLE_API_KEY를 읽지 못했습니다.")
    client = None

app = FastAPI(title="TRIPLY AI Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. Pydantic 모델 (데이터 규격 정의)
# ==========================================

# 인텐트 추출용
class ChatMessage(BaseModel):
    role: str
    content: str

class IntentRequest(BaseModel):
    chat_history: List[ChatMessage]

# GA 경로 최적화용
class Place(BaseModel):
    place_id: int
    name: str
    latitude: float
    longitude: float
    trend_score: float
    festival_score: float

class Festival(BaseModel):
    festival_id: int
    latitude: float
    longitude: float

class GARequest(BaseModel):
    places: List[Place]
    festivals: List[Festival]
    weight_media: float
    weight_festival: float

# ==========================================
# 3. 인텐트 및 가중치 분석 (/ai/intent)
# ==========================================
@app.post("/ai/intent")
async def extract_intent(req: IntentRequest):
    """
    Gemini Flash를 통해 대화 맥락에서 지역, 가중치, 키워드를 추출합니다.
    """
    if not client:
        raise HTTPException(status_code=500, detail="API 키 설정이 필요합니다.")

    conversation = "\n".join([f"{msg.role}: {msg.content}" for msg in req.chat_history])
    
    system_instruction ="""
    너는 여행 큐레이터 'TRIPLY'의 AI 엔진이야. 사용자의 대화를 분석해 여행 의도를 JSON으로 추출해.
    1. region: 언급된 지역명 (예: "제주", "고흥" 등, 없으면 null)
    2. weight_media: 인스타 핫플 선호도 (0.0 ~ 1.0 사이의 소수점)
    3. weight_festival: 축제 참여 의지 (0.0 ~ 1.0 사이의 소수점)
    4. keyword_filter: 관심 키워드 리스트 (예: ["바다", "카페"])
    응답은 오직 순수 JSON 형식만 허용함.
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=conversation,
            config={"system_instruction": system_instruction, "response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 4. MFS-GA 기반 경로 최적화 (/ai/ga)
# ==========================================
@app.post("/ai/ga")
async def run_mfs_ga(req: GARequest):
    """
    유전 알고리즘을 통해 장소 만족도는 최대화하고 거리는 최소화하는 최적 경로를 산출합니다.
    """
    places = req.places
    festivals = req.festivals
    
    if len(places) == 0:
        raise HTTPException(status_code=400, detail="장소가 없습니다.")

    # [Bridge Logic] 축제 인근 장소 보너스 점수 부여 (10km 이내 +50점)
    place_values = {}
    nearest_dist = 9999 
    for p in places:
        bonus = 0
        min_dist_to_fest = 9999
        for f in festivals:
            dist = geodesic((p.latitude, p.longitude), (f.latitude, f.longitude)).km
            if dist <= 10:
                bonus = 50
            if dist < min_dist_to_fest:
                min_dist_to_fest = dist
        
        place_values[p.place_id] = (req.weight_media * p.trend_score) + (req.weight_festival * p.festival_score) + bonus
        if min_dist_to_fest < nearest_dist:
            nearest_dist = min_dist_to_fest

    if len(places) == 1:
        return {
            "itinerary": [
                {
                    "order": 1, 
                    "place_id": places[0].place_id, 
                    "name": places[0].name, 
                    "lat": places[0].latitude, 
                    "lng": places[0].longitude
                }
            ],
            "total_distance": f"{round(nearest_dist, 1)}km"
        }

    # [GA Engine] 유전 알고리즘 연산부
    POP_SIZE = 100
    GENS = 150

    def get_fitness(route: List[Place]) -> float:
        dist = sum(geodesic((route[i].latitude, route[i].longitude), (route[i+1].latitude, route[i+1].longitude)).km for i in range(len(route)-1))
        val = sum(place_values[p.place_id] for p in route)
        return val / (dist if dist > 0 else 0.1)

    population = [random.sample(places, len(places)) for _ in range(POP_SIZE)]

    for _ in range(GENS):
        population.sort(key=get_fitness, reverse=True)
        next_gen = population[:10]  
        
        while len(next_gen) < POP_SIZE:
            p1, p2 = random.sample(population[:20], 2)
            idx = random.randint(1, max(1, len(places)-2))
            child = p1[:idx] + [p for p in p2 if p not in p1[:idx]]
            if random.random() < 0.1: 
                i1, i2 = random.sample(range(len(child)), 2)
                child[i1], child[i2] = child[i2], child[i1]
            next_gen.append(child)
        population = next_gen

    best = max(population, key=get_fitness)
    total_dist = sum(geodesic((best[i].latitude, best[i].longitude), (best[i+1].latitude, best[i+1].longitude)).km for i in range(len(best)-1))

    return {
        "itinerary": [{"order": i+1, "place_id": p.place_id, "name": p.name, "lat": p.latitude, "lng": p.longitude} for i, p in enumerate(best)],
        "total_distance": f"{round(total_dist, 1)}km"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)