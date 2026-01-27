"""
robot_serial.py
---------------
Small, reliable Serial link between Raspberry Pi and Arduino (Mega/Uno).

Protocol (one command per line):
  STOP
  AUTO_LF
  MANUAL
  FWD
  BACK
  LEFT
  RIGHT
  SPEED <0-255>

Arduino should reply with short status lines (optional).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

import serial


@dataclass
class SerialConfig:
    port: str = "/dev/ttyACM0"
    baud: int = 9600
    timeout_s: float = 0.2
    reconnect_s: float = 2.0


@dataclass
class SensorState:
    flame: bool = False
    gas: bool = False
    mq2_val: int = 0
    flame_val: int = 0
    warm: bool = True
    updated_at: float = 0.0

    def as_dict(self) -> Dict[str, object]:
        return {
            "flame": self.flame,
            "gas": self.gas,
            "mq2_val": int(self.mq2_val),
            "flame_val": int(self.flame_val),
            "warm": bool(self.warm),
            "updated_at": float(self.updated_at),
        }


class RobotSerial:
    def __init__(self, cfg: SerialConfig):
        self.cfg = cfg
        self._lock = threading.Lock()
        self._ser: Optional[serial.Serial] = None
        self._last_connect_try = 0.0

        # Reader thread (for SENSOR lines / debug)
        self._run_reader = False
        self._reader_th: Optional[threading.Thread] = None

        self._sensor = SensorState()
        self._sensor_lock = threading.Lock()

        self._on_sensor: Optional[Callable[[SensorState], None]] = None

    def connect(self) -> bool:
        with self._lock:
            if self._ser and self._ser.is_open:
                return True

            now = time.time()
            if now - self._last_connect_try < self.cfg.reconnect_s:
                return False

            self._last_connect_try = now
            try:
                self._ser = serial.Serial(
                    self.cfg.port,
                    self.cfg.baud,
                    timeout=self.cfg.timeout_s,
                    write_timeout=self.cfg.timeout_s,
                )
                # Arduino resets on serial open; give it a moment.
                time.sleep(2.0)
                return True
            except Exception:
                self._ser = None
                return False

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return bool(self._ser and self._ser.is_open)

    def start_reader(self, on_sensor: Optional[Callable[[SensorState], None]] = None) -> None:
        """Start background serial reader to capture SENSOR lines from Arduino."""
        self._on_sensor = on_sensor
        if self._reader_th and self._reader_th.is_alive():
            return
        self._run_reader = True
        self._reader_th = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_th.start()

    def stop_reader(self) -> None:
        self._run_reader = False

    def get_sensor_state(self) -> SensorState:
        with self._sensor_lock:
            return SensorState(**self._sensor.as_dict())  # copy

    def _update_sensor(self, **kwargs) -> None:
        with self._sensor_lock:
            for k, v in kwargs.items():
                if hasattr(self._sensor, k):
                    setattr(self._sensor, k, v)
            self._sensor.updated_at = time.time()
            snapshot = SensorState(**self._sensor.as_dict())

        if callable(self._on_sensor):
            try:
                self._on_sensor(snapshot)
            except Exception:
                pass

    @staticmethod
    def _parse_sensor_line(line: str) -> Dict[str, str]:
        # Expected: SENSOR KEY=VAL KEY=VAL ...
        parts = line.strip().split()
        out: Dict[str, str] = {}
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                out[k.strip().upper()] = v.strip()
        return out

    def _reader_loop(self) -> None:
        while self._run_reader:
            if not self.connect():
                time.sleep(0.5)
                continue

            try:
                with self._lock:
                    ser = self._ser
                if not ser:
                    time.sleep(0.2)
                    continue

                raw = ser.readline()
                if not raw:
                    continue

                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                if line.startswith("SENSOR"):
                    kv = self._parse_sensor_line(line)
                    flame = kv.get("FLAME")
                    gas = kv.get("GAS")
                    mq2v = kv.get("MQ2VAL")
                    flv = kv.get("FLAMEVAL")
                    warm = kv.get("WARM")

                    updates = {}
                    if flame is not None:
                        updates["flame"] = flame in ("1", "TRUE", "YES")
                    if gas is not None:
                        updates["gas"] = gas in ("1", "TRUE", "YES")
                    if mq2v is not None and mq2v.isdigit():
                        updates["mq2_val"] = int(mq2v)
                    if flv is not None and flv.isdigit():
                        updates["flame_val"] = int(flv)
                    if warm is not None:
                        updates["warm"] = warm in ("1", "TRUE", "YES")

                    if updates:
                        self._update_sensor(**updates)

            except Exception:
                # force reconnect
                with self._lock:
                    try:
                        if self._ser:
                            self._ser.close()
                    except Exception:
                        pass
                    self._ser = None
                time.sleep(0.5)

    def close(self) -> None:
        self.stop_reader()
        with self._lock:
            try:
                if self._ser:
                    self._ser.close()
            finally:
                self._ser = None

    def send(self, line: str) -> bool:
        """
        Sends a single command line (auto adds \\n).
        Returns True if written, False if not connected.
        """
        if not line:
            return False

        if not self.connect():
            return False

        with self._lock:
            try:
                assert self._ser is not None
                payload = (line.strip() + "\n").encode("utf-8")
                self._ser.write(payload)
                self._ser.flush()
                return True
            except Exception:
                # force reconnect next time
                try:
                    if self._ser:
                        self._ser.close()
                except Exception:
                    pass
                self._ser = None
                return False

    # Convenience wrappers
    def stop(self) -> bool: return self.send("STOP")
    def auto_line_follow(self) -> bool: return self.send("AUTO_LF")
    def manual(self) -> bool: return self.send("MANUAL")
    def fwd(self) -> bool: return self.send("FWD")
    def back(self) -> bool: return self.send("BACK")
    def left(self) -> bool: return self.send("LEFT")
    def right(self) -> bool: return self.send("RIGHT")
    def speed(self, spd: int) -> bool:
        spd = max(0, min(255, int(spd)))
        return self.send(f"SPEED {spd}")
