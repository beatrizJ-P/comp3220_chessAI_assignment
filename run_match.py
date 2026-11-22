"""Agent-vs-agent match harness.

Run from the project root:
    python run_match.py                          # 6 games, depth 3 each
    python run_match.py --games 10 --depth-a 2 --depth-b 3 --max-plies 200

Agent A = Beatrice's (aggressive), Agent B = Sukanayna's (defensive). Colours alternate every game
(A is White in games 1, 3, 5...). Writes to match_results/:
    games.csv   one row per game (players, opening, first moves, result, how it ended, plies, seconds)
    moves.txt   every move of every game in numbered SAN
    games.pgn   the same games as PGN, loadable in any chess viewer
"""
import argparse
import csv
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import chess
import chess.pgn

from agents.beatrice_chess_agent import make_beatrice_agent
from agents.sukanayna_chess_agent import make_defensive_agent
from engine.engine import OPENINGS

NAMES = {"A": "Beatrice's Agent", "B": "Sukanayna's Agent"}
SITE = "COMP3220"


def play_game(white, black, max_plies):
    """Play one game. Returns (board, list_of_san_moves, end_reason)."""
    board, sans = chess.Board(), []
    while not board.is_game_over(claim_draw=True) and len(sans) < max_plies:
        agent = white if board.turn == chess.WHITE else black
        move = agent.get_move(board)
        if move not in board.legal_moves:                      # never let a bad agent stall the match
            print(f"  ! {agent.name} returned {move!r}; playing a random legal move instead")
            move = random.choice(list(board.legal_moves))
        sans.append(board.san(move))
        board.push(move)
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return board, sans, "move cap reached (scored as a draw)"
    return board, sans, outcome.termination.name.replace("_", " ").lower()


# Names for games that leave Beatrice's book early, keyed by the opening SAN moves (most specific first).
FAMILIES = [
    (("e4", "e5"), "Open Game (1.e4 e5)"), (("e4", "c5"), "Sicilian Defence (1.e4 c5)"),
    (("e4", "d6"), "Pirc Defence (1.e4 d6)"), (("e4",), "King's Pawn Game (1.e4)"),
    (("d4", "Nf6"), "Indian Defence (1.d4 Nf6)"), (("d4", "d5"), "Closed Game (1.d4 d5)"),
    (("d4",), "Queen's Pawn Game (1.d4)"), (("c4",), "English Opening (1.c4)"),
    (("Nf3",), "Reti Opening (1.Nf3)"), (("Nc3",), "Van Geet Opening (1.Nc3)"),
]
MIN_BOOK_PLIES = 4          # the game must follow a book line for two full moves to be named after it


def detect_opening(sans, preferred=None):
    """Name the opening a game started with. Returns (name, book_plies).

    Compares the game with every line in engine.OPENINGS and finds the one it follows for the most
    half-moves (`book_plies`). If that is at least MIN_BOOK_PLIES the game is named after that book
    opening; ties (e.g. Evans/Scotch/King's Gambit all start 1.e4 e5) go to `preferred`, the opening
    Beatrice's agent selected. Otherwise the game left the book too early and is named after its first
    moves from FAMILIES (e.g. "Reti Opening (1.Nf3)").
    """
    best_name, best_len = None, 0
    for name, line in OPENINGS.items():
        n = 0
        while n < min(len(line), len(sans)) and line[n] == sans[n]:
            n += 1
        if n > best_len or (n == best_len and n > 0 and name == preferred):
            best_name, best_len = name, n
    if best_len >= MIN_BOOK_PLIES:
        return best_name, best_len
    for prefix, family in FAMILIES:
        if tuple(sans[:len(prefix)]) == prefix:
            return family, best_len
    return f"Irregular opening (1.{sans[0]})" if sans else "None", best_len


def movetext(sans):
    return " ".join(f"{i // 2 + 1}. {sans[i]}" + (f" {sans[i + 1]}" if i + 1 < len(sans) else "")
                    for i in range(0, len(sans), 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games", type=int, default=6, help="number of games (default 6, minimum 5 recommended)")
    ap.add_argument("--depth", type=int, default=3, help="search depth for both agents")
    ap.add_argument("--depth-a", type=int, help="override depth for Agent A (Beatrice)")
    ap.add_argument("--depth-b", type=int, help="override depth for Agent B (Sukanayna)")
    ap.add_argument("--max-plies", type=int, default=300, help="stop and call it a draw after this many half-moves")
    ap.add_argument("--out", default="match_results", help="output folder")
    ap.add_argument("--seed", type=int, help="random seed, so a match (and its report) can be reproduced exactly")
    args = ap.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    depth = {"A": args.depth_a or args.depth, "B": args.depth_b or args.depth}

    os.makedirs(args.out, exist_ok=True)
    score = {"A": 0.0, "B": 0.0}
    tally = {"A wins": 0, "B wins": 0, "draws": 0}
    rows, pgn_games, move_log = [], [], []

    for g in range(1, args.games + 1):
        a_white = g % 2 == 1                                      # alternate colours
        agents = {"A": make_beatrice_agent(depth["A"]), "B": make_defensive_agent(depth["B"])}
        white_key, black_key = ("A", "B") if a_white else ("B", "A")
        t0 = time.time()
        game_date = datetime.now().strftime("%Y.%m.%d")           # PGN date format: YYYY.MM.DD
        board, sans, reason = play_game(agents[white_key], agents[black_key], args.max_plies)
        secs = round(time.time() - t0)

        outcome = board.outcome(claim_draw=True)
        result = outcome.result() if outcome else "1/2-1/2"
        if result == "1-0":
            winner = white_key
        elif result == "0-1":
            winner = black_key
        else:
            winner = None
        if winner:
            score[winner] += 1
            tally[f"{winner} wins"] += 1
        else:
            score["A"] += 0.5
            score["B"] += 0.5
            tally["draws"] += 1

        opening, book_plies = detect_opening(sans, preferred=agents["A"].opening_name)
        label = NAMES[winner] if winner else "draw"
        print(f"Game {g}: White = {NAMES[white_key]}  Black = {NAMES[black_key]}  ->  {result} "
              f"({label}; {reason}; {len(sans)} plies; {secs}s; opening: {opening})")
        rows.append({"game": g, "date": game_date, "site": SITE,
                     "white": NAMES[white_key], "black": NAMES[black_key], "opening": opening,
                     "book_plies": book_plies, "first_moves": movetext(sans[:4]), "result": result, "winner": label, "reason": reason, "plies": len(sans), "seconds": secs,
                     "depth_A": depth["A"], "depth_B": depth["B"]})
        move_log.append(f"Game {g} ({SITE}, {game_date}): {NAMES[white_key]} (White) vs "
                        f"{NAMES[black_key]} (Black)  [{result}, {reason}; {opening}]\n"
                        f"{movetext(sans)}\n")
        game = chess.pgn.Game.from_board(board)
        game.headers.update({"Event": "Agent match", "Site": SITE, "Date": game_date, "Opening": opening,
                             "Round": str(g), "White": NAMES[white_key],
                             "Black": NAMES[black_key], "Result": result, "Termination": reason})
        pgn_games.append(game)

    with open(os.path.join(args.out, "games.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(args.out, "moves.txt"), "w") as f:
        f.write("\n".join(move_log))
    with open(os.path.join(args.out, "games.pgn"), "w") as f:
        for game in pgn_games:
            print(game, file=f, end="\n\n")

    print("\n=== Match result ===")
    print(f"{NAMES['A']} {score['A']:g} - {score['B']:g} {NAMES['B']}   "
          f"(wins {tally['A wins']}-{tally['B wins']}, draws {tally['draws']}, "
          f"depth {depth['A']} vs {depth['B']})")
    print(f"Logs written to {args.out}/")


if __name__ == "__main__":
    main()
