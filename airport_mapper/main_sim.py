#  deque for FIFO queue, used for BFS
#  defaultdict for grouping aircraft by requested node
import argparse
import itertools
import json
import os
import sys

import matplotlib.pyplot as plt

from airport_mapper.graph import (build_weighted_graph, compress_graph,
                                  draw_graph, exclusive_nodes, graph,
                                  node_types, plot_route)
from airport_mapper.models import Aircraft, Node
from airport_mapper.planning import collect_proposals, dijkstra_path
from airport_mapper.polyline_to_graph import haversine_m
from airport_mapper.rules import (block_reason, commit_moves, is_blocked,
                                  resolve_conflicts)
from airport_mapper.scenarios import SCENARIOS

# Load node positions from graph file
HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "jfk_graph_labeled.json"), "r") as f:
    graph_data = json.load(f)
    node_pos = graph_data.get("node_positions", {})

weighted_graph = build_weighted_graph(graph, node_pos)
compressed_graph = compress_graph(weighted_graph, node_types)


def loc(ac):
    return "AIRBORNE" if ac.removed else ac.current.name


def build_nodes():
    return {name: Node(name, exclusive=(name in exclusive_nodes)) for name in graph}


def run_scenario(
    scenario,
    max_steps=200,
):
    aircraft_list = []
    nodes = build_nodes()

    for spec in scenario:
        start = spec["start"]
        goal = spec["goal"]

        # path = bfs_path(graph, start, goal)
        path = dijkstra_path(compressed_graph, start, goal)
        if path is None:
            raise ValueError(
                f"No path for {spec['aircraft_id']} from {start} to {goal}"
            )

        ac = Aircraft(spec["aircraft_id"], None, None, [nodes[n] for n in path])

        ac.path_index = 0
        ac.current = ac.path[0]
        ac.goal = ac.path[-1]
        ac.current.occupied_by = ac.id

        aircraft_list.append(ac)

    no_progress = 0
    deadlock = False

    history = {
        "positions": {ac.id: [] for ac in aircraft_list},
        "wait_ticks": {ac.id: [] for ac in aircraft_list},
        "events": [],
    }

    for t in range(max_steps):
        for ac in aircraft_list:
            if ac.done and not ac.removed:
                ac.current.occupied_by = None
                ac.removed = True

        proposals = collect_proposals(aircraft_list)
        approved = resolve_conflicts(proposals)

        for ac in aircraft_list:
            if ac.removed or ac.done:
                ac.wait_ticks = 0
                continue

            if ac.propose_next() is None:
                ac.wait_ticks = 0
                continue

            if ac.id in approved:
                ac.wait_ticks = 0
            else:
                ac.wait_ticks += 1

        moved = commit_moves(proposals, approved)

        event = {
            "t": t,
            "moved": [],
            "blocked": {},
        }

        for ac in aircraft_list:
            history["positions"][ac.id].append(loc(ac))
            history["wait_ticks"][ac.id].append(ac.wait_ticks)

            if ac.id in approved:
                event["moved"].append(ac.id)
            elif is_blocked(ac, approved, aircraft_list):
                reason = block_reason(ac, approved)
                event["blocked"][ac.id] = reason

            if not ac.done and ac.current is ac.goal:
                ac.done = True

        if event["moved"] or event["blocked"]:
            history["events"].append(event)

        if moved:
            no_progress = 0
        else:
            no_progress += 1
            if no_progress >= 3:
                deadlock = True
                break

        if all(ac.removed for ac in aircraft_list):
            break

    print(f"Scenario completed in {t} steps. Deadlock: {deadlock}")
    # for ac in aircraft_list:
    #     print(f'{ac.id}: removed={ac.removed}, done={ac.done}, current={loc(ac)}')

    return {
        "aircraft": aircraft_list,
        "deadlock": deadlock,
        "steps": t,
        "history": history,
    }


def compute_metrics(result):
    history = result["history"]
    metrics = {
        "deadlock": result["deadlock"],
        "steps": result["steps"],
        "aircraft": {},
    }

    for a_id, positions in history["positions"].items():
        waits = history["wait_ticks"][a_id]

        time_to_airborne = next(
            (t for t, p in enumerate(positions) if p == "AIRBORNE"), None
        )

        distance_m = round(get_distance_travelled(positions, node_pos), 1)

        metrics["aircraft"][a_id] = {
            "time_to_airborne": time_to_airborne,
            "total_blocked_ticks": sum(1 for w in waits if w > 0),
            "max_wait_ticks": max(waits) if waits else 0,
            "distance_travelled_m": f"{distance_m} m",
        }

    return metrics


def print_events(history, limit=None):
    events = history["events"][:limit]
    for e in events:
        moved = ",".join(e["moved"])
        blocked = ", ".join(f"{k}:{v}" for k, v in e["blocked"].items())
        print(f"t={e['t']:>3} | moved=[{moved}] | blocked=[{blocked}]")


def print_timeline(history, aircraft_id):
    for t, pos in enumerate(history["positions"][aircraft_id]):
        print(f"t={t:>3}: {aircraft_id} at {pos}")


def plot_wait_ticks(history):
    ticks = range(len(next(iter(history["wait_ticks"].values()))))

    for ac_id, wait_list in history["wait_ticks"].items():
        plt.plot(ticks, wait_list, label=ac_id)

    plt.xlabel("Time Step")
    plt.ylabel("Wait Ticks")
    plt.legend()
    plt.show()


# draw_graph(graph)


def print_aircraft_timelines(aircraft):
    for ac in aircraft:
        print_timeline(result["history"], ac)
        print("\n")


def get_distance_travelled(path, node_pos):
    total_m = 0.0
    for a, b in zip(path, path[1:]):
        if a == "AIRBORNE" or b == "AIRBORNE":
            break
        total_m += haversine_m(node_pos[a], node_pos[b])

    return total_m


DEFAULT_COLOURS = [
    'red', 'orange', 'purple', 'blue', 'green',
    'magenta', 'brown', 'teal', 'olive', 'navy',
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog='airport_mapper',
        description='JFK airport surface movement simulator.',
    )
    parser.add_argument(
        '--scenario', '-s',
        default='three_departures',
        help="scenario key from scenarios.py (default: 'three_departures')",
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='list available scenarios and exit',
    )
    parser.add_argument(
        '--max-steps',
        type=int,
        default=200,
        help='maximum simulation ticks before forcing termination (default: 200)',
    )
    parser.add_argument(
        '--no-plot',
        action='store_true',
        help='run headless without showing the matplotlib window',
    )
    parser.add_argument(
        '--timeline',
        metavar='AIRCRAFT_ID',
        help='print a per-tick timeline for one aircraft (e.g. A1)',
    )
    parser.add_argument(
        '--animate',
        action='store_true',
        help='play an animation of the simulation instead of the static plot',
    )
    parser.add_argument(
        '--save-gif',
        metavar='PATH',
        help='save the animation to the given .gif path (implies --animate)',
    )
    parser.add_argument(
        '--fps',
        type=int,
        default=8,
        help='animation frames per second (default: 8)',
    )
    parser.add_argument(
        '--sub-frames',
        type=int,
        default=4,
        help='frames per simulation tick for smoother motion (default: 4)',
    )
    return parser.parse_args(argv)


def list_scenarios():
    print('available scenarios:')
    for name, spec in sorted(SCENARIOS.items()):
        ids = ', '.join(s['aircraft_id'] for s in spec)
        print(f'  {name:<22}  {len(spec)} aircraft  ({ids})')


def main(argv=None):
    args = parse_args(argv)

    if args.list:
        list_scenarios()
        return 0

    if args.scenario not in SCENARIOS:
        print(f"error: unknown scenario '{args.scenario}'", file=sys.stderr)
        print('run with --list to see available scenarios.', file=sys.stderr)
        return 2

    scenario = SCENARIOS[args.scenario]
    print(f"running scenario: {args.scenario} ({len(scenario)} aircraft)\n")

    result = run_scenario(scenario, max_steps=args.max_steps)

    if args.timeline:
        if args.timeline in result['history']['positions']:
            print_timeline(result['history'], args.timeline)
            print()
        else:
            print(
                f"warning: aircraft '{args.timeline}' not in scenario, "
                f'skipping timeline.',
                file=sys.stderr,
            )

    metrics = compute_metrics(result)
    print(metrics)

    if args.no_plot and not args.save_gif:
        return 0

    if args.animate or args.save_gif:
        from airport_mapper.animate import animate_simulation
        animate_simulation(
            result,
            scenario,
            node_pos,
            save_path=args.save_gif,
            fps=args.fps,
            sub_frames=args.sub_frames,
            title=f'scenario: {args.scenario}',
        )
        return 0

    draw_graph(graph, node_pos, node_types=node_types)

    colour_cycle = itertools.cycle(DEFAULT_COLOURS)
    colours = {spec['aircraft_id']: next(colour_cycle) for spec in scenario}

    for i, spec in enumerate(scenario):
        ac_id = spec['aircraft_id']
        path = dijkstra_path(compressed_graph, spec['start'], spec['goal'])
        if path is None:
            continue
        plot_route(
            path,
            node_pos,
            color=colours[ac_id],
            label=ac_id,
            offset_index=i,
            total=len(scenario),
        )

    plt.legend(loc='best', fontsize=8)
    plt.title(f'scenario: {args.scenario}')
    plt.show()
    return 0


if __name__ == '__main__':
    sys.exit(main())
