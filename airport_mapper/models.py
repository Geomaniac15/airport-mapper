class Node:
    # represents a place in the airport
    def __init__(self, name, exclusive=False):
        self.name = name
        self.exclusive = exclusive  # only one aircraft may occupy this node at a time
        self.occupied_by = None  # aircraft id or None

    def is_free(self):
        return self.occupied_by is None


class Aircraft:
    def __init__(self, aircraft_id, start_node, goal_node, path, spawn_tick=0):
        self.id = aircraft_id
        self.current = start_node
        self.goal = goal_node
        self.path = path
        self.path_index = 0  # how far along the path it is
        self.waiting = False
        self.done = False
        self.removed = False
        self.lookahead = 3  # how many nodes ahead to consider for corridor proposal
        self.wait_ticks = 0  # how many consecutive ticks the aircraft has been waiting
        # Staggered spawn support. Aircraft does not interact with the simulation
        # (no proposals, no node occupation) until `spawned` is True.
        self.spawn_tick = spawn_tick
        self.spawned = False
        self.spawned_at = None  # the simulation tick when spawn actually happened

    def step(self):
        if not self.spawned:
            return  # not yet in the simulation
        if self.path_index + 1 >= len(self.path):
            return  # already at destination

        next_node = self.path[self.path_index + 1]

        if next_node.exclusive and not next_node.is_free():
            self.waiting = True
            return

        # Move
        self.current.occupied_by = None
        next_node.occupied_by = self.id
        self.current = next_node
        self.path_index += 1
        self.waiting = False

    def propose_next(self):
        # propose what node the aircraft wants next
        if not self.spawned or self.done:
            return None

        i = self.path_index + 1
        if i >= len(self.path):
            return None  # no move, already at goal

        return self.path[i]

    def propose_corridor(self, k=None):
        # return a list of nodes representing the corridor the aircraft wants to reserve

        if not self.spawned or self.done or self.removed:
            return None

        if k is None:
            k = self.lookahead

        # next nodes along the path (skips current node)
        start = self.path_index + 1
        end = min(len(self.path), start + k)

        corridor = self.path[start:end]
        return corridor if corridor else None
