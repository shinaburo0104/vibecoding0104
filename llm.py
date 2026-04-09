"""멀티 프로바이더 LLM 클라이언트 (Claude / OpenAI / Gemini).

하나의 Personal API Key로 세 가지 프로바이더를 지원합니다.
각 프로바이더는 동일한 generate(...) 시그니처와 동일한 JSON 반환 형식을 공유합니다.
"""
import base64
import io
import json
import re


SYSTEM_PROMPT = """당신은 한국어 메신저 답장 어시스턴트입니다.
사용자가 상대방에게서 받은 메시지(텍스트 또는 화면 캡처 이미지)를 보면,
MBTI의 T(Thinking, 사고)와 F(Feeling, 감정) 축을 기준으로 4가지 버전의 답장을 생성하세요.

[버전 정의]
- t_extreme  : F=0.   완전 T형. 사실/논리/해결책 중심. 공감 표현은 최소화하되 무례하지 않게.
- balanced   : F=50.  균형형. 짧게 공감한 뒤 실용적 제안/정보 제공.
- f_extreme  : F=100. 완전 F형. 정서 공감과 위로 중심. "그랬구나", "속상했겠다" 같은 반응.
                     해결책을 먼저 들이밀지 말고 감정부터 받아주기.
- custom     : 사용자가 지정한 F값(0~100)에 맞게 비율 조정. 0=t_extreme과 유사, 100=f_extreme과 유사.

[규칙]
1. 상대와의 관계(친구/연인/가족/상사 등)에 맞는 말투를 사용하세요.
   - 친구/연인/가까운 가족 → 반말, 자연스러운 구어체
   - 직장 상사/선생님/처음 보는 사람 → 정중한 존댓말
2. 각 답장은 2~4문장, 카카오톡에서 실제로 칠 법한 길이.
3. 이모지는 관계와 상황에 맞게 절제해서 사용.
4. 상대 메시지가 이미지로 주어지면, 이미지에서 가장 최근/핵심 메시지를 읽어 답변.
5. 4가지 버전은 서로 명확히 다르게 — 단어만 살짝 바꾼 느낌 금지.
6. "한줄 메모"가 주어지면, 사용자가 알려준 상황/힌트를 4가지 버전 모두에 반영하세요
   (예: "사실 내가 약속 까먹음" → 사과 뉘앙스 필수 / "걔 요즘 예민함" → 조심스러운 어조).

[출력 형식]
아래 JSON 형식만 반환하세요. 코드블록(```), 설명, 접두/접미 텍스트 모두 금지.
{
  "detected_message": "(상대가 보낸 메시지의 핵심 요약, 이미지일 경우 읽어낸 내용)",
  "t_extreme": "...",
  "balanced": "...",
  "f_extreme": "...",
  "custom": "..."
}
"""


TAIL_INSTRUCTION = (
    "\n위 메시지에 대해 t_extreme / balanced / f_extreme / custom 4가지 버전 답장을"
    " 위에 안내한 JSON 형식 그대로만 반환하세요."
)

IMAGE_NOTE = (
    "(위 이미지는 메신저 화면 캡처입니다. "
    "상대방이 보낸 가장 최근 메시지를 읽고 답장을 만들어주세요.)"
)


# ───────────────── 공통 유틸 ─────────────────
def _build_header(relation: str, f_value: int, memo: str) -> str:
    memo_line = (
        f"[내 한줄 메모(상황/힌트)] {memo.strip()}\n" if memo and memo.strip() else ""
    )
    return (
        f"[상대와의 관계] {relation}\n"
        f"{memo_line}"
        f"[내가 원하는 custom 버전의 F값] {f_value} (0=완전 T, 100=완전 F)\n\n"
        f"[상대방이 방금 보낸 메시지]"
    )


def _parse_json(raw: str) -> dict:
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"AI 응답에서 JSON을 찾을 수 없습니다:\n{raw[:200]}")
    chunk = raw[start : end + 1]
    try:
        data = json.loads(chunk)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}\n원본: {chunk[:300]}")
    for key in ("t_extreme", "balanced", "f_extreme", "custom"):
        data.setdefault(key, "")
    return data


# ───────────────── 프로바이더 식별 ─────────────────
PROVIDERS = ["Claude", "OpenAI (GPT)", "Gemini"]

DEFAULT_MODELS = {
    "claude": "claude-sonnet-4-5",
    "openai": "gpt-4o",
    "gemini": "gemini-2.5-flash",
}


def normalize_provider(name: str) -> str:
    n = (name or "").strip().lower()
    if "claude" in n or "anthropic" in n:
        return "claude"
    if "openai" in n or "gpt" in n:
        return "openai"
    if "gemini" in n or "google" in n:
        return "gemini"
    return "claude"


def detect_provider(api_key: str) -> str | None:
    """API 키 프리픽스로 프로바이더 자동 감지."""
    k = (api_key or "").strip()
    if not k:
        return None
    if k.startswith("sk-ant-"):
        return "claude"
    if k.startswith("AIza"):
        return "gemini"
    if k.startswith("sk-"):
        return "openai"
    return None


# ───────────────── Claude ─────────────────
class ClaudeClient:
    def __init__(self, api_key: str, model: str | None = None):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or DEFAULT_MODELS["claude"]

    def generate(
        self, message_text=None, image_bytes=None, relation="친구", f_value=50, memo=""
    ) -> dict:
        blocks: list = [{"type": "text", "text": _build_header(relation, f_value, memo)}]
        if image_bytes:
            b64 = base64.standard_b64encode(image_bytes).decode("ascii")
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": b64,
                    },
                }
            )
            blocks.append({"type": "text", "text": IMAGE_NOTE})
        elif message_text:
            blocks.append({"type": "text", "text": message_text})
        else:
            raise ValueError("메시지나 이미지가 필요합니다.")
        blocks.append({"type": "text", "text": TAIL_INSTRUCTION})

        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": blocks}],
        )
        return _parse_json(resp.content[0].text)


# ───────────────── OpenAI ─────────────────
class OpenAIClient:
    def __init__(self, api_key: str, model: str | None = None):
        import openai

        self.client = openai.OpenAI(api_key=api_key)
        self.model = model or DEFAULT_MODELS["openai"]

    def generate(
        self, message_text=None, image_bytes=None, relation="친구", f_value=50, memo=""
    ) -> dict:
        content: list = [{"type": "text", "text": _build_header(relation, f_value, memo)}]
        if image_bytes:
            b64 = base64.standard_b64encode(image_bytes).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )
            content.append({"type": "text", "text": IMAGE_NOTE})
        elif message_text:
            content.append({"type": "text", "text": message_text})
        else:
            raise ValueError("메시지나 이미지가 필요합니다.")
        content.append({"type": "text", "text": TAIL_INSTRUCTION})

        kwargs = dict(
            model=self.model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        )
        # gpt-4o/gpt-4o-mini는 JSON mode 지원
        try:
            kwargs["response_format"] = {"type": "json_object"}
            resp = self.client.chat.completions.create(**kwargs)
        except Exception:
            kwargs.pop("response_format", None)
            resp = self.client.chat.completions.create(**kwargs)

        return _parse_json(resp.choices[0].message.content or "")


# ───────────────── Gemini ─────────────────
class GeminiClient:
    def __init__(self, api_key: str, model: str | None = None):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai
        self.model_name = model or DEFAULT_MODELS["gemini"]
        self.model_obj = genai.GenerativeModel(
            self.model_name, system_instruction=SYSTEM_PROMPT
        )

    def generate(
        self, message_text=None, image_bytes=None, relation="친구", f_value=50, memo=""
    ) -> dict:
        from PIL import Image

        parts: list = [_build_header(relation, f_value, memo)]
        if image_bytes:
            parts.append(Image.open(io.BytesIO(image_bytes)))
            parts.append(IMAGE_NOTE)
        elif message_text:
            parts.append(message_text)
        else:
            raise ValueError("메시지나 이미지가 필요합니다.")
        parts.append(TAIL_INSTRUCTION)

        try:
            resp = self.model_obj.generate_content(
                parts,
                generation_config={
                    "max_output_tokens": 2048,
                    "response_mime_type": "application/json",
                },
            )
        except Exception:
            resp = self.model_obj.generate_content(parts)

        text = getattr(resp, "text", None)
        if not text:
            # candidates[0].content.parts[0].text 폴백
            try:
                text = resp.candidates[0].content.parts[0].text
            except Exception:
                text = ""
        return _parse_json(text)


# ───────────────── 팩토리 ─────────────────
def make_client(provider: str, api_key: str, model: str | None = None):
    """provider: 'claude' | 'openai' | 'gemini' (대/소문자 무관, 'GPT' 등 별칭도 허용)"""
    p = normalize_provider(provider)
    if p == "claude":
        return ClaudeClient(api_key, model)
    if p == "openai":
        return OpenAIClient(api_key, model)
    if p == "gemini":
        return GeminiClient(api_key, model)
    raise ValueError(f"지원하지 않는 프로바이더: {provider}")
