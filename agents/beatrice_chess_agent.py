"""
This agent is built on an aggressive strategy, prioritizing threats and attacks on the opponent's pieces. 
It evaluates the state of the board, making moves that maximize the potential for attacks and counter play.
"""
import chess
import random

from agents import base_agent
from engine import engine

PIECE_VALUES = {chess.PAWN: 10, chess.KNIGHT: 32, chess.BISHOP: 33,
                chess.ROOK: 50, chess.QUEEN: 90} # a dictionary of piece values for evaluation purposes
BISHOP_PAIR_BONUS = 3 # bonus for having both bishops on the board
NON_PAWN_BOARD_VALUE = 6400 # non-pawn material on the board at the start (both sides)
TRADE_FACTOR = 0.25 # weight on the value of trades, relative to the material lead
MY_THREAT_VALUE = 0.3 # bonus for our own threats
OPPONENT_COUNTER_VALUE = 0.1 # penalty for the opponent's counter-threats
KING_ZONE = 0.5  # bonus for attacking the opponent's king
CHECK_VALUE = 2.5 # bonus for putting the opponent in check
PAWN_ADVANCEMENT_VALUE = 0.4 # bonus for advancing pawns on the board

""".................... STRATEGY FUNCTIONS ...................."""

def material_strategy(board, color):
    """Sums up the material value of all pieces on the board."""
    material_score = 0
    non_pawn_board_value = 0
    for piece_type, value in PIECE_VALUES.items():
        material_score += value * (len(board.pieces(piece_type, color)))
        if piece_type != chess.PAWN:
            non_pawn_board_value += value * (len(board.pieces(piece_type, color)))
    # Bishop pair bonus
    if len(board.pieces(chess.BISHOP, color)) >= 2:
        material_score += BISHOP_PAIR_BONUS
    return material_score, non_pawn_board_value

def aggressive_strategy(board, color):
    """Prioritizes threats and attacks on opponent's pieces."""
    enemy = not color
    aggression_level = MY_THREAT_VALUE if board.turn == color else OPPONENT_COUNTER_VALUE
    aggression_score = 0

    for piece_type, value in PIECE_VALUES.items():
        if piece_type == chess.PAWN:
            continue
        for square in board.pieces(piece_type, enemy):
            attackers = board.attackers(color, square)
            if not attackers:
                continue
            if not board.is_attacked_by(enemy, square):
                aggression_score += aggression_level * value 
            else:
                smallest_attacker_value = min(PIECE_VALUES.get(board.piece_type_at(attacker),1000) for attacker in attackers)
                if smallest_attacker_value < value:
                    aggression_score += aggression_level * (value - smallest_attacker_value)

    zone = chess.SquareSet(chess.BB_KING_ATTACKS[board.king(enemy)])
    aggression_score += KING_ZONE * sum(len(board.attackers(color, square)) for square in zone)

    for square in board.pieces(chess.PAWN, color):
        rank = chess.square_rank(square)
        if color == chess.WHITE:
            advancement = rank
        else:
            advancement = 7 - rank
        
        if advancement > 2:
            aggression_score += PAWN_ADVANCEMENT_VALUE * (advancement-2)**2

    return aggression_score


def evaluate_board(board):
    """Evaluates the board state and returns a score from the perspective of white."""
    white_material_score, white_non_pawn_value = material_strategy(board, chess.WHITE)
    black_material_score, black_non_pawn_value = material_strategy(board, chess.BLACK)
    lead = white_material_score - black_material_score
    lead_score = lead+(lead*TRADE_FACTOR*(1-(white_non_pawn_value+black_non_pawn_value)/NON_PAWN_BOARD_VALUE))

    lead_score += aggressive_strategy(board, chess.WHITE) - aggressive_strategy(board, chess.BLACK)
    if board.is_check():
        if board.turn == chess.WHITE:
            lead_score -= CHECK_VALUE
        else:
            lead_score += CHECK_VALUE
    return round(lead_score, 1)


def convert_to_legal_moves(sans):
    """Convert a opening string into chess.Move objects."""
    board = chess.Board()
    moves = []
    for san in sans:
        move = board.parse_san(san)
        moves.append(move)
        board.push(move)
    return moves

OPENING_LINES = {name: convert_to_legal_moves(sans) for name, sans in engine.OPENINGS.items()}

class BeatriceChessAgent(base_agent.ChessAgent):
    """Uses an opening book, then search with move ordering."""
    def __init__(self, name, depth, evaluate_board):
        super().__init__(name, depth, evaluate_board)
        self.opening_name = None
        self.opening_line = None            # the selected opening, as a list of moves
        self.last_move_from_book = False

    def book_move(self, board):
        """Next move of the selected opening, or None if the opening is over."""
        if board.root().fen() != chess.STARTING_FEN:
            return None                     # the book only applies to normal games
        history = board.move_stack
        ply = len(history)

        if ply <= 1:                        # a new game has started: forget the old opening
            self.opening_name, self.opening_line = None, None

        line = self.opening_line
        if line is not None:
            n = min(ply, len(line))
            if history[:n] == line[:n]:     # the game is still following our opening
                return line[ply] if ply < len(line) else None   # None = opening complete
        # No opening selected yet, or the opponent left it: pick one that fits the game so far
        candidates = [name for name, l in OPENING_LINES.items()
                      if len(l) > ply and l[:ply] == history]
        if not candidates:
            self.opening_name, self.opening_line = None, None
            return None
        self.opening_name = random.choice(candidates)
        self.opening_line = OPENING_LINES[self.opening_name]
        return self.opening_line[ply]

    def get_move(self, board):
        """Return the next move to play, or None if the game is over."""
        if board.is_game_over():
            return None
        move = self.book_move(board)
        self.last_move_from_book = move is not None
        if move is not None and move in board.legal_moves:
            return move
        self.last_move_from_book = False
        return engine.get_best_move(board.copy(), self.depth, self.evaluate_board)


def make_agent(depth = 3):
    return base_agent.ChessAgent("Beatrice's Agent", depth, evaluate_board)

def make_beatrice_agent(depth = 3):
    """Uses an opening book, then search with move ordering."""
    return BeatriceChessAgent("Beatrice's Agent", depth, evaluate_board)
