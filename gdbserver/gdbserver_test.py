from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass
class GDBResponse:
    payload: str


class GDBServerTestClient:
    def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.settimeout(self.timeout)

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def __enter__(self) -> "GDBServerTestClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _require_socket(self) -> socket.socket:
        if self.sock is None:
            raise RuntimeError("client is not connected")
        return self.sock

    @staticmethod
    def _checksum(payload: str) -> int:
        return sum(ord(ch) for ch in payload) & 0xFF

    def _recv_exact(self, size: int) -> bytes:
        sock = self._require_socket()
        data = bytearray()
        while len(data) < size:
            chunk = sock.recv(size - len(data))
            if not chunk:
                raise ConnectionError("unexpected EOF from gdbserver")
            data.extend(chunk)
        return bytes(data)

    def _recv_packet(self) -> GDBResponse:
        start = self._recv_exact(1)
        while start != b"$":
            start = self._recv_exact(1)

        payload = bytearray()
        while True:
            ch = self._recv_exact(1)
            if ch == b"#":
                break
            payload.extend(ch)

        checksum = int(self._recv_exact(2).decode("ascii"), 16)
        decoded = payload.decode("ascii")
        expected = self._checksum(decoded)
        if checksum != expected:
            raise AssertionError(f"checksum mismatch: got {checksum:02x}, expected {expected:02x}")
        return GDBResponse(payload=decoded)

    def _send_packet_and_ack(self, payload: str) -> None:
        sock = self._require_socket()
        packet = f"${payload}#{self._checksum(payload):02x}".encode("ascii")
        sock.sendall(packet)
        ack = self._recv_exact(1)
        if ack != b"+":
            raise AssertionError(f"expected '+' ack, got {ack!r}")

    def send_packet(self, payload: str) -> str:
        self._send_packet_and_ack(payload)
        return self._recv_packet().payload

    def send_packet_no_response(self, payload: str) -> None:
        self._send_packet_and_ack(payload)

    def send_break(self) -> str:
        sock = self._require_socket()
        sock.sendall(b"\x03")
        return self._recv_packet().payload

    @staticmethod
    def decode_u32_le_words(register_hex: str) -> list[int]:
        if len(register_hex) % 8 != 0:
            raise ValueError("register payload length must be a multiple of 8 hex chars")
        words: list[int] = []
        for i in range(0, len(register_hex), 8):
            raw = bytes.fromhex(register_hex[i:i + 8])
            words.append(int.from_bytes(raw, byteorder="little", signed=False))
        return words

    @staticmethod
    def decode_memory_bytes(memory_hex: str) -> bytes:
        return bytes.fromhex(memory_hex)
