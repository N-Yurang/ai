# 🤖 TRIPLY AI Core Server (Python)

본 리포지토리는 대화형 여행 큐레이션 서비스 **TRIPLY**의 핵심 인지 및 경로 최적화 연산을 담당하는 파이썬 AI 백엔드 서버입니다. 

자연어 처리(NLP)를 통한 유저 인텐트 추출, 공간 데이터 반경 확장 검색, 그리고 유전 알고리즘(GA) 기반의 이동 동선 최적화 파이프라인을 제공합니다.

---

## 🛠 Tech Stack
- **Framework:** FastAPI (Asynchronous Web Framework)
- **LLM Engine:** Google GenAI SDK (`gemini-2.5-flash`)
- **Database Adapter:** Psycopg2 (RealDictCursor)
- **Geospatial Library:** Geopy (Geodesic Distance Calculation)
- **Deployment:** Google Cloud Run (Serverless Container)

---

## 🏗 Core Pipeline Architecture

AI 서버는 원스톱 API 엔드포인트(`/ai/recommend`)를 통해 호출되며, 내부적으로 3단계의 하이브리드 파이프라인을 거쳐 검증된 최적 경로를 반환합니다.

~~~text
[Client / Node.js] ──(chat_history)──> 1. Gemini Intent Extraction
                                                 │ (JSON Intent)
                                                 ▼
                                       2. Supabase Spatial Query
                                          - Administrative Suffix Trimming
                                          - Multi-Region OR Fallback
                                          - 15km/30km Radius Expansion
                                                 │ (Filtered Places & Festivals)
                                                 ▼
                                       3. MFS-GA Optimization
                                          - Evolutionary Path Search
                                                 │ (Optimized Itinerary)
[Client / Node.js] <──(JSON Response)────────────┘
~~~

### 1. Gemini Intent Extraction (NLP)
유저와 주고받은 전체 대화 내역(`chat_history`)을 컨텍스트로 입력받아 다중 요구사항을 분석합니다. 마지막 메시지에만 매몰되어 화제를 전환하는 최신 편향(Recency Bias)을 제약 조건으로 방어하며, 고유명사 예시 없이 추상화된 추론 로직만으로 순수 JSON 포맷을 추출합니다.
- **주요 추출 데이터:** 서비스 가능 지역(`region`), 선호 태그(`tags`), 인스타 핫플 선호도(`weight_media`), 축제 선호도(`weight_festival`), 수락 여부(`is_ready`), 창작 코스명(`course_name`).

### 2. Intelligent Spatial Query & Fallback Mechanism
데이터베이스(Supabase)와의 정합성을 보장하고, 텍스트 검색의 한계를 극복하기 위해 백엔드 파이썬 레벨에서 3단계 방어벽을 수행합니다.
- **행정구역 접미사 필터링:** 유저가 입력한 지역명 끝의 `시`, `군`, `구` 단어를 정규화하여 DB 내의 와일드카드(`LIKE %kw%`) 매칭률을 극대화합니다.
- **다중 지역 AND-to-OR Fallback:** 서로 다른 두 지역(예: 강릉, 영월)을 동시에 요구하여 AND 조건이 0건을 반환할 경우, 즉시 교집합 실패를 감지하고 OR 쿼리로 전환하여 장소 풀을 복구합니다.
- **LBS 반경 확장 검색 (Radius Expansion):** 특정 단일 구역(예: 광안리)만 매칭되어 동선이 단조로워지는 문제를 방지합니다. 최초 검색된 마커를 중심점(Center Coordinate)으로 설정하고, `geopy.distance.geodesic` 연산을 통해 **반경 15km~30km 이내**의 전체 DB 장소를 실시간으로 결합합니다.

### 3. MFS-GA (Multi-Factor Scoring Genetic Algorithm)
확장된 장소 풀을 대상으로 유저 취향 가산점 점수판(Score Board)을 구축한 뒤, 최적의 이동 동선 순서를 찾기 위해 메타헤우리스틱 연산을 수행합니다.
- **Scoring Factor:** 트렌드 점수, 유저 취향 태그 일치 보너스(+20.0), 카테고리 선호도 보너스(+30.0), 축제 인접도 보너스(+50.0).
- **Genetic Algorithm 세팅:**
  - `POP_SIZE = 100` (개체군 크기)
  - `GENS = 150` (최대 진화 세대 수)
  - `Mutation Rate = 0.1` (적응도 정체 방지를 위한 돌연변이 확률)
  - **Fitness Function:** `Fitness = 10000 / Total Geodesic Distance (km)` (총 이동 거리가 짧을수록 적응도가 높아지는 반비례 구조)

---

## 🚀 API Specification

### `POST /ai/recommend`

#### Request Body
~~~json
{
  "chat_history": [
    {
      "role": "user",
      "content": "축제도 즐기고 싶고 시원한 밤바다도 보고 싶어"
    },
    {
      "role": "model",
      "content": "활기찬 축제와 밤바다를 동시에 즐기기엔 부산이 제격이에요! 특히 '광안리어방축제' 기간에 방문하시면 아름다운 야경과 축제를 모두 만끽할 수 있답니다. 이 코스로 기획해 드릴까요?"
    },
    {
      "role": "user",
      "content": "ㅇㅇ 그 코스로 짜줘"
    }
  ],
  "travel_date": "2026-05-31"
}
~~~

#### Response Body (`is_ready: true` 일 때 최적화 경로 반환)
~~~json
{
  "intent_extracted": {
    "is_ready": true,
    "reply": "",
    "region": "부산 수영구",
    "tags": ["바다뷰", "야경명소", "활기찬", "커플"],
    "category_pref": "TREND",
    "weight_media": 0.8,
    "weight_festival": 1.0,
    "start_date": null,
    "end_date": null,
    "course_name": "광안리어방축제 낭만 바다 투어",
    "selected_festival": "광안리어방축제"
  },
  "reply": "원하시는 분위기에 맞게 '광안리어방축제 낭만 바다 투어' 기획을 완료했어요!\n\n아래 버튼을 눌러 동선을 확인해 보세요! ✨",
  "course_name": "광안리어방축제 낭만 바다 투어",
  "itinerary": [
    {
      "order": 1,
      "place_id": 22,
      "name": "부산 해운대해수욕장",
      "lat": 35.1587,
      "lng": 129.1603
    },
    {
      "order": 2,
      "place_id": 41,
      "name": "광안리 해수욕장",
      "lat": 35.1531,
      "lng": 129.1189
    },
    {
      "order": 3,
      "place_id": "fest_19",
      "name": "🎉 광안리어방축제",
      "lat": 35.1531,
      "lng": 129.1189
    }
  ],
  "total_distance": "4.2km"
}
~~~

---

## 💻 Environment Variables

서버 실행을 위해 최상위 디렉토리에 `.env` 파일을 생성하고 아래 환경 변수를 정의해야 합니다.

~~~env
GOOGLE_API_KEY=AIzaSy...YourGeminiKey
SUPABASE_DB_URL=postgres://postgres:[비밀번호]@[호스트]:6543/postgres
~~~

---

## 🏃‍♂️ Installation & Running

### 1. 가상환경 구축 및 의존성 설치
~~~bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/Scripts/activate  # Windows (Git Bash)
source venv/bin/activate      # Mac/Linux

# 필수 패키지 설치
pip install -r requirements.txt
~~~

### 2. 로컬 개발 서버 구동
~~~bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
~~~

---

## 🛡️ Robustness & Exception Handling (Troubleshooting)
- **Silent Pivot (지역 무단 변경) 방어:** AI가 자신이 가진 사전 지식에 갇혀 DB에 없는 축제를 유저에게 제안한 뒤, 최종 페이로드 조립 시 데이터가 존재하는 다른 지역으로 컴포넌트를 바꿔치기하는 현상을 시스템 제약 층위에서 원천 차단했습니다.
- **Empty Festival Array Handling:** 축제 이름 텍스트가 DB 내 정보와 완전히 일치하지 않아 파싱에 실패할 경우, 강제로 전체 축제 배열을 참조하여 무관한 지역으로 지도가 튀는 버그를 `else: festivals = []` 구조를 도입해 완전히 방어했습니다.
- **Data Type Safety:** 위도/경도 연산 및 가산점 총합 연산 과정에서 발생할 수 있는 데이터 타입 불일치와 `None` 에러를 안정적으로 처리하기 위해 `COALESCE` 및 파이썬 Null Safety 가드 코드가 내장되어 있습니다.
