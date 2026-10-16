# /// script
# dependencies = []
# ///
# ─── How to run ───
# uv run tools/generate_ambient_audio.py [output-directory]
"""Reproduce ScreenBot's original CC0 ambience loops using Python and ffmpeg."""
from __future__ import annotations

import math
from pathlib import Path
import random
import struct
import subprocess
import sys
import wave

RATE = 22_050
DURATION = 8
LOOPS = ('rain', 'wind', 'waves', 'forest', 'crickets', 'city', 'space', 'thunder')


def sample(kind: str, index: int, previous: float, noise: float) -> float:
    """Synthesize one normalized mono sample for a named ambience loop."""
    time = index / RATE
    if kind == 'rain':
        return .16 * (noise * .48 + previous * .52) * (.78 + .22 * math.sin(time * math.tau * .13))
    if kind == 'wind':
        return .14 * (noise * .06 + previous * .94) * (.68 + .32 * math.sin(time * math.tau * .07))
    if kind == 'waves':
        return .2 * (noise * .32 + previous * .68) * (.15 + .85 * (.5 + .5 * math.sin(time * math.tau * .12)) ** 2)
    if kind == 'city':
        drone = .04 * math.sin(math.tau * 55 * time) + .025 * math.sin(math.tau * 82 * time)
        return drone + .08 * (noise * .08 + previous * .92)
    if kind == 'thunder':
        rain = .12 * (noise * .38 + previous * .62)
        envelope = max(0.0, math.sin(math.tau * time / DURATION)) ** 6
        rumble = math.sin(math.tau * (38 + 2 * math.sin(time * .9)) * time) * envelope * .11
        return rain + rumble
    if kind == 'space':
        fade = .5 + .5 * math.sin(math.tau * time / DURATION)
        return .028 * fade * (math.sin(math.tau * 48 * time) + .4 * math.sin(math.tau * 72 * time))
    base = .015 * (noise * .12 + previous * .88)
    if kind == 'forest':
        pulse = max(0.0, math.sin(math.tau * .61 * time)) ** 18
        phase = (time * 7) % 1
        return base + math.sin(math.tau * (1450 + 500 * phase) * time) * pulse * .055
    pulse = max(0.0, math.sin(math.tau * 4.8 * time)) ** 26
    return base + math.sin(math.tau * 3100 * time) * pulse * .028


def write_loop(kind: str, destination: Path, rng: random.Random) -> None:
    """Write a deterministic temporary PCM loop and encode it as compact Ogg."""
    temporary = destination.with_suffix('.wav')
    previous = 0.0
    frames = bytearray()
    for index in range(RATE * DURATION):
        previous = sample(kind, index, previous, rng.gauss(0.0, 1.0))
        frames.extend(struct.pack('<h', round(max(-1.0, min(1.0, previous)) * 32767)))
    with wave.open(str(temporary), 'wb') as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(frames)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(temporary),
                    '-c:a', 'libvorbis', '-q:a', '2', str(destination)], check=True)
    temporary.unlink()


def main() -> None:
    """Regenerate all seven project-owned audio loops."""
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('assets/audio')
    target.mkdir(parents=True, exist_ok=True)
    rng = random.Random(26026)
    for loop in LOOPS:
        write_loop(loop, target / f'{loop}.ogg', rng)


if __name__ == '__main__':
    main()
