"""Offline tests of the actual exported helper; never opens a serial port."""
import contextlib
import io
import unittest
from capture_uplink import Dump, Terminal, fnv, stop_for_export, until


class FakeSerial:
    def __init__(self, fragment=False):
        self.pending = bytearray(b"\x1b[6n")
        self.writes = []
        self.fragment = fragment

    @property
    def in_waiting(self):
        return len(self.pending)

    def read(self, count):
        count = 1 if self.fragment else count
        chunk = bytes(self.pending[:count])
        del self.pending[:count]
        return chunk

    def write(self, data):
        self.writes.append(data)
        if data == b"\x1b[1;80R":
            self.pending.extend(b"Firmware: test\r\n")


class CaptureTests(unittest.TestCase):
    def header(self, data):
        return (f"VCAP BEGIN bytes={len(data)} fnv={fnv(data):08x} mode=3 "
                "generation=1 width=960 height=1280 frames=2")

    def test_dump_roundtrip(self):
        data = bytes(range(128))
        dump = Dump()
        dump.feed(self.header(data))
        for offset in (0, 64):
            dump.feed("unrelated redacted log")
            dump.feed(f"VCAP DATA {offset:08x} " + data[offset:offset+64].hex())
        self.assertTrue(dump.feed("VCAP END"))
        self.assertEqual(dump.data, data)

    def test_dump_rejects_corruption(self):
        data = b"1234"
        cases = [
            ["VCAP END"],
            ["VCAP DATA 00000001 31323334"],
            ["VCAP DATA 00000000 zz"],
            ["VCAP DATA 00000000 31323335", "VCAP END"],
            ["VCAP DATA 00000000 31323334", "VCAP DATA 00000000 31323334"],
            [self.header(data)],
        ]
        for lines in cases:
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                dump = Dump(); dump.feed(self.header(data))
                for line in lines:
                    dump.feed(line)

    def test_cursor_query_without_newline_and_fragmented(self):
        for fragment in (False, True):
            raw = FakeSerial(fragment)
            self.assertEqual(until(Terminal(raw), "Firmware:", 1), "Firmware: test")
            self.assertEqual(raw.writes, [b"\x1b[1;80R"])

    def test_command_clears_stale_input_and_submits_cr(self):
        raw = FakeSerial(); raw.pending.clear()
        terminal = Terminal(raw)
        terminal.settle = lambda: None
        terminal.command("version")
        self.assertEqual(raw.writes, [b"\x15version\r"])

    def test_disconnect_not_mislabeled_as_reboot(self):
        class Broken(FakeSerial):
            def read(self, count):
                raise OSError("disconnected")
        with self.assertRaisesRegex(RuntimeError, "不能排除重启"):
            Terminal(Broken()).readline()

    def test_export_stops_and_only_clears_empty_capture(self):
        class Port:
            def __init__(self, size):
                self.size = size; self.commands = []
            def command(self, text):
                self.commands.append(text)
            def readline(self):
                return (f"VCAP STATUS active=0 bytes={self.size} frames=1 "
                        "width=960 height=1280 reason=manual-stop\n").encode()
        with contextlib.redirect_stdout(io.StringIO()):
            port = Port(100)
            self.assertEqual(stop_for_export(port)["bytes"], 100)
            self.assertEqual(port.commands, ["video-capture stop"])
            port = Port(0)
            with self.assertRaisesRegex(RuntimeError, "0字节"):
                stop_for_export(port)
            self.assertEqual(port.commands, ["video-capture stop", "video-capture clear"])


if __name__ == "__main__":
    unittest.main()
