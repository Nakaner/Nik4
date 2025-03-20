# -*- coding: utf-8 -*-

import mapnik
import os
import unittest
import shlex

from nik4.nik4_image import Nik4Image
from nik4.utils import prepare_map


SCRIPTDIR = os.path.dirname(os.path.abspath(__file__))

class FitLayerTest(unittest.TestCase):

    def setUp(self):
        self.parser = Nik4Image.get_argument_parser()

    def get_map(self, args, style, output):
        args = '{} "{}/{}" "{}"'.format(args, SCRIPTDIR, style, output)
        options = self.parser.parse_args(shlex.split(args))
        settings = Nik4Image(options, True)
        settings.setup_options()
        m = prepare_map(options, settings)
        return m

    def assert_box(self, got, expected):
        if expected is None:
            self.assertIsNone(got)
            return
        self.assertIsInstance(got, mapnik.Box2d)
        for i in range(len(expected)):
            self.assertAlmostEqual(got[i], expected[i], delta=1)

    def create_map_and_assert(self, args, bbox, style, output):
        m = self.get_map(args, style, output)
        m_bbox = m.envelope()
        self.assert_box(m_bbox, bbox)

    def test_no_fitting(self):
        args = "-b -40.6304 28.5457 32.0553 71.0205 -x 400 400"
        style = "data/maps/world-test-2.xml"
        output = "out.png"
        bbox = [-4522956, 3317949, 3568380, 11409286]
        self.create_map_and_assert(args, bbox, style, output)

    def test_fitting(self):
        args = "-b -40.6304 28.5457 32.0553 71.0205 -x 400 400 --fit cities"
        style = "data/maps/world-test-cities-limited.xml"
        output = "out.png"
        bbox = [182753, 4571870, 2031937, 8045173]
        self.create_map_and_assert(args, bbox, style, output)
