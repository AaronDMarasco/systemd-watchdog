"""
sd_notify(3) and sd_watchdog_enabled(3) client functionality implemented in Python 3 for writing Python daemons.

See README.md and examples/daemon.py for usage
"""

from __future__ import annotations

import os
import socket
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING


class WatchDog:
    """The systemd watchdog class."""

    _default_timeout = timedelta(hours=24)  # Safe value to do math with; if disabled won't matter

    def __init__(self, sock: socket.socket | None = None, addr: str | None = None) -> None:  # noqa: D107
        self._address: str | None = addr or os.getenv("NOTIFY_SOCKET")
        self._lastcall: datetime = datetime.fromtimestamp(1, tz=timezone.utc)
        self._socket: socket.socket = sock or socket.socket(family=socket.AF_UNIX, type=socket.SOCK_DGRAM)
        self._timeout_td: timedelta = self._default_timeout

        # Note this fix is untested in a live system; https://unix.stackexchange.com/q/206386
        if self._address and self._address[0] == "@":
            self._address = "\0" + self._address[1:]

        # Check for our timeout
        if self._address:
            wtime = os.getenv("WATCHDOG_USEC")
            wpid = os.getenv("WATCHDOG_PID")
            if wtime and wtime.isdigit():  # noqa: SIM102
                if wpid is None or (wpid.isdigit() and (wpid == str(os.getpid()))):
                    self._timeout_td = timedelta(microseconds=int(wtime))

    def _send(self, msg: str) -> None:
        """Send string as bytes on the notification socket."""
        if self.is_enabled:
            if TYPE_CHECKING:
                assert self._address is not None  # we "know" because is_enabled told us
            self._socket.sendto(msg.encode(), self._address)

    @property
    def is_enabled(self) -> bool:
        """Property indicating whether watchdog is enabled."""
        return bool(self._address)

    def notify(self) -> None:
        """Send healthy notification to systemd."""
        self._lastcall = self._now
        self._send("WATCHDOG=1\n")

    @property
    def notify_due(self) -> bool:
        """Report if notification is due."""
        return (self._now - self._lastcall) >= (self._timeout_td / 2)

    def notify_error(self, msg: str | None = None) -> None:
        """
        Report a watchdog error. This program will likely be killed by the service manager.

        If msg is provided, it will be reported as a status message prior to the error.
        """
        if msg:
            self.status(msg)
        self._send("WATCHDOG=trigger\n")

    @property
    def _now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def ping(self) -> bool:
        """Send healthy notification to systemd if prudent to."""
        if self.notify_due:
            self.notify()
            return True
        return False

    beat = ping  # alias for ping if you prefer heartbeat terminology

    def ready(self) -> None:
        """Report ready service state, i.e. completed init."""
        self._send("READY=1\n")

    def status(self, msg: str) -> None:
        """Send a free-form service status message."""
        self._send(f"STATUS={msg}\n")

    @property
    def timeout(self) -> int:
        """Report the watchdog window in microseconds as int (cf. sd_watchdog_enabled(3) )."""
        return int(self._timeout_td / timedelta(microseconds=1))

    @property
    def timeout_td(self) -> timedelta:
        """Report the watchdog window as datetime.timedelta (cf. sd_watchdog_enabled(3) )."""
        return self._timeout_td
