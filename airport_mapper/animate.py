import itertools

import matplotlib.animation as animation
import matplotlib.pyplot as plt

from airport_mapper.graph import (compress_graph, draw_graph, graph,
                                  node_types, plot_route)
from airport_mapper.planning import dijkstra_path

DEFAULT_COLOURS = [
    'red', 'orange', 'purple', 'blue', 'green',
    'magenta', 'brown', 'teal', 'olive', 'navy',
]


def _interpolate_positions(positions, node_pos, sub_frames):
    'Expand a per-tick position list into per-sub-frame (x, y) coords.'
    
    coords = []
    for tick, name in enumerate(positions):
        if name == 'AIRBORNE' or name not in node_pos:
            for _ in range(sub_frames):
                coords.append(None)
            continue

        x0, y0 = node_pos[name]

        # Look ahead to find the next concrete position to interpolate toward.
        next_xy = None
        for j in range(tick + 1, len(positions)):
            nxt = positions[j]
            if nxt != 'AIRBORNE' and nxt in node_pos:
                next_xy = node_pos[nxt]
                break

        if next_xy is None or sub_frames == 1:
            for _ in range(sub_frames):
                coords.append((x0, y0))
            continue

        x1, y1 = next_xy
        for k in range(sub_frames):
            alpha = k / sub_frames
            coords.append((x0 + (x1 - x0) * alpha, y0 + (y1 - y0) * alpha))

    return coords


def animate_simulation(
    result,
    scenario,
    node_pos,
    save_path=None,
    fps=8,
    sub_frames=4,
    title=None,
    figsize=(10, 10),
):
    '''Animate a finished simulation result.

    Parameters
    ----------
    result : dict
        The dict returned by run_scenario().
    scenario : list[dict]
        The scenario specification used to produce that result. Required so
        we can re-derive each aircraft's planned route to draw as a faint
        background line.
    node_pos : dict[str, (float, float)]
        Node id to (lon, lat) mapping.
    save_path : str or None
        If given, save to this path (use a .gif extension). Otherwise,
        the animation is shown interactively.
    fps : int
        Frames per second of the rendered animation.
    sub_frames : int
        Frames per simulation tick. Higher values give smoother motion at
        the cost of longer renders. 1 = discrete node-to-node hops.
    title : str or None
        Optional title to display above the plot.
    figsize : (float, float)
        Matplotlib figure size in inches.
    '''
    history = result['history']
    positions = history['positions']  # ac_id -> list[str]

    if not positions:
        raise ValueError('result has no aircraft positions to animate')

    fig, ax = plt.subplots(figsize=figsize)
    plt.sca(ax)

    # Background: the airport graph itself.
    draw_graph(graph, node_pos, node_types=node_types)

    # Faint planned route per aircraft, plus a coloured marker that will move.
    compressed = compress_graph(_weighted_graph(node_pos), node_types)

    colour_cycle = itertools.cycle(DEFAULT_COLOURS)
    colours = {spec['aircraft_id']: next(colour_cycle) for spec in scenario}

    for i, spec in enumerate(scenario):
        ac_id = spec['aircraft_id']
        path = dijkstra_path(compressed, spec['start'], spec['goal'])
        if path is None:
            continue
        plot_route(
            path,
            node_pos,
            color=colours[ac_id],
            label=ac_id,
            offset_index=i,
            total=len(scenario),
            lw=1.0,
        )

    # Per-aircraft marker. ax.plot returns a list; we keep the line2D handle.
    markers = {}
    for ac_id in positions:
        (m,) = ax.plot(
            [], [],
            marker='o',
            markersize=10,
            color=colours.get(ac_id, 'black'),
            markeredgecolor='black',
            markeredgewidth=0.8,
            linestyle='',
            zorder=20,
        )
        markers[ac_id] = m

    # Tick label (top-left) so the viewer can see the simulation clock.
    tick_text = ax.text(
        0.02, 0.98, '',
        transform=ax.transAxes,
        fontsize=11,
        verticalalignment='top',
        family='monospace',
        bbox={'facecolor': 'white', 'alpha': 0.8, 'edgecolor': 'none'},
    )

    if title:
        ax.set_title(title)
    ax.legend(loc='lower right', fontsize=9)

    # Pre-compute per-frame coords for every aircraft so update() is O(1).
    coords_per_ac = {
        ac_id: _interpolate_positions(positions[ac_id], node_pos, sub_frames)
        for ac_id in positions
    }
    total_frames = max(len(c) for c in coords_per_ac.values())

    def init():
        for m in markers.values():
            m.set_data([], [])
        tick_text.set_text('')
        return list(markers.values()) + [tick_text]

    def update(frame):
        tick = frame // sub_frames
        for ac_id, coords in coords_per_ac.items():
            if frame < len(coords) and coords[frame] is not None:
                x, y = coords[frame]
                markers[ac_id].set_data([x], [y])
            else:
                markers[ac_id].set_data([], [])
        tick_text.set_text(f't = {tick:>3}')
        return list(markers.values()) + [tick_text]

    ani = animation.FuncAnimation(
        fig,
        update,
        frames=total_frames,
        init_func=init,
        interval=1000 / fps,
        blit=True,
        repeat=False,
    )

    if save_path:
        writer = animation.PillowWriter(fps=fps)
        ani.save(save_path, writer=writer)
        plt.close(fig)
        print(f'saved animation to: {save_path}')
        return ani

    plt.show()
    return ani


def _weighted_graph(node_pos):
    '''Local helper to avoid circular import of build_weighted_graph.'''
    from airport_mapper.graph import build_weighted_graph
    return build_weighted_graph(graph, node_pos)
