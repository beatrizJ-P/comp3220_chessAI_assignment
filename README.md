# COMP3220 Chess Agents: Minimax enhanced with Alpha-Beta Pruning

# Group Members:
Beatrice Matthias - 620161377
Sukanayna Hoo - 620173255

Two chess-playing agents that share one Minimax + Alpha-Beta search engine but
use deliberately different evaluation functions (strategies), plus a GUI, an
agent-vs-agent match harness and a Stockfish move-grading script.

| Agent | Strategy | Built by |
|---|---|---|
| **Aggressive** (`agents/beatrice_chess_agent.py`) | Threats, initiative and pressure on the enemy king; sharp gambit opening book | Beatrice |
| **Defensive** (`agents/sukanayna_chess_agent.py`) | Loss-averse: king safety, pawn structure, protected pieces; simplifies when ahead | Sukanayna |

Shared (built together): search engine, GUI, match harness, Stockfish grading.
See `documentation/match_report.md` for the agent-vs-agent results.

---

## 1. Setup

Requires **Python 3.9+**.

```bash
pip install chess
```

### Stockfish (optional)

Stockfish is **only** used by `stockfish_grade.py` to grade finished games. The
agents never use it to choose moves, and everything else works without it.

- macOS: `brew install stockfish`
- Linux: `sudo apt install stockfish`
- Windows / other: download a build from <https://stockfishchess.org/download/>
  and pass its location with `--stockfish /path/to/stockfish`.

All commands below are run **from the project root** (the folder containing
`agents/`, `engine/` and `gui/`).

## 2. GUI (human vs agent, agent vs agent)

> **TODO:** confirm the launch command and list the GUI's real features below.

```bash
python gui/app.py
```

**or to run from outside of the gui folder**

```bash
python -m gui.app
```

- **Human vs agent**: choose which of the two agents to play and play a full
  game against it on the board.
- **Agent vs agent**: the two agents play each other with the board updating
  after every move.
- **Search depth**: sets how many plies each agent looks ahead (the difficulty).

## 3. Agent-vs-agent match harness

```bash
python run_match.py                                   # 6 games, depth 3 each
python run_match.py --games 10 --depth-a 2 --depth-b 3 --max-plies 200
python run_match.py --games 6 --depth 3 --seed 3220  # reproducible
```

| Option | Description | Default |
|---|---|---|
| `--games N` | Number of games (at least 5 recommended) | 6 |
| `--depth D` | Search depth for both agents | 3 |
| `--depth-a D` | Override depth for Agent A (aggressive) | none |
| `--depth-b D` | Override depth for Agent B (defensive) | none |
| `--max-plies N` | Call the game a draw after `N` half-moves | 300 |
| `--out DIR` | Base folder; each run is saved in its own subfolder | `match_results` |
| `--seed N` | Fix the random seed so a match can be reproduced exactly | none |

- Colours alternate every game: the aggressive agent is White in games 1, 3, 5, ...
- If an agent returns an illegal move, a random legal move is played instead
  and a warning is printed.

Every run is saved in its own timestamped folder, `match_results/<date_time>/`
(for example `match_results/2026-11-22_14-30-05/`), so earlier runs are never
overwritten:

| File | Contents |
|---|---|
| `games.csv` | One row per game: date, site, players, opening, book plies, first moves, result, how it ended, plies, seconds, depths |
| `moves.txt` | Every move of every game in numbered SAN |
| `games.pgn` | The same games as PGN, with `Site`, `Date` and `Opening` headers (opens in any chess viewer, e.g. lichess.org/paste) |

## 4. Stockfish grading

```bash
python stockfish_grade.py --stockfish /path/to/stockfish             # newest run, depth 12
python stockfish_grade.py --stockfish /path/to/stockfish --depth 14  # slower, more reliable
python stockfish_grade.py --stockfish /path/to/stockfish --run match_results/2026-11-22_14-30-05
```

For each move, Stockfish scores the position before it and after the move that
was actually played. The difference is the **centipawn loss (CPL)**: 0 means the
best move, and higher means a worse move. Evaluations are capped at +/-1000 cp.
Moves are classed as inaccuracy (CPL 50-99), mistake (100-299) or blunder (300+).

| Option | Description | Default |
|---|---|---|
| `--stockfish PATH` | Stockfish executable | `stockfish` on PATH |
| `--run DIR` | Run folder to grade | newest folder in `--results-dir` |
| `--results-dir DIR` | Where `run_match.py` saves its runs | `match_results` |
| `--depth D` | Stockfish depth per position | 12 |
| `--time S` | Seconds per position instead of a fixed depth | none |
| `--threads N` | Stockfish threads | 1 |

The grades are saved in the same run folder as the games they grade:

| File | Contents |
|---|---|
| `move_grades.csv` | One row per move: agent, move, Stockfish's best move, both evaluations, CPL, class |
| `game_grades.csv` | One row per agent per game: average CPL, best-move %, inaccuracies, mistakes, blunders |
| `agent_summary.csv` | One row per agent across the whole match |

## 5. How the search works

### Minimax

Minimax assumes both players choose their best move. Positions are scored from
**White's point of view**: White picks the move that maximises the score and
Black picks the move that minimises it. The search plays out every legal move to
a fixed depth, scores the leaf positions with the agent's evaluation function and
passes the best score back up the tree. The agent plays the root move with the
best backed-up score.

- **Depth control.** The depth is set per agent. Depth 3 means the agent looks at
  its move, the opponent's reply and its own follow-up.
- **Terminal positions.** Checkmate scores 10000 plus the remaining depth, so a
  quicker mate is preferred. Stalemate, insufficient material and repetition
  score as a draw (0 by default, adjustable with `contempt`).
- **Ties.** Moves with equal scores are chosen between at random, so the same
  position does not always produce the same game.

### Alpha-beta pruning

Alpha-beta pruning returns the same answer as plain Minimax but skips branches
that cannot affect it. `alpha` is the best score White is already guaranteed and
`beta` is the best score Black is already guaranteed. When `beta <= alpha`, the
current line is already worse for the side choosing than an option it has, so
the rest of that branch is not searched.

Pruning works best when good moves are tried first, so `order_moves()` sorts
moves before searching:

1. Captures, by most-valuable-victim / least-valuable-attacker (`10 x victim - attacker`)
2. Promotions (+8)
3. Checking moves (+3)

At the root each move is searched with a full window, so equal scores stay exact
and ties can be compared. Pruning applies everywhere below the root.

**Known limitation.** The search is fixed-depth with no quiescence search, so an
agent can misjudge a position that is mid-capture at the depth limit (the
horizon effect). Game 3 of the match report shows this.

## 6. The two strategies

### Aggressive agent (Beatrice)

Built on initiative and pressure. It will accept material risk if that creates
threats. Its evaluation (decipawns, pawn = 10) rewards:

- **Material**, with a bishop-pair bonus and a bonus for being ahead that grows
  as pieces come off the board (it likes to trade down when winning).
- **Threats on enemy pieces**: attacking an undefended piece, or attacking a
  piece with a cheaper one, scores points. Threats on its own move count more
  than threats it must answer.
- **Pressure on the enemy king**: each attacker on a square next to the enemy
  king adds to the score, and being in check costs points.
- **Pawn advancement**: pawns past the third rank earn a bonus that grows
  quadratically.
- **A sharp opening book** of nine lines: King's Gambit, Evans Gambit, Scotch
  Gambit, Najdorf Sicilian, Smith-Morra, Benko Gambit, Samisch King's Indian,
  Queen's Gambit and English Opening. It follows a line while the opponent does,
  then switches to search.

### Defensive agent (Sukanayna)

Built on safety and counter-play. It tries not to lose material or expose its
king, and waits for the opponent to overreach. Its evaluation (centipawns,
pawn = 100) combines:

- **Loss aversion**: its own material is weighted 1.15x against the opponent's 1.0x.
- **King safety**: a bonus for a castled king and for pawns shielding it, and a
  penalty for each enemy attacker near it.
- **Piece safety**: a small bonus for protected pieces, and penalties for hanging
  pieces and losing exchanges.
- **Pawn structure**: penalties for doubled and isolated pawns, and a bonus for
  pawns protected by pawns.
- **Development**: a bonus for each minor piece that has left its home rank.
- **Simplification**: when at least two pawns ahead, a bonus for trading pieces off.
- **Piece-square tables**: compact, defensive placement for every piece (shelter
  pawns stay home, knights guard the centre from their own half, the queen stays
  back), with the king switching to an endgame table once little material remains.

### How they differ

| | Aggressive | Defensive |
|---|---|---|
| **Core question** | "What can I attack?" | "What can I lose?" |
| **Material** | Neutral, trades for initiative | Loss-averse (own material x1.15) |
| **King** | Targets the enemy king zone | Protects its own king (castling, pawn shield) |
| **Pawns** | Rewards advancing | Rewards structure and keeping shelter pawns home |
| **Pieces** | Rewards threats on targets | Rewards protection, penalises hanging pieces |
| **Opening** | Sharp gambit book | No book; piece-square tables guide development |
| **Endgame** | Trades down when ahead | Simplifies when two pawns ahead |

The two agents differ in *what they reward*, not just in weights on a shared
formula: one scores what the opponent is exposed to, the other scores what the
agent itself is exposed to. In the match this showed up as more pawn advances and
no castling for the aggressive agent, versus castling in half the games for the
defensive one.

## 7. Results

6 games at depth 3 (`python run_match.py --games 6 --depth 3 --seed 3220`):

| Agent | Wins | Draws | Losses | Score |
|---|:-:|:-:|:-:|:-:|
| **Aggressive** | 3 | 1 | 2 | **3.5** |
| **Defensive** | 2 | 1 | 3 | **2.5** |

Five of the six games ended in checkmate. Stockfish grading put the two agents
close together on accuracy (average CPL 60.0 vs 63.6). See
`documentation/match_report.md` for the game-by-game breakdown, opening
statistics and analysis.

## 8. Project structure

```
agents/
  base_agent.py              ChessAgent: name, depth and evaluation function on top of the engine
  beatrice_chess_agent.py    Aggressive agent: evaluation function and opening-line player
  sukanayna_chess_agent.py   Defensive agent: evaluation function and piece-square tables

engine/
  engine.py                  Shared Minimax + Alpha-Beta search, move ordering, opening book

gui/
  app.py                     GUI: human vs agent and agent vs agent
  images/                    Piece images

documentation/
  match_report.md            Agent-vs-agent results and analysis

match_results/               One timestamped folder per run, from run_match.py and stockfish_grade.py (generated)
run_match.py                 Agent-vs-agent match harness
stockfish_grade.py           Stockfish grading of a finished match
README.md
```

## AI Disclaimer

Generative AI was used to assist with strengthening the agents, and creating match harness, the Stockfish grading script and the documentation for this project.