'''Parameter sweep: aircraft count x stagger x seed.

For each cell we record total steps, deadlock outcome, mean taxi duration,
mean blocked ticks, and per-aircraft maxima. Results are saved as JSON for
downstream plotting.

Usage:
    python -m analysis.sweep
'''

import json
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

from airport_mapper.main_sim import compute_metrics, run_scenario
from airport_mapper.scenarios import random_departures

# Sweep grid
N_VALUES = [5, 10, 15, 20, 25]
STAGGER_VALUES = [0, 5, 10, 20, 40]
SEEDS = list(range(1, 11))  # 10 seeds per (n, stagger) cell -> 250 runs


def _safe_mean(xs):
    xs = [x for x in xs if x is not None]
    return mean(xs) if xs else None


def run_one(n, stagger, seed, max_steps=2000):
    'Run a single simulation and return a flat dict of metrics.'
    scenario = random_departures(n, seed=seed, stagger=stagger)
    t0 = time.perf_counter()
    result = run_scenario(scenario, max_steps=max_steps)
    elapsed = time.perf_counter() - t0
    metrics = compute_metrics(result)

    per_ac = list(metrics['aircraft'].values())
    total_blocked = sum(m['total_blocked_ticks'] for m in per_ac)
    completed = sum(1 for m in per_ac if m['time_to_airborne'] is not None)

    return {
        'n': n,
        'stagger': stagger,
        'seed': seed,
        'deadlock': bool(metrics['deadlock']),
        'steps': int(metrics['steps']),
        'wallclock_s': round(elapsed, 4),
        'completed_aircraft': completed,
        'completion_rate': completed / n,
        'total_blocked_ticks': total_blocked,
        'mean_blocked_per_ac': total_blocked / n,
        'mean_taxi_duration': _safe_mean(m['taxi_duration'] for m in per_ac),
        'mean_max_wait': _safe_mean(m['max_wait_ticks'] for m in per_ac),
        'max_wait_seen': max(
            (m['max_wait_ticks'] for m in per_ac), default=0,
        ),
    }


def aggregate(results):
    'Aggregate per-cell statistics across seeds.'
    cells = defaultdict(list)
    for r in results:
        cells[(r['n'], r['stagger'])].append(r)

    summary = []
    for (n, stagger), rs in sorted(cells.items()):
        deadlocks = sum(1 for r in rs if r['deadlock'])
        completed_rs = [r for r in rs if not r['deadlock']]

        steps_completed = [r['steps'] for r in completed_rs]
        blocked_completed = [r['mean_blocked_per_ac'] for r in completed_rs]
        taxi_completed = [
            r['mean_taxi_duration'] for r in completed_rs
            if r['mean_taxi_duration'] is not None
        ]

        summary.append({
            'n': n,
            'stagger': stagger,
            'runs': len(rs),
            'deadlock_rate': deadlocks / len(rs),
            'mean_steps_completed': (
                round(mean(steps_completed), 2) if steps_completed else None
            ),
            'std_steps_completed': (
                round(stdev(steps_completed), 2)
                if len(steps_completed) > 1 else 0.0
            ),
            'mean_blocked_per_ac': (
                round(mean(blocked_completed), 3) if blocked_completed else None
            ),
            'mean_taxi_duration': (
                round(mean(taxi_completed), 2) if taxi_completed else None
            ),
        })
    return summary


def main():
    here = Path(__file__).parent
    here.mkdir(exist_ok=True)

    results = []
    total = len(N_VALUES) * len(STAGGER_VALUES) * len(SEEDS)
    i = 0
    overall_start = time.perf_counter()

    print(f'sweeping {total} runs '
          f'(n in {N_VALUES}, stagger in {STAGGER_VALUES}, '
          f'{len(SEEDS)} seeds each)\n')

    for n in N_VALUES:
        for stagger in STAGGER_VALUES:
            for seed in SEEDS:
                i += 1
                r = run_one(n, stagger, seed)
                results.append(r)
                marker = 'X' if r['deadlock'] else '.'
                if i % 10 == 0 or i == total:
                    print(f'  [{i:>3}/{total}] '
                          f'n={n:>2} stagger={stagger:>2} seed={seed:>2}: '
                          f"steps={r['steps']:>3} {marker}")

    overall = time.perf_counter() - overall_start

    raw_path = here / 'sweep_results.json'
    raw_path.write_text(json.dumps(results, indent=2))
    print(f'\nwrote raw results: {raw_path} ({len(results)} rows)')

    summary = aggregate(results)
    summary_path = here / 'sweep_summary.json'
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f'wrote per-cell summary: {summary_path} ({len(summary)} cells)')

    print(f'\ntotal sweep wallclock: {overall:.1f}s '
          f'(mean {overall/total*1000:.0f} ms / run)')

    print('\nsummary table:')
    print(f"{'n':>3} {'stag':>5} {'dlrate':>7} {'mean_steps':>11} "
          f"{'mean_blk/ac':>12} {'mean_taxi':>10}")
    for row in summary:
        dl = f'{row["deadlock_rate"]:.0%}'
        ms = (
            f'{row["mean_steps_completed"]:.1f}'
            if row['mean_steps_completed'] is not None else '   -'
        )
        mb = (
            f'{row["mean_blocked_per_ac"]:.2f}'
            if row['mean_blocked_per_ac'] is not None else '   -'
        )
        mt = (
            f'{row["mean_taxi_duration"]:.1f}'
            if row['mean_taxi_duration'] is not None else '   -'
        )
        print(f"{row['n']:>3} {row['stagger']:>5} {dl:>7} {ms:>11} "
              f"{mb:>12} {mt:>10}")


if __name__ == '__main__':
    main()
