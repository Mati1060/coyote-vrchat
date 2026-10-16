import socket
import struct
import threading
import time
import unittest

from coyote_vrc import osc, patterns, uimath


class OscCodec(unittest.TestCase):
    def test_hand_built_vector_independent_of_encoder(self):
        # "/foo" + ",f" + 0.5 (0x3F000000) — built by hand, not by our encoder
        raw = b"/foo\x00\x00\x00\x00,f\x00\x00\x3f\x00\x00\x00"
        self.assertEqual(osc.parse_packet(raw), [("/foo", [0.5])])

    def test_roundtrip_types(self):
        addr = "/avatar/parameters/CoyoteA"
        self.assertEqual(osc.parse_packet(osc.encode_message(addr, 0.25)), [(addr, [0.25])])
        self.assertEqual(osc.parse_packet(osc.encode_message(addr, 7)), [(addr, [7])])
        self.assertEqual(osc.parse_packet(osc.encode_message(addr, True)), [(addr, [True])])
        self.assertEqual(osc.parse_packet(osc.encode_message(addr, False)), [(addr, [False])])
        self.assertEqual(osc.parse_packet(osc.encode_message(addr, "oi")), [(addr, ["oi"])])

    def test_padding_for_every_address_length(self):
        for n in range(1, 12):
            addr = "/" + "x" * n
            self.assertEqual(osc.parse_packet(osc.encode_message(addr, 1.0)), [(addr, [1.0])], n)

    def test_bundle(self):
        m1 = osc.encode_message("/a", 1.0)
        m2 = osc.encode_message("/b", 2)
        bundle = b"#bundle\x00" + b"\x00" * 8 + struct.pack(">i", len(m1)) + m1 + struct.pack(">i", len(m2)) + m2
        self.assertEqual(osc.parse_packet(bundle), [("/a", [1.0]), ("/b", [2])])

    def test_message_without_typetag(self):
        self.assertEqual(osc.parse_packet(b"/ping\x00\x00\x00"), [("/ping", [])])

    def test_unsupported_tag_raises(self):
        raw = osc._enc_str("/x") + osc._enc_str(",Z")
        with self.assertRaises(ValueError):
            osc.parse_packet(raw)


class OscListenerTests(unittest.TestCase):
    def test_receives_udp(self):
        got, evt = [], threading.Event()

        def handler(addr, args):
            got.append((addr, args))
            evt.set()

        lst = osc.OscListener("127.0.0.1", 0, handler)
        lst.start()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(osc.encode_message("/avatar/parameters/CoyoteA", 0.75), ("127.0.0.1", lst.port))
            self.assertTrue(evt.wait(2.0))
            self.assertEqual(got[0], ("/avatar/parameters/CoyoteA", [0.75]))
            self.assertIsNotNone(lst.last_packet)
            s.sendto(b"\xff\xfe meaningless junk", ("127.0.0.1", lst.port))  # a bad packet does not take it down
            s.sendto(osc.encode_message("/depois", 1), ("127.0.0.1", lst.port))
            deadline = time.time() + 2
            while len(got) < 2 and time.time() < deadline:
                time.sleep(0.02)
            self.assertEqual(got[-1], ("/depois", [1]))
            self.assertTrue(lst.listening)
            s.close()
        finally:
            lst.stop()
        self.assertFalse(lst.listening)

    def test_port_in_use_raises(self):
        a = osc.OscListener("127.0.0.1", 0, lambda *_: None)
        a.start()
        try:
            b = osc.OscListener("127.0.0.1", a.port, lambda *_: None)
            with self.assertRaises(OSError):
                b.start()
        finally:
            a.stop()


class PatternTests(unittest.TestCase):
    def test_all_patterns_stay_in_valid_range(self):
        for key in patterns.PATTERNS:
            for i in range(0, 1200):
                hz, w = patterns.sample(key, i * 0.025, 50.0, 100.0, seed=7)
                self.assertTrue(1.0 <= hz <= 100.0, (key, i, hz))
                self.assertTrue(0.0 <= w <= 100.0, (key, i, w))

    def test_const(self):
        self.assertEqual(patterns.sample("const", 3.3, 42.0, 77.0), (42.0, 77.0))

    def test_breathing_shape(self):
        self.assertAlmostEqual(patterns.sample("breathing", 0.0, 50, 100)[1], 0.0, places=6)
        self.assertAlmostEqual(patterns.sample("breathing", 4.0, 50, 100)[1], 100.0, places=6)
        self.assertAlmostEqual(patterns.sample("breathing", 8.0, 50, 100)[1], 0.0, places=6)

    def test_pulse_and_staccato(self):
        self.assertEqual(patterns.sample("pulse", 0.1, 50, 80)[1], 80.0)
        self.assertEqual(patterns.sample("pulse", 0.5, 50, 80)[1], 0.0)
        self.assertEqual(patterns.sample("staccato", 0.05, 50, 80)[1], 80.0)
        self.assertEqual(patterns.sample("staccato", 0.15, 50, 80)[1], 0.0)

    def test_ramp_increases_then_resets(self):
        a = patterns.sample("ramp", 1.0, 50, 100)[1]
        b = patterns.sample("ramp", 3.0, 50, 100)[1]
        self.assertLess(a, b)
        self.assertLess(patterns.sample("ramp", 5.01, 50, 100)[1], a)

    def test_sweep_goes_5_to_100(self):
        self.assertAlmostEqual(patterns.sample("sweep", 0.0, 50, 100)[0], 5.0, places=6)
        self.assertAlmostEqual(patterns.sample("sweep", 6.0, 50, 100)[0], 100.0, places=6)

    def test_random_is_deterministic_per_seed_and_step(self):
        self.assertEqual(patterns.sample("random", 1.2, 50, 100, 3), patterns.sample("random", 1.2, 50, 100, 3))
        self.assertNotEqual(patterns.sample("random", 1.2, 50, 100, 3), patterns.sample("random", 1.2, 50, 100, 4))

    def test_heartbeat_has_two_beats(self):
        on = [patterns.sample("heartbeat", t, 50, 100)[1] > 0 for t in (0.05, 0.2, 0.33, 0.6)]
        self.assertEqual(on, [True, False, True, False])


class UiMath(unittest.TestCase):
    def test_value_from_x_endpoints_and_clamp(self):
        self.assertEqual(uimath.value_from_x(0, 300, 10, 0, 200), 0)
        self.assertEqual(uimath.value_from_x(10, 300, 10, 0, 200), 0)
        self.assertEqual(uimath.value_from_x(290, 300, 10, 0, 200), 200)
        self.assertEqual(uimath.value_from_x(999, 300, 10, 0, 200), 200)
        self.assertEqual(uimath.value_from_x(150, 300, 10, 0, 200), 100)

    def test_resolution_snapping(self):
        v = uimath.value_from_x(150, 300, 10, 0.25, 3.0, 0.05)
        self.assertAlmostEqual(v / 0.05, round(v / 0.05), places=6)

    def test_roundtrip(self):
        for val in (0, 1, 50, 137, 200):
            x = uimath.x_from_value(val, 400, 12, 0, 200)
            self.assertAlmostEqual(uimath.value_from_x(x, 400, 12, 0, 200), val, delta=1)

    def test_degenerate(self):
        self.assertEqual(uimath.x_from_value(5, 100, 10, 5, 5), 10)


if __name__ == "__main__":
    unittest.main()
