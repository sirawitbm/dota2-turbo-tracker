"""Win32 helpers. Every ctypes signature is declared (windows-game-overlay
skill, bug #1): undeclared calls assume 32-bit ints and fail silently."""

import ctypes
import os
from ctypes import wintypes

HWND_TOPMOST = -1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
ERROR_ALREADY_EXISTS = 183
DWMWA_USE_IMMERSIVE_DARK_MODE = 20

if os.name == "nt":
    U = ctypes.WinDLL("user32", use_last_error=True)
    K = ctypes.WinDLL("kernel32", use_last_error=True)
    try:
        D = ctypes.WinDLL("dwmapi")
        D.DwmSetWindowAttribute.argtypes = (wintypes.HWND, wintypes.DWORD,
                                            wintypes.LPCVOID, wintypes.DWORD)
        D.DwmSetWindowAttribute.restype = ctypes.c_long
    except OSError:
        D = None
    U.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int,
                               ctypes.c_int, ctypes.c_int, ctypes.c_int,
                               wintypes.UINT)
    U.SetWindowPos.restype = wintypes.BOOL
    U.FindWindowW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR)
    U.FindWindowW.restype = wintypes.HWND
    U.FindWindowExW.argtypes = (wintypes.HWND, wintypes.HWND,
                                wintypes.LPCWSTR, wintypes.LPCWSTR)
    U.FindWindowExW.restype = wintypes.HWND
    U.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    U.GetWindowRect.restype = wintypes.BOOL
    U.MessageBoxW.argtypes = (wintypes.HWND, wintypes.LPCWSTR,
                              wintypes.LPCWSTR, wintypes.UINT)
    U.MessageBoxW.restype = ctypes.c_int
    K.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL,
                               wintypes.LPCWSTR)
    K.CreateMutexW.restype = wintypes.HANDLE
    K.CloseHandle.argtypes = (wintypes.HANDLE,)
    K.CloseHandle.restype = wintypes.BOOL


def pin_topmost(hwnd):
    """Re-assert always-on-top without stealing focus (skill bug #4)."""
    if os.name != "nt":
        return
    try:
        U.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                       SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    except (AttributeError, OSError, ValueError):
        pass


def dark_title_bar(hwnd):
    """Ask Windows 11 for a dark title bar to match the app."""
    if os.name != "nt" or D is None:
        return
    try:
        on = ctypes.c_int(1)
        D.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                                ctypes.byref(on), ctypes.sizeof(on))
    except (AttributeError, OSError, ValueError):
        pass


def notify_area_left_px():
    """Left edge of the taskbar's clock-and-icons block, in physical pixels
    (skill bug #8: dock beside it, not in the centre over Start)."""
    if os.name != "nt":
        return None
    try:
        tray = U.FindWindowW("Shell_TrayWnd", None)
        notify = U.FindWindowExW(tray, None, "TrayNotifyWnd", None) if tray else None
        if not notify:
            return None
        r = wintypes.RECT()
        return r.left if U.GetWindowRect(notify, ctypes.byref(r)) else None
    except (AttributeError, OSError, ValueError):
        return None


_INSTANCE_HANDLE = None


def acquire_single_instance(name="Local\\TurboTracker"):
    """Named mutex so two copies never fight over the port and database."""
    global _INSTANCE_HANDLE
    if os.name != "nt":
        return True
    handle = K.CreateMutexW(None, False, name)
    err = ctypes.get_last_error()
    if not handle:
        return True
    if err == ERROR_ALREADY_EXISTS:
        K.CloseHandle(handle)
        return False
    _INSTANCE_HANDLE = handle
    return True


def message_box(text, title):
    if os.name == "nt":
        U.MessageBoxW(None, text, title, 0x40)
