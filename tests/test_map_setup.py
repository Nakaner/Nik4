# -*- coding: utf-8 -*-

import mapnik
import unittest
import shlex

from nik4.nik4_image import Nik4Image


WEB_MERC = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over'
ExpectedExceptionType = Exception

class MapSettingsTestCase(unittest.TestCase):

    def setUp(self):
        self.parser = Nik4Image.get_argument_parser()

    def get_args_str(self):
        return 'style.xml out.png'

    def get_settings(self, test_str):
        test_str += ' ' + self.get_args_str()
        options = self.parser.parse_args(shlex.split(test_str))
        settings = Nik4Image(options, True)
        settings.setup_options()
        settings.calculate_size_px()
        return settings

    def assert_box(self, got, expected):
        self.assertIsInstance(got, mapnik.Box2d)
        for i in range(len(expected)):
            self.assertAlmostEqual(got[i], expected[i])

    def assert_bbox_size_px_scale_factor(self, args, bbox, size_px, scale, scale_factor):
        settings = self.get_settings(args)
        self.assertFalse(settings.need_cairo)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertAlmostEqual(settings.scale, scale)
        self.assertEqual(settings.size, size_px)
        self.assertAlmostEqual(settings.scale_factor, scale_factor)
        self.assertEqual(settings.fmt, 'png')
        self.assert_box(settings.bbox, bbox)
        return settings

    def assert_size_px_scale_factor(self, args, size_px, scale, scale_factor):
        bbox = [891669.1212541225, 6290146.33132722, 896121.9008858531, 6295247.466433874]
        self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, size_px=size_px, scale=scale, scale_factor=scale_factor)

    def test_zoom_and_bbox(self):
        self.assert_size_px_scale_factor('-z 14 -b 8.01 49.09 8.05 49.12', [466, 534], 9.55462047, 1)

    def test_zoom_and_bbox_ppi300(self):
        self.assert_size_px_scale_factor('-z 14 -b 8.01 49.09 8.05 49.12 --ppi 300', [1541, 1766], 2.88868025, 3.307607497)

    def test_zoom_and_bbox_factor3(self):
        self.assert_size_px_scale_factor('-z 14 -b 8.01 49.09 8.05 49.12 --factor 3', [1398, 1602], 9.55462047/3.0, 3)

    def test_center_zoom_pixel_dimensions(self):
        args = '-c 8.0327 49.0748 -z 14 -x 400 600'
        bbox= [892285.14960208, 6284696.54652795, 896106.99778817, 6290429.31880707]
        scale = 9.5546204652
        size_px = [400, 600]
        scale_factor = 1
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=scale, scale_factor=scale_factor, size_px=size_px)
        self.assertFalse(settings.need_cairo)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertEqual(settings.fmt, 'png')

    def test_only_center_scale(self):
        opts = '-c 8.0327 49.0748 --scale 25000'
        self.assertRaisesRegex(ExpectedExceptionType, 'Image dimensions or scale were not specified in any way', self.get_settings, opts)

    def test_bbox_scale_ppi(self):
        args = '-b 8.0327 49.0748 8.0828 49.1049 --scale 25000 --ppi 90'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        scale = 10.7722048292
        size = [518, 475]
        scale_factor = 0.992282249173
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=scale, scale_factor=scale_factor, size_px=size)
        self.assertFalse(settings.need_cairo)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertEqual(settings.fmt, 'png')

    def test_bbox_scale_ppi_center_size_overspecified(self):
        # size-px is correct
        args = '-b 8.0327 49.0748 8.0828 49.1049 --scale 25000 --ppi 90 -x 1000 917'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        scale = 10.7722048292
        # Mapnik itself will change the bounding box to fit the requested map size.
        size = [1000, 917]
        scale_factor = 0.992282249173
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=scale, scale_factor=scale_factor, size_px=size)
        self.assertFalse(settings.need_cairo)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertEqual(settings.fmt, 'png')

    def test_bbox_scale_ppi_center_size_overspecified2(self):
        # size-px is wrong.
        args = '-b 8.0327 49.0748 8.0828 49.1049 --scale 25000 --ppi 90 -x 1000 1000'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        scale = 10.7722048292
        # Mapnik itself will change the bounding box to fit the requested map size.
        size = [1000, 1000]
        scale_factor = 0.992282249173
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=scale, scale_factor=scale_factor, size_px=size)
        self.assertFalse(settings.need_cairo)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertEqual(settings.fmt, 'png')

    def test_center_scale_ppi_pixels(self):
        args = '-c 8.0327 49.0748 --scale 25000 --ppi 90 -x 400 600'
        bbox = [892042.28552930, 6284332.25041877, 896349.86186095, 6290793.61491624]
        scale = 10.7689408291
        size = [400, 600]
        scale_factor = 0.992282249173
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=scale, scale_factor=scale_factor, size_px=size)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)

    def test_center_scale_ppi_mm(self):
        args = '-c 8.0327 49.0748 --scale 25000 --ppi 90 -d 400 600'
        bbox = [886566.27911769, 6276115.54856614, 901825.86827256, 6299010.31676887]
        scale = 10.7689408291
        size = [1417, 2126]
        scale_factor = 0.992282249173
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=scale, scale_factor=scale_factor, size_px=size)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)

    def test_center_scale_300ppi_mm(self):
        args = '-c 8.0327 49.0748 --scale 25000 --ppi 300 -d 400 600'
        bbox = [886565.20222361,6276115.01011910,901826.94516665,6299010.85521591]
        scale = 3.23068224874
        size = [4724, 7087]
        scale_factor = 3.30760749724
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=scale, scale_factor=scale_factor, size_px=size)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)

    def test_bbox_pixels(self):
        args = '-b 8.0327 49.0748 8.0828 49.1049 -x 400 600'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        size = [400, 600]
        scale_factor = 1
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=scale_factor, size_px=size)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)

    def test_bbox_pixels_sf3(self):
        args = '-b 8.0327 49.0748 8.0828 49.1049 -x 400 600 --factor 3'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        size = [400, 600]
        scale_factor = 3.0
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=scale_factor, size_px=size)

    def test_bbox_pixels_300ppi(self):
        args = '-b 8.0327 49.0748 8.0828 49.1049 -x 400 600 --ppi 300'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        size = [400, 600]
        scale_factor = 3.30760749724
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=scale_factor, size_px=size)
        self.assertEqual(settings.proj_target.expanded(), WEB_MERC)
        self.assertFalse(settings.need_cairo)


if __name__ == "__main__":
        unittest.main()
