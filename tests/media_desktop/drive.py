# /// script
# requires-python = ">=3.11"
# dependencies = ["PyQt6"]
# ///
# Run only through tests/test_media_desktop.sh in its private virtual desktop.
"""Send real XTest input to a KCM shell on private Xwayland; capture its window."""
import configparser
import ctypes
import json
import os
from pathlib import Path
import subprocess
import time
import tempfile

from PyQt6.QtGui import QGuiApplication, QImage
from PyQt6.QtDBus import QDBus, QDBusConnection, QDBusMessage, QDBusUnixFileDescriptor
from PyQt6.QtTest import QTest

assert os.environ['XDG_RUNTIME_DIR'].startswith('/tmp/screenbot-media-')
assert os.environ['DBUS_SYSTEM_BUS_ADDRESS'] == os.environ['DBUS_SESSION_BUS_ADDRESS']
assert os.environ['SCREENBOT_MEDIA_SANDBOX'] == '1'
EVIDENCE = Path(os.environ['SCREENBOT_MEDIA_EVIDENCE'])
APP = QGuiApplication([])
X = ctypes.CDLL('libX11.so.6')
XT = ctypes.CDLL('libXtst.so.6')
X.XOpenDisplay.argtypes = [ctypes.c_char_p]
X.XOpenDisplay.restype = ctypes.c_void_p
DISPLAY = X.XOpenDisplay(None)
assert DISPLAY
X.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
X.XDefaultRootWindow.restype = ctypes.c_ulong
X.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)), ctypes.POINTER(ctypes.c_uint)]
X.XFetchName.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_char_p)]
X.XFree.argtypes = [ctypes.c_void_p]
X.XFlush.argtypes = [ctypes.c_void_p]
X.XSetInputFocus.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
X.XStringToKeysym.argtypes = [ctypes.c_char_p]
X.XStringToKeysym.restype = ctypes.c_ulong
X.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
X.XKeysymToKeycode.restype = ctypes.c_uint
XT.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
XT.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
XT.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]


def windows(parent: int) -> list[tuple[int, str]]:
    root, ancestor, count = ctypes.c_ulong(), ctypes.c_ulong(), ctypes.c_uint()
    children = ctypes.POINTER(ctypes.c_ulong)()
    if not X.XQueryTree(DISPLAY, parent, ctypes.byref(root), ctypes.byref(ancestor), ctypes.byref(children), ctypes.byref(count)):
        return []
    result = []
    for index in range(count.value):
        child = children[index]
        name = ctypes.c_char_p()
        if X.XFetchName(DISPLAY, child, ctypes.byref(name)) and name.value:
            result.append((child, name.value.decode(errors='replace')))
            X.XFree(name)
        result.extend(windows(child))
    if children:
        X.XFree(children)
    return result


def key(name: str, shift: bool = False) -> None:
    code = X.XKeysymToKeycode(DISPLAY, X.XStringToKeysym(name.encode()))
    modifier = X.XKeysymToKeycode(DISPLAY, X.XStringToKeysym(b'Shift_L'))
    if shift:
        XT.XTestFakeKeyEvent(DISPLAY, modifier, 1, 0)
    XT.XTestFakeKeyEvent(DISPLAY, code, 1, 0)
    XT.XTestFakeKeyEvent(DISPLAY, code, 0, 0)
    if shift:
        XT.XTestFakeKeyEvent(DISPLAY, modifier, 0, 0)
    X.XFlush(DISPLAY)


def capture(label: str, window: int) -> None:
    QTest.qWait(750)
    with tempfile.TemporaryFile() as pixels:
        message = QDBusMessage.createMethodCall('org.kde.KWin', '/org/kde/KWin/ScreenShot2',
                                               'org.kde.KWin.ScreenShot2', 'CaptureWorkspace')
        message.setArguments([{}, QDBusUnixFileDescriptor(pixels.fileno())])
        reply = QDBusConnection.sessionBus().call(message, QDBus.CallMode.Block, 5000)
        assert reply.type() == QDBusMessage.MessageType.ReplyMessage, reply.errorMessage()
        metadata = reply.arguments()[0]
        (EVIDENCE / f'{label}-capture.json').write_text(json.dumps(metadata))
        expected = metadata['stride'] * metadata['height']
        deadline = time.monotonic() + 5
        while os.fstat(pixels.fileno()).st_size < expected and time.monotonic() < deadline:
            QTest.qWait(20)
        pixels.seek(0)
        data = pixels.read()
        assert len(data) >= expected, (len(data), expected)
        image = QImage(data, metadata['width'], metadata['height'], metadata['stride'], QImage.Format(metadata['format']))
        assert image.save(str(EVIDENCE / f'{label}.png'))
    config = Path(os.environ['XDG_CONFIG_HOME']) / 'screenbot-screensaver.ini'
    contents = config.read_text() if config.exists() else '# Configuration not yet created\n'
    (EVIDENCE / f'{label}.ini').write_text(contents)
    (EVIDENCE / f'{label}-windows.json').write_text(json.dumps(windows(X.XDefaultRootWindow(DISPLAY))))


with (EVIDENCE / 'shell.log').open('w') as log:
    shell = subprocess.Popen(['kcmshell6', '--caption', 'ScreenBot Media QA', 'kcm_screenbot_screensaver', 'kcm_colors'], stdout=log, stderr=log)
    try:
        deadline = time.monotonic() + 20
        window = 0
        while time.monotonic() < deadline:
            candidates = windows(X.XDefaultRootWindow(DISPLAY))
            found = [handle for handle, title in candidates if 'ScreenBot' in title or 'Screensaver' in title]
            if found:
                window = found[0]
                break
            QTest.qWait(100)
        assert window, candidates
        X.XSetInputFocus(DISPLAY, window, 2, 0)
        X.XFlush(DISPLAY)
        XT.XTestFakeMotionEvent(DISPLAY, -1, 1250, 920, 0)
        X.XFlush(DISPLAY)
        QTest.qWait(1500)  # Let private Xwayland establish its EIS input connection.
        capture('initial', window)
        completed = 0
        deadline = time.monotonic() + 180
        done = False
        while time.monotonic() < deadline and not done:
            plan = EVIDENCE / 'actions.json'
            actions = json.loads(plan.read_text()) if plan.exists() else []
            for action in actions[completed:]:
                operation = action['operation']
                if operation == 'key':
                    key(action['key'], action.get('shift', False))
                elif operation == 'click':
                    XT.XTestFakeMotionEvent(DISPLAY, -1, action['x'], action['y'], 0)
                    XT.XTestFakeButtonEvent(DISPLAY, 1, 1, 0)
                    XT.XTestFakeButtonEvent(DISPLAY, 1, 0, 0)
                    X.XFlush(DISPLAY)
                elif operation == 'done':
                    done = True
                elif operation != 'capture':
                    raise AssertionError(operation)
                capture(action['label'], window)
                if 'expect_saved' in action:
                    settings = configparser.ConfigParser()
                    settings.read(EVIDENCE / f"{action['label']}.ini")
                    actual = settings.getboolean('Screensaver', 'now_playing_enabled', fallback=None)
                    assert actual == action['expect_saved'], (action['label'], actual)
                if action.get('expect_dialog'):
                    assert any(title == 'Apply Settings' for _, title in windows(X.XDefaultRootWindow(DISPLAY)))
                completed += 1
                (EVIDENCE / 'progress.json').write_text(json.dumps({'completed': completed, 'last': action['label']}))
            QTest.qWait(100)
        assert done, 'desktop action plan did not complete'
        off = QImage(str(EVIDENCE / 'off-applied.png')).copy(620, 555, 260, 32)
        repeated = QImage(str(EVIDENCE / 'off-settled-repeat.png')).copy(620, 555, 260, 32)
        assert off == repeated, 'Off switch did not settle'
        (EVIDENCE / 'shell-receipts.json').write_text(json.dumps({'passed': True, 'actions': completed, 'off_switch_stable': True, 'config_home': os.environ['XDG_CONFIG_HOME'], 'runtime': os.environ['XDG_RUNTIME_DIR'], 'display': os.environ['DISPLAY'], 'bus': os.environ['DBUS_SESSION_BUS_ADDRESS']}, indent=2))
    finally:
        shell.terminate()
        shell.wait(timeout=5)
