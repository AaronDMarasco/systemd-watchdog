#!/bin/env python3
"""systemd_watchdog unit tests."""
import os
from datetime import timedelta
from time import sleep
from unittest import TestCase
from unittest.mock import Mock, call, patch, sentinel

from systemd_watchdog import watchdog


class WatchdogTestCase(TestCase):
    """The tests."""

    TEST_ADDR = "/var/string/to/socket"

    def test_send(self):
        cut = watchdog(sock=Mock(spec=["sendto"]), addr=self.TEST_ADDR)
        cut._send("Hello, world!")
        cut._socket.sendto.assert_called_once_with(b"Hello, world!", self.TEST_ADDR)

    def test_enabled(self):
        # We expect these 3 variables to be checked whenever NOTIFY_SOCKET is set:
        expected_vars = [call("NOTIFY_SOCKET"), call("WATCHDOG_USEC"), call("WATCHDOG_PID")]

        # With no environment set
        with patch("os.getenv", return_value=None) as getenv_mock:
            cut = watchdog(sock=Mock(spec=["sendto"]))
            res = cut.is_enabled
            getenv_mock.assert_called_once_with("NOTIFY_SOCKET")
            self.assertFalse(res)

        # With empty string set
        with patch("os.getenv", return_value="") as getenv_mock:
            cut = watchdog(sock=Mock(spec=["sendto"]))
            res = cut.is_enabled
            getenv_mock.assert_called_once_with("NOTIFY_SOCKET")
            self.assertFalse(res)

        # With environment set
        with patch("os.getenv", return_value=self.TEST_ADDR) as getenv_mock:
            cut = watchdog(sock=Mock(spec=["sendto"]))
            res = cut.is_enabled
            getenv_mock.assert_has_calls(expected_vars)
            self.assertTrue(res)

        # With abstract namespace socket set
        with patch("os.getenv", return_value="@" + self.TEST_ADDR) as getenv_mock:
            cut = watchdog(sock=Mock(spec=["sendto"]))
            res = cut.is_enabled
            getenv_mock.assert_has_calls(expected_vars)
            self.assertTrue(res)

    def test_addr_parsing(self):
        # Standard address
        with patch("os.getenv", return_value=self.TEST_ADDR):
            sock = Mock(spec=["sendto"])
            cut = watchdog(sock=sock)
            cut.ready()
            sock.sendto.assert_called_once_with(b"READY=1\n", self.TEST_ADDR)

        # Abstract namespace address
        with patch("os.getenv", return_value="@" + self.TEST_ADDR):
            sock = Mock(spec=["sendto"])
            cut = watchdog(sock=sock)
            cut.ready()
            sock.sendto.assert_called_once_with(b"READY=1\n", "\0" + self.TEST_ADDR)

    def test_ready(self):
        cut = watchdog(sock=Mock(spec=["sendto"]), addr=self.TEST_ADDR)
        with patch("systemd_watchdog.watchdog._send") as patched_send:
            cut.ready()
            patched_send.assert_called_once_with("READY=1\n")

    def test_status(self):
        cut = watchdog(sock=Mock(spec=["sendto"]), addr=self.TEST_ADDR)
        with patch("systemd_watchdog.watchdog._send") as patched_send:
            cut.status("Hello, world!")
            patched_send.assert_called_once_with("STATUS=Hello, world!\n")

    def test_notify(self):
        cut = watchdog(sock=Mock(spec=["sendto"]), addr=self.TEST_ADDR)
        with patch("systemd_watchdog.watchdog._send") as patched_send:
            cut.notify()
            patched_send.assert_called_once_with("WATCHDOG=1\n")

    def test_notify_error(self):
        cut = watchdog(sock=Mock(spec=["sendto"]), addr=self.TEST_ADDR)
        with patch("systemd_watchdog.watchdog._send") as patched_send:
            # Without msg arg
            cut.notify_error()
            patched_send.assert_called_once_with("WATCHDOG=trigger\n")

    def test_notify_error_with_message(self):
        cut = watchdog(sock=Mock(spec=["sendto"]), addr=self.TEST_ADDR)
        with patch("systemd_watchdog.watchdog._send") as patched_send:
            cut.notify_error(msg="Hello world!")
            self.assertEqual(patched_send.call_count, 2)
            patched_send.assert_any_call("WATCHDOG=trigger\n")
            patched_send.assert_any_call("STATUS=Hello world!\n")

    def test_timeout_parsing(self):
        test_dict = {
            "NOTIFY_SOCKET": self.TEST_ADDR,
            "WATCHDOG_USEC": "15000000",  # 15s
        }
        # simplest, good case (no PID at all)
        with patch.dict(os.environ, test_dict, clear=True):
            cut = watchdog(sock=Mock(spec=["sendto"]))
            self.assertEqual(cut.timeout, 15000000)

        # with our PID
        with patch.dict(os.environ, {"WATCHDOG_PID": str(os.getpid()), **test_dict}, clear=True):
            cut = watchdog(sock=Mock(spec=["sendto"]))
            self.assertEqual(cut.timeout, 15000000)

        # with our PID (as timedelta)
        with patch.dict(os.environ, {"WATCHDOG_PID": str(os.getpid()), **test_dict}, clear=True):
            cut = watchdog(sock=Mock(spec=["sendto"]))
            self.assertEqual(cut.timeout_td, timedelta(microseconds=15000000))

        # bad PID (not ours)
        # somebody's going to try to test us in a container and get mad when we were PID 1
        with patch.dict(os.environ, {"WATCHDOG_PID": str(1), **test_dict}, clear=True):
            cut = watchdog(sock=Mock(spec=["sendto"]))
            default_timeout = cut._default_timeout / timedelta(microseconds=1)
            self.assertEqual(cut.timeout, default_timeout)

        # worse PID
        with patch.dict(os.environ, {"WATCHDOG_PID": "not even a number", **test_dict}, clear=True):
            cut = watchdog(sock=Mock(spec=["sendto"]))
            self.assertEqual(cut.timeout, default_timeout)

    def test_timeouts(self):
        test_dict = {
            "NOTIFY_SOCKET": self.TEST_ADDR,
            "WATCHDOG_USEC": "2000000",  # 2s
        }
        with (
            patch.dict(os.environ, test_dict, clear=True),
            patch("systemd_watchdog.watchdog._send"),  # Don't do anything on send
        ):
            cut = watchdog(sock=sentinel.socket)
            self.assertEqual(cut.timeout, 2000000)
            self.assertTrue(cut.notify_due)  # At start, it is "overdue" since never sent
            cut.notify()
            self.assertFalse(cut.notify_due)  # It shouldn't be expecting already
            sleep(0.7)
            self.assertFalse(cut.notify_due)  # Still shouldn't
            sleep(0.4)
            self.assertTrue(cut.notify_due)  # Now it should

        with patch.dict(os.environ, test_dict, clear=True), patch("systemd_watchdog.watchdog._send") as patched_send:
            # Similar to above, but instead we intercept send and leave the logic to ping()
            cut = watchdog(sock=sentinel.socket)
            self.assertEqual(cut.timeout, 2000000)
            self.assertTrue(cut.notify_due)  # At start, it is "overdue" since never sent
            cut.notify()
            patched_send.assert_called_once_with("WATCHDOG=1\n")
            patched_send.reset_mock()
            res = cut.ping()
            self.assertFalse(res)  # It shouldn't be expecting already
            patched_send.assert_not_called()
            sleep(0.7)
            res = cut.ping()
            self.assertFalse(res)  # Still shouldn't
            patched_send.assert_not_called()
            sleep(0.4)
            res = cut.beat()  # Test the alias
            self.assertTrue(res)  # Now it should
            patched_send.assert_called_once_with("WATCHDOG=1\n")


if __name__ == "__main__":
    import unittest

    unittest.main()
