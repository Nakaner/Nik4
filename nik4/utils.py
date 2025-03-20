# -*- coding: utf-8 -*-
# Nik4: Export image from mapnik
# Written by Ilya Zverev, licensed WTFPL

import codecs
import logging
import mapnik
import os
import re
import sys

def layer_bbox(m, names, proj_target, bbox=None):
    """Calculate extent of given layers and bbox"""
    for layer in (l for l in m.layers if l.name in names):
        # it may as well be a GPX layer in WGS84
        layer_proj = mapnik.Projection(layer.srs)
        box_trans = mapnik.ProjTransform(layer_proj, proj_target)
        lbbox = box_trans.forward(layer.envelope())
        if bbox:
            bbox.expand_to_include(lbbox)
        else:
            bbox = lbbox
    return bbox


def filter_layers(m, lst):
    """Leave only layers in list active, disable others"""
    for l in m.layers:
        l.active = l.name in lst


def select_layers(m, enable, disable):
    """Enable and disable layers in corresponding lists"""
    for l in m.layers:
        if l.name in enable:
            l.active = True
        if l.name in disable:
            l.active = False


def xml_vars(style, variables):
    """Replace ${name:default} from style with variables[name] or 'default'"""
    # Convert variables to a dict
    v = {}
    for kv in variables:
        keyvalue = kv.split('=', 1)
        if len(keyvalue) > 1:
            v[keyvalue[0]] = keyvalue[1].replace('&', '&amp;').replace(
                '<', '&lt;').replace('>', '&gt;').replace(
                '"', '&quot;').replace("'", '&#39;')
    if not v:
        return style
    # Scan all variables in style
    r = re.compile(r'\$\{([a-z0-9_]+)(?::([^}]*))?\}')
    rstyle = ''
    last = 0
    for m in r.finditer(style):
        if m.group(1) in v:
            value = v[m.group(1)]
        elif m.group(2) is not None:
            value = m.group(2)
        else:
            raise Exception('Found required style parameter: ' + m.group(1))
        rstyle = rstyle + style[last:m.start()] + value
        last = m.end()
    if last < len(style):
        rstyle = rstyle + style[last:]
    return rstyle


def reenable_layers(style, layers):
    """Remove status=off from layers we need."""
    layer_select = '|'.join([l.replace('\\', '\\\\').replace('|', '\\|')
                             .replace('.', '\\.').replace('+', '\\+')
                             .replace('*', '\\*') for l in layers])
    style = re.sub(
        r'(<Layer[^>]+name=["\'](?:{})["\'][^>]+)status=["\']off["\']'.format(layer_select),
        r'\1', style, flags=re.DOTALL)
    style = re.sub(
        r'(<Layer[^>]+)status=["\']off["\']([^>]+name=["\'](?:{})["\'])'.format(layer_select),
        r'\1\2', style, flags=re.DOTALL)
    return style


def parse_layers_string(layers):
    if not layers:
        return []
    return [l1 for l1 in (l.strip() for l in layers.split(',')) if l1]


def add_fonts(path):
    if os.path.exists(path):
        mapnik.register_fonts(path)
    else:
        raise Exception('The directory "{p}" does not exists'.format(p=path))


def init_mapnik_map(settings, style_xml, style_path):
    # for layer processing we need to create the Map object
    m = mapnik.Map(100, 100)  # temporary size, will be changed before output
    mapnik.load_map_from_string(m, style_xml.encode("utf-8"), False, style_path)
    m.srs = settings.proj_target.params()
    return m


def prepare_map(options, settings):
    style_xml, style_path = read_style(options)

    m = init_mapnik_map(settings, style_xml, style_path)

    # register non-standard fonts
    if options.fonts:
        for f in options.fonts:
            add_fonts(f)

    # get bbox from layer extents
    if options.fit:
        bbox_from_layer = layer_bbox(m, settings.options.fit.split(','), settings.proj_target, settings.bbox)
        settings.fit_to_layer(bbox_from_layer)

    # bbox should be specified by this point
    if not settings.bbox:
        raise Exception('Bounding box was not specified in any way')

    # rotate image to fit bbox better
    if settings.rotate and settings.size:
        settings.rotate_if_necessary()

    # calculate pixel size from bbox and scale
    settings.calculate_size_px()

    if options.output == '-' or (settings.need_cairo and (settings.tiles_x > 1 or settings.tiles_y > 1)):
        settings.tiles_x = 1
        settings.tiles_y = 1
    max_img_size = max(settings.size[0] / settings.tiles_x, settings.size[1] / settings.tiles_y)
    if max_img_size > 16384:
        raise Exception('Image size exceeds mapnik limit ({} > {}), use {}--tiles'.format(
           max_img_size , 16384, 'a larger value for ' if settings.tiles_x > 1 or settings.tiles_y > 1 else ''))

    # add / remove some layers
    if options.layers:
        filter_layers(m, parse_layers_string(options.layers))
    if options.add_layers or options.hide_layers:
        select_layers(m, parse_layers_string(options.add_layers),
                      parse_layers_string(options.hide_layers))

    logging.debug('scale=%s', settings.scale)
    logging.debug('scale_factor=%s', settings.scale_factor)
    logging.debug('size=%s,%s', settings.size[0], settings.size[1])
    logging.debug('bbox=%s', settings.bbox)
    logging.debug('bbox_wgs84=%s', settings.transform.backward(settings.bbox) if settings.bbox else None)
    logging.debug('layers=%s', ','.join([l.name for l in m.layers if l.active]))

    # export image
    m.aspect_fix_mode = mapnik.aspect_fix_mode.GROW_BBOX
    m.resize(settings.size[0], settings.size[1])
    m.zoom_to_box(settings.bbox)
    logging.debug('m.envelope(): {}'.format(m.envelope()))

    return m


def read_style(options):
    """Reading style xml into memory for preprocessing.
    """
    style_path = ''
    if options.style == '-':
        style_xml = sys.stdin.read()
    else:
        with codecs.open(options.style, 'r', 'utf-8') as style_file:
            style_xml = style_file.read()
        style_path = os.path.dirname(options.style)
    if options.base:
        style_path = options.base
    if options.vars:
        style_xml = xml_vars(style_xml, options.vars)
    if options.layers or options.add_layers:
        style_xml = reenable_layers(
            style_xml, parse_layers_string(options.layers) +
            parse_layers_string(options.add_layers))
    return style_xml, style_path


