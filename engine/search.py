import chess
import random

CHECKMATE = 10000

PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def order_moves(board):
    def score(move):
        s = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            victim_value = PIECE_VALUES[victim.piece_type] if victim else 1
            s += 10 * victim_value - PIECE_VALUES[attacker.piece_type]
        if move.promotion:
            s += 8
        if board.gives_check(move):
            s += 3
        return s

    return sorted(board.legal_moves, key=score, reverse=True)


def minimax(board, depth, alpha, beta, maximizing_player, evaluate_board):

    if board.is_checkmate():
        if maximizing_player:
            return -CHECKMATE - depth  # Black wins
        else:
            return CHECKMATE + depth  # White wins

    if board.is_game_over(): # for stalemate, insufficient material etc.
        return 0

    if depth == 0:
        return evaluate_board(board)

    moves = order_moves(board)

    # White's turn
    if maximizing_player:
        max_eval = float('-inf')
        for move in moves:
            board.push(move)
            score = minimax(board, depth - 1, alpha, beta, False, evaluate_board)
            board.pop()
            max_eval = max(max_eval, score)
            alpha = max(alpha, score)
            if beta <= alpha: 
                break
        return max_eval

    # Black's turn
    else:
        min_eval = float('inf')
        for move in moves:
            board.push(move)
            score = minimax(board, depth - 1, alpha, beta, True, evaluate_board)
            board.pop()
            min_eval = min(min_eval, score)
            beta = min(beta, score)
            if beta <= alpha:
                break
        return min_eval


def get_best_move(board, depth, evaluate_board):
    best_move = []
    
    if board.turn == chess.WHITE:
        maximizing_player = True
        best_score = float('-inf')
    else:
        maximizing_player = False
        best_score = float('inf')

    moves = order_moves(board)

    for move in moves:
        board.push(move)
        score = minimax(board, depth - 1, float('-inf'), float('inf'), not maximizing_player, evaluate_board)
        board.pop()
        if (maximizing_player and score > best_score) or (not maximizing_player and score < best_score): 
                best_score = score
                best_moves = [move]
                
        elif score == best_score:
                best_moves.append(move)

    return random.choice(best_moves)
