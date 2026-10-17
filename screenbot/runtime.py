import math
import random
from pathlib import Path

def battery_powered(root: Path = Path('/sys/class/power_supply')) -> bool:
    """Return true when a battery exists and no online AC supply is detected."""
    try:
        supplies = [entry for entry in root.iterdir() if entry.is_dir()]
    except OSError:
        return False
    has_battery = False
    online_ac = False
    for supply in supplies:
        try:
            kind = (supply / 'type').read_text(encoding='ascii').strip().lower()
        except OSError:
            kind = ''
        if kind == 'battery':
            has_battery = True
        elif kind in ('mains', 'usb', 'usb_c'):
            try:
                online_ac = online_ac or (supply / 'online').read_text(encoding='ascii').strip() == '1'
            except OSError:
                pass
    return has_battery and not online_ac

def frame_interval_ms(mode: str, on_battery: bool, elapsed_seconds: float) -> int:
    if mode == 'smooth':
        fps = 30
    elif mode == 'extra-high':
        fps = 45
    elif mode == 'ultra':
        fps = 60
    elif mode == 'battery-saver':
        fps = 10
    elif on_battery or elapsed_seconds >= 15 * 60:
        fps = 15
    else:
        fps = 30
    return round(1000 / fps)

def quality_particle_count(base_count: int, mode: str) -> int:
    if base_count <= 0:
        return 0
    multiplier = {'extra-high': 1.25, 'ultra': 1.5}.get(mode, 1.0)
    return round(base_count * multiplier)

def scene_particle_sets(generator: random.Random, mode: str):
    return (
        [(generator.random(), generator.random(), generator.uniform(.65, 2.6), generator.random()*math.tau)
         for _ in range(quality_particle_count(110, mode))],
        [(generator.random(), generator.random(), generator.uniform(.8, 1.8), generator.random())
         for _ in range(quality_particle_count(150, mode))],
        [(generator.random(), generator.random(), generator.uniform(1.2, 4.0), generator.uniform(.5, 1.6), generator.random()*math.tau)
         for _ in range(quality_particle_count(110, mode))],
    )

def particle_count(total: int, effect_scale: float) -> int:
    """Apply an effect budget without mutating the stable random particle set."""
    if total <= 0:
        return 0
    return max(1, min(total, round(total * max(0.0, min(1.0, effect_scale)))))
