# -*- coding: utf-8 -*-
"""
Created on Sat Oct 26 09:37:19 2019

@author: James
"""

import os
from pathlib import Path
import subprocess
import warnings

from lxml import etree
from ppadb.client import Client as AdbClient


DEFAULT_NOX_DIR = Path(r"C:\Program Files (x86)\Nox\bin")
DEFAULT_NOX_EXE = DEFAULT_NOX_DIR / "Nox.exe"

try:
    NOX_PLAYER_DIR = Path(
        [
            directory
            for directory in os.getenv("PATH").split(";")
            if r"Nox\bin" in directory
        ][-1]
    )
    NOX_PLAYER_EXE = NOX_PLAYER_DIR / "Nox.exe"
except IndexError:
    warnings.warn(
        f"unable to find Nox\\bin on path. Setting exe location to {DEFAULT_NOX_EXE}..."
    )
    NOX_PLAYER_DIR = DEFAULT_NOX_DIR
    NOX_PLAYER_EXE = DEFAULT_NOX_EXE

STARTUP_PARAMS = {
    "title",
    "lang",
    "locale",
    "screen",
    "resolution",
    "dpi",
    "performance",
    "cpu",
    "memory",
    "root",
    "virtualKey",
}

MAX_CLONES = 4


class NoxEmulator:
    _available_clone_names = [f"Nox_{i}" for i in range(MAX_CLONES)]
    _adb_client = AdbClient()

    def __init__(self, **kwargs):
        try:
            self._clone_name = NoxEmulator._available_clone_names.pop(0)
        except IndexError:
            raise ValueError("No available clones")
        self._cmd_string = f"{NOX_PLAYER_EXE} -clone:{self._clone_name} "
        startup_string = self._cmd_string
        for key, value in kwargs.items():
            if key not in STARTUP_PARAMS:
                raise ValueError(f"Invalid keyword argument: {key}")
            else:
                startup_string += f"-{key}:{value} "
        self._popen = subprocess.Popen(startup_string.split(" "))
        self._count = MAX_CLONES - len(NoxEmulator._available_clone_names)
        # wait until the number of adb devices increases before
        # assigning the adb device to this emulator
        while self._count > len(NoxEmulator._adb_client.devices()):
            pass
        self._adb_device = NoxEmulator._adb_client.devices()[-self._count]

    @property
    def is_open(self):
        result = self._popen.poll()
        if result is None:
            return True
        else:
            return False

    def _raise_if_not_open(self):
        if not self.is_open:
            raise ValueError("Instance not open")

    def release_clone_name(self):
        if not self.is_open:
            if self._clone_name not in NoxEmulator._available_clone_names:
                NoxEmulator._available_clone_names.insert(0, self._clone_name)
        else:
            raise ValueError("Instance still open")

    def install(self, apk):
        self._raise_if_not_open()
        install_string = f"{self._cmd_string} -apk:{apk}"
        return subprocess.run(install_string.split())

    def launch_activity(self, activity, **kwargs):
        self._raise_if_not_open()
        launch_str = f"{self._cmd_string} -activity:{activity} "
        if kwargs:
            launch_str += "-param: "
        for key, value in kwargs.items():
            launch_str += f"-e {key} {value} "

        return subprocess.run(launch_str.split())

    def launch_package(self, package):
        self._raise_if_not_open()
        if package in self.adb_device.list_packages():
            launch_str = f"{self._cmd_string} -package:{package} "
            return subprocess.run(launch_str.split())
        else:
            raise ValueError(f"{package} not found on device")

    @property
    def adb_device(self):
        return self._adb_device

    def tap(self, x, y):
        self.adb_device.shell(f"input tap {x} {y}")

    def swipe(self, x0, y0, x1, y1, duration):
        self.adb_device.shell(f"input swipe {x0} {y0} {x1} {y1} {duration}")

    def text(self, txt):
        self.adb_device.shell(f"input text {txt}")

    def get_ui_xml(self):
        ui_xml = (
            self.adb_device.shell("uiautomator dump /dev/tty")
            .replace("UI hierchary dumped to: /dev/tty\r\n", "")
            .encode("utf-8")
        )
        return ui_xml


    def __del__(self):
        self._raise_if_not_open()
        stop_string = f"{self._cmd_string} -quit"
        result = subprocess.run(stop_string.split())
        self._popen.wait()
        self.release_clone_name()
        return result
