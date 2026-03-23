import random
import time
import tkinter as tk

# 게임 설정 (pygame 없이 tkinter로 구현)
GRID_W = 10
GRID_H = 20
CELL = 20
PADDING = 20

PLAY_W = GRID_W * CELL
PLAY_H = GRID_H * CELL

PREVIEW_W = 160
PREVIEW_H = 160

WINDOW_W = PLAY_W + PREVIEW_W + PADDING * 3
WINDOW_H = PLAY_H + PADDING * 3

# 색상
BG = "#0f1222"
GRID = "#2a2f47"
BORDER = "#444a67"
TEXT = "#ffffff"
MUTED = "#b7bacc"

COLORS = {
    "S": "#2ecc71",
    "Z": "#e74c3c",
    "I": "#1abc9c",
    "O": "#f1c40f",
    "J": "#3498db",
    "L": "#e67e22",
    "T": "#9b59b6",
}

# 테트리스 모양 (회전 상태). '0'이 블록 칸입니다. (5x5 매트릭스)
S = [
    [".....", ".....", "..00.", ".00..", "....."],
    [".....", "..0..", "..00.", "...0.", "....."],
]
Z = [
    [".....", ".....", ".00..", "..00.", "....."],
    [".....", "..0..", ".00..", ".0...", "....."],
]
I = [
    ["..0..", "..0..", "..0..", "..0..", "....."],
    [".....", "0000.", ".....", ".....", "....."],
]
O = [
    [".....", ".....", ".00..", ".00..", "....."],
]
J = [
    [".....", ".0...", ".000.", ".....", "....."],
    [".....", "..00.", "..0..", "..0..", "....."],
    [".....", ".....", ".000.", "...0.", "....."],
    [".....", "..0..", "..0..", ".00..", "....."],
]
L = [
    [".....", "...0.", ".000.", ".....", "....."],
    [".....", "..0..", "..0..", "..00.", "....."],
    [".....", ".....", ".000.", ".0...", "....."],
    [".....", ".00..", "..0..", "..0..", "....."],
]
T = [
    [".....", "..0..", ".000.", ".....", "....."],
    [".....", "..0..", "..00.", "..0..", "....."],
    [".....", ".....", ".000.", "..0..", "....."],
    [".....", "..0..", ".00..", "..0..", "....."],
]

SHAPES = [("S", S), ("Z", Z), ("I", I), ("O", O), ("J", J), ("L", L), ("T", T)]
SHAPE_ONLY = [shape for _, shape in SHAPES]
SHAPE_KEYS = [key for key, _ in SHAPES]


class Piece:
    def __init__(self, x: int, y: int, shape_index: int):
        self.x = x
        self.y = y
        self.shape_index = shape_index
        self.rotation = 0

    @property
    def shape(self):
        return SHAPE_ONLY[self.shape_index]

    @property
    def color(self):
        return COLORS[SHAPE_KEYS[self.shape_index]]


def convert_shape_format(piece: Piece):
    """현재 회전 상태를 기준으로 블록들의 (x, y) 격자 좌표를 반환합니다."""
    positions = []
    matrix = piece.shape[piece.rotation % len(piece.shape)]
    for i, row in enumerate(matrix):
        for j, ch in enumerate(row):
            if ch == "0":
                # 기존 pygame 버전의 시각 보정(5x5 기준 오프셋)을 그대로 적용
                positions.append((piece.x + j - 2, piece.y + i - 4))
    return positions


def is_valid(piece: Piece, locked: dict):
    """경계/충돌 검사."""
    for x, y in convert_shape_format(piece):
        if x < 0 or x >= GRID_W or y >= GRID_H:
            return False
        if y >= 0 and (x, y) in locked:
            return False
    return True


def spawn_piece():
    # 중앙 근처 스폰
    shape_index = random.randrange(len(SHAPE_ONLY))
    return Piece(GRID_W // 2, 0, shape_index)


def lock_piece(piece: Piece, locked: dict):
    for x, y in convert_shape_format(piece):
        if y >= 0:
            locked[(x, y)] = piece.color


def clear_rows(locked: dict):
    """꽉 찬 줄을 제거하고, 위 블록들을 아래로 내립니다."""
    new_locked = {}
    cleared = 0
    # 아래에서부터 훑으며, 이미 제거된 줄 수(cleared)만큼 아래로 내림
    for y in range(GRID_H - 1, -1, -1):
        full = all((x, y) in locked for x in range(GRID_W))
        if full:
            cleared += 1
            continue
        for x in range(GRID_W):
            if (x, y) in locked:
                new_locked[(x, y + cleared)] = locked[(x, y)]
    return cleared, new_locked


class TetrisApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Python Tetris (tkinter)")
        self.root.resizable(False, False)

        # 점수 UI
        self.score_var = tk.StringVar(value="점수: 0")
        self.high_var = tk.StringVar(value="최고 점수: 0")
        self.title_var = tk.StringVar(value="테트리스")

        header = tk.Frame(self.root)
        header.pack(pady=(PADDING, 8))

        tk.Label(header, textvariable=self.title_var, font=("Arial", 18, "bold")).pack()
        tk.Label(header, textvariable=self.score_var, font=("Arial", 12)).pack()
        tk.Label(header, textvariable=self.high_var, font=("Arial", 12), fg=MUTED).pack()

        body = tk.Frame(self.root)
        body.pack(pady=(0, PADDING))

        # 플레이 캔버스
        self.play_canvas = tk.Canvas(
            body, width=PLAY_W, height=PLAY_H, bg=BG, highlightthickness=0
        )
        self.play_canvas.grid(row=0, column=0, padx=(0, 20))

        # 미리보기 캔버스
        self.preview_canvas = tk.Canvas(
            body, width=PREVIEW_W, height=PREVIEW_H, bg=BG, highlightthickness=0
        )
        self.preview_canvas.grid(row=0, column=1)

        self.font_name = "Arial"

        self.locked = {}
        self.current = spawn_piece()
        self.next_piece = spawn_piece()

        self.score = 0
        self.high_score = 0
        self.game_over = False

        # 낙하 속도 (초당)
        self.fall_interval = 0.5
        self.level_speedup = 0.03

        # 루프 타이밍
        self.last_time = time.perf_counter()
        self.fall_acc = 0.0
        self.after_id = None

        self.root.bind("<Left>", self.on_left)
        self.root.bind("<Right>", self.on_right)
        self.root.bind("<Down>", self.on_down)
        self.root.bind("<Up>", self.on_rotate)
        self.root.bind("<space>", self.on_hard_drop)
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<Return>", self.on_restart_if_over)

        self.draw_static()
        self.loop()
        self.root.mainloop()

    def draw_static(self):
        # 배경 격자선을 한 번만 그림
        self.play_canvas.delete("grid")
        for x in range(GRID_W + 1):
            px = x * CELL
            self.play_canvas.create_line(px, 0, px, PLAY_H, fill=GRID, tags="grid")
        for y in range(GRID_H + 1):
            py = y * CELL
            self.play_canvas.create_line(0, py, PLAY_W, py, fill=GRID, tags="grid")

        self.preview_canvas.delete("all")
        self.preview_canvas.create_text(
            80, 20, text="다음 블록", fill=TEXT, font=(self.font_name, 12, "bold")
        )
        # 미리보기 테두리
        self.preview_canvas.create_rectangle(
            30, 40, 130, 140, outline=BORDER, width=2
        )

    def render(self):
        # 블록만 매 프레임 갱신
        self.play_canvas.delete("block")
        self.play_canvas.delete("overlay")
        self.preview_canvas.delete("next_block")

        # locked 블록
        for (x, y), color in self.locked.items():
            self.draw_block(self.play_canvas, x, y, color)

        # 현재 피스
        if not self.game_over:
            for x, y in convert_shape_format(self.current):
                if y >= 0:
                    self.draw_block(self.play_canvas, x, y, self.current.color)

        # next preview
        # 5x5 매트릭스를 프리뷰 박스에 맞춰서 그리기
        matrix = self.next_piece.shape[0]
        base_x = 30 + 2 * 10  # 대략적인 배치
        base_y = 40 + 2 * 10
        cell = 10
        for i, row in enumerate(matrix):
            for j, ch in enumerate(row):
                if ch == "0":
                    px = base_x + j * cell
                    py = base_y + i * cell
                    self.preview_canvas.create_rectangle(
                        px, py, px + cell, py + cell,
                        fill=self.next_piece.color,
                        outline="",
                        tags="next_block"
                    )

        self.score_var.set(f"점수: {self.score}")
        self.high_var.set(f"최고 점수: {self.high_score}")

        if self.game_over:
            self.play_canvas.create_rectangle(
                0, 0, PLAY_W, PLAY_H, fill="#000000", stipple="gray50", tags="overlay"
            )
            self.play_canvas.create_text(
                PLAY_W // 2,
                PLAY_H // 2 - 20,
                text="게임 오버",
                fill=TEXT,
                font=(self.font_name, 26, "bold"),
                tags="overlay",
            )
            self.play_canvas.create_text(
                PLAY_W // 2,
                PLAY_H // 2 + 10,
                text="Enter: 다시 시작  |  ESC: 종료",
                fill=MUTED,
                font=(self.font_name, 12, "bold"),
                tags="overlay",
            )

    def draw_block(self, canvas: tk.Canvas, x: int, y: int, color: str):
        px1 = x * CELL + 1
        py1 = y * CELL + 1
        px2 = (x + 1) * CELL - 1
        py2 = (y + 1) * CELL - 1
        canvas.create_rectangle(px1, py1, px2, py2, fill=color, outline="", tags="block")

    def try_move(self, dx: int, dy: int):
        """dx, dy 이동. 가능하면 적용하고 True, 아니면 False."""
        test = Piece(self.current.x + dx, self.current.y + dy, self.current.shape_index)
        test.rotation = self.current.rotation
        if is_valid(test, self.locked):
            self.current = test
            return True
        return False

    def try_rotate(self):
        test = Piece(self.current.x, self.current.y, self.current.shape_index)
        test.rotation = (self.current.rotation + 1) % len(self.current.shape)
        if is_valid(test, self.locked):
            self.current = test

    def hard_drop(self):
        moved = False
        while self.try_move(0, 1):
            moved = True
        if moved and not self.game_over:
            # 바닥에 닿았으면 즉시 고정
            self.lock_and_continue()

    def lock_and_continue(self):
        lock_piece(self.current, self.locked)
        cleared, self.locked = clear_rows(self.locked)
        if cleared > 0:
            self.score += cleared * 100
            self.high_score = max(self.high_score, self.score)
            self.fall_interval = max(0.1, self.fall_interval - self.level_speedup * cleared)

        self.current = self.next_piece
        self.next_piece = spawn_piece()

        if not is_valid(self.current, self.locked):
            self.game_over = True

    def loop(self):
        if self.game_over:
            self.render()
            return

        now = time.perf_counter()
        delta = now - self.last_time
        self.last_time = now
        self.fall_acc += delta

        # 누적 시간이 충분하면 한 번 이상 낙하
        while self.fall_acc >= self.fall_interval and not self.game_over:
            self.fall_acc -= self.fall_interval
            if not self.try_move(0, 1):
                self.lock_and_continue()
                break

        self.render()
        self.after_id = self.root.after(16, self.loop)

    def reset(self):
        self.locked = {}
        self.current = spawn_piece()
        self.next_piece = spawn_piece()
        self.score = 0
        self.fall_interval = 0.5
        self.fall_acc = 0.0
        self.last_time = time.perf_counter()
        self.game_over = False
        self.draw_static()

    # 키 처리
    def on_left(self, _=None):
        if not self.game_over:
            self.try_move(-1, 0)

    def on_right(self, _=None):
        if not self.game_over:
            self.try_move(1, 0)

    def on_down(self, _=None):
        if not self.game_over:
            if not self.try_move(0, 1):
                # 내려가다 막히면 즉시 고정
                self.lock_and_continue()

    def on_rotate(self, _=None):
        if not self.game_over:
            self.try_rotate()

    def on_hard_drop(self, _=None):
        if not self.game_over:
            self.hard_drop()

    def on_restart_if_over(self, _=None):
        if self.game_over:
            self.game_over = False
            self.reset()


def main():
    TetrisApp()


if __name__ == "__main__":
    main()

