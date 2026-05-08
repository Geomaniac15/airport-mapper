'''Plot the sweep results into a 2x2 figure.

Reads analysis/sweep_results.json (or sweep_summary.json) and writes a PNG.

Usage:
    python -m analysis.plot_results
'''

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt


HERE = Path(__file__).parent


def load_results():
    return json.loads((HERE / 'sweep_results.json').read_text())


def group(results, key):
    grouped = defaultdict(list)
    for r in results:
        grouped[r[key]].append(r)
    return grouped


def plot(results, out_path):
    n_values = sorted({r['n'] for r in results})
    stagger_values = sorted({r['stagger'] for r in results})

    # Aggregate per (n, stagger).
    cells = defaultdict(list)
    for r in results:
        cells[(r['n'], r['stagger'])].append(r)

    def stat(n, s, fn):
        return fn(cells[(n, s)])

    fig, axes = plt.subplots(2, 2, figsize=(13, 10))
    fig.suptitle(
        'JFK ground sim: aircraft count vs spawn stagger (10 seeds per cell)',
        fontsize=13, y=0.995,
    )

    # Panel 1: Deadlock rate
    ax = axes[0, 0]
    for s in stagger_values:
        rates = [
            mean(1.0 if r['deadlock'] else 0.0 for r in cells[(n, s)])
            for n in n_values
        ]
        ax.plot(n_values, rates, marker='o', label=f'stagger={s}')
    ax.set_xlabel('aircraft (n)')
    ax.set_ylabel('deadlock rate')
    ax.set_title('Deadlock rate vs n')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    # Panel 2: Mean steps to completion (excluding deadlocks)
    ax = axes[0, 1]
    for s in stagger_values:
        ys = []
        for n in n_values:
            completed = [r['steps'] for r in cells[(n, s)] if not r['deadlock']]
            ys.append(mean(completed) if completed else float('nan'))
        ax.plot(n_values, ys, marker='o', label=f'stagger={s}')
    ax.set_xlabel('aircraft (n)')
    ax.set_ylabel('mean ticks')
    ax.set_title('Time to drain (completed runs only)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    # Panel 3: Mean blocked ticks per aircraft (completed runs only)
    ax = axes[1, 0]
    for s in stagger_values:
        ys = []
        for n in n_values:
            completed = [
                r['mean_blocked_per_ac'] for r in cells[(n, s)]
                if not r['deadlock']
            ]
            ys.append(mean(completed) if completed else float('nan'))
        ax.plot(n_values, ys, marker='o', label=f'stagger={s}')
    ax.set_xlabel('aircraft (n)')
    ax.set_ylabel('mean blocked ticks per aircraft')
    ax.set_title('Intersection contention vs n')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    # Panel 4: Mean taxi duration (per-aircraft time in system)
    ax = axes[1, 1]
    for s in stagger_values:
        ys = []
        for n in n_values:
            completed = [
                r['mean_taxi_duration'] for r in cells[(n, s)]
                if not r['deadlock'] and r['mean_taxi_duration'] is not None
            ]
            ys.append(mean(completed) if completed else float('nan'))
        ax.plot(n_values, ys, marker='o', label=f'stagger={s}')
    ax.set_xlabel('aircraft (n)')
    ax.set_ylabel('mean taxi duration (ticks)')
    ax.set_title('Per-aircraft time in system')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f'wrote: {out_path}')


def main():
    results = load_results()
    plot(results, HERE / 'sweep_plots.png')


if __name__ == '__main__':
    main()
