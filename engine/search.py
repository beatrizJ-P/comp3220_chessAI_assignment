import chess
import random

CHECKMATE = 10000

def minimax(board, depth, alpha, beta, maximizing_player, evaluate_board):

    if board.is_checkmate():
        if maximizing_player:
            return -CHECKMATE - depth  # Black wins
        else:
            return CHECKMATE + depth  # White wins

    if board.is_game_over(): # for  stalemate, resignations etc.
        return 0

    if depth == 0:
        return evaluate_board(board)

    # White's turn
    if maximizing_player:
        max_eval = float('-inf')
        for move in board.legal_moves:
            board.push(move)
            score = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            max_eval = max(max_eval, score)
            alpha = max(alpha, score)
            if beta <= alpha: 
                break
        return max_eval

    # Black's turn
    else:
        min_eval = float('inf')
        for move in board.legal_moves:
            board.push(move)
            score = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            min_eval = min(min_eval, score)
            beta = min(beta, score)
            if beta <= alpha:
                break
        return min_eval

def get_best_move(board, depth, evaluate_board):
    best_move = None
    moves_with_same_eval = []
    alpha, beta = float('-inf'), float('inf')
    if board.turn == chess.WHITE:
        maximizing_player = True
        best_score = float('-inf')
    else:
        maximizing_player = False
        best_score = float('inf')

    for move in board.legal_moves:
        board.push(move)
        score = minimax(board, depth - 1, alpha, beta, maximizing_player, evaluate_board)
        board.pop()
        if maximizing_player: 
            if score > best_score:
                best_score = score
                best_move = move
                alpha = max(alpha, score)
                moves_with_same_eval = [move]
            elif score == best_score:
                moves_with_same_eval.append(move)

        elif not maximizing_player:
            if score < best_score:
                best_score = score
                best_move = move
                beta = min(beta, score)
                moves_with_same_eval = [move]
            elif score == best_score:
                moves_with_same_eval.append(move)
    return random.choice(moves_with_same_eval) if len(moves_with_same_eval) > 1 else best_move
