import unittest

from coyote_vrc import protocol as p


def hexb(s: str) -> bytes:
    return bytes.fromhex(s)


class DocVectors(unittest.TestCase):
    """Hexadecimal examples copied from the 'More Examples' section of the official README_V3."""

    def test_no1_waveform_only(self):
        got = p.encode_b0(0, 0, 0, 0, 0, [10] * 4, [0, 10, 20, 30], [0] * 4, [0, 0, 0, 101])
        self.assertEqual(got, hexb("B00000000A0A0A0A000A141E0000000000000065"))

    def test_no1_line2(self):
        got = p.encode_b0(0, 0, 0, 0, 0, [15] * 4, [40, 50, 60, 70], [0] * 4, [0, 0, 0, 101])
        self.assertEqual(got, hexb("B00000000F0F0F0F28323C460000000000000065"))

    def test_no1_line4(self):
        got = p.encode_b0(0, 0, 0, 0, 0, [40, 60, 80, 100], [100, 90, 90, 90], [0] * 4, [0, 0, 0, 101])
        self.assertEqual(got, hexb("B0000000283C5064645A5A5A0000000000000065"))

    def test_no2_relative_add_5_on_A(self):
        got = p.encode_b0(0, p.ADD, p.KEEP, 5, 0, [10] * 4, [0, 10, 20, 30], [0] * 4, [0, 0, 0, 101])
        self.assertEqual(got, hexb("B00405000A0A0A0A000A141E0000000000000065"))

    def test_no2_relative_add_10_with_seq_1(self):
        got = p.encode_b0(1, p.ADD, p.KEEP, 10, 0, [40, 60, 80, 100], [100, 90, 90, 90], [0] * 4, [0, 0, 0, 101])
        self.assertEqual(got, hexb("B0140A00283C5064645A5A5A0000000000000065"))

    def test_no4_both_channels(self):
        got = p.encode_b0(0, 0, 0, 0, 0, [10] * 4, [0, 10, 20, 30], [10] * 4, [0, 0, 0, 0])
        self.assertEqual(got, hexb("B00000000A0A0A0A000A141E0A0A0A0A00000000"))
        got = p.encode_b0(0, 0, 0, 0, 0, [40, 60, 80, 100], [0, 90, 90, 90], [10] * 4, [0, 0, 0, 10])
        self.assertEqual(got, hexb("B0000000283C5064005A5A5A0A0A0A0A0000000A"))

    def test_length_is_20(self):
        self.assertEqual(len(p.encode_b0(0, 0, 0, 0, 0, [10] * 4, [0] * 4, [10] * 4, [0] * 4)), 20)

    def test_interp_nibble_layout(self):
        # doc: 0b1101 = A absolute (11) + B add (01)
        b = p.encode_b0(0, p.ABS, p.ADD, 5, 8, [10] * 4, [0] * 4, [10] * 4, [0] * 4)
        self.assertEqual(b[1] & 0x0F, 0b1101)
        self.assertEqual((b[2], b[3]), (5, 8))

    def test_wrong_slice_count(self):
        with self.assertRaises(ValueError):
            p.encode_b0(0, 0, 0, 0, 0, [10] * 3, [0] * 4, [10] * 4, [0] * 4)


class Frequency(unittest.TestCase):
    def test_doc_example_1_periods_to_bytes(self):
        periods = [1000, 500, 333, 250, 200, 166, 142, 125, 111, 100]
        expected = [240, 180, 146, 130, 120, 113, 108, 105, 102, 100]
        self.assertEqual([p.period_ms_to_byte(x) for x in periods], expected)

    def test_doc_example_2_periods_to_bytes(self):
        periods = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        expected = [100, 120, 140, 160, 180, 200, 210, 220, 230, 240]
        self.assertEqual([p.period_ms_to_byte(x) for x in periods], expected)

    def test_doc_table_rows(self):
        self.assertEqual(p.period_ms_to_byte(10), 10)
        self.assertEqual(p.period_ms_to_byte(20), 20)
        self.assertEqual(p.period_ms_to_byte(50), 50)
        self.assertEqual(p.period_ms_to_byte(110), 102)
        self.assertEqual(p.period_ms_to_byte(150), 110)
        self.assertEqual(p.period_ms_to_byte(680), 208)
        self.assertEqual(p.period_ms_to_byte(750), 215)

    def test_out_of_range_falls_back_to_10(self):
        self.assertEqual(p.period_ms_to_byte(5), 10)
        self.assertEqual(p.period_ms_to_byte(1001), 10)

    def test_hz_to_byte_key_points(self):
        self.assertEqual(p.hz_to_byte(100), 10)    # 10 ms
        self.assertEqual(p.hz_to_byte(50), 20)     # 20 ms
        self.assertEqual(p.hz_to_byte(10), 100)    # 100 ms
        self.assertEqual(p.hz_to_byte(1), 240)     # 1000 ms

    def test_hz_limits_are_clamped_to_1_100(self):
        self.assertEqual(p.hz_to_byte(200), 10)    # 200 Hz does not exist in V3: becomes 100 Hz
        self.assertEqual(p.hz_to_byte(0.1), 240)
        self.assertEqual(p.hz_to_byte(-5), 240)

    def test_always_valid_wire_range_and_monotonic(self):
        prev = None
        for i in range(1, 1001):
            hz = i / 10.0
            b = p.hz_to_byte(hz)
            self.assertTrue(p.FREQ_BYTE_MIN <= b <= p.FREQ_BYTE_MAX, (hz, b))
            if prev is not None:
                self.assertLessEqual(b, prev)   # more Hz => shorter period => smaller or equal byte
            prev = b

    def test_byte_to_hz_roundtrip(self):
        for hz in (1, 2, 3, 5, 10, 20, 50, 100):
            back = p.byte_to_hz(p.hz_to_byte(hz))
            self.assertAlmostEqual(back / hz, 1.0, delta=0.05, msg=(hz, back))

    def test_sanitize_slices(self):
        f, w = p.sanitize_slices([100, 50, 10, 1], [0, 50.4, 100, 250])
        self.assertEqual(f, [10, 20, 100, 240])
        self.assertEqual(w, [0, 50, 100, 100])  # width limited to 100 (>100 would invalidate the channel)
        with self.assertRaises(ValueError):
            p.sanitize_slices([1, 2], [1, 2])


class Other(unittest.TestCase):
    def test_bf_layout_and_range(self):
        self.assertEqual(p.encode_bf(150, 30, 160, 160, 100, 100), hexb("BF961EA0A06464"))
        self.assertEqual(len(p.encode_bf(200, 200)), 7)
        with self.assertRaises(ValueError):
            p.encode_bf(201, 10)   # per the doc: outside 0..200 the device ignores it

    def test_zero_command(self):
        z = p.encode_zero()
        self.assertEqual(z[0], 0xB0)
        self.assertEqual(z[1] & 0x0F, 0b1111)       # both channels in absolute mode
        self.assertEqual((z[2], z[3]), (0, 0))
        self.assertEqual(list(z[8:12]) + list(z[16:20]), [0] * 8)  # onda silenciosa

    def test_parse_b1(self):
        self.assertEqual(p.parse_b1(bytes([0xB1, 3, 10, 20])), p.B1(3, 10, 20))
        self.assertIsNone(p.parse_b1(bytes([0xB2, 3, 10, 20])))
        self.assertIsNone(p.parse_b1(bytes([0xB1, 3])))

    def test_uuids(self):
        self.assertEqual(p.CHAR_WRITE, "0000150a-0000-1000-8000-00805f9b34fb")
        self.assertEqual(p.CHAR_NOTIFY, "0000150b-0000-1000-8000-00805f9b34fb")
        self.assertEqual(p.SERVICE_CMD, "0000180c-0000-1000-8000-00805f9b34fb")
        self.assertEqual(p.CHAR_BATTERY, "00001500-0000-1000-8000-00805f9b34fb")


if __name__ == "__main__":
    unittest.main()
