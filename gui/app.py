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
    """Beatrice's Agent: your agent."""
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


def main():
    """Main function to run the chess GUI."""
    clock = pygame.time.Clock()
    global running
    running = True
    draw_board()
    while running:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.quit()

if __name__ == "__main__":
    main()