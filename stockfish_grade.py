"""Grade the agents' moves with Stockfish and write the results to CSV.

Run from the project root, after run_match.py has produced match_results/games.pgn:
    python stockfish_grade.py --stockfish /path/to/stockfish
    python stockfish_grade.py --stockfish stockfish --depth 14 --pgn match_results/games.pgn --out match_results

How a move is graded
    Stockfish scores the position before the move (what the best move would achieve) and the position
    after the move that was actually played. The difference, from the mover's point of view, is the
    *centipawn loss* (CPL): how much worse the played move was than Stockfish's best. 0 = best move.
    Scores are clamped to +/-1000 cp so one move in an already won or lost game cannot dominate.

Move classes (by centipawn loss)
    best/good  < 50     inaccuracy  50-99     mistake  100-299     blunder  >= 300

Writes to the output folder:
    move_grades.csv      one row per move (who, move, scores, CPL, Stockfish's best move, class)
    game_grades.csv      one row per agent per game (average CPL, best-move %, inaccuracies, ...)
    agent_summary.csv    one row per agent across the whole match
"""
import argparse
import csv
import os
import statistics
import sys

import chess
import chess.engine
import chess.pgn

CLAMP = 1000                    # centipawns; evaluations are clamped to +/- this before taking differences
MATE_SCORE = 10000              # value given to a forced mate before clamping
OPENING_MOVES = 10              # moves 1-10 count as "opening" in the phase breakdown
THRESHOLDS = [(300, "blunder"), (100, "mistake"), (50, "inaccuracy")]


def classify(cpl):
    """Name a move by its centipawn loss."""
    for limit, name in THRESHOLDS:
        if cpl >= limit:
            return name
    return "good" if cpl > 0 else "best"


def clamp(cp):
    return max(-CLAMP, min(CLAMP, cp))


def analyse_position(engine, board, limit):
    """Return (score in centipawns for the side to move, Stockfish's best move) for a non-final position."""
    info = engine.analyse(board, limit)
    score = info["score"].pov(board.turn).score(mate_score=MATE_SCORE)
    return clamp(score), info["pv"][0]


def terminal_value(board):
    """Score (for the side to move) of a finished game: mated = -CLAMP, draw = 0."""
    return -CLAMP if board.is_checkmate() else 0


def grade_game(engine, game, limit):
    """Grade every move of one game. Returns a list of per-move dicts."""
    board = game.board()
    moves = list(game.mainline_moves())

    # One analysis per position; position i is the board before move i, position len(moves) is the final board.
    evals, best_moves, boards = [], [], []
    for move in moves:
        boards.append(board.copy())
        score, best = analyse_position(engine, board, limit)
        evals.append(score)
        best_moves.append(best)
        board.push(move)
    final_value = terminal_value(board) if board.is_game_over() else analyse_position(engine, board, limit)[0]

    rows = []
    for i, move in enumerate(moves):
        before = boards[i]
        after_value = final_value if i == len(moves) - 1 else evals[i + 1]
        played_value = -after_value                      # next position is scored for the opponent
        cpl = max(0, evals[i] - played_value)
        color = before.turn
        rows.append({
            "ply": i + 1,
            "move_number": before.fullmove_number,
            "color": "White" if color == chess.WHITE else "Black",
            "agent": game.headers["White" if color == chess.WHITE else "Black"],
            "move": before.san(move),
            "best_move": before.san(best_moves[i]),
            "is_best": int(move == best_moves[i]),
            "eval_best_cp": evals[i],
            "eval_played_cp": played_value,
            "cpl": cpl,
            "class": classify(cpl),
            "phase": "opening" if before.fullmove_number <= OPENING_MOVES else "later",
        })
    return rows


def summarise(rows):
    """Aggregate a list of move rows into one summary dict (used per game and per agent)."""
    cpls = [r["cpl"] for r in rows]
    opening = [r["cpl"] for r in rows if r["phase"] == "opening"]
    later = [r["cpl"] for r in rows if r["phase"] == "later"]
    count = lambda name: sum(1 for r in rows if r["class"] == name)
    return {
        "moves": len(rows),
        "avg_cpl": round(float(statistics.mean(cpls)), 1) if cpls else "",
        "median_cpl": round(float(statistics.median(cpls)), 1) if cpls else "",
        "avg_cpl_opening": round(float(statistics.mean(opening)), 1) if opening else "",
        "avg_cpl_later": round(float(statistics.mean(later)), 1) if later else "",
        "best_move_pct": round(100 * sum(r["is_best"] for r in rows) / len(rows), 1) if rows else "",
        "inaccuracies": count("inaccuracy"),
        "mistakes": count("mistake"),
        "blunders": count("blunder"),
    }


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stockfish", default="stockfish", help="path to the Stockfish executable (default: 'stockfish' on PATH)")
    ap.add_argument("--pgn", default=os.path.join("match_results", "games.pgn"), help="PGN file written by match.py")
    ap.add_argument("--out", default="match_results", help="output folder for the CSV files")
    ap.add_argument("--depth", type=int, default=12, help="Stockfish search depth per position (default 12)")
    ap.add_argument("--time", type=float, help="seconds per position instead of a fixed depth")
    ap.add_argument("--threads", type=int, default=1, help="Stockfish threads (default 1)")
    args = ap.parse_args()

    limit = chess.engine.Limit(time=args.time) if args.time else chess.engine.Limit(depth=args.depth)
    try:
        engine = chess.engine.SimpleEngine.popen_uci(args.stockfish)
    except FileNotFoundError:
        sys.exit(f"Could not find Stockfish at '{args.stockfish}'. Download it from https://stockfishchess.org/download/ "
                 "and pass its path with --stockfish.")
    engine.configure({"Threads": args.threads})
    os.makedirs(args.out, exist_ok=True)

    move_rows, game_rows = [], []
    with engine, open(args.pgn) as pgn:
        while True:
            game = chess.pgn.read_game(pgn)
            if game is None:
                break
            number = game.headers.get("Round", str(len(game_rows) // 2 + 1))
            print(f"Grading game {number}: {game.headers['White']} vs {game.headers['Black']} ...", flush=True)
            rows = grade_game(engine, game, limit)
            for r in rows:
                move_rows.append({"game": number, **r})
            for color in ("White", "Black"):
                mine = [r for r in rows if r["color"] == color]
                game_rows.append({"game": number, "agent": game.headers[color], "color": color,
                                  "game_result": game.headers.get("Result", ""), **summarise(mine)})

    if not move_rows:
        sys.exit(f"No games found in {args.pgn}.")

    agent_rows = []
    for agent in sorted({r["agent"] for r in move_rows}):
        agent_rows.append({"agent": agent, "games": sum(1 for g in game_rows if g["agent"] == agent),
                           "stockfish_depth": args.depth if not args.time else f"{args.time}s",
                           **summarise([r for r in move_rows if r["agent"] == agent])})

    write_csv(os.path.join(args.out, "move_grades.csv"), move_rows)
    write_csv(os.path.join(args.out, "game_grades.csv"), game_rows)
    write_csv(os.path.join(args.out, "agent_summary.csv"), agent_rows)

    print("\n=== Agent summary (lower average CPL = more accurate) ===")
    for r in agent_rows:
        print(f"{r['agent']}: avg CPL {r['avg_cpl']}, best-move {r['best_move_pct']}%, "
              f"{r['inaccuracies']} inaccuracies, {r['mistakes']} mistakes, {r['blunders']} blunders "
              f"over {r['moves']} moves")
    print(f"Grades written to {args.out}/")


if __name__ == "__main__":
    main()
