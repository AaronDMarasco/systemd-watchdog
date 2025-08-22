#!/bin/env python3
"""systemd_watchdog example."""
import time

import systemd_watchdog

wd = systemd_watchdog.WatchDog()
if not wd.is_enabled:
    # Then it's probably not running is systemd with watchdog enabled
    msg = "Watchdog not enabled"
    raise Exception(msg)  # noqa: TRY002

# Report a status message
wd.status("Starting my service...")
time.sleep(3)

# Report that the program init is complete
wd.ready()
wd.status("Init is complete...")
wd.notify()
time.sleep(3)

# Compute time between notifications
timeout_half_sec = int(float(wd.timeout) / 2e6)  # Convert us->s and half that
wd.status("Sleeping and then notify x 3")
time.sleep(timeout_half_sec)
wd.notify()
time.sleep(timeout_half_sec)
wd.notify()
time.sleep(timeout_half_sec)
wd.notify()
wd.status("Spamming loop - should only see 2-3 notifications")
t = float(0)
while t <= 4 * timeout_half_sec:
    time.sleep(0.05)
    wd.ping()
    t += 0.05

# Report an error to the service manager
wd.notify_error("An irrecoverable error occured!")
# The service manager will probably kill the program here
time.sleep(3)
