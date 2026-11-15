from engine.search import get_best_move


class ChessAgent:
    def __init__(self, name, depth, evaluate_board):
        self.name = name
        self.depth = depth
        self.evaluate_board = evaluate_board

    def get_move(self, board):
        return get_best_move(board.copy(), self.depth, self.evaluate_board)