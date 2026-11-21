#This agent is built on a defense strategy, prioritizing piece protection and counter attacks.
#This agent evaluates the state of the board, making moves that minimise risk and maximise the potential for counter play. 

import os
import sys
import chess
from agents.beatrice_chess_agent import evaluate_board
from engine import openings, search

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import base_agent

MIN_DEPTH, MAX_DEPTH, DEFAULT_DEPTH = 1, 3, 3

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

LOSS_AVERSION = 1.15            # weight on our own material (opponent's counts 1.0)
LEAD_THRESHOLD = 200            # "ahead" = at least two pawns up
START_NON_PAWN = 6400           # non-pawn material on the board at the start (both sides)
# Scale of the whole piece-square score. Tested against this agent without PSTs (10 games,
# depth 2, moves graded by Stockfish): 7-3, blunders 27 vs 36, opening accuracy 51 vs 66 cp lost/move.

PST_WEIGHT = 1.0

#----------------------------------------------------------------------------------------------- Piece-square tables

#Defensive piece-square tables: a bonus/penalty for each piece on each square, in centipawns.
#Written from White's point of view as the board looks to White (first row = rank 8, last row = rank 1).
#Black uses the same tables mirrored, so the evaluation stays colour-symmetric.
#Unlike the aggressive agent's tables (which reward advancing), these reward a solid, compact setup:
#shelter pawns stay home, pieces guard their own half, and the queen stays back.

PAWN_TABLE = [
     0,   0,   0,   0,   0,   0,   0,   0,
    50,  50,  50,  50,  50,  50,  50,  50,    # only really near promotion
    15,  15,  20,  25,  25,  20,  15,  15,
     5,   5,  10,  20,  20,  10,   5,   5,
     0,   0,  10,  20,  20,   5, -10, -15,    # flank pawn pushes (g4/h4) loosen the king
     5,   5,   5,  10,  10,   0, -10, -10,
     5,   5,   5, -15, -15,  15,  20,  20,    # shelter pawns f2/g2/h2 stay home
     0,   0,   0,   0,   0,   0,   0,   0,
]
KNIGHT_TABLE = [
   -50, -40, -30, -30, -30, -30, -40, -50,
   -40, -20,   0,   0,   0,   0, -20, -40,    # deep raids are risky
   -30,   0,  10,  10,  10,  10,   0, -30,
   -30,   5,  15,  20,  20,  15,   5, -30,
   -30,   0,  15,  20,  20,  15,   0, -30,
   -30,   5,  15,  15,  15,  15,   5, -30,    # c3/f3: guarding the centre from home
   -40, -20,   0,   5,   5,   0, -20, -40,
   -50, -40, -30, -30, -30, -30, -40, -50,    # rim and corners are poor
]
BISHOP_TABLE = [
   -20, -10, -10, -10, -10, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,  10,  10,   5,   0, -10,
   -10,   5,   5,  10,  10,   5,   5, -10,
   -10,   0,  10,  10,  10,  10,   0, -10,
   -10,  10,  10,  10,  10,  10,  10, -10,
   -10,  15,   5,  10,  10,   5,  15, -10,    # fianchetto (b2/g2) and e2/d2 cover the king
   -20, -10, -10, -10, -10, -10, -10, -20,
]
ROOK_TABLE = [
     0,   0,   0,   0,   0,   0,   0,   0,
     5,  10,  10,  10,  10,  10,  10,   5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     0,   5,   5,   5,   5,   5,   5,   0,    # 2nd rank: defending its own pawns
     0,   0,   5,  10,  10,   5,   0,   0,    # d1/e1 after castling
]
QUEEN_TABLE = [
   -30, -20, -20, -15, -15, -20, -20, -30,    # deep in enemy territory = easy target
   -20, -10, -10, -10, -10, -10, -10, -20,
   -10,  -5,   0,   0,   0,   0,  -5, -10,
    -5,   0,   5,   5,   5,   5,   0,  -5,
    -5,   0,   5,   5,   5,   5,   0,  -5,
   -10,   5,   5,   5,   5,   5,   5, -10,
   -10,   0,   5,  10,  10,   5,   0, -10,    # d2/e2: centralised but safe
   -20, -10,  -5,   0,   0,  -5, -10, -20,
]
KING_MIDDLEGAME_TABLE = [
   -60, -60, -60, -70, -70, -60, -60, -60,
   -60, -60, -60, -70, -70, -60, -60, -60,
   -50, -50, -50, -60, -60, -50, -50, -50,
   -40, -40, -40, -50, -50, -40, -40, -40,
   -30, -30, -30, -40, -40, -30, -30, -30,
   -20, -20, -20, -30, -30, -20, -20, -20,
     5,   5, -10, -20, -20, -10,   5,   5,
    20,  35,  15, -10,   0, -10,  35,  25,    # strongly prefer a castled corner
]
KING_ENDGAME_TABLE = [
   -50, -40, -30, -20, -20, -30, -40, -50,
   -30, -20, -10,   0,   0, -10, -20, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -10,  30,  35,  35,  30, -10, -30,
   -30, -10,  30,  35,  35,  30, -10, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -30,   0,   0,   0,   0, -30, -30,
   -50, -30, -30, -30, -30, -30, -30, -50,    # endgame: the king must still come out
]
PIECE_TABLES = {chess.PAWN: PAWN_TABLE, chess.KNIGHT: KNIGHT_TABLE, chess.BISHOP: BISHOP_TABLE,
                chess.ROOK: ROOK_TABLE, chess.QUEEN: QUEEN_TABLE}


#----------------------------------------------------------------------------------------------- Code 

#King attacking a piece is last priority, hence king recieves a big value.
#Agent avoids making a move that would endager the King, even if it loses a less valued piece.

def _attacker_value(piece_type):
    return 10_000 if piece_type == chess.KING else PIECE_VALUES[piece_type]



#Main defensive Agent class, inherits Minmax Class and uses the eval function for the board state.
#Eval function is designed to be loss averse. Rewards piece protection, pawn structure, king safety and development. 
#Penalizes hanging pieces, doubled pawns, isolated pawns and losing exchanges.

class DefensiveAgent(base_agent.ChessAgent):
    """Defensive agent: the shared engine search + this file's evaluation function."""

    def __init__(self, depth=DEFAULT_DEPTH):
        super().__init__("Defensive", self.evaluate_board, depth)
        self.color = chess.WHITE        # the side we are playing; set at the start of each search

    def choose_move(self, board):
        self.color = board.turn
        return super().get_best_move(board)

    # ------------------------------------------------------------ Board evaluation
    #Score board from White's point of view (centipawns); see the engine's score convention.

    def evaluate_board(self, board):
        score = 0.0
        for color in (chess.WHITE, chess.BLACK):
            sign = 1 if color == chess.WHITE else -1
            weight = LOSS_AVERSION if color == self.color else 1.0
            score += sign * (weight * self._material(board, color)
                             + self._king_safety(board, color)
                             + self._pawn_structure(board, color)
                             + self._piece_safety(board, color)
                             + self._development(board, color))
        score += self._simplification_bonus(board)
        return int(score)

    @staticmethod
    def _material(board, color):
        return sum(PIECE_VALUES[p.piece_type] for p in board.piece_map().values() if p.color == color)

    @staticmethod
    def _king_safety(board, color):
        king = board.king(color)
        if king is None:
            return 0
        kf, kr = chess.square_file(king), chess.square_rank(king)
        home, step = (0, 1) if color == chess.WHITE else (7, -1)
        score = 40 if (kr == home and kf in (1, 2, 6)) else 0          # tucked away on a castled square

        for f in range(max(0, kf - 1), min(7, kf + 1) + 1):             # pawn shield on the 3 files in front
            for dist, bonus in ((1, 15), (2, 8)):
                r = kr + step * dist
                if 0 <= r <= 7:
                    p = board.piece_at(chess.square(f, r))
                    if p and p.piece_type == chess.PAWN and p.color == color:
                        score += bonus
                        break
            else:
                score -= 12                                             # no shield pawn on this file

        enemy = not color                                               # enemy pressure around the king
        for sq in list(board.attacks(king)) + [king]:
            score -= 6 * len(board.attackers(enemy, sq))
        return score

    @staticmethod
    def _pawn_structure(board, color):
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(s) for s in pawns]
        score = 0
        for sq in pawns:
            f = chess.square_file(sq)
            if files.count(f) > 1:
                score -= 10                                             # doubled
            if not any(abs(f - g) == 1 for g in files):
                score -= 12                                             # isolated
            if board.attackers(color, sq) & pawns:
                score += 8                                              # protected by another pawn
        return score

    @staticmethod
    def _piece_safety(board, color):
        score = 0
        for sq, piece in board.piece_map().items():
            if piece.color != color or piece.piece_type == chess.KING:
                continue
            defenders = board.attackers(color, sq)
            if defenders:
                score += 3                                              # protected pieces are good
            attackers = board.attackers(not color, sq)
            if not attackers:
                continue
            value = PIECE_VALUES[piece.piece_type]
            cheapest = min(_attacker_value(board.piece_type_at(a)) for a in attackers)
            if not defenders:
                score -= 0.5 * value                                    # hanging
            elif cheapest < value:
                score -= 0.5 * (value - cheapest)                       # losing exchange
        return score

    @staticmethod
    def _development(board, color):
        home = 0 if color == chess.WHITE else 7
        minors = board.pieces(chess.KNIGHT, color) | board.pieces(chess.BISHOP, color)
        return 8 * sum(1 for sq in minors if chess.square_rank(sq) != home)

    #If more pieces ahead, rewards for trading pieces off the board for simplification.
    def _simplification_bonus(self, board):
        mine = self._material(board, self.color)
        theirs = self._material(board, not self.color)
        if mine - theirs < LEAD_THRESHOLD:
            return 0
        non_pawn = sum(PIECE_VALUES[p.piece_type] for p in board.piece_map().values()
                       if p.piece_type not in (chess.PAWN, chess.KING))
        bonus = max(0, START_NON_PAWN - non_pawn) // 20
        return bonus if self.color == chess.WHITE else -bonus

def make_sukanayna_agent(depth = DEFAULT_DEPTH):
    return base_agent.ChessAgent("Sukanayna's Agent", depth, evaluate_board)