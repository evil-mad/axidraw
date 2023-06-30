#
# Copyright 2023 Windell H. Oskay, Evil Mad Scientist Laboratories
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""
preview.py

Classes for managing AxiDraw plot preview data

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw


"""

# import time
import math
from lxml import etree

from axidrawinternal.plot_utils_import import from_dependency_import
simpletransform = from_dependency_import('ink_extensions.simpletransform')
simplestyle = from_dependency_import('ink_extensions.simplestyle')
inkex = from_dependency_import('ink_extensions.inkex')
plot_utils = from_dependency_import('plotink.plot_utils')

# ebb_serial = from_dependency_import('plotink.ebb_serial')  # https://github.com/evil-mad/plotink
# ebb_motion = from_dependency_import('plotink.ebb_motion')


class VelocityChart:
    """
    Preview: Class for velocity data plots
    """

    def __init__(self):
        self.enable = False # Velocity charts are disabled by default. (Set True to enable.
        self.vel_data_time = 0
        self.vel_chart1 = [] # Velocity chart, for preview of velocity vs time Motor 1
        self.vel_chart2 = []  # Velocity chart, for preview of velocity vs time Motor 2
        self.vel_data_chart_t = [] # Velocity chart, for preview of velocity vs time Total V

    def reset(self):
        """ Clear data; reset for a new plot. """
        self.vel_data_time = 0
        self.vel_chart1.clear()
        self.vel_chart2.clear()
        self.vel_data_chart_t.clear()

    def rest(self, ad_ref, v_time):
        """
        Update velocity charts and plot time estimate with a zero-velocity segment for
        given time duration; typically used after raising or lowering the pen.
        """
        if not ad_ref.options.preview:
            return
        ad_ref.plot_status.stats.pt_estimate += v_time
        if not self.enable:
            return
        self.update(ad_ref, 0, 0, 0)
        self.vel_data_time += v_time
        self.update(ad_ref, 0, 0, 0)

    def update(self, ad_ref, v_1, v_2, v_tot):
        """ Update velocity charts, using some appropriate scaling for X and Y display."""

        if not (ad_ref.options.preview and self.enable):
            return
        temp_time = self.vel_data_time / 1000.0
        scale_factor = 10.0 / ad_ref.options.resolution
        self.vel_chart1.append(f' {temp_time:0.3f} {8.5 - v_1 / scale_factor:0.3f}')
        self.vel_chart2.append(f' {temp_time:0.3f} {8.5 - v_2 / scale_factor:0.3f}')
        self.vel_data_chart_t.append(f' {temp_time:0.3f} {8.5 - v_tot / scale_factor:0.3f}')


class Preview:
    """
    Preview: Main class for organizing preview and rendering
    """

    def __init__(self):
        self.path_data_pu = []  # pen-up path data for preview layers
        self.path_data_pd = []  # pen-down path data for preview layers
        self.v_chart = VelocityChart()
        self.preview_pen_state = -1 # to be moved from pen handling

    def reset(self):
        """ Clear all data; reset for a new plot. """
        self.path_data_pu.clear()
        self.path_data_pd.clear()
        self.v_chart.reset()
        self.preview_pen_state = -1 # to be moved from pen handling

    def log_sm_move(self, ad_ref, move):
        """ Log data from single "SM" move for rendering that move in preview rendering """

        if not ad_ref.options.rendering:
            return

        # 'SM' move is formatted as:
        # ['SM', (move_steps2, move_steps1, move_time), seg_data]
        # where seg_data begins with:
        #   * final x position, float
        #   * final y position, float
        #   * final pen_up state, boolean
        #   * travel distance (inch)

        move_steps2 = move[1][0]
        move_steps1 = move[1][1]
        move_time = move[1][2]
        f_new_x = move[2][0]
        f_new_y = move[2][1]

        if self.v_chart.enable:
            vel_1 = move_steps1 / float(move_time)
            vel_2 = move_steps2 / float(move_time)
            vel_tot = plot_utils.distance(move_steps1, move_steps2) / float(move_time)
            self.v_chart.update(ad_ref, vel_1, vel_2, vel_tot)
            self.v_chart.vel_data_time += move_time
            self.v_chart.update(ad_ref, vel_1, vel_2, vel_tot)
        if ad_ref.rotate_page:
            if ad_ref.params.auto_rotate_ccw: # Rotate counterclockwise 90 degrees
                x_new_t = ad_ref.svg_width - f_new_y
                y_new_t = f_new_x
                x_old_t = ad_ref.svg_width - ad_ref.pen.phys.ypos
                y_old_t = ad_ref.pen.phys.xpos
            else:
                x_new_t = f_new_y
                x_old_t = ad_ref.pen.phys.ypos
                y_new_t = ad_ref.svg_height - f_new_x
                y_old_t = ad_ref.svg_height - ad_ref.pen.phys.xpos
        else:
            x_new_t = f_new_x
            y_new_t = f_new_y
            x_old_t = ad_ref.pen.phys.xpos
            y_old_t = ad_ref.pen.phys.ypos
        if ad_ref.pen.phys.z_up:
            if ad_ref.options.rendering > 1: # Render pen-up movement
                if ad_ref.pen.status.preview_pen_state != 1:
                    self.path_data_pu.append(f'M{x_old_t:0.3f} {y_old_t:0.3f}')
                    ad_ref.pen.status.preview_pen_state = 1
                self.path_data_pu.append(f' {x_new_t:0.3f} {y_new_t:0.3f}')
        else:
            if ad_ref.options.rendering in [1, 3]: # Render pen-down movement
                if ad_ref.pen.status.preview_pen_state != 0:
                    self.path_data_pd.append(f'M{x_old_t:0.3f} {y_old_t:0.3f}')
                    ad_ref.pen.status.preview_pen_state = 0
                self.path_data_pd.append(f' {x_new_t:0.3f} {y_new_t:0.3f}')

    def render(self, ad_ref):
        """ Render preview layers in the SVG document """

        if not ad_ref.options.preview:
            return

        # Remove old preview layers, whenever preview mode is enabled
        for node in ad_ref.svg:
            if node.tag in ('{http://www.w3.org/2000/svg}g', 'g'):
                if node.get('{http://www.inkscape.org/namespaces/inkscape}groupmode') == 'layer':
                    layer_name = node.get('{http://www.inkscape.org/namespaces/inkscape}label')
                    if layer_name == '% Preview':
                        ad_ref.svg.remove(node)

        if ad_ref.options.rendering == 0: # If preview rendering is disabled
            return

        s_x, s_y, o_x, o_y = ad_ref.vb_stash

        preview_transform = simpletransform.parseTransform(
            f'translate({-o_x:.6E},{-o_y:.6E}) scale({1.0/s_x:.6E},{1.0/s_y:.6E})')
        path_attrs = { 'transform': simpletransform.formatTransform(preview_transform)}
        preview_layer = etree.Element(inkex.addNS('g', 'svg'),
            path_attrs, nsmap=inkex.NSS)

        preview_sl_u = etree.SubElement(preview_layer, inkex.addNS('g', 'svg'))
        preview_sl_d = etree.SubElement(preview_layer, inkex.addNS('g', 'svg'))

        preview_layer.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
        preview_layer.set(inkex.addNS('label', 'inkscape'), '% Preview')
        preview_sl_d.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
        preview_sl_d.set(inkex.addNS('label', 'inkscape'), 'Pen-down movement')
        preview_sl_u.set(inkex.addNS('groupmode', 'inkscape'), 'layer')
        preview_sl_u.set(inkex.addNS('label', 'inkscape'), 'Pen-up movement')

        ad_ref.svg.append(preview_layer)

        # Preview stroke width: Lesser of 1/1000 of page width or height:
        width_du = min(ad_ref.svg_width , ad_ref.svg_height) / 1000.0

        """
        Stroke-width is a css style element, and cannot accept scientific notation.

        Thus, in cases with large scaling (i.e., high values of 1/sx, 1/sy) resulting
        from the viewbox attribute of the SVG document, it may be necessary to use
        a _very small_ stroke width, so that the stroke width displayed on the screen
        has a reasonable width after being displayed greatly magnified by the viewbox.

        Use log10(the number) to determine the scale, and thus the precision needed.
        """
        log_ten = math.log10(width_du)
        if log_ten > 0:  # For width_du > 1
            width_string = f'{width_du:.3f}'
        else:
            prec = int(math.ceil(-log_ten) + 3)
            width_string = f'{width_du:.{prec}f}'

        p_style = {'stroke-width': width_string, 'fill': 'none',
            'stroke-linejoin': 'round', 'stroke-linecap': 'round'}

        ns_prefix = "plot"
        if ad_ref.options.rendering > 1:
            p_style.update({'stroke': ad_ref.params.preview_color_up})
            path_attrs = {
                'style': simplestyle.formatStyle(p_style),
                'd': " ".join(self.path_data_pu),
                inkex.addNS('desc', ns_prefix): "pen-up transit"}
            etree.SubElement(preview_sl_u,
                             inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

        if ad_ref.options.rendering in (1, 3):
            p_style.update({'stroke': ad_ref.params.preview_color_down})
            path_attrs = {
                'style': simplestyle.formatStyle(p_style),
                'd': " ".join(self.path_data_pd),
                inkex.addNS('desc', ns_prefix): "pen-down drawing"}
            etree.SubElement(preview_sl_d,
                             inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

        if ad_ref.options.rendering > 0 and self.v_chart.enable: # Preview enabled w/ velocity
            self.v_chart.vel_chart1.insert(0, "M")
            self.v_chart.vel_chart2.insert(0, "M")
            self.v_chart.vel_data_chart_t.insert(0, "M")

            p_style.update({'stroke': 'black'})
            path_attrs = {
                'style': simplestyle.formatStyle(p_style),
                'd': " ".join(self.v_chart.vel_data_chart_t),
                inkex.addNS('desc', ns_prefix): "Total V"}
            etree.SubElement(preview_layer,
                             inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

            p_style.update({'stroke': 'red'})
            path_attrs = {
                'style': simplestyle.formatStyle(p_style),
                'd': " ".join(self.v_chart.vel_chart1),
                inkex.addNS('desc', ns_prefix): "Motor 1 V"}
            etree.SubElement(preview_layer,
                             inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

            p_style.update({'stroke': 'green'})
            path_attrs = {
                'style': simplestyle.formatStyle(p_style),
                'd': " ".join(self.v_chart.vel_chart2),
                inkex.addNS('desc', ns_prefix): "Motor 2 V"}
            etree.SubElement(preview_layer,
                             inkex.addNS('path', 'svg '), path_attrs, nsmap=inkex.NSS)

