"""Chess GUI (pygame): human-vs-agent and agent-vs-agent.

Run from the project root:   python -m gui.app      (or: python gui/app.py)

Features
  * Start menu: Human vs Agent A, Human vs Agent B, Agent A vs Agent B
  * Click-click move input with legal-move dots, promotion pop-up, last-move highlight
  * Agents think in a background thread so the window never freezes
  * Agent-vs-agent: auto-play with a delay, Pause/Resume, Step (SPACE)
  * Game-over banner: checkmate / stalemate / draw (and why)
  * Bonus: per-agent search depth selector in the menu
"""
import os
import random
import sys
import threading
import time
from pathlib import Path

# Make `engine`, `agents` importable when run as a script from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chess
import pygame

from agents.base_agent import ChessAgent
from agents.beatrice_chess_agent import make_beatrice_agent

# ------------------------------------------------------------------ config
SQUARE = 70
BOARD_PX = SQUARE * 8
PANEL_W = 260
WIN_W, WIN_H = BOARD_PX + PANEL_W, BOARD_PX
FPS = 30
AGENT_DELAY_MS = 700            # pause between moves in agent-vs-agent mode
MIN_DEPTH, MAX_DEPTH, DEFAULT_DEPTH = 1, 5, 3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")     # expects wP.png, bN.png, ...
PIECE_LETTERS = {chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B",
                 chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K"}

LIGHT_SQ, DARK_SQ = (240, 217, 181), (181, 136, 99)
LAST_MOVE_RGBA = (246, 246, 105, 140)
SELECT_RGBA = (80, 200, 120, 150)
CHECK_RGBA = (230, 60, 60, 170)
PANEL_BG, MENU_BG = (38, 36, 33), (30, 30, 34)
TEXT, TEXT_DIM = (235, 235, 235), (160, 160, 165)
BTN, BTN_HOVER, BTN_ACTIVE, BTN_OFF = (72, 70, 66), (100, 98, 92), (70, 140, 90), (52, 51, 49)


# ------------------------------------------------------------------ agents
def _placeholder_eval(board):
    """Material-only evaluation, used until Agent B exists."""
    values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
              chess.ROOK: 500, chess.QUEEN: 900}
    return sum(v * (len(board.pieces(p, chess.WHITE)) - len(board.pieces(p, chess.BLACK)))
               for p, v in values.items())


def make_agent_a(depth):
    """Beatrice'sAgent: your agent."""
    return make_beatrice_agent(depth)


def make_agent_b(depth):
    """Agent B: TODO - replace with your partner's agent, e.g.
         from agents.partner_agent import make_partner_agent
         return make_partner_agent(depth)
    Until then a plain material-only agent stands in."""
    return ChessAgent("Agent B (placeholder)", depth, _placeholder_eval)


AGENTS = {"A": ("Beatrice's Agent", make_agent_a), "B": ("Agent B", make_agent_b)}


# ----------------------------------------------------------------- helpers
def font(size, bold=False):
    return pygame.font.SysFont("segoeui,arial,helvetica,dejavusans", size, bold=bold)


def draw_text(surf, text, fnt, color, pos, center=False):
    img = fnt.render(text, True, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(img, rect)


def load_images():
    """Load piece images keyed by (piece_type, color); fall back to drawn
    letter-discs for any image that is missing so the GUI always runs."""
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
                fill, ink = ((250, 250, 250), (30, 30, 30)) if color == chess.WHITE \
                    else ((40, 40, 40), (240, 240, 240))
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
        pygame.draw.rect(surf, col, self.rect, border_radius=8)
        text = self.label() if callable(self.label) else self.label
        color = TEXT if self.enabled() else TEXT_DIM
        draw_text(surf, text, fnt, color, self.rect.center, center=True)

    def click(self, pos):
        if self.enabled() and self.rect.collidepoint(pos):
            self.callback()
            return True
        return False


# --------------------------------------------------------------------- app
class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Chess AI")
        self.images = load_images()
        self.f_title, self.f_big = font(34, True), font(20, True)
        self.f_mid, self.f_small = font(17), font(14)
        self.running = True
        self.state = "menu"                 # "menu" or "game"
        self.depths = {"A": DEFAULT_DEPTH, "B": DEFAULT_DEPTH}
        self.human_white = True
        self.session = 0                    # bumps on every new game (ignores stale threads)
        self.hl = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
        self._reset_game_state()
        self._build_menu()
        self._build_game_buttons()

    # ------------------------------------------------------------ menu
    def _build_menu(self):
        cx = WIN_W // 2
        b = []
        modes = (("ha", f"Human vs {AGENTS['A'][0]} (Agent A)"),
                 ("hb", f"Human vs {AGENTS['B'][0]} (Agent B)"),
                 ("ab", "Agent A vs Agent B"))
        for i, (mode, label) in enumerate(modes):
            b.append(Button((cx - 190, 130 + i * 68, 380, 54), label,
                            lambda m=mode: self.start_game(m)))
        # depth selectors (bonus)
        for i, key in enumerate(("A", "B")):
            y = 360 + i * 46
            b.append(Button((cx + 20, y, 36, 36), "-", lambda k=key: self._change_depth(k, -1)))
            b.append(Button((cx + 108, y, 36, 36), "+", lambda k=key: self._change_depth(k, +1)))
        # colour choice for human modes
        b.append(Button((cx - 20, 462, 90, 36), "White", lambda: self._set_color(True),
                        is_active=lambda: self.human_white))
        b.append(Button((cx + 80, 462, 90, 36), "Black", lambda: self._set_color(False),
                        is_active=lambda: not self.human_white))
        self.menu_buttons = b

    def _change_depth(self, key, delta):
        self.depths[key] = max(MIN_DEPTH, min(MAX_DEPTH, self.depths[key] + delta))

    def _set_color(self, white):
        self.human_white = white

    def draw_menu(self):
        self.screen.fill(MENU_BG)
        cx = WIN_W // 2
        draw_text(self.screen, "Chess AI", self.f_title, TEXT, (cx, 70), center=True)
        draw_text(self.screen, "Minimax + Alpha-Beta agents", self.f_mid, TEXT_DIM, (cx, 104), center=True)
        mouse = pygame.mouse.get_pos()
        for btn in self.menu_buttons:
            btn.draw(self.screen, self.f_mid, mouse)
        draw_text(self.screen, "Search depth (higher = stronger, slower)", self.f_small,
                  TEXT_DIM, (cx, 342), center=True)
        for i, key in enumerate(("A", "B")):
            y = 360 + i * 46
            draw_text(self.screen, f"{AGENTS[key][0]}:", self.f_mid, TEXT, (cx - 190, y + 8))
            draw_text(self.screen, str(self.depths[key]), self.f_big, TEXT, (cx + 82, y + 18), center=True)
        draw_text(self.screen, "You play as:", self.f_mid, TEXT, (cx - 190, 470))

    # ------------------------------------------------------- game setup
    def _reset_game_state(self):
        self.board = chess.Board()
        self.mode = None
        self.agents = {chess.WHITE: None, chess.BLACK: None}   # None = human
        self.flip = False
        self.selected, self.targets = None, set()
        self.promo = None                    # (from_sq, to_sq) awaiting piece choice
        self.last_move = None
        self.san_log, self.last_info = [], ""
        self.outcome = None
        self.thinking, self.result = False, None
        self.paused, self.step_requested = False, False
        self.last_move_tick = 0

    def start_game(self, mode):
        self.session += 1
        self._reset_game_state()
        self.mode = mode
        a = AGENTS["A"][1](self.depths["A"])
        b = AGENTS["B"][1](self.depths["B"])
        if mode == "ab":
            self.agents = {chess.WHITE: a, chess.BLACK: b}
        else:
            human = chess.WHITE if self.human_white else chess.BLACK
            self.agents = {human: None, (not human): (a if mode == "ha" else b)}
            self.flip = not self.human_white
        self.last_move_tick = pygame.time.get_ticks()
        self.state = "game"

    def restart(self):
        self.start_game(self.mode)

    def to_menu(self):
        self.session += 1                    # abandon any running search
        self.state = "menu"
        self.thinking, self.result = False, None

    def _build_game_buttons(self):
        x0, w = BOARD_PX + 16, (PANEL_W - 44) // 2
        x1 = x0 + w + 12
        self.game_buttons = [
            Button((x0, 446, w, 38), lambda: "Resume" if self.paused else "Pause",
                   self.toggle_pause, is_enabled=lambda: self.mode == "ab" and not self.outcome),
            Button((x1, 446, w, 38), "Step (Space)", self.step,
                   is_enabled=lambda: self.mode == "ab" and not self.outcome),
            Button((x0, 496, w, 38), "New game", self.restart),
            Button((x1, 496, w, 38), "Menu", self.to_menu),
        ]

    def toggle_pause(self):
        if self.mode == "ab":
            self.paused = not self.paused

    def step(self):
        """Agent-vs-agent: pause auto-play and play exactly one move."""
        if self.mode == "ab" and not self.outcome and not self.thinking:
            self.paused, self.step_requested = True, True

    # ------------------------------------------------------ coordinates
    def sq_xy(self, sq):
        f, r = chess.square_file(sq), chess.square_rank(sq)
        return ((7 - f) * SQUARE, r * SQUARE) if self.flip else (f * SQUARE, (7 - r) * SQUARE)

    def xy_sq(self, pos):
        col, row = pos[0] // SQUARE, pos[1] // SQUARE
        if not (0 <= col < 8 and 0 <= row < 8):
            return None
        return chess.square(7 - col, row) if self.flip else chess.square(col, 7 - row)

    # -------------------------------------------------------- game logic
    def player_name(self, color):
        agent = self.agents[color]
        return "You" if agent is None else agent.name

    def refresh_outcome(self):
        self.outcome = self.board.outcome(claim_draw=True)

    def push_move(self, move, info=None):
        self.san_log.append(self.board.san(move))      # SAN must be computed BEFORE the push
        self.board.push(move)
        self.last_move = move
        self.last_move_tick = pygame.time.get_ticks()
        self.selected, self.targets, self.promo = None, set(), None
        if info:
            self.last_info = info
        self.refresh_outcome()

    def human_to_move(self):
        return (self.state == "game" and not self.outcome and not self.thinking
                and self.agents[self.board.turn] is None)

    def click_board(self, pos):
        if not self.human_to_move():
            return
        if self.promo:                                   # promotion pop-up is open
            for piece_type, rect in self.promo_rects():
                if rect.collidepoint(pos):
                    frm, to = self.promo
                    move = chess.Move(frm, to, promotion=piece_type)
                    if move in self.board.legal_moves:
                        self.push_move(move)
                    return
            self.promo = None                            # clicked elsewhere: cancel
            return
        sq = self.xy_sq(pos)
        if sq is None:
            return
        if self.selected is not None and sq in self.targets:
            self._try_move(self.selected, sq)
            return
        piece = self.board.piece_at(sq)
        if piece and piece.color == self.board.turn:     # (re)select own piece
            self.selected = sq
            self.targets = {m.to_square for m in self.board.legal_moves if m.from_square == sq}
        else:
            self.selected, self.targets = None, set()

    def _try_move(self, frm, to):
        piece = self.board.piece_at(frm)
        if piece.piece_type == chess.PAWN and chess.square_rank(to) in (0, 7):
            self.promo = (frm, to)                       # ask which piece
            return
        move = chess.Move(frm, to)
        if move in self.board.legal_moves:               # legality check
            self.push_move(move)
        else:
            self.selected, self.targets = None, set()

    def promo_rects(self):
        """[(piece_type, rect)] for the four promotion choices, centred on the board."""
        order = (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
        x0 = (BOARD_PX - SQUARE * 4) // 2
        y0 = (BOARD_PX - SQUARE) // 2
        return [(pt, pygame.Rect(x0 + i * SQUARE, y0, SQUARE, SQUARE)) for i, pt in enumerate(order)]

    # ----------------------------------------------------- agent turns
    def update(self):
        if self.state != "game" or self.outcome:
            return
        agent = self.agents[self.board.turn]
        if agent is None:
            return
        if self.thinking:
            if self.result is not None and self.result[0] == self.session:
                _, move, secs, from_book, name = self.result
                self.result, self.thinking = None, False
                san = self.board.san(move)
                tag = "book" if from_book else f"{secs:.1f}s"
                self.push_move(move, f"{name}: {san} ({tag})")
            return
        if self.mode == "ab":
            if self.paused:
                if not self.step_requested:
                    return
            elif pygame.time.get_ticks() - self.last_move_tick < AGENT_DELAY_MS:
                return
        self._start_thinking(agent)

    def _start_thinking(self, agent):
        self.thinking, self.step_requested, self.result = True, False, None
        board_copy, sid = self.board.copy(), self.session

        def work():
            t0 = time.time()
            try:
                move = agent.get_move(board_copy)
            except Exception as exc:                     # never leave the GUI stuck
                print(f"[gui] {agent.name} raised {exc!r}; playing a random legal move")
                move = None
            if move is None or move not in board_copy.legal_moves:
                move = random.choice(list(board_copy.legal_moves))
            if sid == self.session:
                self.result = (sid, move, time.time() - t0,
                               getattr(agent, "last_move_from_book", False), agent.name)

        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------- drawing
    def _tint(self, sq, rgba):
        self.hl.fill(rgba)
        self.screen.blit(self.hl, self.sq_xy(sq))

    def draw_board(self):
        for sq in chess.SQUARES:
            light = (chess.square_file(sq) + chess.square_rank(sq)) % 2 == 1
            pygame.draw.rect(self.screen, LIGHT_SQ if light else DARK_SQ,
                             (*self.sq_xy(sq), SQUARE, SQUARE))
        if self.last_move:
            self._tint(self.last_move.from_square, LAST_MOVE_RGBA)
            self._tint(self.last_move.to_square, LAST_MOVE_RGBA)
        if self.board.is_check():
            self._tint(self.board.king(self.board.turn), CHECK_RGBA)
        if self.selected is not None:
            self._tint(self.selected, SELECT_RGBA)
        for sq, piece in self.board.piece_map().items():
            self.screen.blit(self.images[(piece.piece_type, piece.color)], self.sq_xy(sq))
        for sq in self.targets:                          # legal-move markers
            x, y = self.sq_xy(sq)
            centre = (x + SQUARE // 2, y + SQUARE // 2)
            if self.board.piece_at(sq) or sq == self.board.ep_square:
                pygame.draw.circle(self.screen, (60, 60, 60), centre, SQUARE // 2 - 3, 4)
            else:
                pygame.draw.circle(self.screen, (60, 60, 60), centre, 9)
        # coordinates
        for i in range(8):
            f = 7 - i if self.flip else i
            r_bottom = 7 if self.flip else 0
            on_light = (f + r_bottom) % 2 == 1
            draw_text(self.screen, chess.FILE_NAMES[f], self.f_small,
                      DARK_SQ if on_light else LIGHT_SQ, (i * SQUARE + SQUARE - 12, BOARD_PX - 18))
            rank = i if self.flip else 7 - i
            on_light = (0 + rank) % 2 == 1
            draw_text(self.screen, str(rank + 1), self.f_small,
                      DARK_SQ if on_light else LIGHT_SQ, (4, i * SQUARE + 3))
        if self.promo:
            self._draw_promo()
        if self.outcome:
            self._draw_banner()

    def _draw_promo(self):
        shade = pygame.Surface((BOARD_PX, BOARD_PX), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 120))
        self.screen.blit(shade, (0, 0))
        rects = self.promo_rects()
        box = rects[0][1].unionall([r for _, r in rects]).inflate(24, 44)
        pygame.draw.rect(self.screen, (60, 58, 54), box, border_radius=10)
        draw_text(self.screen, "Promote to:", self.f_small, TEXT, (box.centerx, box.top + 12), center=True)
        for pt, rect in rects:
            pygame.draw.rect(self.screen, (200, 190, 170), rect.inflate(-6, -6), border_radius=6)
            self.screen.blit(self.images[(pt, self.board.turn)], rect)

    def _draw_banner(self):
        band = pygame.Surface((BOARD_PX, 120), pygame.SRCALPHA)
        band.fill((0, 0, 0, 190))
        self.screen.blit(band, (0, BOARD_PX // 2 - 60))
        draw_text(self.screen, outcome_text(self.outcome, self.player_name), self.f_big,
                  (255, 255, 255), (BOARD_PX // 2, BOARD_PX // 2 - 12), center=True)
        draw_text(self.screen, "R: new game     Esc: menu", self.f_small, TEXT_DIM,
                  (BOARD_PX // 2, BOARD_PX // 2 + 28), center=True)

    def draw_panel(self):
        pygame.draw.rect(self.screen, PANEL_BG, (BOARD_PX, 0, PANEL_W, WIN_H))
        x = BOARD_PX + 16
        draw_text(self.screen, "Chess AI", self.f_big, TEXT, (x, 12))
        for i, color in enumerate((chess.WHITE, chess.BLACK)):
            label = f"{'White' if color else 'Black'}: {self.player_name(color)}"
            draw_text(self.screen, label[:30], self.f_mid, TEXT_DIM, (x, 46 + i * 22))
        # status
        turn_name = self.player_name(self.board.turn)
        if self.outcome:
            status = outcome_text(self.outcome, self.player_name)
        elif self.thinking:
            status = f"{turn_name} is thinking" + "." * (1 + (pygame.time.get_ticks() // 400) % 3)
        elif self.agents[self.board.turn] is None:
            status = f"Your move ({'White' if self.board.turn else 'Black'})"
        else:
            status = f"{'White' if self.board.turn else 'Black'} to move" + (" (paused)" if self.paused else "")
        draw_text(self.screen, status[:34], self.f_mid, TEXT, (x, 104))
        draw_text(self.screen, self.last_info[:36], self.f_small, TEXT_DIM, (x, 128))
        # move list (last 10 full moves)
        draw_text(self.screen, "Moves", self.f_small, TEXT_DIM, (x, 160))
        rows = []
        for i in range(0, len(self.san_log), 2):
            black = self.san_log[i + 1] if i + 1 < len(self.san_log) else ""
            rows.append(f"{i // 2 + 1:>2}. {self.san_log[i]:<8} {black}")
        for j, row in enumerate(rows[-10:]):
            draw_text(self.screen, row, self.f_small, TEXT, (x, 182 + j * 22))
        mouse = pygame.mouse.get_pos()
        for btn in self.game_buttons:
            btn.draw(self.screen, self.f_small, mouse)

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        else:
            self.draw_board()
            self.draw_panel()

    # ----------------------------------------------------------- events
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN:
            if self.state == "game":
                if e.key == pygame.K_ESCAPE:
                    self.to_menu()
                elif e.key == pygame.K_r:
                    self.restart()
                elif e.key == pygame.K_SPACE:
                    self.step()
                elif e.key == pygame.K_p:
                    self.toggle_pause()
            elif e.key == pygame.K_ESCAPE:
                self.running = False
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.state == "menu":
                for btn in self.menu_buttons:
                    if btn.click(e.pos):
                        break
            else:
                for btn in self.game_buttons:
                    if btn.click(e.pos):
                        return
                if e.pos[0] < BOARD_PX:
                    self.click_board(e.pos)

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            for e in pygame.event.get():
                self.handle_event(e)
            self.update()
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)
        pygame.quit()


def main():
    App().run()


if __name__ == "__main__":
    main()