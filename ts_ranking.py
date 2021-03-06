#!/usr/bin/env python3

import argparse
import json
import math
import sys

import trueskill
import utility

def ts_ratings(game_results):
    players = {p: trueskill.Rating() for p in
            set(p for game in game_results for p in game)}
    for gnum, game in enumerate(game_results, start=1):
        game = list(game.items())
        ratings = [{p[0]: players[p[0]]} for p in game]
        ranks = [(p[1],) for p in game]
        ratings = trueskill.rate(ratings, ranks)
        for group in ratings:
            for name, rating in group.items():
                players[name] = rating
        if gnum % 10000 == 0:
            print("\rRated %d games" % (gnum,), end="")
    if gnum >= 10000:
        print("\r", end="")
    print("Rated %d games" % (gnum,))
    return players

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser("Create TrueSkill ratings from game data.")
    parser.add_argument("game_files", nargs="+",
            help="Json files containing game data.")
    parser.add_argument("-d", "--display", type=int, default=40,
            help="Limit display of rating to top N (0 for all)")
    parser.add_argument("-n", "--num-games", type=int,
            help="Limit the number of games used (positive for first, negative for last")
    parser.add_argument("--remove-suspect", action="store_true",
            help="Filter out suspect games based on workerID.")
    parser.add_argument("--no-error", action="store_true",
            help="Filter out games that had bot errors.")
    parser.add_argument("-o", "--out-file",
            help="If specified will write the full ratings to given filename")
    parser.add_argument("-t", "--tau", type=float,
            help="Set trueskill tau.")
    parser.add_argument("--draw-prob", type=float,
            help="Set trueskill draw probability.")
    config = parser.parse_args(args)

    games = utility.load_games(config.game_files)
    if config.no_error:
        games = utility.filter_error_games(games)
        print("Filtered out error games, leaving %d" % (len(games),))
    if config.remove_suspect:
        start_num = len(games)
        games = utility.filter_suspect_games(games)
        print("Filtered out %d suspect games, leaving %d" % (
            start_num - len(games), len(games)))

    game_results = [{"%s (%s)" % (u['username'], u['userID']): int(u['rank'])
        for u in g['users']}
            for g in games]
    if config.num_games:
        if config.num_games > 0:
            game_results = game_results[:config.num_games]
            print("Using first %d games." % (len(game_results),))
        else:
            game_results = game_results[config.num_games:]
            print("Using last %d games." % (len(game_results),))

    if config.tau is not None:
        trueskill.global_env().tau = config.tau
        print("Using tau %g" % (trueskill.global_env().tau,))
    if config.draw_prob is not None:
        trueskill.global_env().draw_probability = config.draw_prob
        print("Using draw probability %g" % (
            trueskill.global_env().draw_probability,))

    ratings = ts_ratings(game_results)

    ratings = sorted(ratings.items(), key=lambda x: -(x[1].mu - (x[1].sigma*3)))

    if config.out_file:
        with open(config.out_file, 'w') as out:
            for rank, (player, rating) in enumerate(ratings, start=1):
                score = rating.mu - (rating.sigma * 3)
                out.write('%d,%s,%f,%r,%r\n' % (rank, player, score,
                    rating.mu, rating.sigma))

    if config.display > 0:
        ratings = ratings[:config.display]

    rwidth = math.floor(math.log10(len(ratings))) + 1
    pwidth = max(len(r[0]) for r in ratings)
    for rank, (player, rating) in enumerate(ratings, start=1):
        score = rating.mu - (rating.sigma * 3)
        print("%*d: %*s %.2f (%.2f, %.2f)" % (rwidth, rank, pwidth, player,
            score, rating.mu, rating.sigma))

if __name__ == "__main__":
    main()
