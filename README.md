# systemd_watchdog

![](https://img.shields.io/pypi/l/systemd-watchdog)
![](https://img.shields.io/pypi/v/systemd-watchdog.svg)
![](https://img.shields.io/travis/com/aarondmarasco/systemd-watchdog)
![](https://img.shields.io/pypi/wheel/systemd-watchdog.svg)
![](https://img.shields.io/pypi/pyversions/systemd-watchdog.svg)

sd_notify(3) and sd_watchdog_enabled(3) client functionality implemented in Python 3 for writing Python daemons

## Install
```
$ pip install systemd-watchdog
```
or
```
$ git clone ...
$ make install
```

## Usage
### `example.py`
```python
import systemd_watchdog
import time

wd = systemd_watchdog.WatchDog()
if not wd.is_enabled:
    # Then it's probably not running is systemd with watchdog enabled
    raise Exception("Watchdog not enabled")

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
while t <= 4*timeout_half_sec:
    time.sleep(0.05)
    wd.ping()
    t += 0.05

# Report an error to the service manager
wd.notify_error("An irrecoverable error occured!")
# The service manager will probably kill the program here
time.sleep(3)
```
### Quick Example
In one terminal:
`socat unix-recv:/tmp/tempo.sock -`

In another terminal:
`NOTIFY_SOCKET=/tmp/tempo.sock WATCHDOG_USEC=5000000 python example.py`

Expected output (in first terminal):
```
STATUS=Starting my service...
READY=1
STATUS=Init is complete...
WATCHDOG=1
STATUS=Sleeping and then notify x 3
WATCHDOG=1
WATCHDOG=1
WATCHDOG=1
STATUS=Spamming loop - should only see 2-3 notifications
WATCHDOG=1
WATCHDOG=1
WATCHDOG=1
STATUS=An irrecoverable error occured!
WATCHDOG=trigger
```

## Public Interface
### `systemd_watchdog.WatchDog` - commonly used properties and methods
#### `ping`
The only method required for the simplest implementation; combines `notify_due` with `notify()` to _only_ send "alive" notifications at reasonable intervals.

Returns boolean indicating if a message was sent or not.

#### `beat`
Alias for `ping()` if you prefer heartbeat terminology.

#### `ready()`
Report ready service state, _i.e._ completed init (only needed with `Type=notify`).

#### `status(msg)`
Send a service status message.

### `systemd_watchdog.WatchDog` - less-used properties and methods
#### `is_enabled`
Boolean property stating whether watchdog capability is enabled.

#### `timeout`
Property reporting the number of microseconds (int) before process will be killed.

It is recommended that you call `notify()` once roughly half of this interval has passed (see `notify_due`).

#### `timeout_td`
Property that is the same as `timeout` but presented as `datetime.timedelta` for easier manipulation.

#### `notify_due`
Boolean property indicating more than half of the watchdog interval has passed since last update.

#### `notify()`
Report a healthy service state. Other calls, _e.g._ `status()` do *not* reset the watchdog.

#### `notify_error(msg=None)`
Report an error to the watchdog manager. This program will likely be killed upon receipt.

If `msg` is provided, it will be reported as a status message prior to the error.


## History
Aaron D. Marasco Aug 2025 (1.0.0)
 * Added typing
 * Modernized build (pyproject.toml, poetry, etc)
 * Renamed watchdog => WatchDog

Aaron D. Marasco May 2020 (0.9.0)
 * Forked from the sd-notify project <https://github.com/stigok/sd-notify>
 * Additional contributors can be found in GitHub repository history

## License

See `LICENSE` file
