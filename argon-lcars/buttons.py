"""
Reads the 4 Argon POD Display buttons directly (GPIO16/20/21/26, active
LOW thanks to the onboard 10K pull-ups per the wiring diagram in the
Argon POD manual).

Layout:
  Button 1 (GPIO16) -> previous screen (cycle left)
  Button 2 (GPIO20) -> dim
  Button 3 (GPIO21) -> brighten
  Button 4 (GPIO26) -> next screen (cycle right)

NOTE: this bypasses Argon's own argonpodd.service, which normally owns
these same GPIO lines to drive its config menu. The install script stops
and disables that service so there's no conflict -- see install.sh.
"""
import queue
import threading
import time

import config

try:
    import RPi.GPIO as GPIO
    HAVE_GPIO = True
except (ImportError, RuntimeError):
    HAVE_GPIO = False

EVT_PREV = "PREV"
EVT_NEXT = "NEXT"
EVT_DIM = "DIM"
EVT_BRIGHT = "BRIGHT"
EVT_ANY = "ANY"  # fired on every press, used to snooze red alert


class ButtonManager:
    def __init__(self):
        self.events = queue.Queue()
        self._stop = False
        self._pins = {
            config.BTN_1: EVT_PREV,
            config.BTN_2: EVT_DIM,
            config.BTN_3: EVT_BRIGHT,
            config.BTN_4: EVT_NEXT,
        }
        if HAVE_GPIO:
            GPIO.setmode(GPIO.BCM)
            for pin in self._pins:
                GPIO.setup(pin, GPIO.IN)

    def start(self):
        if HAVE_GPIO:
            threading.Thread(target=self._poll_loop, daemon=True).start()
        # When HAVE_GPIO is False (dev machine), main.py feeds keyboard
        # presses in via feed_key() from the main pygame event loop instead
        # of a second thread, since pygame's event queue isn't thread-safe.

    def stop(self):
        self._stop = True
        if HAVE_GPIO:
            GPIO.cleanup()

    def _poll_loop(self):
        pressed_since = {pin: None for pin in self._pins}
        last_state = {pin: 1 for pin in self._pins}  # idle high

        while not self._stop:
            for pin, evt in self._pins.items():
                state = GPIO.input(pin)  # 0 = pressed
                if state == 0 and last_state[pin] == 1:
                    pressed_since[pin] = time.time()
                elif state == 1 and last_state[pin] == 0:
                    held = time.time() - (pressed_since[pin] or time.time())
                    pressed_since[pin] = None
                    if held >= config.DEBOUNCE_SEC:
                        self.events.put(EVT_ANY)
                        self.events.put(evt)
                last_state[pin] = state
            time.sleep(0.02)

    def feed_key(self, pygame_key):
        """Dev-mode fallback (no GPIO): call from main.py's own event loop.
        Left/Right arrows cycle screens, Up/Down adjust brightness."""
        import pygame
        mapping = {
            pygame.K_LEFT: EVT_PREV,
            pygame.K_RIGHT: EVT_NEXT,
            pygame.K_DOWN: EVT_DIM,
            pygame.K_UP: EVT_BRIGHT,
        }
        if pygame_key in mapping:
            self.events.put(EVT_ANY)
            self.events.put(mapping[pygame_key])

    def poll(self):
        """Drain and return all pending events as a list."""
        out = []
        try:
            while True:
                out.append(self.events.get_nowait())
        except queue.Empty:
            pass
        return out
