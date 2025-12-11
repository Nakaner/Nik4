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
        if expected is None:
            self.assertIsNone(got)
            return
        self.assertIsInstance(got, mapnik.Box2d)
        for i in range(len(expected)):
            self.assertAlmostEqual(got[i], expected[i], 0)

    def assert_projections_equal(self, proj1, proj2_str):
        proj2 = mapnik.Projection(proj2_str)
        trans_def = mapnik.ProjTransform(proj1, proj2).definition()
        # Assert that params of the projections are equal (the simple case, if
        # Mapnik did not call Proj). Otherwise:
        # Defintion of the transformation is supposed to start with "proj=noop"
        # if proj1 and proj2 are equal.
        self.assertTrue(proj1.params() == proj2_str or "proj=noop" in trans_def.split(" "))

    def assert_bbox_size_px_scale_factor(self, args, bbox, size_px, scale, scale_factor, projection=WEB_MERC):
        settings = self.get_settings(args)
        self.assertFalse(settings.need_cairo)
        self.assert_projections_equal(settings.proj_target, projection)
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
        self.assert_size_px_scale_factor('-z 14 -b 8.01 49.09 8.05 49.12', size_px=[466, 534], scale=9.55462047, scale_factor=1)

    def test_zoom_and_bbox_ppi300(self):
        self.assert_size_px_scale_factor('-z 14 -b 8.01 49.09 8.05 49.12 --ppi 300', size_px=[1541, 1766], scale=2.88868025, scale_factor=3.307607497)

    def test_zoom_and_bbox_factor3(self):
        self.assert_size_px_scale_factor('-z 14 -b 8.01 49.09 8.05 49.12 --factor 3', size_px=[1398, 1602], scale=9.55462047/3.0, scale_factor=3)

    def test_zoom_and_bbox_scale(self):
        # overspecified, --scale will be ignored
        for scale in [1.0, 3.0, 10.0, 25.0, 200.0]:
            self.assert_size_px_scale_factor('-z 14 -b 8.01 49.09 8.05 49.12 --scale {}'.format(scale), size_px=[466, 534], scale=9.55462047, scale_factor=1)

    def test_center_zoom_pixel_dimensions(self):
        args = '-c 8.0327 49.0748 -z 14 -x 400 600'
        bbox= [892285.14960208, 6284696.54652795, 896106.99778817, 6290429.31880707]
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=9.5546204652, scale_factor=1, size_px=[400, 600])
        self.assertFalse(settings.need_cairo)
        self.assertEqual(settings.fmt, 'png')

    def test_only_center_scale(self):
        opts = '-c 8.0327 49.0748 --scale 25000'
        self.assertRaisesRegex(ExpectedExceptionType, 'Image dimensions or scale were not specified in any way', self.get_settings, opts)

    def test_bbox_scale_ppi(self):
        args = '-b 8.0327 49.0748 8.0828 49.1049 --scale 25000 --ppi 90'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=10.7722048292, scale_factor=0.992282249173, size_px=[518, 475])
        self.assertFalse(settings.need_cairo)
        self.assertEqual(settings.fmt, 'png')

    def test_bbox_scale_ppi_center_size_overspecified(self):
        # size-px is correct
        args = '-b 8.0327 49.0748 8.0828 49.1049 --scale 25000 --ppi 90 -x 1000 917'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        # Mapnik itself will change the bounding box to fit the requested map size.
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=10.7722048292, scale_factor=0.992282249173, size_px=[1000, 917])
        self.assertFalse(settings.need_cairo)
        self.assertEqual(settings.fmt, 'png')

    def test_bbox_scale_ppi_center_size_overspecified2(self):
        # size-px is wrong.
        args = '-b 8.0327 49.0748 8.0828 49.1049 --scale 25000 --ppi 90 -x 1000 1000'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        # Mapnik itself will change the bounding box to fit the requested map size.
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=10.7722048292, scale_factor=0.992282249173, size_px=[1000, 1000])
        self.assertFalse(settings.need_cairo)
        self.assertEqual(settings.fmt, 'png')

    def test_bbox_center_size_overspecified(self):
        args = '-b 8.1049 49.0822 8.2108 49.1515 -c 8.1253 49.0822 -x 1000 1000'
        bbox = [902233, 6288821, 914022, 6300607]
        self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=1, size_px=[1000, 1000])

    def test_center_sizepx_size_overspecified(self):
        args = '-c 8.1253 49.0822 -x 1000 1000 -d 297 210'
        # Bounding box is not set and no exeception is raised. Instead, Mapnik will raise the exception after parsing the style.
        self.assert_bbox_size_px_scale_factor(args=args, bbox=None, scale=None, scale_factor=1, size_px=[1000, 1000])
        #self.assertRaisesRegex(ExpectedExceptionType, 'Image dimensions or scale were not specified in any way', self.get_settings, args)

    def test_bbox_sizepx_size_overspecified(self):
        args = '-b 8.1049 49.0822 8.2108 49.1515 -x 1000 1000 -d 297 210'
        bbox = [902233, 6288821, 914022, 6300607]
        self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=1, size_px=[1000, 1000])
        #self.assertRaisesRegex(ExpectedExceptionType, 'Image dimensions or scale were not specified in any way', self.get_settings, args)

    def test_center_sizepx_size_zoom_overspecified(self):
        args = '-c 8.1253 49.0822 -x 1000 1000 -d 297 210 -z 14'
        bbox = [899727, 6284043, 909282, 6293598]
        self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=9.55462047, scale_factor=1, size_px=[1000, 1000])

    def test_center_scale_ppi_pixels(self):
        args = '-c 8.0327 49.0748 --scale 25000 --ppi 90 -x 400 600'
        bbox = [892042.28552930, 6284332.25041877, 896349.86186095, 6290793.61491624]
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=10.7689408291, scale_factor=0.992282249173, size_px=[400, 600])

    def test_center_scale_ppi_mm(self):
        args = '-c 8.0327 49.0748 --scale 25000 --ppi 90 -d 400 600'
        bbox = [886566.27911769, 6276115.54856614, 901825.86827256, 6299010.31676887]
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=10.7689408291, scale_factor=0.992282249173, size_px=[1417, 2126])

    def test_center_scale_300ppi_mm(self):
        args = '-c 8.0327 49.0748 --scale 25000 --ppi 300 -d 400 600'
        bbox = [886565.20222361,6276115.01011910,901826.94516665,6299010.85521591]
        scale = 3.23068224874
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=scale, scale_factor=3.30760749724, size_px=[4724, 7087])

    def test_bbox_pixels(self):
        args = '-b 8.0327 49.0748 8.0828 49.1049 -x 400 600'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=1, size_px=[400, 600])

    def test_bbox_pixels_sf3(self):
        args = '-b 8.0327 49.0748 8.0828 49.1049 -x 400 600 --factor 3'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=3.0, size_px=[400, 600])

    def test_bbox_pixels_300ppi(self):
        args = '-b 8.0327 49.0748 8.0828 49.1049 -x 400 600 --ppi 300'
        bbox = [894196.07369513, 6287562.93266751, 899773.18018387, 6292679.50961837]
        settings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=3.30760749724, size_px=[400, 600])
        self.assertFalse(settings.need_cairo)

    def test_paper_a4(self):
        args = '-b 8.0252 49.0748 8.0903 49.1049 --ppi 300'
        bbox = [893361, 6287563, 900608, 6292680]
        # Landscape and auto rotated A4 paper
        for p in ['a4', '4', '+a4', '+4']:
           self.assert_bbox_size_px_scale_factor(args='{} --paper {}'.format(args, p), bbox=bbox, scale=None, scale_factor=3.30760749724, size_px=[round(297 * (300 / 25.4)), round(210 * (300 / 25.4))])
        # Portrait, Mapnik will change the bounding box but we cannot test this here.
        for p in ['-a4', '-4']:
           self.assert_bbox_size_px_scale_factor(args='{} --paper={}'.format(args, p), bbox=bbox, scale=None, scale_factor=3.30760749724, size_px=[round(210 * (300 / 25.4)), round(297 * (300 / 25.4))])

    def test_paper_a4_norotate(self):
        args = '-b 8.0252 49.0597 8.0903 49.129 --norotate --ppi 300'
        bbox = [893361, 6284997, 900608, 6296778]
        expected_size = [round(297 * (300 / 25.4)), round(210 * (300 / 25.4))]
        # landscape
        for p in ['+a4', '+4']:
           self.assert_bbox_size_px_scale_factor(args='{} --paper={}'.format(args, p), bbox=bbox, scale=None, scale_factor=3.30760749724, size_px=expected_size)
        # portrait
        expected_size.reverse()
        for p in ['-a4', '-4']:
           self.assert_bbox_size_px_scale_factor(args='{} --paper={}'.format(args, p), bbox=bbox, scale=None, scale_factor=3.30760749724, size_px=expected_size)

    def test_paper_margin(self):
        args = '-b 8.0252 49.0748 8.0903 49.1049 --paper a4 --ppi 300 --margin 5'
        bbox = [893361, 6287563, 900608, 6292680]
        # Landscape and auto rotated A4 paper
        for p in ['a4', '4', '+a4', '+4']:
           self.assert_bbox_size_px_scale_factor(args='{} --paper {}'.format(args, p), bbox=bbox, scale=None, scale_factor=3.30760749724, size_px=[round(287 * (300 / 25.4)), round(200 * (300 / 25.4))])

    def test_margin_size_mm(self):
        args = '-b 8.0252 49.0748 8.0903 49.1049 -d 297 210 --ppi 300 --margin 5'
        bbox = [893361, 6287563, 900608, 6292680]
        self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=3.30760749724, size_px=[round(287 * (300 / 25.4)), round(200 * (300 / 25.4))])

    def test_margin_noop(self):
        """--margin is support with --paper or --size only. If size is specified in pixels, it will be ignored.
        """
        args = '-b 8.0252 49.0748 8.0903 49.1049 -x 3508 2480 --ppi 300 --margin 5'
        bbox = [893361, 6287563, 900608, 6292680]
        self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=None, scale_factor=3.30760749724, size_px=[3508, 2480])

    def test_projection_umt32n_bbox(self):
        """--margin is support with --paper or --size only. If size is specified in pixels, it will be ignored.
        """
        if not mapnik.has_proj():
            return
        args = '-b 8.0252 49.0748 8.0903 49.1049 -x 1000 1000 -P 25832 -z 14'
        bbox = [428808, 5436170, 433602, 5439575]
        setings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=6.3212818, scale_factor=1.0, size_px=[1000, 1000], projection='+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs +type=crs')

    def test_projection_umt32n_center(self):
        """--margin is support with --paper or --size only. If size is specified in pixels, it will be ignored.
        """
        if not mapnik.has_proj():
            return
        args = '-c 8.0252 49.0748 -x 1000 1000 -P 25832 -z 14'
        bbox = [425634, 5433054, 431982, 5439403]
        setings = self.assert_bbox_size_px_scale_factor(args=args, bbox=bbox, scale=6.3486878, scale_factor=1.0, size_px=[1000, 1000], projection='+proj=utm +zone=32 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs +type=crs')



if __name__ == "__main__":
        unittest.main()
