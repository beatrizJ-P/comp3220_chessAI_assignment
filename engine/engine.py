import random
import chess

CHECKMATE = 10000
PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

# ------------------------------------------------------------------ openings
OPENINGS = {
    "King's Gambit":         ["e4", "e5", "f4", "exf4", "Nf3", "g5"],
    "Evans Gambit":          ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "b4", "Bxb4", "c3", "Ba5"],
    "Scotch Gambit":         ["e4", "e5", "Nf3", "Nc6", "d4", "exd4", "Bc4", "Nf6"],
    "Najdorf Sicilian":      ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"],
    "Smith-Morra":           ["e4", "c5", "d4", "cxd4", "c3", "dxc3", "Nxc3", "Nc6"],
    "Benko Gambit":          ["d4", "Nf6", "c4", "c5", "d5", "b5", "cxb5", "a6"],
    "Samisch King's Indian": ["d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f3", "O-O"],
    "Queen's Gambit":        ["d4", "d5", "c4", "e6", "Nc3", "Nf6"],
    "English Opening":       ["c4", "e5", "Nc3", "Nf6", "Nf3", "Nc6"],
}


def _book_key(board):
    """Position key ignoring move counters, so transpositions still match the book."""
    return " ".join(board.fen().split()[:4])


def build_opening_book(openings=OPENINGS):
    """Map position key -> list of UCI book moves played from that position."""
    book = {}
    for moves in openings.values():
        board = chess.Board()
        for san in moves:
            uci = board.parse_san(san).uci()
            replies = book.setdefault(_book_key(board), [])
            if uci not in replies:
                replies.append(uci)
            board.push_san(san)
    return book


opening_book = build_opening_book()


def get_book_move(board):
    """Return a random legal book move for this position, or None if out of book."""
    replies = list(opening_book.get(_book_key(board), []))
    random.shuffle(replies)
    for uci in replies:
        move = chess.Move.from_uci(uci)
        if move in board.legal_moves:
            return move
    return None


# ------------------------------------------------------------------ search
def order_moves(board):
    """Order moves best-first (captures by MVV-LVA, promotions, checks) so pruning cuts more."""
    def score(move):
        s = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)          # None for en passant
            attacker = board.piece_at(move.from_square)
            victim_value = PIECE_VALUES[victim.piece_type] if victim else 1
            s += 10 * victim_value - PIECE_VALUES[attacker.piece_type]
        if move.promotion:
            s += 8
        if board.gives_check(move):
            s += 3
        return s

    return sorted(board.legal_moves, key=score, reverse=True)


def _is_repetition(board):
    """True if this position has already occurred (game history + search line).
    Needs a few plies since the last capture/pawn move, so the cheap clock test comes first."""
    return board.halfmove_clock >= 4 and board.is_repetition(2)


def minimax(board, depth, alpha, beta, maximizing_player, evaluate_board, draw_value=0):
    """Minimax with alpha-beta pruning. White maximizes, Black minimizes.
    `draw_value` is what a drawn position (stalemate, repetition, ...) is worth, from White's view."""
    if board.is_checkmate():
        # Side to move is mated; the +depth term prefers faster mates.
        return (-CHECKMATE - depth) if maximizing_player else (CHECKMATE + depth)
    if board.is_game_over() or _is_repetition(board):         # stalemate, insufficient material, repetition
        return draw_value
    if depth == 0:
        return evaluate_board(board)

    if maximizing_player:
        best = float("-inf")
        for move in order_moves(board):
            board.push(move)
            best = max(best, minimax(board, depth - 1, alpha, beta, False, evaluate_board, draw_value))
            board.pop()
            alpha = max(alpha, best)
            if beta <= alpha:                                 # Black would never allow this line
                break
        return best

    best = float("inf")
    for move in order_moves(board):
        board.push(move)
        best = min(best, minimax(board, depth - 1, alpha, beta, True, evaluate_board, draw_value))
        board.pop()
        beta = min(beta, best)
        if beta <= alpha:                                     # White would never allow this line
            break
    return best


def get_best_move(board, depth, evaluate_board, use_book=False, contempt=0):
    """Pick the best move for the side to move; ties are broken randomly for variety.

    contempt: how much worse than equal a draw is for the side to move, in the evaluation's own units.
    0 = a draw is worth 0; positive = avoid draws (play on); negative = accept draws more readily.
    """
    if use_book:
        book_move = get_book_move(board)
        if book_move:
            return book_move

    maximizing = board.turn == chess.WHITE
    draw_value = -contempt if maximizing else contempt        # converted to White's point of view
    best_score = float("-inf") if maximizing else float("inf")
    best_moves = []

    for move in order_moves(board):
        board.push(move)
        # Full window per root move so equal scores are exact and ties can be compared.
        score = minimax(board, depth - 1, float("-inf"), float("inf"), not maximizing, evaluate_board, draw_value)
        board.pop()
        if score == best_score:
            best_moves.append(move)
        elif (maximizing and score > best_score) or (not maximizing and score < best_score):
            best_score, best_moves = score, [move]

    return random.choice(best_moves) if best_moves else None