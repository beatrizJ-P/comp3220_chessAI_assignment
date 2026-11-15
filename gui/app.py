import io
import os
import chess
import chess.svg
import pygame

SQUARE = 50
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

Piece_symbols = {
    chess.PAWN: 'P',
    chess.KNIGHT: 'N',
    chess.BISHOP: 'B',
    chess.ROOK: 'R',
    chess.QUEEN: 'Q',
    chess.KING: 'K'
}

board = chess.Board()

pygame.init()
screen = pygame.display.set_mode((400, 400))
pygame.display.set_caption("Chess")


def load_images():
    """Load and scale all 12 piece images once, keyed by (piece_type, color)."""
    images = {}
    for piece_type, symbol in Piece_symbols.items():
        for color, letter in ((chess.WHITE, 'w'), (chess.BLACK, 'b')):
            path = os.path.join(BASE_DIR, "images", f"{letter}{symbol}.png")
            image = pygame.image.load(path).convert_alpha()
            images[(piece_type, color)] = pygame.transform.smoothscale(image, (SQUARE, SQUARE))
    return images


IMAGES = load_images()


def draw_board():
    svg = chess.svg.board(board, size=400, coordinates=False)
    background = pygame.image.load(io.BytesIO(svg.encode()), "board.svg")
    screen.blit(background, (0, 0))

    for square, piece in board.piece_map().items():
        x = chess.square_file(square) * SQUARE
        y = (7 - chess.square_rank(square)) * SQUARE
        screen.blit(IMAGES[(piece.piece_type, piece.color)], (x, y))

    pygame.display.flip()


running = True
draw_board()
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

pygame.quit()