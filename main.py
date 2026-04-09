"""F/T Messenger 진입점 — 시스템 트레이 + 글로벌 핫키 + 팝업."""
import sys
import threading

from PIL import Image, ImageDraw, ImageFont

from config import Config
from popup import PopupWindow


HOTKEY = "ctrl+shift+space"


def _make_tray_icon() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 배경 원
    d.ellipse((4, 4, 60, 60), fill=(60, 110, 200, 255))
    # F/T 텍스트
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    d.text((12, 16), "F/T", fill=(255, 255, 255, 255), font=font)
    return img


def main():
    cfg = Config()

    app = PopupWindow(cfg)
    # 시작할 때는 항상 창을 보여줌 (사용자가 프로그램 실행한 걸 인지할 수 있도록)
    # 이후 X 버튼을 누르면 트레이로 숨겨지고, 핫키로 다시 호출 가능.
    app.deiconify()
    app.after(100, app.lift)
    app.after(120, app.focus_force)

    def show_window():
        """핫키/트레이에서 호출 — 메인 스레드로 마샬링."""
        app.after(0, _show_window_impl)

    def _show_window_impl():
        try:
            app.deiconify()
            app.lift()
            app.focus_force()
            app.attributes("-topmost", True)
        except Exception as e:
            print(f"[show] {e}")

    def quit_app():
        try:
            if tray_icon is not None:
                tray_icon.stop()
        except Exception:
            pass
        app.after(0, app.destroy)

    # ── 시스템 트레이 ─────────────────────────────
    tray_icon = None
    try:
        import pystray

        def on_show(icon, item):
            show_window()

        def on_quit(icon, item):
            quit_app()

        menu = pystray.Menu(
            pystray.MenuItem(
                f"보이기 ({HOTKEY})", on_show, default=True
            ),
            pystray.MenuItem("종료", on_quit),
        )
        tray_icon = pystray.Icon(
            "FTMessenger", _make_tray_icon(), "F/T Messenger", menu
        )
        threading.Thread(target=tray_icon.run, daemon=True).start()
    except Exception as e:
        print(f"[tray] 시스템 트레이 사용 불가: {e}")

    # ── 글로벌 핫키 ────────────────────────────────
    try:
        import keyboard

        keyboard.add_hotkey(HOTKEY, show_window)
    except Exception as e:
        print(f"[hotkey] 글로벌 핫키 등록 실패: {e}")
        print("        (권한 부족 시 관리자 권한으로 실행해보세요)")

    # ── 메인 루프 ──────────────────────────────────
    try:
        app.mainloop()
    finally:
        try:
            if tray_icon is not None:
                tray_icon.stop()
        except Exception:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()
