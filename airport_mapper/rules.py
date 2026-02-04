from collections import defaultdict

from airport_mapper.graph import graph, node_types
from airport_mapper.planning import corridor_is_clear

holding_to_runway = set()

for u, nbrs in graph.items():
    if node_types.get(u) != "H":
        continue
    for v in nbrs:
        if node_types.get(v) == "R":
            holding_to_runway.add((u, v))


def runway_is_occupied(aircraft):
    return any(
        (not ac.removed) and node_types.get(ac.current.name) == "R" for ac in aircraft
    )


def resolve_conflicts(proposals):
    # who is allowed to move
    node_requests = defaultdict(list)

    # group requests by node
    for ac, next_node, corridor in proposals.values():
        if corridor_is_clear(corridor):
            # eligible.append((ac, next_node))
            node_requests[next_node].append(ac)

        # # normal case: at least one aircraft eligible
        # if eligible:
        #     for ac, next_node in eligible:
        #         node_requests[next_node].append(ac)
        # else:
        #     # escape hatch: one aircraft can go
        #     # its next node must be free tho
        #     candidates = []
        #     for ac, next_node, _corridor in proposals.values():
        #         if (not next_node.exclusive) or next_node.is_free():
        #             candidates.append((ac, next_node))
        #     if candidates:
        #         ac, next_node = sorted(candidates, key=lambda x: x[0].id)[0]
        #         node_requests[next_node].append(ac)

    approved = set()
    chosen_moves = {}

    for node, requesters in node_requests.items():
        # block entry if already occupied
        # two aircraft cannot be on the runway at the same time
        if node.exclusive and not node.is_free():
            continue

        if not node.exclusive:
            # everyone can go
            for ac in requesters:
                approved.add(ac.id)
                chosen_moves[ac.id] = (ac, node)
        else:
            # aircraft with lowest id wins
            winner = sorted(
                requesters,
                key=lambda a: (
                    -a.wait_ticks,
                    a.id,
                ),  # prioritise longest waiting, then lowest id
            )[0]
            approved.add(winner.id)
            chosen_moves[winner.id] = (winner, node)

    vacated = {ac.current.name for ac_id, (ac, _next) in chosen_moves.items()}

    final_approved = set()
    for ac_id, (ac, next_node) in chosen_moves.items():
        # ensure no two aircraft move into same node
        if not next_node.exclusive:
            final_approved.add(ac_id)
            continue

        if next_node.is_free() or next_node.name in vacated:
            final_approved.add(ac_id)

    return final_approved


def commit_moves(proposals, approved):
    # execute moves

    # proposals: ac_id -> (ac, next_node, corridor)
    movers = []
    for ac_id, (ac, next_node, _corridor) in proposals.items():
        if ac_id in approved:
            movers.append((ac, next_node))

    if not movers:
        return False

    # phase 1: vacate current nodes (simultaneous departure)
    for ac, _next in movers:
        ac.current.occupied_by = None

    # phase 2: occupy next all next nodes (simultaneous arrival)
    for ac, next_node in movers:
        # safety check: if something else is already there
        # there is a bug in approval logic
        if next_node.exclusive and not next_node.is_free():
            raise RuntimeError(
                f"Conflict detected during move commit: "
                f"{ac.id} cannot move to occupied node {next_node.name}"
            )

        next_node.occupied_by = ac.id
        ac.current = next_node

        if ac.path_index >= len(ac.path):
            raise RuntimeError(f"{ac.id} tried to step beyond end of path")
        ac.path_index += 1

        # if ac.current is not ac.path[ac.path_index]:
        #     raise RuntimeError(
        #         f'{ac.id} mismatch after move commit: current={ac.current.name} '
        #         f'path_index={ac.path_index} expected={ac.path[ac.path_index].name}'
        #     )

        if ac.current.name == ac.goal:
            ac.done = True

    return True

    # moved = False
    # for ac_id, (ac, next_node, _corridor) in proposals.items():
    #     if ac_id not in approved:
    #         continue

    #     # move
    #     ac.current.occupied_by = None
    #     next_node.occupied_by = ac.id
    #     ac.current = next_node
    #     ac.path_index += 1

    #     moved = True

    #     if ac.current.name == 'RWY':
    #         ac.done = True

    # return moved


def is_blocked(ac, approved):
    cur = ac.current.name
    # use propose_next() API from Aircraft model
    next_node = ac.propose_next()
    nxt = next_node.name if next_node else None

    # holding position clearance rule
    if nxt is not None and (cur, nxt) in holding_to_runway:
        if runway_is_occupied(ac.sim.aircraft_list):
            return True

    if ac.removed or ac.done:
        return False
    if ac.propose_next() is None:
        return False
    return ac.id not in approved


def block_reason(ac, appproved, lookahead=3):
    if ac.removed or ac.done:
        return "DONE"
    next = ac.propose_next()
    if next is None:
        return "NO_MOVE"
    if ac.id in appproved:
        return "MOVED"
    if next.exclusive and not next.is_free():
        return f"NEXT_OCCUPIED({next.name})"
    corridor = ac.propose_corridor(lookahead)
    if corridor and any(n.exclusive and not n.is_free() for n in corridor):
        return "CORRIDOR_BLOCKED"
    return "PRIORITY_BLOCKED"
