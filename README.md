# Airport Surface Movement Simulator

A discrete-time simulation of airport surface movement on real OpenStreetMap-derived taxiway graphs. Pick any airport by IATA code, run aircraft from stands to runways under safety and fairness rules, animate the result.

The project explores whether simple local rules can produce safe, deadlock-free surface movement without global scheduling. It is a research exploration only and is **not** intended for real-world deployment.

![Three aircraft taxiing across the JFK graph](demo.gif)

*Three departures from JFK stands to runway holds. Faint lines show planned routes; solid markers show live aircraft positions. A2 visibly waits two ticks behind A1 at a shared intersection before the priority resolver releases it.*

---

![Ten random departures across JFK](demo_stress.gif)

*10 random departures with staggered spawns. Half the aircraft get priority-blocked at intersections at some point but the run completes without deadlock.*

---

## Motivation

Modern aircraft can autoland reliably, but ground movement (taxiing) remains operationally complex and heavily dependent on human controllers and procedural separation.

This project investigates whether airport surface movement can be:

- modelled as a graph problem
- coordinated using local rules rather than global planning
- kept safe (collision-free) while guaranteeing progress and fairness

The focus is on reasoning, correctness, and failure modes rather than optimisation or real-time performance. A reproducible parameter sweep is included in `analysis/REPORT.md` that quantifies how the model degrades with traffic density.

---

## Model Overview

The airport surface is represented as an **undirected graph** built from OSM aeroway features. Nodes are stands, taxiway intersections, runway access (holding) points, and runway segments. Edges are taxiway, taxilane, runway, and apron segments.

Each aircraft:

- computes a path to its goal using Dijkstra over a haversine-weighted graph (planned on a compressed graph for speed, then expanded back to raw nodes so the simulator visits every real intersection)
- proposes a next node each simulation tick
- proposes a 3-node lookahead corridor for deadlock prevention
- has an optional `spawn_tick` so a scenario can stagger entries
- may be blocked due to exclusive node occupancy, corridor constraints, or priority loss

The simulation advances in discrete time steps ("ticks").

---

## Safety and Coordination Rules

- **Exclusive nodes.** Intersections, runway access points, and runways may only be occupied by one aircraft at a time. Stands are non-exclusive.
- **Corridor lookahead.** Aircraft may only enter a shared choke point if they can safely clear it, preventing deadlock at intersections.
- **Fair priority resolution.** When multiple aircraft request the same exclusive node, priority goes to the aircraft that has waited the longest, with a deterministic tie-break.
- **Two-phase commit.** Approved movers all vacate their current node before any of them occupy their next node, so swap-positions cases resolve cleanly.
- **Deadlock detection.** If no spawned, active aircraft makes progress for three consecutive ticks, the simulation terminates.

---

**Current Features**

- Multi-airport support: pick any IATA code, fetch and build the graph on demand
- Real OSM data via the Overpass API
- Dijkstra path planning, weighted by haversine edge length
- Path expansion: planning happens on a compressed graph for speed, then paths are expanded back to raw OSM nodes so each tick is one real edge
- Apron-island bridging: stand clusters disconnected from the main taxiway network in OSM are auto-connected via short synthetic edges
- Random scenario generation (departures, arrivals, mixed) with reachability validation
- Staggered spawn times (uniform random in `[0, stagger]`)
- Animated playback with sub-tick interpolation, exportable as GIF
- Connectivity inspector (`--info`) for any loaded airport
- Comprehensive CLI with reproducible RNG seeding
- 64-test pytest suite with documented edge cases (`tests/test_random_scenarios.py`)

---

**Limitations**

- Taxiways are undirected and edges are not yet locked, so two aircraft can pass each other on a single-lane taxiway in the model
- All movements take one tick (no per-aircraft speed model; tick count scales with edge count, not real-world time)
- No sensor uncertainty or perception errors
- Aircraft commit to a path at spawn time; no en-route re-planning
- Some airports have sparse OSM tagging that the bridging pass cannot fully recover from

---

**Planned Work**

- Edge locking for single-lane taxiways (the dominant remaining failure mode at high traffic, per `analysis/REPORT.md`)
- Conflict-Based Search planner for an A/B comparison against local rules
- Speed/time model so ticks correspond to wall-clock seconds
- Pushback/clearance protocol delaying spawn until the route ahead is clear
- Web-based interactive viewer with Leaflet over a real map

---

## Running the Simulation

### Requirements

- Python 3.10+
- `matplotlib` (plots, animation)
- `pillow` (GIF export)
- `requests` (only needed when fetching new airport data)
- `pytest` (only needed for tests)

```bash
pip install matplotlib pillow requests pytest
```

### Quick start (JFK)

```bash
# list named scenarios
python -m airport_mapper.main_sim --list

# default scenario, static plot
python -m airport_mapper.main_sim

# animate a hand-written scenario
python -m airport_mapper.main_sim --scenario three_departures --animate

# random departures, save as GIF
python -m airport_mapper.main_sim --random-departures 10 --seed 7 --save-gif demo.gif

# 10 aircraft with staggered entries over 30 ticks
python -m airport_mapper.main_sim --random-departures 10 --stagger 30 --animate

# headless run with per-tick timeline for one aircraft
python -m airport_mapper.main_sim --random-departures 5 --no-plot --timeline A1

# inspect connectivity of the loaded airport
python -m airport_mapper.main_sim --info
```

Full flag reference: `python -m airport_mapper.main_sim --help`

### Multi-airport

Airport graphs live in `airport_mapper/airports/`, one JSON per IATA code. JFK ships with the project; other airports are fetched and built on demand from OpenStreetMap via the Overpass API.

```bash
# fetch + build LHR (one-time, hits Overpass)
python -m airport_mapper.polyline_to_graph --iata LHR

# inspect connectivity (number of components, stands and runways reachable)
python -m airport_mapper.main_sim --iata LHR --info

# run a stress scenario at LHR
python -m airport_mapper.main_sim --iata LHR --random-departures 10 --animate
```

`--iata` accepts any airport code with `aeroway=aerodrome` and an `iata` tag in OSM. The named scenarios in `scenarios.py` use JFK-specific node IDs and only work for JFK; for other airports use `--random-departures`, `--random-arrivals`, or `--random-mixed`.

OSM data quality varies by airport. The build pipeline runs an automatic apron-island bridging pass that connects disconnected stand clusters to the main taxiway network via short synthetic edges (modelling apron-entry connectors that are physically present but sometimes missing from OSM). The `--info` command reports how many bridges were added and how many stands ended up in the operational component.

### Tests

```bash
python -m pytest tests/
```

### Analysis

A reproducible parameter sweep over aircraft count, stagger window, and seed lives in `analysis/`. See `analysis/REPORT.md` for findings.

```bash
python -m analysis.sweep         # writes sweep_results.json + sweep_summary.json
python -m analysis.plot_results  # writes sweep_plots.png
```

The 250-run sweep takes about 2.5 seconds.

### Rebuilding an airport graph

Airport graphs are versioned build artifacts. To regenerate one without re-fetching from Overpass (for example after changing the labelling logic):

```bash
python -m airport_mapper.polyline_to_graph --iata JFK --no-fetch
```

Importing the package never triggers a rebuild.

### Author

George
