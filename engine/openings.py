import chess

OPENINGS = {
    "King's Gambit":     ["e4", "e5", "f4", "exf4", "Nf3", "g5"],
    "Evans Gambit":      ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "b4", "Bxb4", "c3", "Ba5"],
    "Scotch Gambit":     ["e4", "e5", "Nf3", "Nc6", "d4", "exd4", "Bc4", "Nf6"],
    "Najdorf Sicilian":  ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6", "Nc3", "a6"],
    "Smith-Morra":       ["e4", "c5", "d4", "cxd4", "c3", "dxc3", "Nxc3", "Nc6"],
    "Benko Gambit":      ["d4", "Nf6", "c4", "c5", "d5", "b5", "cxb5", "a6"],
    "Samisch King's Indian": ["d4", "Nf6", "c4", "g6", "Nc3", "Bg7", "e4", "d6", "f3", "O-O"],
    "Queen's Gambit":   ["d4", "d5", "c4", "e6", "Nc3", "Nf6"],
    "English Opening":  ["c4", "e5", "Nc3", "Nf6", "Nf3", "Nc6"],
}

def build_opening_book(openings):
    book = {}
    for name, moves in OPENINGS.items():
        board = chess.Board()
        for move in moves:
            uci_move = board.parse_san(move).uci()
            if board.fen() not in book:
                book[board.fen()] = []
            book[board.fen()].append(uci_move)
            board.push_san(move)
    return book

opening_book = build_opening_book(OPENINGS)