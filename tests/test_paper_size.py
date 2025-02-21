# -*- coding: utf-8 -*-

import unittest
from nik4.paper_size import get_paper_size

class PaperSizeTestCase(unittest.TestCase):

    def assert_size(self, got, expected):
        if expected is None:
            self.assertIsNone(got)
            return
        self.assertIsInstance(got, list) 
        for i in range(len(expected)):
            self.assertAlmostEqual(got[i], expected[i], 0)

    def test_a4(self):
        self.assert_size(get_paper_size("a4"), [297.0, 210.0])
        self.assert_size(get_paper_size("4"), [297.0, 210.0])
