from engine.engine import get_best_move as _search
 
 
class ChessAgent:
    def __init__(self, name, depth, evaluate_board, use_book=False, contempt=0):
        if callable(depth):                      # also accept (name, evaluate_board, depth) order
            depth, evaluate_board = evaluate_board, depth
        self.name = name
        self.depth = depth
        self.evaluate_board = evaluate_board
        self.use_book = use_book
        self.contempt = contempt          # >0: avoid draws, <0: accept them (see engine.get_best_move)
 
    def get_best_move(self, board):
        """Run minimax + alpha-beta on a copy of the board."""
        return _search(board.copy(), self.depth, self.evaluate_board, self.use_book)
 
    def choose_move(self, board):
        """Hook subclasses may override (e.g. to set which colour they play)."""
        return self.get_best_move(board)
 
    def get_move(self, board):
        """Entry point used by the GUI and match harness."""
        return self.choose_move(board)
 