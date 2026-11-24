# COMP3220 Chess Agents: Match Report

Agent-vs-agent results for the **Aggressive** agent and the **Defensive** agent:
6 games, both agents at search depth 3, colours alternating every game.

> To run the match harness (adjustable): 
> `python run_match.py ` #standard 6 games
> `python run_match.py --games 6 --depth 3 --seed 3220` 
> `python run_match.py --games 10 --depth-a 2 --depth-b 3 --max-plies 200`

| Agent | Strategy |
|---|---|
| **Aggressive** | Piece activity, initiative and attacking the enemy king |
| **Defensive** | Loss-averse: king safety, pawn structure, protected pieces; simplifies when ahead |

---

## 1. Result

| Agent | Wins | Draws | Losses | Score |
|---|:-:|:-:|:-:|:-:|
| **Aggressive** | 3 | 1 | 2 | **3.5** |
| **Defensive** | 2 | 1 | 3 | **2.5** |

**Final scoreline: Aggressive 3.5 - 2.5 Defensive.**

- Five of six games ended in checkmate; one was drawn by insufficient material.
- Games averaged 107 plies and about 56 seconds each at depth 3.
- The margin is one point over six games, so the match is **not conclusive**.

## 2. Games

| # | White | Black | Opening played | Result | Ended by | Plies |
|:-:|---|---|---|:-:|---|:-:|
| 1 | Aggressive | Defensive | Pirc Defence (1.e4 d6) | 1-0 | Checkmate | 53 |
| 2 | Defensive | Aggressive | Van Geet Opening (1.Nc3) | 1-0 | Checkmate | 149 |
| 3 | Aggressive | Defensive | English Opening (1.c4) | 0-1 | Checkmate | 40 |
| 4 | Defensive | Aggressive | Reti Opening (1.Nf3) | 0-1 | Checkmate | 72 |
| 5 | Aggressive | Defensive | Queen's Pawn Game (1.d4) | 1-0 | Checkmate | 115 |
| 6 | Defensive | Aggressive | Reti Opening (1.Nf3) | 1/2-1/2 | Insufficient material | 215 |

**By colour.** The Aggressive agent scored 2/3 as White and 1.5/3 as Black. The
Defensive agent scored 1.5/3 as White and 1/3 as Black. Both did better with
White, as expected, but the sample is too small to say more.

### Notes on each game

- **Game 1 (Aggressive wins, 27 moves).** The Aggressive agent lost a rook
  (14...Qxh1) but kept attacking the exposed black king and mated with 27.Qc4#.
- **Game 2 (Defensive wins, 75 moves).** The longest decisive game: a slow
  queen-and-rook grind ending in Qh8#.
- **Game 3 (Defensive wins, 20 moves).** The shortest game and the clearest case
  of the aggressive style backfiring. The Aggressive queen left home on move 2
  (2.Qa4) and collected pawns on a7 and b7, leaving the a1 and b1 rooks and the
  king exposed. The Defensive queen and rook took on b2, a1 and b1 before mating
  with 20...Qc3#.
- **Game 4 (Aggressive wins, 36 moves).** Won with Black against 1.Nf3,
  finishing with Rxf1#.
- **Game 5 (Aggressive wins, 58 moves).** The queen won pawns early (5.Qxg5) and
  kept checking the black king until the final Rd1#.
- **Game 6 (draw, 108 moves).** The Defensive agent could not convert a long
  queen endgame. The Aggressive queen delivered an almost unbroken run of checks
  (moves 81-106) until the queens were traded (107.Qxb3 axb3 108.Kxb3), leaving
  only the two kings.

## 3. Stockfish analysis

Every move was re-evaluated with Stockfish 16 at depth 14. The **centipawn loss
(CPL)** of a move is how much worse it was than Stockfish's best move (0 = best
move). Moves are classed as inaccuracy (CPL 50-99), mistake (100-299) or blunder
(300+). Evaluations are capped at +/-1000 cp.

| Measure | Aggressive | Defensive |
|---|:-:|:-:|
| Moves graded | 322 | 322 |
| Average CPL | 60.0 | 63.6 |
| Median CPL | 10.0 | 10.0 |
| Average CPL, moves 1-10 | 66.7 | 92.3 |
| Average CPL, move 11 onwards | 58.5 | 57.0 |
| Stockfish's best move played | 39.1% | 34.5% |
| Inaccuracies | 40 | 41 |
| Mistakes | 52 | 57 |
| Blunders | 14 | 13 |

Average CPL per game (lower is more accurate):

| # | Aggressive | Defensive | Result |
|:-:|:-:|:-:|:-:|
| 1 | 58.3 | 98.1 | Aggressive won |
| 2 | 67.3 | 57.1 | Defensive won |
| 3 | 146.5 | 95.5 | Defensive won |
| 4 | 46.4 | 71.2 | Aggressive won |
| 5 | 44.3 | 59.6 | Aggressive won |
| 6 | 52.3 | 53.4 | Draw |

- **Overall accuracy is very close.** The gap in average CPL (60.0 vs 63.6) is
  small, and the median is identical.
- **The opening is the one clear difference.** The Aggressive agent lost 66.7 cp
  per move in moves 1-10 against 92.3 for the Defensive agent, which has no book.
  After move 10 the two are level (58.5 vs 57.0).
- **In all five decisive games the winner had the lower average CPL.** The
  analysis agrees with the scoreline, and the draw (game 6) is the only game
  where the two averages are almost equal.
- **Game 3 is the Aggressive agent's worst game by far** (146.5 average CPL, four
  blunders), including 10.Bd2 and 11.d5, where Stockfish preferred 10.Nc3 and
  11.Nc3.

## 4. How the strategies showed up in play

Statistics over all 322 moves each agent made:

| Measure | Aggressive | Defensive |
|---|:-:|:-:|
| Captures | 67 (21%) | 58 (18%) |
| Checks given | 66 | 73 |
| Pawn moves | 69 (21%) | 41 (13%) |
| Castled | 0 of 6 games | 3 of 6 games |
| Queen moves | 105 (33%) | 109 (34%) |
| King moves | 86 (27%) | 72 (22%) |

**Where the strategies clearly differ**

- **Pawn advances.** The Aggressive evaluation pays a growing bonus for advanced
  pawns, and that agent made noticeably more pawn moves (21% vs 13%).
- **Castling and king safety.** The Defensive evaluation rewards a castled king
  and an intact pawn shield, and that agent castled in three of six games. The
  Aggressive agent never castled: its evaluation has no castling or shelter term
  and its book lines never reached a castling move.
- **Captures.** The Aggressive agent captured more often, in line with an
  evaluation that rewards attacking enemy pieces and the enemy king zone.

**Where they look alike**

Both agents moved their queen about a third of the time. At depth 3 both are
drawn to early queen captures. The Defensive agent is not passive: its
piece-safety and loss-aversion terms show up mainly in how it avoids hanging
material and answers threats, not in a refusal to attack.

## 5. Analysis

1. **The aggressive evaluation produces sharper, riskier games.** The two
   shortest games (3 and 1) were both decided by king attacks, one for each side.
   The Aggressive agent will give up material or leave pieces undeveloped for the
   initiative. At depth 3 that works when the attack lands (games 1, 4, 5) and
   fails when the search cannot see the counter-punch (game 3).
2. **The defensive evaluation punishes overreach and converts patiently.** Its
   wins came from exploiting exposed pieces (game 3) and a long, controlled grind
   (game 2). Its king-safety, pawn-structure and piece-safety terms mean it
   rarely drops material for free, but it has no matching drive to finish an
   attack, which is why game 6 was drawn despite long pressure.
3. **Search depth was equal, so the result reflects the evaluation functions.**
   Both agents use the same engine at depth 3 and neither can see past three
   plies, so both can misjudge long capture sequences.
4. **The scoreline is not conclusive.** 3.5-2.5 is a one-point margin over six
   games, and an earlier unseeded run of the same match finished 3-3. The styles
   are genuinely different and roughly evenly matched at depth 3, but the data
   cannot show that one is stronger.

## 6. Limitation

- **Search.** A quiescence search reduces the horizon-effect blunders seen in
  game 3.

## 8. Reproducing the match

Earlier standalone harness (used for the results above):

```bash
python run_match.py --games 6 --depth 3 --seed 3220
python stockfish_grade.py --stockfish /path/to/stockfish --depth 14
```

The raw logs for the results above are `games.csv`, `moves.txt`, `games.pgn`,
`move_grades.csv`, `game_grades.csv` and `agent_summary.csv`.
