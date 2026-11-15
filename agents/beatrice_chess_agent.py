import chess

from agents import base_agent
from engine import openings

PIECE_VALUES = {chess.PAWN: 10, chess.KNIGHT: 32, chess.BISHOP: 33,
                chess.ROOK: 50, chess.QUEEN: 90}
BISHOP_PAIR_BONUS = 3
NON_PAWN_BOARD_VALUE = 2*(2*PIECE_VALUES[chess.KNIGHT] + 2*PIECE_VALUES[chess.BISHOP] + 2*PIECE_VALUES[chess.ROOK] + PIECE_VALUES[chess.QUEEN])
TRADE_FACTOR = 0.25
MY_THREAT_VALUE = 0.03
OPPONENT_COUNTER_VALUE = 0.01
KING_ZONE = 0.5
CHECK_VALUE = 2.5
PAWN_ADVANCEMENT_VALUE = 0.4


def material_strategy(board, color):
    """Material strategy: sum up the material value of all pieces on the board."""
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
    """Aggressive strategy: prioritize threats and attacks on opponent's pieces."""
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
    return int(lead_score)


def make_agent(depth = 3):
    return base_agent.ChessAgent("Beatrice's Agent", depth, evaluate_board)

