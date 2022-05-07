import importlib
import unittest
from unittest import TestCase

import disc_append


BLANK_BD = """INQUIRY:                [HL-DT-ST][BD-RE  WH16NS40 ][1.00]
GET [CURRENT] CONFIGURATION:
 Mounted Media:         41h, BD-R SRM
 Media ID:              VERBAT/IMe
 Current Write Speed:   12.0x4495=53952KB/s
 Write Speed #0:        12.0x4495=53952KB/s
 Write Speed #1:        10.0x4495=44960KB/s
 Write Speed #2:        8.0x4495=35968KB/s
 Write Speed #3:        6.0x4495=26976KB/s
 Write Speed #4:        4.0x4495=17984KB/s
 Speed Descriptor#0:    08/12219391 R@6.0x4495=26976KB/s W@12.0x4495=53952KB/s
 Speed Descriptor#1:    08/12219391 R@6.0x4495=26976KB/s W@10.0x4495=44960KB/s
 Speed Descriptor#2:    08/12219391 R@6.0x4495=26976KB/s W@8.0x4495=35968KB/s
 Speed Descriptor#3:    08/12219391 R@6.0x4495=26976KB/s W@6.0x4495=26976KB/s
 Speed Descriptor#4:    00/12219391 R@6.0x4495=26976KB/s W@4.0x4495=17984KB/s
:-[ READ BD SPARE INFORMATION failed with SK=5h/INVALID FIELD IN CDB]: Input/output error
READ DISC INFORMATION:
 Disc status:           blank
 Number of Sessions:    1
 State of Last Session: empty
 "Next" Track:          1
 Number of Tracks:      1
READ FORMAT CAPACITIES:
 unformatted:           12219392*2048=25025314816
 00h(3000):             11826176*2048=24220008448
 32h(0):                11826176*2048=24220008448
 32h(0):                5796864*2048=11871977472
 32h(0):                12088320*2048=24756879360
READ TRACK INFORMATION[#1]:
 Track State:           invisible incremental
 Track Start Address:   0*2KB
 Next Writable Address: 0*2KB
 Free Blocks:           12219392*2KB
 Track Size:            12219392*2KB
READ CAPACITY:          0*2048=0
"""


WRITTEN_BD = """INQUIRY:                [HL-DT-ST][BD-RE  WH16NS40 ][1.00]
GET [CURRENT] CONFIGURATION:
 Mounted Media:         41h, BD-R SRM+POW
 Media ID:              VERBAT/IMe
 Current Write Speed:   12.0x4495=53952KB/s
 Write Speed #0:        12.0x4495=53952KB/s
 Write Speed #1:        10.0x4495=44960KB/s
 Write Speed #2:        8.0x4495=35968KB/s
 Write Speed #3:        6.0x4495=26976KB/s
 Write Speed #4:        4.0x4495=17984KB/s
 Speed Descriptor#0:    08/12088319 R@6.0x4495=26976KB/s W@12.0x4495=53952KB/s
 Speed Descriptor#1:    08/12088319 R@6.0x4495=26976KB/s W@10.0x4495=44960KB/s
 Speed Descriptor#2:    08/12088319 R@6.0x4495=26976KB/s W@8.0x4495=35968KB/s
 Speed Descriptor#3:    08/12088319 R@6.0x4495=26976KB/s W@6.0x4495=26976KB/s
 Speed Descriptor#4:    00/12088319 R@6.0x4495=26976KB/s W@4.0x4495=17984KB/s
BD SPARE AREA INFORMATION:
 Spare Area:            36672/65536=56.0% free
POW RESOURCES INFORMATION:
 Remaining Replacements:16843552
 Remaining Map Entries: 0
 Remaining Updates:     0
READ DISC INFORMATION:
 Disc status:           appendable
 Number of Sessions:    1
 State of Last Session: incomplete
 "Next" Track:          1
 Number of Tracks:      3
READ TRACK INFORMATION[#1]:
 Track State:           partial incremental
 Track Start Address:   0*2KB
 Free Blocks:           0*2KB
 Track Size:            761152*2KB
READ TRACK INFORMATION[#2]:
 Track State:           partial incremental
 Track Start Address:   761152*2KB
 Free Blocks:           0*2KB
 Track Size:            1906976*2KB
READ TRACK INFORMATION[#3]:
 Track State:           incomplete incremental
 Track Start Address:   2668128*2KB
 Next Writable Address: 7925792*2KB
 Free Blocks:           4162528*2KB
 Track Size:            9420192*2KB
FABRICATED TOC:
 Track#1  :             14@0
 Track#AA :             14@12088320
 Multi-session Info:    #1@0
READ CAPACITY:          12088320*2048=24756879360
"""


class TestReadMediaInfo(TestCase):
    def test_total_size_written(self):
        media_info = disc_append.parse_media_info(WRITTEN_BD)
        self.assertEqual(24756879360, media_info.total_size)

    def test_total_size_blank(self):
        media_info = disc_append.parse_media_info(BLANK_BD)
        self.assertEqual(24220008448, media_info.total_size)

    def test_free_size_written(self):
        media_info = disc_append.parse_media_info(WRITTEN_BD)
        self.assertEqual(8524857344, media_info.free_size)

    def test_free_size_blank(self):
        media_info = disc_append.parse_media_info(BLANK_BD)
        self.assertEqual(24220008448, media_info.free_size)

    def test_is_blank_written(self):
        media_info = disc_append.parse_media_info(WRITTEN_BD)
        self.assertFalse(media_info.is_blank)

    def test_is_plank_blank(self):
        media_info = disc_append.parse_media_info(BLANK_BD)
        self.assertTrue(media_info.is_blank)


if __name__ == '__main__':
    unittest.main()
