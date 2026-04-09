# F/T Messenger — MBTI 감정·논리 답장 어시스턴트

> 제1회 Vibe Coding 경진대회 (2026 대한기계학회 IT지능융합부문 춘계학술대회) 출품작

카카오톡/디스코드 등 메신저에서 **"F형이 필요한 순간인데 말이 T밖에 안 나올 때"**,
반대로 **"T형 답변을 해야 하는데 감정이 앞설 때"**,
사용자가 선택한 AI (**Claude / GPT / Gemini**) 가 **T형·균형·F형·커스텀** 4가지 버전의 답장을 즉시 생성해주는 Windows 유틸리티입니다.

## ✨ 주요 기능

| 기능 | 설명 |
|---|---|
| **멀티 AI 프로바이더** | **Claude / OpenAI GPT / Google Gemini** 중 선택. Personal API Key 하나로 어떤 프로바이더든 사용. 키 프리픽스(`sk-ant-`, `sk-`, `AIza`)로 **자동 감지** |
| **글로벌 핫키** | `Ctrl + Shift + Space` — 어느 창에서든 즉시 호출 |
| **시스템 트레이 상주** | 평소엔 트레이에 숨어 있다가 핫키로 호출 |
| **스마트 입력** | (1) 클립보드 붙여넣기 (2) 화면 영역 캡처 — 선택한 AI의 Vision 기능이 이미지를 직접 읽음 (별도 OCR 불필요) |
| **한줄 메모** | "걔 요즘 예민함", "내가 약속 까먹음" 같은 **상황/힌트**를 한 줄로 전달 → 4가지 버전 모두에 반영 |
| **F/T 슬라이더** | 0(완전 T) ~ 100(완전 F) 로 원하는 감정/논리 비율 지정 |
| **4-in-1 생성** | 한 번의 API 호출로 T형·균형·F형·커스텀(슬라이더 값) **4가지 버전**을 동시 생성 |
| **관계 맞춤 말투** | 친구/연인/가족/상사 등 관계에 맞는 반말·존댓말 자동 선택 |
| **원클릭 복사** | 원하는 카드의 "복사" 버튼 → 메신저에 바로 붙여넣기 |

## 🚀 빠른 시작

### 1) 실행 파일로 쓰기

저장소 우측 **[Releases](../../releases)** 에서 `FTMessenger.exe` 를 내려받아 더블클릭하면 트레이 아이콘이 생성됩니다.
(파일 크기가 GitHub 단일 파일 제한(100MB)을 넘어서 Release 에셋으로 배포합니다.)
처음 실행 시 Personal API Key (Gemini / Claude / OpenAI 아무거나) 를 입력 후 저장하세요.

### 2) 소스에서 실행

```bash
pip install -r requirements.txt
python main.py
```

### 3) `.exe` 빌드

```bash
build.bat
```
→ `dist\FTMessenger.exe` 생성.

## 🔑 API 키 받는 법 — 누구나 무료로 시작 가능

셋 중 **하나만** 있으면 됩니다. 가장 쉬운 선택은 **Gemini (완전 무료, 카드 등록 불필요)**.

| 프로바이더 | 무료 여부 | 키 발급 | 키 형식 |
|---|---|---|---|
| 🌟 **Google Gemini** *(추천)* | ✅ **완전 무료** | https://aistudio.google.com/apikey | `AIza...` |
| **Claude** (Anthropic) | ⭕ $5 가입 크레딧 | https://console.anthropic.com/ | `sk-ant-...` |
| **OpenAI** (GPT) | ❌ 유료만 가능 | https://platform.openai.com/api-keys | `sk-...` |

### 🌟 Gemini 무료 키 발급 — 3분

1. **Google 계정으로 로그인** → https://aistudio.google.com/apikey
2. **"Create API key"** 클릭
3. 프로젝트 없으면 "Create API key in new project" 선택 → 자동 생성
4. `AIzaSy…` 로 시작하는 **39자 키 복사**
5. 프로그램의 **Personal API Key** 칸에 붙여넣고 **저장**
   → 프리픽스 `AIza` 로 자동 감지되어 드롭다운이 **Gemini**로 전환됨

**무료 한도 (Gemini 2.5 Flash 기준)**: 분당 10회 · 일 250회 · 250k 토큰/분.
일반 사용에는 충분합니다.

> 만약 `429 limit: 0` 에러가 나면 리전 제약일 수 있습니다.
> `~/.ft_messenger_config.json` 의 `model_gemini` 필드를
> `gemini-2.5-flash-lite` 또는 `gemini-2.0-flash-lite` 로 바꿔보세요.

### ⭕ Claude 무료 크레딧 ($5)

1. https://console.anthropic.com 가입 (Google OAuth)
2. 가입 시 $5 무료 크레딧 자동 지급 *(리전·프로모션 따라 상이)*
3. Dashboard → **API Keys** → **Create Key**
4. `sk-ant-…` 키 복사 → 프로그램에 붙여넣기

$5로 Sonnet 4.5 기준 **약 500~1,000회 생성** 가능합니다 (4버전 동시 생성 아키텍처 덕분에 1회당 비용이 낮음).

> 키는 `~/.ft_messenger_config.json` 에 로컬 저장됩니다.

## 🎯 사용 흐름

1. 카카오톡에서 친구가 "나 오늘 너무 힘들었어..." 라고 보냄
2. `Ctrl + Shift + Space` 누름 → 팝업 나타남
3. 메시지를 복사하거나 **"📸 화면 영역 캡처"** 로 카카오톡 말풍선을 드래그 선택
4. 관계를 **"친구"** 로, F 슬라이더는 예를 들어 **70** 으로 조정
5. **"답변 생성"** 클릭 → 4가지 버전이 카드로 표시됨
6. 마음에 드는 카드의 **📋 복사** → 카카오톡에 붙여넣기

## 🧱 기술 스택

- **Python 3.11** + **CustomTkinter** (GUI)
- **Anthropic Claude / OpenAI GPT / Google Gemini** — 세 AI를 동일 인터페이스로 사용 (모두 Vision 지원)
- **pystray** (시스템 트레이)
- **keyboard** (글로벌 핫키)
- **Pillow** (화면 캡처)
- **pyperclip** (클립보드)
- **PyInstaller** (.exe 패키징)

## 📁 파일 구조

```
ft-messenger/
├── main.py            # 진입점: 트레이 + 핫키 + 팝업 wiring
├── popup.py           # 메인 팝업 UI
├── region_picker.py   # 화면 영역 선택 오버레이
├── llm.py             # Claude API 래퍼 (4버전 JSON 생성)
├── config.py          # 설정 저장소
├── requirements.txt
├── build.bat          # PyInstaller 빌드 스크립트
└── README.md
```

## ⚠️ 알려진 한계

- 글로벌 핫키는 Windows 권한에 따라 관리자 모드가 필요할 수 있습니다.
- 화면 캡처는 **메인 모니터만 지원** (멀티모니터는 향후 개선 대상).
- 네트워크가 필요합니다 (Claude API 호출).

## 🔮 향후 개선 방향

- 2차원 슬라이더 (F/T × 격식/친근)
- 대화 히스토리 기반 문맥 유지
- 로컬 LLM (llama.cpp) 지원으로 오프라인 모드
- 관계별 프리셋 템플릿 커스터마이징
