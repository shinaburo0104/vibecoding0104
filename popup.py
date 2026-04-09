"""메인 팝업 UI (CustomTkinter)."""
import io
import threading
from tkinter import messagebox

import customtkinter as ctk
import pyperclip
from PIL import ImageGrab

from llm import (
    DEFAULT_MODELS,
    PROVIDERS,
    detect_provider,
    make_client,
    normalize_provider,
)
from region_picker import pick_region


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


RELATIONS = [
    "친구",
    "연인",
    "가족",
    "직장 상사",
    "직장 동료",
    "선생님",
    "처음 보는 사람",
]

def _provider_label(provider_key: str) -> str:
    """내부 키 → 드롭다운에 표시되는 라벨."""
    return {
        "claude": "Claude",
        "openai": "OpenAI (GPT)",
        "gemini": "Gemini",
    }.get(provider_key, "Claude")


CARD_DEFS = [
    ("t_extreme", "🧠  T형 (논리 · 해결)", "#2a4d7a"),
    ("balanced", "⚖️  균형 (반반)", "#4a4a4a"),
    ("f_extreme", "💖  F형 (공감 · 위로)", "#7a2a55"),
    ("custom", "🎚️  커스텀 (슬라이더)", "#55357a"),
]


class PopupWindow(ctk.CTk):
    def __init__(self, config):
        super().__init__()
        self.cfg = config
        self.current_image_bytes: bytes | None = None
        self.cards: dict = {}

        self.title("F/T Messenger — MBTI 답장 어시스턴트")
        self.geometry("600x870")
        self.minsize(540, 760)
        self.attributes("-topmost", True)

        self._build_ui()

        # 저장된 키가 있다면 프로바이더 자동감지 1회 실행
        if self.api_entry.get().strip():
            self._autodetect_from_entry()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda _e: self._on_close())

    # ─────────────────────────── UI BUILD ───────────────────────────
    def _build_ui(self):
        # ── 타이틀
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            header,
            text="F/T Messenger",
            font=("Segoe UI", 20, "bold"),
        ).pack(side="left")
        ctk.CTkLabel(
            header,
            text="Ctrl+Shift+Space 로 호출 · ESC로 숨기기",
            text_color="#888",
            font=("Segoe UI", 10),
        ).pack(side="right")

        # ── 프로바이더 선택
        prov_row = ctk.CTkFrame(self)
        prov_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(prov_row, text="AI 프로바이더", width=110).pack(side="left", padx=8)
        # 저장된 프로바이더를 사람이 보는 라벨로 변환
        saved_provider = normalize_provider(self.cfg.get("provider", "claude"))
        self.prov_var = ctk.StringVar(value=_provider_label(saved_provider))
        self.prov_menu = ctk.CTkOptionMenu(
            prov_row,
            variable=self.prov_var,
            values=PROVIDERS,
            command=self._provider_changed,
        )
        self.prov_menu.pack(side="left", padx=(0, 8), pady=6)
        ctk.CTkLabel(
            prov_row,
            text="(키를 붙여넣으면 자동 감지됨)",
            text_color="#888",
            font=("Segoe UI", 10),
        ).pack(side="left")

        # ── API 키 행
        key_row = ctk.CTkFrame(self)
        key_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(key_row, text="Personal API Key", width=110).pack(side="left", padx=8)
        self.api_entry = ctk.CTkEntry(
            key_row, show="•", placeholder_text="sk-ant-... / sk-... / AIza..."
        )
        self.api_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.api_entry.insert(0, self.cfg.get("api_key", ""))
        # 키가 변경될 때마다 자동 감지
        self.api_entry.bind("<KeyRelease>", self._on_key_typed)
        self.api_entry.bind("<<Paste>>", lambda e: self.after(10, self._autodetect_from_entry))
        ctk.CTkButton(key_row, text="저장", width=60, command=self._save_key).pack(
            side="left", padx=(0, 8), pady=6
        )

        # ── 관계 선택
        rel_row = ctk.CTkFrame(self)
        rel_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(rel_row, text="상대와의 관계", width=110).pack(side="left", padx=8)
        self.rel_var = ctk.StringVar(value=self.cfg.get("relation", "친구"))
        self.rel_menu = ctk.CTkOptionMenu(
            rel_row,
            variable=self.rel_var,
            values=RELATIONS,
            command=self._save_relation,
        )
        self.rel_menu.pack(side="left", padx=(0, 8), pady=6)

        # ── 한줄 메모 (상황/힌트)
        memo_row = ctk.CTkFrame(self)
        memo_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(memo_row, text="한줄 메모", width=110).pack(side="left", padx=8)
        self.memo_entry = ctk.CTkEntry(
            memo_row,
            placeholder_text="상황/힌트 (예: 내가 약속 까먹음, 걔 요즘 예민함 등) — 선택사항",
        )
        self.memo_entry.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=6)

        # ── 메시지 입력 섹션
        ctk.CTkLabel(
            self, text="상대방이 보낸 메시지", font=("Segoe UI", 13, "bold"), anchor="w"
        ).pack(fill="x", padx=18, pady=(10, 2))

        self.msg_box = ctk.CTkTextbox(self, height=90, font=("Segoe UI", 12))
        self.msg_box.pack(fill="x", padx=14, pady=(0, 4))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 4))
        ctk.CTkButton(
            btn_row, text="📋  클립보드에서 붙여넣기", command=self._paste_clipboard, height=30
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btn_row, text="📸  화면 영역 캡처", command=self._capture_screen, height=30
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            btn_row,
            text="✕ 지우기",
            command=self._clear_input,
            height=30,
            fg_color="#555",
            hover_color="#444",
            width=70,
        ).pack(side="left")

        self.input_status = ctk.CTkLabel(
            self, text="", text_color="#888", font=("Segoe UI", 10), anchor="w"
        )
        self.input_status.pack(fill="x", padx=18)

        # ── F/T 슬라이더
        slider_box = ctk.CTkFrame(self)
        slider_box.pack(fill="x", padx=14, pady=(10, 4))
        top = ctk.CTkFrame(slider_box, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(top, text="🧠  T (논리)", text_color="#6db0ff").pack(side="left")
        self.f_label = ctk.CTkLabel(
            top, text="F = 50", font=("Segoe UI", 14, "bold")
        )
        self.f_label.pack(side="left", expand=True)
        ctk.CTkLabel(top, text="F (공감)  💖", text_color="#ff6db0").pack(side="right")

        self.f_slider = ctk.CTkSlider(
            slider_box,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._slider_changed,
        )
        self.f_slider.set(50)
        self.f_slider.pack(fill="x", padx=10, pady=(2, 10))

        # ── 생성 버튼
        self.gen_btn = ctk.CTkButton(
            self,
            text="✨  답변 생성",
            height=42,
            font=("Segoe UI", 14, "bold"),
            command=self._generate,
        )
        self.gen_btn.pack(fill="x", padx=14, pady=(4, 6))

        # ── 결과 카드 영역
        self.result_scroll = ctk.CTkScrollableFrame(
            self, label_text="생성된 답변 — 원하는 버전을 클릭하여 복사하세요"
        )
        self.result_scroll.pack(fill="both", expand=True, padx=14, pady=(4, 4))
        self._build_cards()

        # ── 상태바
        self.status = ctk.CTkLabel(
            self,
            text="API 키를 입력하고 저장한 뒤 사용하세요.",
            text_color="#aaa",
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.status.pack(fill="x", padx=18, pady=(0, 10))

    def _build_cards(self):
        for key, title, color in CARD_DEFS:
            card = ctk.CTkFrame(self.result_scroll, fg_color=color, corner_radius=10)
            card.pack(fill="x", pady=5, padx=2)

            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=10, pady=(8, 2))
            ctk.CTkLabel(
                head, text=title, font=("Segoe UI", 12, "bold"), text_color="white"
            ).pack(side="left")
            ctk.CTkButton(
                head,
                text="📋 복사",
                width=72,
                height=26,
                fg_color="white",
                text_color="black",
                hover_color="#ddd",
                command=lambda k=key: self._copy(k),
            ).pack(side="right")

            body = ctk.CTkLabel(
                card,
                text="(아직 생성되지 않음)",
                font=("Segoe UI", 12),
                justify="left",
                anchor="w",
                wraplength=500,
                text_color="white",
            )
            body.pack(fill="x", padx=12, pady=(0, 10))

            self.cards[key] = {"body": body, "content": ""}

    # ─────────────────────────── EVENTS ───────────────────────────
    def _slider_changed(self, v):
        self.f_label.configure(text=f"F = {int(v)}")

    def _save_key(self):
        key = self.api_entry.get().strip()
        self.cfg.set("api_key", key)
        self.cfg.set("provider", normalize_provider(self.prov_var.get()))
        self._set_status(
            f"✓ 키 저장됨 — 프로바이더: {self.prov_var.get()}", "#5fdd5f"
        )

    def _provider_changed(self, label: str):
        self.cfg.set("provider", normalize_provider(label))

    def _on_key_typed(self, _event=None):
        self._autodetect_from_entry()

    def _autodetect_from_entry(self):
        key = self.api_entry.get().strip()
        detected = detect_provider(key)
        if detected:
            label = _provider_label(detected)
            if self.prov_var.get() != label:
                self.prov_var.set(label)
                self._set_status(
                    f"🔍 키 형식으로 프로바이더 자동 감지됨: {label}", "#6db0ff"
                )

    def _save_relation(self, value):
        self.cfg.set("relation", value)

    def _paste_clipboard(self):
        try:
            text = pyperclip.paste() or ""
        except Exception as e:
            self._set_status(f"클립보드 오류: {e}", "#ff6666")
            return
        if not text.strip():
            self._set_status("클립보드가 비어 있습니다.", "#ffaa55")
            return
        self.msg_box.delete("1.0", "end")
        self.msg_box.insert("1.0", text)
        self.current_image_bytes = None
        self.input_status.configure(text=f"텍스트 {len(text)}자 입력됨", text_color="#888")
        self._set_status(f"클립보드에서 {len(text)}자 가져옴", "#aaa")

    def _capture_screen(self):
        # 캡처 중엔 본 창을 숨김
        self.withdraw()
        self.update_idletasks()
        try:
            region = pick_region(self)
        finally:
            self.deiconify()
            self.lift()
            self.focus_force()

        if not region:
            self._set_status("캡처 취소됨", "#aaa")
            return

        try:
            img = ImageGrab.grab(bbox=region)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            self.current_image_bytes = buf.getvalue()
        except Exception as e:
            self._set_status(f"캡처 오류: {e}", "#ff6666")
            return

        self.msg_box.delete("1.0", "end")
        self.msg_box.insert("1.0", "[화면 캡처됨 — AI가 이미지를 직접 읽습니다]")
        self.input_status.configure(
            text=f"📸 이미지 {img.size[0]}×{img.size[1]} 캡처됨",
            text_color="#6db0ff",
        )
        self._set_status("이미지 캡처 완료", "#aaa")

    def _clear_input(self):
        self.msg_box.delete("1.0", "end")
        self.memo_entry.delete(0, "end")
        self.current_image_bytes = None
        self.input_status.configure(text="")
        for key in self.cards:
            self.cards[key]["body"].configure(text="(아직 생성되지 않음)")
            self.cards[key]["content"] = ""
        self._set_status("입력 지움", "#aaa")

    def _generate(self):
        api_key = self.api_entry.get().strip()
        if not api_key:
            self._set_status("먼저 API 키를 입력·저장하세요.", "#ff6666")
            return

        text = self.msg_box.get("1.0", "end").strip()
        using_image = self.current_image_bytes is not None
        if not using_image and (
            not text or text.startswith("[화면 캡처됨")
        ):
            self._set_status("상대 메시지를 입력하거나 화면을 캡처하세요.", "#ff6666")
            return

        provider = normalize_provider(self.prov_var.get())
        self.gen_btn.configure(state="disabled", text="⏳  생성 중...")
        self._set_status(
            f"{self.prov_var.get()}가 4가지 버전을 만들고 있습니다...", "#ffd866"
        )

        payload_text = None if using_image else text
        memo = self.memo_entry.get().strip()
        # 프로바이더별 모델 키: model_claude / model_openai / model_gemini
        model = self.cfg.get(f"model_{provider}") or None
        threading.Thread(
            target=self._worker_generate,
            args=(
                provider,
                api_key,
                payload_text,
                self.current_image_bytes,
                self.rel_var.get(),
                int(self.f_slider.get()),
                memo,
                model,
            ),
            daemon=True,
        ).start()

    def _worker_generate(
        self, provider, api_key, text, image, relation, f_value, memo, model
    ):
        try:
            client = make_client(provider, api_key, model)
            result = client.generate(
                message_text=text,
                image_bytes=image,
                relation=relation,
                f_value=f_value,
                memo=memo,
            )
            self.after(0, lambda: self._show_results(result))
        except Exception as e:
            msg = str(e)
            self.after(0, lambda: self._show_error(msg))

    def _show_results(self, result: dict):
        detected = result.get("detected_message", "")
        for key in self.cards:
            content = (result.get(key) or "").strip()
            self.cards[key]["content"] = content
            self.cards[key]["body"].configure(
                text=content if content else "(비어있음)"
            )

        self.gen_btn.configure(state="normal", text="✨  답변 생성")
        if detected:
            self.input_status.configure(
                text=f"🤖 AI가 읽은 메시지: {detected[:60]}",
                text_color="#6db0ff",
            )
        self._set_status("✓ 생성 완료 — 원하는 카드의 복사 버튼을 누르세요.", "#5fdd5f")

    def _show_error(self, err: str):
        self.gen_btn.configure(state="normal", text="✨  답변 생성")

        # 429 Rate Limit / Quota 특수 처리
        lower = err.lower()
        is_rate = (
            "429" in err
            or "rate limit" in lower
            or "quota" in lower
            or "resource_exhausted" in lower
            or "too many requests" in lower
        )

        if is_rate:
            provider_label = self.prov_var.get()
            title = "⚠️ 429 — 요청 한도 초과"
            msg = (
                f"선택한 프로바이더({provider_label})의 요청 한도에 걸렸습니다.\n\n"
                f"[가능한 원인]\n"
                f"  1. 무료 티어 일일/분당 요청 수 초과\n"
                f"  2. API 키의 크레딧(잔액) 소진\n"
                f"  3. 결제 정보 미등록 (특히 OpenAI)\n\n"
                f"[해결 방법]\n"
                f"  • 1~2분 기다린 뒤 다시 시도 (분당 한도였다면)\n"
                f"  • 다른 프로바이더로 전환 (드롭다운에서 변경 후 키 저장)\n"
                f"  • Claude: console.anthropic.com 에서 크레딧 확인\n"
                f"  • OpenAI: platform.openai.com/account/billing\n"
                f"  • Gemini: aistudio.google.com 에서 키 상태 확인\n\n"
                f"[원문 에러]\n{err[:500]}"
            )
            messagebox.showwarning(title, msg)
            self._set_status("⚠️ 429 — 한도 초과 (다이얼로그 확인)", "#ffaa55")
            return

        # 일반 에러: 팝업으로 전체 내용 표시
        messagebox.showerror("오류", err[:800] if err else "알 수 없는 오류")
        short = (err.splitlines()[0] if err else "")[:120]
        self._set_status(f"오류: {short}", "#ff6666")

    def _copy(self, key: str):
        content = self.cards[key]["content"]
        if not content:
            self._set_status("아직 이 버전은 생성되지 않았습니다.", "#ffaa55")
            return
        try:
            pyperclip.copy(content)
        except Exception as e:
            self._set_status(f"복사 실패: {e}", "#ff6666")
            return
        nice = {
            "t_extreme": "T형",
            "balanced": "균형",
            "f_extreme": "F형",
            "custom": "커스텀",
        }.get(key, key)
        self._set_status(f"✓ '{nice}' 답변이 클립보드에 복사됨. 메신저에 붙여넣으세요.", "#5fdd5f")

    def _set_status(self, text: str, color: str = "#aaa"):
        self.status.configure(text=text, text_color=color)

    def _on_close(self):
        # 완전 종료가 아니라 숨기기만 — 트레이에 상주
        self.withdraw()
