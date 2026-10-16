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
    """Choose a bounded cadence for Smooth, Balanced, or Battery saver."""
    if mode == 'smooth':
        fps = 30
    elif mode == 'battery-saver':
        fps = 10
    elif on_battery or elapsed_seconds >= 15 * 60:
        fps = 15
    else:
        fps = 30
    return round(1000 / fps)

def particle_count(total: int, effect_scale: float) -> int:
    """Apply an effect budget without mutating the stable random particle set."""
    if total <= 0:
        return 0
    return max(1, min(total, round(total * max(0.0, min(1.0, effect_scale)))))
