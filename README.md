# Airport Surface Movement Simulator

A discrete-time simulation of airport surface movement using a graph-based taxiway model.

Aircraft taxi along a predefined airport graph from start nodes (stands) to goal nodes (runway or other stands), subject to safety and fairness constraints. The project explores whether simple local rules can produce safe, deadlock-free surface movement without global scheduling.

This is a simulation and research exploration only. It is **not** intended for real-world deployment.

---

## Motivation

Modern aircraft can autoland reliably, but ground movement (taxiing) remains operationally complex and heavily dependent on human controllers and procedural separation.

This project investigates whether airport surface movement can be:
- modelled as a graph problem
- coordinated using local rules rather than global planning
- kept safe (collision-free) while guaranteeing progress and fairness

The focus is on reasoning, correctness, and failure modes rather than optimisation or real-time performance.

---

## Model Overview

- The airport surface is represented as an **undirected graph**
- Nodes represent:
  - stands
  - taxiway intersections
  - runway access points
  - the runway
- Edges represent taxiways


Each aircraft:
- computes a path to its goal using BFS
- proposes a next node each simulation tick
- optionally proposes a lookahead *corridor* of future nodes
- may be blocked due to:
  - exclusive node occupancy
  - corridor constraints (deadlock prevention)
  - priority rules (fairness)

The simulation advances in discrete time steps (“ticks”).

---

## Safety and Coordination Rules

Implemented rules include:

- **Exclusive nodes**  
  Certain nodes (intersections, runway access points, runway) may only be occupied by one aircraft at a time.

- **Corridor lookahead**  
  Aircraft may only enter a shared choke point if they can safely clear it, preventing deadlock.

- **Fair priority resolution**  
  When multiple aircraft request the same exclusive node, priority is given to the aircraft that has waited the longest, with a deterministic tie-break.

- **Deadlock detection**  
  If no aircraft makes progress for several consecutive ticks, the simulation terminates.

---

**Current Features**
- Graph-based airport surface model
- BFS path planning
- Exclusive node collision avoidance
- Corridor-based deadlock prevention
- Wait-time based priority (fairness)
- Deadlock detection and termination
- Debug output explaining blocking reasons
- Deterministic behaviour for identical scenarios

---

**Limitations**
- Taxiways are undirected and idealised
- Taxiway segments (edges) are not yet locked
- All movements take one tick (no timing or speed model)
- No sensor uncertainty or perception errors
- No real-world airport geometry

---

**Planned Work**
- Edge locking for single-lane taxiways
- Staggered aircraft spawn times
- Larger stress-test scenarios
- Visualisation and animation of movements
- Comparison of different priority policies

---

## Running the Simulation

Scenarios are defined in the ``` SCENARIO ``` list in the ``` map.py ``` file. Each scenario specifies:
- aircraft ID
- start node
- goal node

Example:
```bash
SCENARIO = [
    { 'aircraft_id': 'A1', 'start': 'S1', 'goal': 'RWY' },
    { 'aircraft_id': 'A2', 'start': 'S2', 'goal': 'RWY' },
]
```
---

### Requirements
- Python 3.10+

### Run
```bash
python map.py
```

### Author

George
