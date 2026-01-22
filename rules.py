from collections import defaultdict
from planning import corridor_is_clear, collect_proposals

def resolve_conflicts(proposals):
    # who is allowed to move
    node_requests = defaultdict(list)

    # eligible to move?
    eligible = []

    # group requests by node
    for ac, next_node, corridor in proposals.values():
        if corridor_is_clear(corridor):
            eligible.append((ac, next_node))

        # normal case: at least one aircraft eligible
        if eligible:
            for ac, next_node in eligible:
                node_requests[next_node].append(ac)
        else:
            # escape hatch: one aircraft can go
            # its next node must be free tho
            candidates = []
            for ac, next_node, _corridor in proposals.values():
                if (not next_node.exclusive) or next_node.is_free():
                    candidates.append((ac, next_node))
            if candidates:
                ac, next_node = sorted(candidates, key=lambda x: x[0].id)[0]
                node_requests[next_node].append(ac)
    
    approved = set()

    for node, requesters in node_requests.items():
        # block entry if already occupied
        # two aircraft cannot be on the runway at the same time
        if node.exclusive and not node.is_free():
            continue
        
        if not node.exclusive:
            # everyone can go
            for ac in requesters:
                approved.add(ac.id)
        else:
            # aircraft with lowest id wins
            winner = sorted(
                requesters, 
                key=lambda a: (-a.wait_ticks, a.id)  # prioritise longest waiting, then lowest id
                )[0]
            approved.add(winner.id)
    
    return approved

def commit_moves(proposals, approved):
    # execute moves
    moved = False
    for ac_id, (ac, next_node, _corridor) in proposals.items():
        if ac_id not in approved:
            continue

        # move
        ac.current.occupied_by = None
        next_node.occupied_by = ac.id
        ac.current = next_node
        ac.path_index += 1 

        moved = True
        
        if ac.current.name == 'RWY':
            ac.done = True
    
    return moved

def is_blocked(ac, approved):
    if ac.removed or ac.done:
        return False
    if ac.propose_next() is None:
        return False
    return ac.id not in approved

def block_reason(ac, appproved, lookahead=3):
    if ac.removed or ac.done:
        return 'DONE'
    next = ac.propose_next()
    if next is None:
        return 'NO_MOVE'
    if ac.id in appproved:
        return 'MOVED'
    if next.exclusive and not next.is_free():
        return f'NEXT_OCCUPIED({next.name})'
    corridor = ac.propose_corridor(lookahead)
    if corridor and any(n.exclusive and not n.is_free() for n in corridor):
        return 'CORRIDOR_BLOCKED'
    return 'PRIORITY_BLOCKED'