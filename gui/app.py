"""Chess GUI (pygame): human-vs-agent and agent-vs-agent.
 
Run from the project root:   python -m gui.app      (or: python gui/app.py)
 
  * Menu: Human vs Agent A, Human vs Agent B, Agent A vs Agent B, per-agent search depth
  * Click-click moves with legal-move dots, promotion pop-up, last-move / check highlights
  * Agents think in a background thread so the window never freezes
  * Agent-vs-agent: auto-play with delay, Pause/Resume, Step (SPACE)
  * Game-over banner (checkmate / stalemate / draw and why); ESC returns to the menu
"""
import os
import random
import sys
import threading
from pathlib import Path
 
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
 
import chess
import pygame
 
from agents.beatrice_chess_agent import make_beatrice_agent
from agents.sukanayna_chess_agent import make_defensive_agent

# ------------------------------------------------------------------ config
SQUARE = 70
BOARD_PX = SQUARE * 8
PANEL_W = 260
WIN_W, WIN_H = BOARD_PX + PANEL_W, BOARD_PX
FPS = 30
AGENT_DELAY_MS = 700            # pause between moves in agent-vs-agent mode
MIN_DEPTH, MAX_DEPTH, DEFAULT_DEPTH = 1, 3, 3
MENU_DY = 45                    # shifts the whole menu layout down (top margin)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")     # expects wP.png, bN.png, ...
PIECE_LETTERS = {chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B",
                 chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K"}

# Chess AI farm-sim palette: wheat + grass board, wooden panels, parchment plaques
LIGHT_SQ, DARK_SQ = (240, 222, 170), (132, 170, 92)
LAST_MOVE_RGBA = (255, 214, 90, 150)
SELECT_RGBA = (255, 150, 170, 150)
CHECK_RGBA = (230, 80, 80, 170)
DOT_RGBA = (90, 60, 30, 110)
WOOD_DARK, WOOD, WOOD_LIGHT = (92, 56, 32), (140, 92, 52), (190, 136, 82)
PARCHMENT, INK = (247, 232, 190), (84, 50, 28)
GRASS, GRASS_DARK = (118, 172, 76), (92, 140, 60)
PANEL_BG, MENU_BG = WOOD, GRASS
TEXT, TEXT_DIM = PARCHMENT, (222, 196, 150)
BTN, BTN_HOVER, BTN_ACTIVE, BTN_OFF = (176, 120, 66), (206, 150, 88), (120, 172, 80), (120, 96, 70)
PETALS = [(255, 150, 170), (255, 255, 255), (200, 160, 255), (255, 190, 110)]

# key -> (display name, factory(depth))
AGENTS = {"A": ("Beatrice's Agent", make_beatrice_agent),
          "B": ("Sukanayna's Agent", make_defensive_agent)}


# ----------------------------------------------------------------- helpers
def font(size, bold=False):
    return pygame.font.SysFont("arialroundedmtbold,comicsansms,trebuchetms,verdana,dejavusans", size, bold=bold)


def draw_text(surf, text, fnt, color, pos, center=False, shadow=None):
    img = fnt.render(text, True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    if shadow:                                           # little drop shadow for a chunky look
        surf.blit(fnt.render(text, True, shadow), rect.move(1, 2))
    surf.blit(img, rect)


def draw_wood(surf, rect, base=WOOD, radius=10):
    """Chunky wooden plank: drop shadow, dark border, lighter top edge."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, WOOD_DARK, rect.move(0, 4), border_radius=radius)
    pygame.draw.rect(surf, WOOD_DARK, rect, border_radius=radius)
    pygame.draw.rect(surf, base, rect.inflate(-6, -6), border_radius=max(radius - 2, 0))
    pygame.draw.line(surf, WOOD_LIGHT, (rect.left + 9, rect.top + 4), (rect.right - 9, rect.top + 4), 2)


def draw_flower(surf, x, y, petal, r=5):
    for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r)):
        pygame.draw.circle(surf, petal, (x + dx, y + dy), r - 1)
    pygame.draw.circle(surf, (255, 214, 90), (x, y), r - 2)


def load_images():
    """Load piece images keyed by (piece_type, color); draw letter-discs for any missing image."""
    images, missing = {}, 0
    glyph_font = font(int(SQUARE * 0.5), bold=True)
    for piece_type, letter in PIECE_LETTERS.items():
        for color, prefix in ((chess.WHITE, "w"), (chess.BLACK, "b")):
            path = os.path.join(IMAGE_DIR, f"{prefix}{letter}.png")
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                images[(piece_type, color)] = pygame.transform.smoothscale(img, (SQUARE, SQUARE))
            else:
                missing += 1
                surf = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
                fill, ink = ((255, 244, 220), (200, 100, 120)) if color == chess.WHITE \
                    else ((96, 70, 110), (255, 224, 240))
                pygame.draw.circle(surf, fill, (SQUARE // 2, SQUARE // 2), SQUARE // 2 - 6)
                pygame.draw.circle(surf, ink, (SQUARE // 2, SQUARE // 2), SQUARE // 2 - 6, 2)
                label = glyph_font.render(letter, True, ink)
                surf.blit(label, label.get_rect(center=(SQUARE // 2, SQUARE // 2)))
                images[(piece_type, color)] = surf
    if missing:
        print(f"[gui] {missing} piece images not found in {IMAGE_DIR}; using letter discs.")
    return images


def outcome_text(outcome, name_of):
    """Human-readable game-over message. `name_of(color)` gives the player's name."""
    T = chess.Termination
    if outcome.termination == T.CHECKMATE:
        winner = "White" if outcome.winner == chess.WHITE else "Black"
        return f"Checkmate! {winner} ({name_of(outcome.winner)}) wins"
    return {
        T.STALEMATE: "Stalemate - draw",
        T.INSUFFICIENT_MATERIAL: "Draw - insufficient material",
        T.SEVENTYFIVE_MOVES: "Draw - 75-move rule",
        T.FIFTY_MOVES: "Draw - 50-move rule",
        T.FIVEFOLD_REPETITION: "Draw - fivefold repetition",
        T.THREEFOLD_REPETITION: "Draw - threefold repetition",
    }.get(outcome.termination, "Draw")


class Button:
    """Rectangular button; `label`, `is_active`, `is_enabled` may be callables."""

    def __init__(self, rect, label, callback, is_active=None, is_enabled=None):
        self.rect, self.label, self.callback = pygame.Rect(rect), label, callback
        self.is_active, self.is_enabled = is_active, is_enabled

    def enabled(self):
        return self.is_enabled() if self.is_enabled else True

    def draw(self, surf, fnt, mouse):
        active = self.is_active() if self.is_active else False
        if not self.enabled():
            col = BTN_OFF
        elif active:
            col = BTN_ACTIVE
        elif self.rect.collidepoint(mouse):
            col = BTN_HOVER
        else:
            col = BTN
        draw_wood(surf, self.rect, col, radius=8)
        text = self.label() if callable(self.label) else self.label
        lines = text.split("\n")
        step = fnt.get_linesize()
        top = self.rect.centery - step * (len(lines) - 1) / 2
        for i, line in enumerate(lines):
            draw_text(surf, line, fnt, TEXT if self.enabled() else TEXT_DIM,
                      (self.rect.centerx, top + i * step), center=True, shadow=WOOD_DARK)

    def click(self, pos):
        if self.enabled() and self.rect.collidepoint(pos):
            self.callback()
            return True
        return False


# --------------------------------------------------------------------- app
class App:
    def __init__(self):
        pygame.init()
        info = pygame.display.Info()        # open at normal size; only shrink if the monitor is too small
        fit = max(0.5, min(1.0, info.current_w * 0.9 / WIN_W, info.current_h * 0.85 / WIN_H))
        pygame.display.set_mode((int(WIN_W * fit), int(WIN_H * fit)), pygame.RESIZABLE)
        self.screen = pygame.Surface((WIN_W, WIN_H)).convert()   # fixed-size canvas; present() scales it
        self.fullscreen, self.view_scale, self.view_origin = False, 1.0, (0, 0)
        self.windowed_size = pygame.display.get_surface().get_size()
        pygame.display.set_caption("Chess AI Chess")
        self.clock = pygame.time.Clock()
        self.images = load_images()
        self.shadow = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)      # soft shadow under pieces
        pygame.draw.ellipse(self.shadow, (60, 40, 20, 70),
                            (SQUARE * 0.18, SQUARE * 0.74, SQUARE * 0.64, SQUARE * 0.16))
        self.menu_bg = self._make_menu_bg()
        self.f_title, self.f_mid, self.f_small = font(34, True), font(19), font(15)
        self.depth = {"A": DEFAULT_DEPTH, "B": DEFAULT_DEPTH}
        self.human_white = True
        self.mode = None
        self.swap = False                   # agent-vs-agent: True = Agent B plays White
        self.state = "menu"
        self.running = True
        self.token = 0                      # bumps on every new game so stale agent results are ignored
        self.result = None
        self._build_menu()
        self._build_game_buttons()

    # ----------------------------------------------------------- menu
    def _build_menu(self):
        """Mode buttons in a 2x2 grid, then the depth +/- buttons."""
        bw, bh, gap = 240, 64, 16
        x0, y0 = (WIN_W - (2 * bw + gap)) // 2, 110 + MENU_DY
        col2, row2 = x0 + bw + gap, y0 + bh + gap
        self.menu_buttons = [
            Button((x0, y0, bw, bh), f"Human vs\n{AGENTS['A'][0]}", lambda: self.start_game("A")),
            Button((col2, y0, bw, bh), f"Human vs\n{AGENTS['B'][0]}", lambda: self.start_game("B")),
            Button((x0, row2, bw, bh), "Agent A\nvs Agent B", lambda: self.start_game("AB")),
            Button((col2, row2, bw, bh),
                   lambda: "Human plays:\n" + ("White" if self.human_white else "Black"), self._toggle_color),
        ]
        x = (WIN_W - 360) // 2
        for i, key in enumerate("AB"):
            y = 300 + MENU_DY + i * 60
            self.menu_buttons.append(Button((x + 250, y, 40, 40), "-", lambda k=key: self._bump(k, -1)))
            self.menu_buttons.append(Button((x + 320, y, 40, 40), "+", lambda k=key: self._bump(k, 1)))

    def _toggle_color(self):
        self.human_white = not self.human_white

    def _bump(self, key, delta):
        self.depth[key] = max(MIN_DEPTH, min(MAX_DEPTH, self.depth[key] + delta))

    def _make_menu_bg(self):
        """Sunny hillside: sky gradient, sun, clouds, rolling hills and scattered flowers (drawn once)."""
        bg = pygame.Surface((WIN_W, WIN_H))
        for y in range(WIN_H):
            t = y / WIN_H
            pygame.draw.line(bg, (int(150 + 70 * t), int(205 + 25 * t), int(240 - 20 * t)), (0, y), (WIN_W, y))
        pygame.draw.circle(bg, (255, 236, 130), (WIN_W - 90, 80), 40)
        pygame.draw.circle(bg, (255, 246, 190), (WIN_W - 90, 80), 29)
        for cx, cy in ((110, 150), (440, 60), (650, 190)):
            for dx, r in ((-26, 18), (0, 26), (28, 20)):
                pygame.draw.circle(bg, (255, 255, 255), (cx + dx, cy), r)
        pygame.draw.ellipse(bg, GRASS_DARK, (-200, 360, 760, 420))
        pygame.draw.ellipse(bg, GRASS, (180, 330, 900, 520))
        rnd = random.Random(7)
        for _ in range(55):
            draw_flower(bg, rnd.randint(8, WIN_W - 8), rnd.randint(400, WIN_H - 8), rnd.choice(PETALS))
        return bg

    def draw_menu(self, mouse):
        self.screen.blit(self.menu_bg, (0, 0))
        cx, x = WIN_W // 2, (WIN_W - 360) // 2
        draw_wood(self.screen, (cx - 170, 14 + MENU_DY, 340, 76), radius=12)               # hanging sign
        draw_text(self.screen, "Chess AI Chess", self.f_title, PARCHMENT, (cx, 44 + MENU_DY), center=True, shadow=WOOD_DARK)
        draw_text(self.screen, "Minimax with Alpha-Beta Algorithm", self.f_small, TEXT_DIM, (cx, 75 + MENU_DY), center=True,
                  shadow=WOOD_DARK)
        draw_wood(self.screen, (x - 20, 286 + MENU_DY, 400, 126), PARCHMENT, radius=12)    # depth plaque
        for b in self.menu_buttons:
            b.draw(self.screen, self.f_mid, mouse)
        for i, key in enumerate("AB"):
            y = 300 + MENU_DY + i * 60
            draw_text(self.screen, f"{AGENTS[key][0]}", self.f_small, INK, (x, y + 12))
            draw_text(self.screen, str(self.depth[key]), self.f_mid, INK, (x + 305, y + 20), center=True)
        draw_text(self.screen, "Search depth: higher = smarter but slower", self.f_small, PARCHMENT,
                  (cx, 442 + MENU_DY), center=True, shadow=WOOD_DARK)

    # ----------------------------------------------------------- game setup
    def _build_game_buttons(self):
        """2x2 grid at the bottom of the side panel."""
        x0, bw, gap, bh = BOARD_PX + 16, 110, 12, 40
        row1, row2 = WIN_H - 100, WIN_H - 52
        is_ava = lambda: self.mode == "AB"
        self.game_buttons = [
            Button((x0, row1, bw, bh), lambda: "Resume" if self.paused else "Pause",
                   self._toggle_pause, is_enabled=is_ava),
            Button((x0 + bw + gap, row1, bw, bh), "Step (SPACE)", self._request_step,
                   is_enabled=lambda: is_ava() and self.paused),
            Button((x0, row2, bw, bh), "New game", lambda: self.start_game(self.mode, alternate=True)),
            Button((x0 + bw + gap, row2, bw, bh), "Menu (ESC)", self._to_menu),
        ]

    def start_game(self, mode, alternate=False):
        """Start a game. With alternate=True (the New game button) agent-vs-agent swaps colours."""
        self.swap = (not self.swap) if (alternate and mode == "AB") else False
        self.mode = mode
        self.token += 1
        self.result = None
        self.board = chess.Board()
        self.selected, self.targets, self.last_move, self.promo = None, [], None, None
        self.san, self.outcome = [], None
        self.thinking, self.paused, self.step = False, False, False
        self.last_time = pygame.time.get_ticks()
        if mode == "AB":
            keys = {chess.WHITE: "B", chess.BLACK: "A"} if self.swap else {chess.WHITE: "A", chess.BLACK: "B"}
        else:
            human = chess.WHITE if self.human_white else chess.BLACK
            keys = {human: None, not human: mode}
        self.players, self.names = {}, {}
        for color, key in keys.items():
            if key is None:
                self.players[color], self.names[color] = None, "Human"
            else:
                self.players[color] = AGENTS[key][1](self.depth[key])
                self.names[color] = f"{AGENTS[key][0]} (d{self.depth[key]})"
        self.flipped = mode != "AB" and not self.human_white
        self.state = "game"

    def _to_menu(self):
        self.token += 1
        self.state = "menu"

    def _toggle_pause(self):
        self.paused = not self.paused

    def _request_step(self):
        self.step = True

    # ----------------------------------------------------------- game logic
    def play(self, move):
        self.san.append(self.board.san(move))
        self.board.push(move)
        self.last_move, self.selected, self.targets = move, None, []
        self.last_time = pygame.time.get_ticks()
        self.outcome = self.board.outcome(claim_draw=True)

    def _start_thinking(self):
        self.thinking = True
        token, board, agent = self.token, self.board.copy(), self.players[self.board.turn]

        def work():
            try:
                move = agent.get_move(board)
            except Exception as exc:                      # never let an agent bug kill the GUI
                print("[gui] agent error:", exc)
                move = None
            self.result = (token, move)

        threading.Thread(target=work, daemon=True).start()

    def update_game(self):
        if self.result:
            token, move = self.result
            self.result = None
            if token == self.token and self.thinking:
                self.thinking = False
                if not isinstance(move, chess.Move) or move not in self.board.legal_moves:
                    move = random.choice(list(self.board.legal_moves))    # fallback: illegal / no move
                self.play(move)
        if self.outcome or self.thinking or self.promo:
            return
        if self.players[self.board.turn] is None:
            return                                          # human's turn
        now = pygame.time.get_ticks()
        if self.mode == "AB":
            ready = self.step or (not self.paused and now - self.last_time >= AGENT_DELAY_MS)
        else:
            ready = now - self.last_time >= 250
        if ready:
            self.step = False
            self._start_thinking()

    # ----------------------------------------------------------- input
    def sq_at(self, pos):
        x, y = pos
        if not (0 <= x < BOARD_PX and 0 <= y < BOARD_PX):
            return None
        col, row = x // SQUARE, y // SQUARE
        return chess.square(7 - col if self.flipped else col, row if self.flipped else 7 - row)

    def sq_xy(self, sq):
        f, r = chess.square_file(sq), chess.square_rank(sq)
        return (7 - f if self.flipped else f) * SQUARE, (r if self.flipped else 7 - r) * SQUARE

    def _promo_rects(self):
        x0, y0 = (BOARD_PX - 4 * SQUARE) // 2, (BOARD_PX - SQUARE) // 2
        order = (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
        return [(pt, pygame.Rect(x0 + i * SQUARE, y0, SQUARE, SQUARE)) for i, pt in enumerate(order)]

    def board_click(self, pos):
        if self.outcome or self.thinking or self.players[self.board.turn] is not None:
            return
        if self.promo:                                       # choosing a promotion piece
            for piece_type, rect in self._promo_rects():
                if rect.collidepoint(pos):
                    frm, to = self.promo
                    self.promo = None
                    self.play(chess.Move(frm, to, promotion=piece_type))
                    return
            self.promo = None
            return
        sq = self.sq_at(pos)
        if sq is None:
            return
        if self.selected is not None and sq in self.targets:
            piece = self.board.piece_at(self.selected)
            if piece.piece_type == chess.PAWN and chess.square_rank(sq) in (0, 7):
                self.promo = (self.selected, sq)
            else:
                self.play(chess.Move(self.selected, sq))
            return
        piece = self.board.piece_at(sq)
        if piece and piece.color == self.board.turn:
            self.selected = sq
            self.targets = [m.to_square for m in self.board.legal_moves if m.from_square == sq]
        else:
            self.selected, self.targets = None, []

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == "game":
                    self._to_menu()
                else:
                    self.running = False
            elif event.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif event.key == pygame.K_SPACE and self.state == "game" and self.mode == "AB":
                self.paused = True if not self.paused and not self.step else self.paused
                self.step = True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            buttons = self.menu_buttons if self.state == "menu" else self.game_buttons
            pos = self.to_logical(event.pos)
            if pos is None:                                  # click on the letterbox border
                return
            if any(b.click(pos) for b in buttons):
                return
            if self.state == "game" and pos[0] < BOARD_PX:
                self.board_click(pos)

    # ----------------------------------------------------------- drawing
    def _tint(self, sq, rgba):
        s = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
        s.fill(rgba)
        self.screen.blit(s, self.sq_xy(sq))

    def draw_board(self):
        for sq in chess.SQUARES:
            x, y = self.sq_xy(sq)
            light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 1
            pygame.draw.rect(self.screen, LIGHT_SQ if light else DARK_SQ, (x, y, SQUARE, SQUARE))
        if self.last_move:
            self._tint(self.last_move.from_square, LAST_MOVE_RGBA)
            self._tint(self.last_move.to_square, LAST_MOVE_RGBA)
        if self.board.is_check():
            self._tint(self.board.king(self.board.turn), CHECK_RGBA)
        if self.selected is not None:
            self._tint(self.selected, SELECT_RGBA)
        for sq, piece in self.board.piece_map().items():
            self.screen.blit(self.shadow, self.sq_xy(sq))
            self.screen.blit(self.images[(piece.piece_type, piece.color)], self.sq_xy(sq))
        for sq in self.targets:                              # legal-move dots (ring if capture)
            s = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
            if self.board.piece_at(sq):
                pygame.draw.circle(s, DOT_RGBA, (SQUARE // 2, SQUARE // 2), SQUARE // 2 - 4, 5)
            else:
                pygame.draw.circle(s, DOT_RGBA, (SQUARE // 2, SQUARE // 2), SQUARE // 7)
            self.screen.blit(s, self.sq_xy(sq))
        pygame.draw.rect(self.screen, WOOD_DARK, (0, 0, BOARD_PX, BOARD_PX), 4)    # wooden frame
        if self.promo:
            color = self.board.turn
            pygame.draw.rect(self.screen, PANEL_BG, (*self._promo_rects()[0][1].topleft, 4 * SQUARE, SQUARE),
                             border_radius=6)
            for piece_type, rect in self._promo_rects():
                self.screen.blit(self.images[(piece_type, color)], rect)
        if self.outcome:
            draw_wood(self.screen, (30, BOARD_PX // 2 - 40, BOARD_PX - 60, 80), PARCHMENT, radius=14)
            draw_text(self.screen, outcome_text(self.outcome, lambda c: self.names[c]), self.f_mid, INK,
                      (BOARD_PX // 2, BOARD_PX // 2), center=True)

    def draw_panel(self, mouse):
        pygame.draw.rect(self.screen, WOOD, (BOARD_PX, 0, PANEL_W, WIN_H))
        for y in range(26, WIN_H, 52):                                  # plank seams
            pygame.draw.line(self.screen, WOOD_DARK, (BOARD_PX, y), (WIN_W, y), 1)
        pygame.draw.rect(self.screen, WOOD_DARK, (BOARD_PX, 0, 6, WIN_H))
        px, pw = BOARD_PX + 16, PANEL_W - 28
        if self.outcome:
            status = "Game over"
        elif self.thinking:
            status = "Thinking..."
        elif self.players[self.board.turn] is None:
            status = "Your move!"
        elif self.mode == "AB" and self.paused:
            status = "Paused (SPACE = step)"
        else:
            status = "Waiting..."
        turn = "White" if self.board.turn == chess.WHITE else "Black"
        draw_wood(self.screen, (px, 12, pw, 96), PARCHMENT, radius=10)
        draw_text(self.screen, f"White: {self.names[chess.WHITE]}", self.f_small, INK, (px + 10, 22))
        draw_text(self.screen, f"Black: {self.names[chess.BLACK]}", self.f_small, INK, (px + 10, 46))
        draw_text(self.screen, f"{turn}: {status}", self.f_small, (150, 70, 90), (px + 10, 76))
        draw_flower(self.screen, px + pw - 16, 24, PETALS[0], r=4)
        draw_wood(self.screen, (px, 122, pw, 306), PARCHMENT, radius=10)
        lines = [f"{i // 2 + 1}. {self.san[i]} {self.san[i + 1] if i + 1 < len(self.san) else ''}"
                 for i in range(0, len(self.san), 2)]
        for j, line in enumerate(lines[-13:]):
            draw_text(self.screen, line, self.f_small, INK, (px + 12, 134 + j * 22))
        for b in self.game_buttons:
            b.draw(self.screen, self.f_small, mouse)

    # ----------------------------------------------------------- window scaling
    def present(self):
        """Scale the fixed-size canvas to the window (aspect ratio kept, letterboxed) and show it."""
        win = pygame.display.get_surface()
        ww, wh = win.get_size()
        self.view_scale = min(ww / WIN_W, wh / WIN_H)
        size = (max(1, int(WIN_W * self.view_scale)), max(1, int(WIN_H * self.view_scale)))
        self.view_origin = ((ww - size[0]) // 2, (wh - size[1]) // 2)
        win.fill(WOOD_DARK)
        frame = self.screen if size == (WIN_W, WIN_H) else pygame.transform.smoothscale(self.screen, size)
        win.blit(frame, self.view_origin)
        pygame.display.flip()

    def to_logical(self, pos):
        """Window pixel -> canvas coordinate, or None if the point is outside the scaled canvas."""
        x = (pos[0] - self.view_origin[0]) / self.view_scale
        y = (pos[1] - self.view_origin[1]) / self.view_scale
        return (int(x), int(y)) if 0 <= x < WIN_W and 0 <= y < WIN_H else None

    def toggle_fullscreen(self):
        """F11: switch between fullscreen and the resizable window."""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.windowed_size = pygame.display.get_surface().get_size()
            pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    # ----------------------------------------------------------- main loop
    def run(self):
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            mouse = self.to_logical(pygame.mouse.get_pos()) or (-1, -1)
            if self.state == "menu":
                self.draw_menu(mouse)
            else:
                self.update_game()
                self.draw_board()
                self.draw_panel(mouse)
            self.present()
            self.clock.tick(FPS)
        pygame.quit()


def main():
    App().run()


if __name__ == "__main__":
    main()
