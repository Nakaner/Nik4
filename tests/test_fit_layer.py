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

    def test_bbox_larger_than_layer(self):
        """If the bounding box is larger than the layer, the bbox of the map
        will not be shrinked to make the layer fill it as good as possible.
        However, the padding (default 5 pixel) will be applied.
        """
        args = "-b -40.6304 28.5457 32.0553 71.0205 -x 400 400 --fit cities"
        style = "data/maps/world-test-cities-limited.xml"
        output = "out.png"
        bbox = [-4884119.0, 2956786.5, 3929543.2, 11770448.7]
        self.create_map_and_assert(args, bbox, style, output)

    def test_bbox_larger_than_layer_pad0(self):
        """Almost identical test setting as test_bbox_larger_than_layer but
        with --padding 0. The bounding box should not be the same.
        """
        args = "-b -40.6304 28.5457 32.0553 71.0205 -x 400 400 --fit cities --padding 0"
        style = "data/maps/world-test-cities-limited.xml"
        output = "out.png"
        bbox = [-4522956, 3317949, 3568380, 11409286]
        self.create_map_and_assert(args, bbox, style, output)

    def test_bbox_smaller_than_layer(self):
        """If the bounding box is larger than the layer, the bbox of the map
        will not be shrinked to make the layer fill it as good as possible.
        However, the padding (default 5 pixel) will be applied.
        """
        args = "-b 8.3248 49.2175 11.7525 51.4607 -x 400 400 --fit cities"
        style = "data/maps/world-test-cities-limited.xml"
        output = "out.png"
        bbox = [-1077887.6, 4911033.7, 2384325.5, 8373246.8]
        self.create_map_and_assert(args, bbox, style, output)

    def test_bbox_smaller_than_layer_no_padding(self):
        args = "-b 8.3248 49.2175 11.7525 51.4607 -x 400 400 --fit cities --padding 0"
        style = "data/maps/world-test-cities-limited.xml"
        output = "out.png"
        bbox = [-957908.6, 5031012.7, 2264346.5, 8253267.9]
        self.create_map_and_assert(args, bbox, style, output)

    def test_bbox_smaller_than_layer_no_pixels(self):
        args = "-b 8.3248 49.2175 11.7525 51.4607 --fit cities"
        style = "data/maps/world-test-cities-limited.xml"
        output = "out.png"
        bbox = [182753, 4571870, 2031937, 8045173]
        with self.assertRaises(Exception):
            self.get_map(args, style, output)
