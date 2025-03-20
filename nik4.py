#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Nik4: Export image from mapnik
# Run it with -h to see the list of options
# Written by Ilya Zverev, licensed WTFPL

import mapnik
import sys
import os
import re
import argparse
import math
import tempfile
import logging

from nik4.nik4_image import Nik4Image, EPSG_3857
from nik4.utils import prepare_map

try:
    import cairo
    HAS_CAIRO = True
except ImportError:
    HAS_CAIRO = False

TILE_BUFFER = 128
IM_MONTAGE = 'montage'



def prepare_ozi(mbbox, mwidth, mheight, name, transform):
    """Create georeferencing file for OziExplorer"""
    def deg(value, is_lon):
        degrees = math.floor(abs(value))
        minutes = (abs(value) - degrees) * 60
        return '{:4d},{:3.5F},{}'.format(
            int(round(degrees)), minutes,
            ('W' if is_lon else 'S') if value < 0 else ('E' if is_lon else 'N'))

    ozipoint = ('Point{:02d},xy,     ,     ,in, deg,    ,        ,N,    ,        ,E' +
                ', grid,   ,           ,           ,N')
    bbox = transform.backward(mbbox)
    points = "\n".join([ozipoint.format(n) for n in range(3, 31)])
    header = '''OziExplorer Map Data File Version 2.2
Nik4
{name}
1 ,Map Code,
WGS 84,WGS 84,   0.0000,   0.0000,WGS 84
Reserved 1
Reserved 2
Magnetic Variation,,,E
Map Projection,Mercator,PolyCal,No,AutoCalOnly,No,BSBUseWPX,No
Point01,xy,    0,    0,in, deg,{top},{left}, grid,   ,           ,           ,N
Point02,xy, {width:4d}, {height:4d},in, deg,{bottom},{right}, grid,   ,           ,           ,N
{points}
Projection Setup,,,,,,,,,,
Map Feature = MF ; Map Comment = MC     These follow if they exist
Track File = TF      These follow if they exist
Moving Map Parameters = MM?    These follow if they exist
MM0,Yes
MMPNUM,4
MMPXY,1,0,0
'''.format(name=name,
           top=deg(bbox.maxy, False),
           left=deg(bbox.minx, True),
           width=mwidth - 1,
           height=mheight - 1,
           bottom=deg(bbox.miny, False),
           right=deg(bbox.maxx, True),
           points=points)
    return ''.join([
        header,
        "MMPXY,2,{},0\n".format(mwidth),
        "MMPXY,3,{},{}\n".format(mwidth, mheight),
        "MMPXY,4,0,{}\n".format(mheight),
        'MMPLL,1,{:4.6f},{:4.6f}\n'.format(bbox.minx, bbox.maxy),
        'MMPLL,2,{:4.6f},{:4.6f}\n'.format(bbox.maxx, bbox.maxy),
        'MMPLL,3,{:4.6f},{:4.6f}\n'.format(bbox.maxx, bbox.miny),
        'MMPLL,4,{:4.6f},{:4.6f}\n'.format(bbox.minx, bbox.miny),
        "MM1B,{}\n".format((mbbox.maxx - mbbox.minx) / mwidth * math.cos(
            math.radians(bbox.center().y))),
        "MOP,Map Open Position,0,0\n",
        "IWH,Map Image Width/Height,{},{}\n".format(mwidth, mheight),
    ])


def prepare_wld(bbox, mwidth, mheight):
    """Create georeferencing world file"""
    pixel_x_size = (bbox.maxx - bbox.minx) / mwidth
    pixel_y_size = (bbox.maxy - bbox.miny) / mheight
    left_pixel_center_x = bbox.minx + pixel_x_size * 0.5
    top_pixel_center_y = bbox.maxy - pixel_y_size * 0.5
    return ''.join(["{:.8f}\n".format(n) for n in [
        pixel_x_size, 0.0,
        0.0, -pixel_y_size,
        left_pixel_center_x, top_pixel_center_y
    ]])


def write_metadata(bbox, mwidth, mheight, transform, img_output_file, wld_file=None, ozi_file=None):
    """Write worldfile and/or OZI file if required.

    Parameters
    ----------
    bbox: mapnik.Box2d
        bounding box of the map
    mwidth : int
        width of the image
    mheight : int
        height of the image
    transform : mapnik.ProjTransform
        transformation from EPSG:4326 to the target projection
    img_output_file : str
        image output path (required for OZI file)
    wld : file
        file pointer to the world file to be written (or None if non has to be written)
    ozi : file
        file pointer to the OZI file to be written (or None if non has to be written)
    """
    if ozi_file:
        ozi_file.write(prepare_ozi(bbox, mwidth, mheight, img_output_file, transform))
    if wld_file:
        wld_file.write(prepare_wld(bbox, mwidth, mheight))


def run(options, settings):
    m = prepare_map(options, settings)
    outfile = options.output
    if options.output == '-':
        outfile = tempfile.TemporaryFile(mode='w+b')

    if settings.need_cairo:
        if HAS_CAIRO:
            if settings.fmt == 'svg':
                surface = cairo.SVGSurface(outfile, settings.size[0], settings.size[1])
            else:
                surface = cairo.PDFSurface(outfile, settings.size[0], settings.size[1])
            mapnik.render(m, surface, settings.scale_factor, 0, 0)
            surface.finish()
        else:
            mapnik.render_to_file(m, outfile, settings.fmt)
        write_metadata(m.envelope(), settings.size[0], settings.size[1], settings.transform, options.output, options.wld, options.ozi)
    else:
        if settings.tiles_x == settings.tiles_y == 1:
            im = mapnik.Image(settings.size[0], settings.size[1])
            mapnik.render(m, im, settings.scale_factor)
            im.save(outfile, settings.fmt)
            write_metadata(m.envelope(), settings.size[0], settings.size[1], settings.transform, options.output, options.wld, options.ozi)
        else:
            # we cannot make mapnik calculate scale for us, so fixing aspect ratio outselves
            rdiff = (settings.bbox.maxx-settings.bbox.minx) / (settings.bbox.maxy-settings.bbox.miny) - settings.size[0] / settings.size[1]
            if rdiff > 0:
                settings.bbox.height((settings.bbox.maxx - settings.bbox.minx) * settings.size[1] / settings.size[0])
            elif rdiff < 0:
                settings.bbox.width((settings.bbox.maxy - settings.bbox.miny) * settings.size[0] / settings.size[1])
            settings.scale = (settings.bbox.maxx - settings.bbox.minx) / settings.size[0]
            width = max(32, int(math.ceil(1.0 * settings.size[0] / settings.tiles_x)))
            height = max(32, int(math.ceil(1.0 * settings.size[1] / settings.tiles_y)))
            m.resize(width, height)
            m.buffer_size = TILE_BUFFER
            tile_cnt = [int(math.ceil(1.0 * settings.size[0] / width)),
                        int(math.ceil(1.0 * settings.size[1] / height))]
            logging.debug('tile_count=%s %s', tile_cnt[0], tile_cnt[1])
            logging.debug('tile_size=%s,%s', width, height)
            tmp_tile = '{:02d}_{:02d}_{}'
            tile_files = []
            for row in range(0, tile_cnt[1]):
                for column in range(0, tile_cnt[0]):
                    logging.debug('tile=%s,%s', row, column)
                    tile_bbox = mapnik.Box2d(
                        settings.bbox.minx + 1.0 * width * settings.scale * column,
                        settings.bbox.maxy - 1.0 * height * settings.scale * row,
                        settings.bbox.minx + 1.0 * width * settings.scale * (column + 1),
                        settings.bbox.maxy - 1.0 * height * settings.scale * (row + 1))
                    tile_size = [
                        width if column < tile_cnt[0] - 1 else settings.size[0] - width * (tile_cnt[0] - 1),
                        height if row < tile_cnt[1] - 1 else settings.size[1] - height * (tile_cnt[1] - 1)]
                    m.zoom_to_box(tile_bbox)
                    im = mapnik.Image(tile_size[0], tile_size[1])
                    mapnik.render(m, im, settings.scale_factor)
                    tile_name = tmp_tile.format(row, column, options.output)
                    im.save(tile_name, settings.fmt)
                    if options.just_tiles:
                        # write ozi/wld for a tile if needed
                        if '.' not in tile_name:
                            tile_basename = tile_name + '.'
                        else:
                            tile_basename = tile_name[0:tile_name.rindex('.')+1]
                        if options.ozi:
                            with open(tile_basename + 'ozi', 'w') as f:
                                f.write(prepare_ozi(tile_bbox, tile_size[0], tile_size[1],
                                                    tile_basename + '.ozi', settings.transform))
                        if options.wld:
                            with open(tile_basename + 'wld', 'w') as f:
                                f.write(prepare_wld(tile_bbox, tile_size[0], tile_size[1]))
                    else:
                        tile_files.append(tile_name)
            if not options.just_tiles:
                # join tiles and remove them if joining succeeded
                import subprocess
                result = subprocess.call([
                    IM_MONTAGE, '-geometry', '+0+0', '-tile',
                    '{}x{}'.format(tile_cnt[0], tile_cnt[1])] +
                    tile_files + [options.output])
                if result == 0:
                    for tile in tile_files:
                        os.remove(tile)
                    write_metadata(bbox, size[0], size[1], transform, options.output, options.wld, options.ozi)

    if options.output == '-':
        if sys.platform == "win32":
            # fix binary output on windows
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

        outfile.seek(0)
        sys.stdout.write(outfile.read())
        outfile.close()


if __name__ == "__main__":
    options = Nik4Image.get_argument_parser().parse_args()
    if options.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
    settings = Nik4Image(options, HAS_CAIRO)
    settings.setup_options()
    logging.info(settings.__dict__)
    run(options, settings)
