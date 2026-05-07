#  deque for FIFO queue, used for BFS
#  defaultdict for grouping aircraft by requested node
import json
import os

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


if __name__ == "__main__":
    print("\n")
    result = run_scenario(SCENARIOS["three_departures"])
    # print_events(result['history'], limit=30)
    # print('\n')
    # print_timeline(result['history'], 'A1')
    aircraft_list = [ac.id for ac in result["aircraft"]]
    # print_aircraft_timelines(aircraft_list)
    print_timeline(result["history"], "A1")
    print("\n")
    metrics = compute_metrics(result)
    print(metrics)
    # plot_wait_ticks(result['history'])

    draw_graph(graph, node_pos, node_types=node_types)

    colours = {"A1": "red", "A2": "orange", "A3": "purple"}

    scenario = SCENARIOS["swap_positions"]
    for i, spec in enumerate(scenario):
        ac_id = spec["aircraft_id"]
        start = spec["start"]
        goal = spec["goal"]

        path = dijkstra_path(compressed_graph, start, goal)
        plot_route(
            path,
            node_pos,
            color=colours[ac_id],
            label=ac_id,
            offset_index=i,
            total=len(scenario),
        )

    plt.show()

    # for scenario_name in scenario_names:
    #     print(f"Running scenario: {scenario_name}")
    #     result = run_scenario(SCENARIOS[scenario_name])
    #     metrics = compute_metrics(result)
    #     # print(metrics)
    #     if 'A1' in [ac.id for ac in result['aircraft']]:
    #         print_timeline(result['history'], 'A1')
    #         print("\n")
    #     if 'A2' in [ac.id for ac in result['aircraft']]:
    #         print_timeline(result['history'], 'A2')
    #         print("\n")
    #     if 'A3' in [ac.id for ac in result['aircraft']]:
    #         print_timeline(result['history'], 'A3')
    #         print("\n")
