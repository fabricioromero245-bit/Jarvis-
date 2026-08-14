#!/usr/bin/env python3
"""Diagnostic: prints every key pynput detects, press and release.
Not part of the pipeline — just to debug hotkey detection issues.
Ctrl+C in this terminal to quit.
"""

from pynput import keyboard


def on_press(key):
    print(f"PRESS   {key!r}")


def on_release(key):
    print(f"RELEASE {key!r}")


print("Listening for all keys. Press some (both Ctrls, both Shifts, etc). Ctrl+C here to quit.")
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
