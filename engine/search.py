import chess

CHECKMATE = 10000

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

    # White's turn
    if maximizing_player:
        max_eval = float('-inf')
        for move in board.legal_moves:
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
        for move in board.legal_moves:
            board.push(move)
            score = minimax(board, depth - 1, alpha, beta, True, evaluate_board)
            board.pop()
            min_eval = min(min_eval, score)
            beta = min(beta, score)
            if beta <= alpha:
                break
        return min_eval

def get_best_move(board, depth, evaluate_board):
    best_move = None
    alpha, beta = float('-inf'), float('inf')
    if board.turn == chess.WHITE:
        maximizing_player = True
        best_score = float('-inf')
    else:
        maximizing_player = False
        best_score = float('inf')

    for move in board.legal_moves:
        board.push(move)
        score = minimax(board, depth - 1, alpha, beta, not maximizing_player, evaluate_board)
        board.pop()
        if maximizing_player and score > best_score: 
                best_score = score
                best_move = move
                alpha = max(alpha, score)

        elif not maximizing_player and score < best_score:
                best_score = score
                best_move = move
                beta = min(beta, score)
            
    return best_move
