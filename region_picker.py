"""전체화면 반투명 오버레이로 화면 영역을 드래그 선택."""
import tkinter as tk


def pick_region(parent) -> tuple[int, int, int, int] | None:
    """
    parent: 기존 Tk root (CustomTkinter 루트 가능)
    반환: (x1, y1, x2, y2) 스크린 좌표 or None (취소 시)
    """
    result: list = [None]

    overlay = tk.Toplevel(parent)
    overlay.attributes("-fullscreen", True)
    overlay.attributes("-alpha", 0.3)
    overlay.attributes("-topmost", True)
    overlay.configure(bg="black")
    overlay.config(cursor="cross")
    overlay.focus_force()

    canvas = tk.Canvas(overlay, bg="black", highlightthickness=0, cursor="cross")
    canvas.pack(fill="both", expand=True)

    # 안내 텍스트
    canvas.create_text(
        20,
        20,
        anchor="nw",
        text="드래그하여 영역 선택  |  ESC = 취소",
        fill="white",
        font=("Segoe UI", 14, "bold"),
    )

    state = {"start": None, "rect": None}

    def on_press(e):
        state["start"] = (e.x, e.y)
        if state["rect"]:
            canvas.delete(state["rect"])
        state["rect"] = canvas.create_rectangle(
            e.x, e.y, e.x, e.y, outline="#ff3355", width=3
        )

    def on_drag(e):
        if state["start"] and state["rect"] is not None:
            x1, y1 = state["start"]
            canvas.coords(state["rect"], x1, y1, e.x, e.y)

    def on_release(e):
        if state["start"]:
            x1, y1 = state["start"]
            x2, y2 = e.x, e.y
            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                rx = overlay.winfo_rootx()
                ry = overlay.winfo_rooty()
                result[0] = (
                    min(x1, x2) + rx,
                    min(y1, y2) + ry,
                    max(x1, x2) + rx,
                    max(y1, y2) + ry,
                )
        overlay.destroy()

    def on_escape(_e=None):
        overlay.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    overlay.bind("<Escape>", on_escape)

    parent.wait_window(overlay)
    return result[0]
