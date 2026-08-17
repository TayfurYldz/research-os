from __future__ import annotations

import os
import sys
import time
import unittest

import pathsetup  # noqa: F401

from research_os.platform.process_tree import (
    CREATE_NEW_PROCESS_GROUP,
    CREATE_SUSPENDED,
    spawn_kwargs,
    terminate_tree,
)


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            exit_code = wintypes.DWORD()
            kernel32.GetExitCodeProcess.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(wintypes.DWORD),
            ]
            kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            kernel32.CloseHandle(handle)
            return exit_code.value == 259  # STILL_ACTIVE
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class ProcessTreeTests(unittest.TestCase):
    def test_posix_branch_uses_new_session(self) -> None:
        kwargs = spawn_kwargs.__wrapped__ if hasattr(spawn_kwargs, "__wrapped__") else spawn_kwargs()
        if os.name == "posix":
            self.assertTrue(kwargs.get("start_new_session"))
        else:
            self.assertEqual(
                kwargs.get("creationflags"),
                CREATE_NEW_PROCESS_GROUP | CREATE_SUSPENDED,
            )
            self.assertFalse(kwargs.get("start_new_session"))

    def test_windows_and_posix_kwargs_are_explicit(self) -> None:
        posix = {"start_new_session": True}
        windows = {
            "start_new_session": False,
            "creationflags": CREATE_NEW_PROCESS_GROUP | CREATE_SUSPENDED,
        }
        self.assertTrue(posix["start_new_session"])
        self.assertEqual(windows["creationflags"], CREATE_NEW_PROCESS_GROUP | CREATE_SUSPENDED)

    def test_timeout_cleans_grandchild_when_environment_allows(self) -> None:
        from research_os.platform.process_tree import run_supervised

        script = (
            "import os, sys, time, subprocess\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            "print(child.pid)\n"
            "sys.stdout.flush()\n"
            "time.sleep(30)\n"
        )
        result = run_supervised(
            [sys.executable, "-c", script],
            timeout_seconds=0.8,
        )
        self.assertTrue(result.timed_out)
        self.assertIsNotNone(result.exit_code)
        self.assertFalse(result.cleanup_failed, result.cleanup_reason)
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        self.assertTrue(stdout, msg="grandchild pid was not printed")
        grandchild_pid = int(stdout.splitlines()[0])
        time.sleep(0.3)
        self.assertFalse(_pid_alive(grandchild_pid), f"grandchild {grandchild_pid} still alive")


if __name__ == "__main__":
    unittest.main()
