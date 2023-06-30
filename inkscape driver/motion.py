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
motion.py

Legacy trajectory planning routines

Part of the AxiDraw driver for Inkscape
https://github.com/evil-mad/AxiDraw

Requires Python 3.7 or newer.
"""
# pylint: disable=pointless-string-statement

import copy
import math
import logging
from array import array

from axidrawinternal.plot_utils_import import from_dependency_import # plotink
plot_utils = from_dependency_import('plotink.plot_utils')

def trajectory(ad_ref, vertex_list, xyz_pos=None):
    """
    Plan the trajectory for a full path, beginning with lowering the pen and ending with
        raising the pen.

    Inputs: Ordered (x,y) pair vertex list, corresponding to a single polyline.
            ad_ref: reference to an AxiDraw() object with its settings
            xyz_pos: A pen_handling.PenPosition object, giving XYZ position to be used
                as initial XYZ position for the purpose of computing the trajectory.
                The default, None, will cause the current XYZ position to be used,

    Output: move_list, data_list
            move_list: A list of specific motion commands to execute.
            Commands may include: Pen lift, pen lower, horizontal movement, etc.
            [['lift', (params tuple), (seg_data)],
            ['SM', (params tuple), (seg_data)],

            seg_data: Segment data list for a motion segment.
                * final x position, float
                * final y position, float
                * final pen_up, boolean
                * Distance plotted
                * execution time to plot this element (possible future addition)

            data_list: Trajectory data list for the vertex list
                * final x position, float
                * final y position, float
                * final pen_up, boolean
                * Distance plotted
                * execution time to plot this element  (possible future addition)
    """

    move_list = []
    move_list.append(['lower', None])     # Initial pen lowering; default parameters.

    if xyz_pos is None:
        xyz_pos = copy.copy(ad_ref.pen.phys)
    xyz_pos.z_up = False # Set initial pen_up state for trajectory calculation to False
    traj = plan_trajectory(ad_ref, vertex_list, xyz_pos)
    if traj is None:
        return None # Skip pen lower and raise if there is no trajectory to plot
    middle_moves, data_list = traj
    if middle_moves is not None:
        move_list.extend(middle_moves)
    move_list.append(['raise', None])     # final pen raising; default parameters.

    return move_list, data_list


def plan_trajectory(ad_ref, vertex_list, xyz_pos=None):
    """
    Plan the trajectory for a full path, accounting for acceleration.

    Inputs: ad_ref: reference to an AxiDraw() object with its settings
            Ordered (x,y) pair vertex list, corresponding to a single polyline.
            xyz_pos: A pen_handling.PenPosition object, giving XYZ position to be used
                as initial XYZ position for the purpose of computing the trajectory.
                The default, None, will cause the current XYZ position to be used,

    Output: move_list, data_list
            move_list: A list of specific motion commands to execute, formatted as:
            ['SM', (params tuple), (seg_data)]

            seg_data: Segment data list for a motion segment.
                * final x position, float
                * final y position, float
                * final pen_up, boolean
                * Distance plotted
                * execution time to plot this element (possible future addition)

            data_list: Trajectory data list for the full vertex list
                * final x position, float
                * final y position, float
                * final pen_up, boolean
                * Distance plotted
                * execution time to plot this element  (possible future addition)
    """
    spew_trajectory_debug_data = False # Set True to get entirely too much debugging data

    # traj_logger = logging.getLogger('.'.join([__name__, 'trajectory']))
    # if spew_trajectory_debug_data:
    #     traj_logger.setLevel(logging.DEBUG) # by default level is INFO
    # traj_logger.debug('\nplan_trajectory()\n')

    traj_length = len(vertex_list)
    if traj_length < 2: # Invalid path segment
        return None, None

    if ad_ref.pen.phys.xpos is None:
        return None, None

    if xyz_pos is None:
        xyz_pos = copy.copy(ad_ref.pen.phys)

    f_pen_up = xyz_pos.z_up

    # Handle simple segments (lines) that do not require any complex planning:
    if traj_length < 3:
        # traj_logger.debug('Drawing straight line, not a curve.')  # "SHORTPATH ESCAPE"
        # Get X & Y Destination coordinates from last element, vertex_list[1]:
        segment_input_data = (vertex_list[1][0], vertex_list[1][1], 0, 0, False)
        return compute_segment(ad_ref, segment_input_data, xyz_pos)

    # traj_logger.debug('Input path to plan_trajectory: ')
    # if traj_logger.isEnabledFor(logging.DEBUG):
    #     for x_y in vertex_list:
    #         traj_logger.debug('x: %.3f, y: %.3f', x_y[0], x_y[1])
    #         traj_logger.debug('\ntraj_length: %s', traj_length)

    speed_limit = ad_ref.speed_pendown  # Maximum travel rate (in/s), in XY plane.
    if f_pen_up:
        speed_limit = ad_ref.speed_penup  # For pen-up manual moves
    # traj_logger.debug('\nspeed_limit (plan_trajectory): %.3f in/s', speed_limit)

    traj_dists = array('f')  # float, Segment length (distance) when arriving at the junction
    traj_vels = array('f')  # float, Velocity (_speed_, really) when arriving at the junction

    traj_vectors = []  # Array that will hold normalized unit vectors along each segment
    trimmed_path = []  # Array that will hold usable segments of vertex_list

    traj_dists.append(0.0)  # First value, at time t = 0
    traj_vels.append(0.0)  # First value, at time t = 0

    if ad_ref.options.resolution == 1:  # High-resolution mode
        min_dist = ad_ref.params.max_step_dist_hr # Skip segments likely to be < one step
    else:
        min_dist = ad_ref.params.max_step_dist_lr # Skip segments likely to be < one step

    last_index = 0
    for i in range(1, traj_length):
        # Construct arrays of position and distances, skipping near-zero length segments.

        tmp_dist_x = vertex_list[i][0] - vertex_list[last_index][0] # Distance per segment
        tmp_dist_y = vertex_list[i][1] - vertex_list[last_index][1]

        tmp_dist = plot_utils.distance(tmp_dist_x, tmp_dist_y)

        if tmp_dist >= min_dist:
            traj_dists.append(tmp_dist)
            # Normalized unit vectors for computing cosine factor
            traj_vectors.append([tmp_dist_x / tmp_dist, tmp_dist_y / tmp_dist])
            tmp_x = vertex_list[i][0]
            tmp_y = vertex_list[i][1]
            trimmed_path.append([tmp_x, tmp_y])  # Selected, usable portions of vertex_list.
            # traj_logger.debug('\nSegment: vertex_list[%s] -> [%s]', last_index, i)
            # traj_logger.debug('Dest: x: %.3f,  y: %.3f. Dist.: %.3f', tmp_x, tmp_y, tmp_dist)
            last_index = i
        else:
            # traj_logger.debug('\nSegment: vertex_list[%s] -> [%s]: near zero; skipping.',
            #     last_index, i)
            # traj_logger.debug(f'  x: {vertex_list[i][0]:1.3f}, ' +
            #     f'y: {vertex_list[i][1]:1.3f}, distance: {tmp_dist:1.3f}')
            pass

    traj_length = len(traj_dists)

    if traj_length < 2:
        # traj_logger.debug('\nSkipped a path element without well-defined segments.')
        return None, None # Handle zero-segment plot

    if traj_length < 3: # plot the element if it is just a line
        # traj_logger.debug('\nDrawing straight line, not a curve.')
        segment_input_data = (trimmed_path[0][0], trimmed_path[0][1], 0, 0, False)
        return compute_segment(ad_ref, segment_input_data, xyz_pos)

    # traj_logger.debug('\nAfter removing any zero-length segments, we are left with: ')
    # traj_logger.debug('traj_dists[0]: %.3f', traj_dists[0])
    # if traj_logger.isEnabledFor(logging.DEBUG):
    #     for i in range(0, len(trimmed_path)):
    #         traj_logger.debug(f'i: {i}, x: {trimmed_path[i][0]:1.3f}, ' +
    #             f'y: {trimmed_path[i][1]:1.3f}, distance: {traj_dists[i + 1]:1.3f}')
    #         traj_logger.debug('  And... traj_dists[i+1]: %.3f', traj_dists[i + 1])

    # Acceleration/deceleration rates:
    if f_pen_up:
        accel_rate = ad_ref.params.accel_rate_pu * ad_ref.options.accel / 100.0
    else:
        accel_rate = ad_ref.params.accel_rate * ad_ref.options.accel / 100.0

    # Maximum acceleration time: Time needed to accelerate from full stop to maximum speed:
    # v = a * t, so t_max = vMax / a
    t_max = speed_limit / accel_rate

    # Distance that is required to reach full speed, from zero speed:  x = 1/2 a t^2
    accel_dist = 0.5 * accel_rate * t_max * t_max

    # traj_logger.debug('\nspeed_limit: %.3f', speed_limit)
    # traj_logger.debug('t_max: %.3f', t_max)
    # traj_logger.debug('accel_rate: %.3f', accel_rate)
    # traj_logger.debug('accel_dist: %.3f', accel_dist)

    """
    Now, step through every vertex in the trajectory, and calculate what the speed
    should be when arriving at that vertex.

    In order to do so, we need to understand how the trajectory will evolve in terms
    of position and velocity for a certain amount of time in the future, past that vertex.
    The most extreme cases of this is when we are traveling at
    full speed initially, and must come to a complete stop.
        (This is actually more sudden than if we must reverse course-- that must also
        go through zero velocity at the same rate of deceleration, and a full reversal
        that does not occur at the path end might be able to have a
        nonzero velocity at the endpoint.)

    Thus, we look ahead from each vertex until one of the following occurs:
        (1) We have looked ahead by at least t_max, or
        (2) We reach the end of the path.

    The data that we have to start out with is this:
        - The position and velocity at the previous vertex
        - The position at the current vertex
        - The position at subsequent vertices
        - The velocity at the final vertex (zero)

    To determine the correct velocity at each vertex, we will apply the following rules:

    (A) For the first point, V(i = 0) = 0.

    (B) For the last point point, V = 0 as well.

    (C) If the length of the segment is greater than the distance
    required to reach full speed, then the vertex velocity may be as
    high as the maximum speed.

    Note that we must actually check not the total *speed* but the acceleration
    along the two native motor axes.

    (D) If not; if the length of the segment is less than the total distance
    required to get to full speed, then the velocity at that vertex
    is limited by to the value that can be reached from the initial
    starting velocity, in the distance given.

    (E) The maximum velocity through the junction is also limited by the
    turn itself-- if continuing straight, then we do not need to slow down
    as much as if we were fully reversing course.
    We will model each corner as a short curve that we can accelerate around.

    (F) To calculate the velocity through each turn, we must _look ahead_ to
    the subsequent (i+1) vertex, and determine what velocity
    is appropriate when we arrive at the next point.

    Because future points may be close together-- the subsequent vertex could
    occur just before the path end -- we actually must look ahead past the
    subsequent (i + 1) vertex, all the way up to the limits that we have described
    (e.g., t_max) to understand the subsequent behavior. Once we have that effective
    endpoint, we can work backwards, ensuring that we will be able to get to the
    final speed/position that we require.

    A less complete (but far simpler) procedure is to first complete the trajectory
    description, and then -- only once the trajectory is complete -- go back through,
    but backwards, and ensure that we can actually decelerate to each velocity.

    (G) The minimum velocity through a junction may be set to a constant.
    There is often some (very slow) speed -- perhaps a few percent of the maximum speed
    at which there are little or no resonances. Even when the path must directly reverse
    itself, we can usually travel at a non-zero speed. This, of course, presumes that we
    still have a solution for getting to the endpoint at zero speed.
    """

    delta = ad_ref.params.cornering / 5000  # Corner rounding/tolerance factor.

    for i in range(1, traj_length - 1):
        dcurrent = traj_dists[i]  # Length of the segment leading up to this vertex

        v_prev_exit = traj_vels[i - 1]  # Velocity when leaving previous vertex

        """
        Velocity at vertex: Part I

        Check to see what our plausible maximum speeds are, from
        acceleration only, without concern about cornering, nor deceleration.
        """

        if dcurrent > accel_dist:
            # There _is_ enough distance in the segment for us to either
            # accelerate to maximum speed or come to a full stop before this vertex.
            vcurrent_max = speed_limit
            # traj_logger.debug('Speed Limit on vel : %s', i)
        else:
            # There is _not necessarily_ enough distance in the segment for us to either
            # accelerate to maximum speed or come to a full stop before this vertex.
            # Calculate how much we *can* swing the velocity by:

            vcurrent_max = plot_utils.vFinal_Vi_A_Dx(v_prev_exit, accel_rate, dcurrent)
            vcurrent_max = min(vcurrent_max, speed_limit)
            # traj_logger.debug('traj_vels I: %.3f', vcurrent_max)

        """
        Velocity at vertex: Part II 

        Assuming that we have the same velocity when we enter and
        leave a corner, our acceleration limit provides a velocity
        that depends upon the angle between input and output directions.

        The cornering algorithm models the corner as a slightly smoothed corner,
        to estimate the angular acceleration that we encounter:
        https://onehossshay.wordpress.com/2011/09/24/improving_grbl_cornering_algorithm/

        The dot product of the unit vectors is equal to the cosine of the angle between the
        two unit vectors, giving the deflection between the incoming and outgoing angles. 
        Note that this angle is (pi - theta), in the convention of that article, giving us
        a sign inversion. [cos(pi - theta) = - cos(theta)]
        """
        cosine_factor = - plot_utils.dotProductXY(traj_vectors[i - 1], traj_vectors[i])

        root_factor = math.sqrt((1 - cosine_factor) / 2)
        denominator = 1 - root_factor
        if denominator > 0.0001:
            rfactor = (delta * root_factor) / denominator
        else:
            rfactor = 100000
        vjunction_max = math.sqrt(accel_rate * rfactor)

        vcurrent_max = min(vcurrent_max, vjunction_max)

        traj_vels.append(vcurrent_max)  # "Forward-going" speed limit at this vertex.
    traj_vels.append(0.0)  # Add zero velocity, for final vertex.

    # if traj_logger.isEnabledFor(logging.DEBUG):
    #     traj_logger.debug('\n')
    #     for dist in traj_vels:
    #         traj_logger.debug('traj_vels II: %.3f', dist)

    """
    Velocity at vertex: Part III

    We have, thus far, ensured that we could reach the desired velocities, going forward, but
    have also assumed an effectively infinite deceleration rate.

    We now go through the completed array in reverse, limiting velocities to ensure that we
    can properly decelerate in the given distances.
    """

    for j in range(1, traj_length):
        i = traj_length - j  # Range: From (traj_length - 1) down to 1.

        v_final = traj_vels[i]
        v_initial = traj_vels[i - 1]
        seg_length = traj_dists[i]

        if v_initial > v_final and seg_length > 0:
            v_init_max = plot_utils.vInitial_VF_A_Dx(v_final, -accel_rate, seg_length)
            # traj_logger.debug(
            #     f'VInit Calc: (v_final = {v_final:1.3f}, accel_rate = {accel_rate:1.3f},' +
            #     f' seg_length = {seg_length:1.3f}) ')
            if v_init_max < v_initial:
                v_initial = v_init_max
            traj_vels[i - 1] = v_initial

    # if traj_logger.isEnabledFor(logging.DEBUG):
    #     for dist in traj_vels:
    #         traj_logger.debug('traj_vels III: %.3f', dist)
    #     traj_logger.debug(' ')

    move_list = []
    for i in range(0, traj_length - 1):

        segment_input_data = (trimmed_path[i][0], trimmed_path[i][1],
            traj_vels[i], traj_vels[i + 1], False)

        move_temp, data_list = compute_segment(ad_ref, segment_input_data, xyz_pos)

        if data_list is not None: # Update current position
            xyz_pos.xpos = data_list[0]
            xyz_pos.ypos = data_list[1]
            xyz_pos.z_up = data_list[2]
        if move_temp is not None:
            move_list.extend(move_temp)
    return move_list, data_list


def compute_segment(ad_ref, data, xyz_pos=None):
    """
    Plan a straight line segment with given initial and final velocity.

    Calculates SM line segments to plot, and returns a list of them.

    Inputs:
            ad_ref: reference to an AxiDraw() object with its settings
            data tuple, in form of (Xfinal, Yfinal, Vinitial, Vfinal, ignore_limits)
            xyz_pos: A pen_handling.PenPosition object, giving XYZ position to be used
                as initial XYZ position for the purpose of computing the trajectory.
                The default, None, will cause the current XYZ position to be used,

    Output: move_list, data_list
            move_list: A list of specific motion commands to execute.
            Commands may include: Pen lift, pen lower, horizontal movement, etc.
            [['lift', (params tuple), (seg_data)],
            ['SM', (params tuple), (seg_data)],
            ['LU', (params tuple), (seg_data)]]

            seg_data: Segment data list for a motion segment.
                * final x position, float
                * final y position, float
                * final pen_up, boolean
                * Distance plotted
                * execution time to plot this element (possible future addition)

            data_list: Trajectory data list for the vertex list
                * final x position, float
                * final y position, float
                * final pen_up, boolean
                * Distance plotted
                * execution time to plot this element  (possible future addition)

    Method: Divide the segment up into smaller segments, each
    of which has constant velocity.
    Prepare to send commands out the com port as a set of short line segments
    (dx, dy) with specified durations (in ms) of how long each segment
    takes to draw.the segments take to draw.
    Uses linear ("trapezoid") acceleration and deceleration strategy.

    Inputs are expected be in units of inches (for distance)
        or inches per second (for velocity).

    Input positions and velocities are in distances of inches and velocities
    of inches per second.

    Within this routine, we convert from inches into motor steps.

    Note: Native motor axes are Motor 1, Motor 2:
        motor_dist1 = ( xDist + yDist ) # Distance for motor to move, Axis 1
        motor_dist2 = ( xDist - yDist ) # Distance for motor to move, Axis 2

    We will only discuss motor steps, and resolution, within the context of native axes.
    """

    # spew_segment_debug_data = False # Set True to get entirely too much debugging data

    x_dest, y_dest, v_i, v_f, ignore_limits = data

    if xyz_pos is None:
        xyz_pos = copy.copy(ad_ref.pen.phys)

    f_current_x = xyz_pos.xpos
    f_current_y = xyz_pos.ypos
    f_pen_up = xyz_pos.z_up

    if f_current_x is None:
        return None, None

    # seg_logger = logging.getLogger('.'.join([__name__, 'segment']))
    # if spew_segment_debug_data:
    #     seg_logger.setLevel(logging.DEBUG) # by default level is INFO

    # if ad_ref.plot_status.stopped:
    #     spew_text = '\nSkipping '
    # else:
    #     spew_text = '\nExecuting '
    # spew_text += 'compute_segment() function\n'
    # if f_pen_up:
    #     spew_text += '  Pen-up transit'
    # else:
    #     spew_text += '  Pen-down move'
    # spew_text += f' from (x = {f_current_x:1.3f}, y = {f_current_y:1.3f})'
    # spew_text += f' to (x = {x_dest:1.3f}, y = {y_dest:1.3f})\n'
    # spew_text += f'    w/ v_i = {v_i:1.2f}, v_f = {v_f:1.2f} '
    # seg_logger.debug(spew_text)
    # if ad_ref.plot_status.stopped:
    #     seg_logger.debug(' -> NOTE: Plot is in a Stopped state.')

    constant_vel_mode = False
    if ad_ref.options.const_speed and not f_pen_up:
        constant_vel_mode = True

    if not ignore_limits:  # check page size limits:
        tolerance = ad_ref.params.bounds_tolerance # Truncate up to 1 step w/o error.
        x_dest, x_bounded = plot_utils.checkLimitsTol(x_dest,
            ad_ref.bounds[0][0], ad_ref.bounds[1][0], tolerance)
        y_dest, y_bounded = plot_utils.checkLimitsTol(y_dest,
            ad_ref.bounds[0][1], ad_ref.bounds[1][1], tolerance)
        if x_bounded or y_bounded:
            ad_ref.warnings.add_new('bounds')

    delta_x_inches = x_dest - f_current_x
    delta_y_inches = y_dest - f_current_y

    # Velocity inputs; clarify units.
    vi_inch_per_s = v_i
    vf_inch_per_s = v_f

    # Look at distance to move along 45-degree axes, for native motor steps:
    # Recall that step_scale gives a scaling factor for converting from inches to steps,
    #   *not* native resolution
    # ad_ref.step_scale is Either 1016 or 2032, for 8X or 16X microstepping, respectively.

    motor_dist1 = delta_x_inches + delta_y_inches # Inches that belt must turn at Motor 1
    motor_dist2 = delta_x_inches - delta_y_inches # Inches that belt must turn at Motor 2
    motor_steps1 = int(round(ad_ref.step_scale * motor_dist1)) # Round to the nearest motor step
    motor_steps2 = int(round(ad_ref.step_scale * motor_dist2)) # Round to the nearest motor step

    # Since we are rounding, we need to keep track of the actual distance moved,
    #   not just the _requested_ distance to move.
    motor_dist1_rounded = float(motor_steps1) / (2.0 * ad_ref.step_scale)
    motor_dist2_rounded = float(motor_steps2) / (2.0 * ad_ref.step_scale)

    # Convert back to find the actual X & Y distances that will be moved:
    delta_x_inches_rounded = (motor_dist1_rounded + motor_dist2_rounded)
    delta_y_inches_rounded = (motor_dist1_rounded - motor_dist2_rounded)

    if abs(motor_steps1) < 1 and abs(motor_steps2) < 1: # If movement is < 1 step, skip it.
        return None, None

    segment_length_inches = plot_utils.distance(delta_x_inches_rounded, delta_y_inches_rounded)

    # seg_logger.debug('\ndelta_x_inches Requested: %.4f', delta_x_inches)
    # seg_logger.debug('delta_y_inches Requested: %.4f', delta_y_inches)
    # seg_logger.debug('motor_steps1: %s', motor_steps1)
    # seg_logger.debug('motor_steps2: %s', motor_steps2)
    # seg_logger.debug('\ndelta_x_inches to be moved: %.4f', delta_x_inches_rounded)
    # seg_logger.debug('delta_y_inches to be moved: %.4f', delta_y_inches_rounded)
    # seg_logger.debug('segment_length_inches: %.4f', segment_length_inches)
    # if not f_pen_up:
    #     seg_logger.debug('\nBefore speedlimit check::')
    #     seg_logger.debug('vi_inch_per_s:  %.4f', vi_inch_per_s)
    #     seg_logger.debug('vf_inch_per_s:  %.4f', vf_inch_per_s)

    if f_pen_up:
        speed_limit = ad_ref.speed_penup # Maximum travel speeds
        accel_rate = ad_ref.params.accel_rate_pu * ad_ref.options.accel / 100.0
    else:
        speed_limit = ad_ref.speed_pendown # Maximum travel speeds
        accel_rate = ad_ref.params.accel_rate * ad_ref.options.accel / 100.0

    # Maximum acceleration time: Time needed to accelerate from full stop to maximum speed:
    #       v = a * t, so t_max = vMax / a
    # t_max = speed_limit / accel_rate
    # Distance that is required to reach full speed, from zero speed:  x = 1/2 a t^2
    # accel_dist = 0.5 * accel_rate * t_max * t_max

    vi_inch_per_s = min(vi_inch_per_s, speed_limit)
    vf_inch_per_s = min(vf_inch_per_s, speed_limit)

    # seg_logger.debug('\nspeed_limit (PlotSegment): %.4f', speed_limit)
    # seg_logger.debug('After speedlimit check::')
    # seg_logger.debug('vi_inch_per_s: %.4f', vi_inch_per_s)
    # seg_logger.debug('vf_inch_per_s: %.4f', vf_inch_per_s)

    # Times to reach maximum speed, from our initial velocity:
    # vMax = vi + a*t  =>  t = (vMax - vi)/a
    # vf = vMax - a*t   =>  t = -(vf - vMax)/a = (vMax - vf)/a
    # -- These are _maximums_. We often do not have enough time/space to reach full speed.

    t_accel_max = (speed_limit - vi_inch_per_s) / accel_rate
    t_decel_max = (speed_limit - vf_inch_per_s) / accel_rate

    # seg_logger.debug('\naccel_rate: %.3f', accel_rate)
    # seg_logger.debug('speed_limit: %.3f', speed_limit)
    # seg_logger.debug('vi_inch_per_s: %.3f', vi_inch_per_s)
    # seg_logger.debug('vf_inch_per_s: %.3f', vf_inch_per_s)
    # seg_logger.debug('t_accel_max: %.3f', t_accel_max)
    # seg_logger.debug('t_decel_max: %.3f', t_decel_max)

    # Distance to reach full speed, starting at speed vi_inch_per_s: d = vi * t + (1/2) a t^2
    accel_dist_max = (vi_inch_per_s * t_accel_max) + (0.5 * accel_rate * t_accel_max * t_accel_max)
    # Use the same model for deceleration distance; modeling it with backwards motion:
    decel_dist_max = (vf_inch_per_s * t_decel_max) + (0.5 * accel_rate * t_decel_max * t_decel_max)

    max_vel_time_estimate = (segment_length_inches / speed_limit)

    # seg_logger.debug('accel_dist_max: %.3f', accel_dist_max)
    # seg_logger.debug('decel_dist_max: %.3f', decel_dist_max)
    # seg_logger.debug('max_vel_time_estimate: %.3f', max_vel_time_estimate)

    # time slices: Slice travel into intervals that are (say) 25 ms long.
    time_slice = ad_ref.params.time_slice

    # Declare arrays: Integers are _normally_ 4-byte integers, but could be 2-byte
    #    on some systems. That could cause errors in rare cases of very long moves.
    duration_array = array('I') # unsigned integer; up to 65 seconds for a move if only 2 bytes.
    dist_array = array('f') # float
    dest_array1 = array('i') # signed integer
    dest_array2 = array('i') # signed integer

    time_elapsed = 0.0
    position = 0.0
    velocity = vi_inch_per_s

    """
    Next, we wish to estimate total time duration of this segment.
    In doing so, we must consider the possible cases:

    Case 1: 'Trapezoid'
        Segment length is long enough to reach full speed.
        Segment length > accel_dist_max + decel_dist_max
        As a second check, make sure that the segment is long enough that it would take at
        least 4 time slices at maximum velocity.

    Case 2: 'Triangle'
        Segment length is not long enough to reach full speed.
        Accelerate from initial velocity to a local maximum speed,
        then decelerate from that point to the final velocity.

    Case 3: 'Linear velocity ramp'
        For small enough moves -- say less than 10 intervals (typ 500 ms),
        we do not have significant time to ramp the speed up and down.
        Instead, perform only a simple speed ramp between initial and final.

    Case 4: 'Constant velocity'
        Use a single, constant velocity for all pen-down movements.
        Also a fallback position, when moves are too short for linear ramps.

    In each case, we ultimately construct the trajectory in segments at constant velocity.
    In cases 1-3, that set of segments approximates a linear slope in velocity.

    Because we may end up with slight over/undershoot in position along the paths
    with this approach, we perform a final scaling operation (to the correct distance) at the end.
    """

    if not constant_vel_mode or f_pen_up:  # Allow accel when pen is up.
        if (segment_length_inches > (accel_dist_max + decel_dist_max + time_slice * speed_limit)
            and max_vel_time_estimate > 4 * time_slice ):
            """ Case 1: 'Trapezoid' """

            # seg_logger.debug('Type 1: Trapezoid \n')
            speed_max = speed_limit  # We will reach _full cruising speed_!

            intervals = int(math.floor(t_accel_max / time_slice)) # Acceleration interval count

            # If intervals == 0, then we are already at (or nearly at) full speed.
            if intervals > 0:
                time_per_interval = t_accel_max / intervals

                velocity_step_size = (speed_max - vi_inch_per_s) / (intervals + 1.0)
                # For six time intervals of acceleration, first interval is at velocity (max/7)
                # 6th (last) time interval is at 6*max/7
                # after this interval, we are at full speed.

                for index in range(0, intervals):  # Calculate acceleration phase
                    velocity += velocity_step_size
                    time_elapsed += time_per_interval
                    position += velocity * time_per_interval
                    duration_array.append(int(round(time_elapsed * 1000.0)))
                    dist_array.append(position)  # Estimated distance along direction of travel
                # seg_logger.debug('Accel intervals: %s', intervals)

            # Add a center "coasting" speed interval IF there is time for it.
            coasting_distance = segment_length_inches - (accel_dist_max + decel_dist_max)

            if coasting_distance > (time_slice * speed_max):
                # There is enough time for (at least) one interval at full cruising speed.
                velocity = speed_max
                cruising_time = coasting_distance / velocity
                ct = cruising_time
                cruise_interval = 20 * time_slice
                while ct > (cruise_interval):
                    ct -= cruise_interval
                    time_elapsed += cruise_interval
                    duration_array.append(int(round(time_elapsed * 1000.0)))
                    position += velocity * cruise_interval
                    dist_array.append(position)  # Estimated distance along direction of travel

                time_elapsed += ct
                duration_array.append(int(round(time_elapsed * 1000.0)))
                position += velocity * ct
                dist_array.append(position)  # Estimated distance along direction of travel

                # seg_logger.debug('Coast Distance: %.3f', coasting_distance)
                # seg_logger.debug('Coast velocity: %.3f', velocity)

            intervals = int(math.floor(t_decel_max / time_slice)) # Deceleration interval count

            if intervals > 0:
                time_per_interval = t_decel_max / intervals
                velocity_step_size = (speed_max - vf_inch_per_s) / (intervals + 1.0)

                for index in range(0, intervals):  # Calculate deceleration phase
                    velocity -= velocity_step_size
                    time_elapsed += time_per_interval
                    position += velocity * time_per_interval
                    duration_array.append(int(round(time_elapsed * 1000.0)))
                    dist_array.append(position)  # Estimated distance along direction of travel
                # seg_logger.debug('Decel intervals: %s', intervals)

        else:
            """
            Case 2: 'Triangle'

            We will _not_ reach full cruising speed, but let's go as fast as we can!

            We begin with given: initial velocity, final velocity,
                maximum acceleration rate, distance to travel.

            The optimal solution is to accelerate at the maximum rate, to some maximum velocity
            Vmax, and then to decelerate at same maximum rate, to the final velocity.
            This forms a triangle on the plot of V(t).

            The value of Vmax -- and the time at which we reach it -- may be varied in order to
            accommodate our choice of distance-traveled and velocity requirements.
            (This does assume that the segment requested is self consistent, and planned
            with respect to our acceleration requirements.)

            In a more detail, with short notation Vi = vi_inch_per_s,
                Vf = vf_inch_per_s, and Amax = accel_rate_local, Dv = (Vf - Vi)

            (i) We accelerate from Vi, at Amax to some maximum velocity Vmax.
            This takes place during an interval of time Ta.

            (ii) We then decelerate from Vmax, to Vf, at the same maximum rate, Amax.
            This takes place during an interval of time Td.

            (iii) The total time elapsed is Ta + Td

            (iv) v = v0 + a * t
                =>    Vmax = Vi + Amax * Ta
                and   Vmax = Vf + Amax * Td  (i.e., Vmax - Amax * Td = Vf)

                Thus Td = Ta - (Vf - Vi) / Amax, or Td = Ta - (Dv / Amax)

            (v) The distance covered during the acceleration interval Ta is given by:
                Xa = Vi * Ta + (1/2) Amax * Ta^2

                The distance covered during the deceleration interval Td is given by:
                Xd = Vf * Td + (1/2) Amax * Td^2

                Thus, the total distance covered during interval Ta + Td is given by:
                segment_length_inches =
                    Xa + Xd = Vi * Ta + (1/2) Amax * Ta^2 + Vf * Td + (1/2) Amax * Td^2

            (vi) Now substituting in Td = Ta - (Dv / Amax), we find:
                Amax * Ta^2 + 2 * Vi * Ta + (Vi^2 - Vf^2)/( 2 * Amax ) - segment_length_inches = 0

                Solving this quadratic equation for Ta, we find:
                Ta = ( sqrt(2 * Vi^2 + 2 * Vf^2 + 4 * Amax * segment_length_inches)
                    - 2 * Vi ) / ( 2 * Amax )

                [We pick the positive root in the quadratic formula, since Ta must be positive.]

            (vii) From Ta and part (iv) above, we can find Vmax and Td.
            """

            # seg_logger.debug('\nType 2: Triangle')

            if segment_length_inches >= 0.9 * (accel_dist_max + decel_dist_max):
                accel_rate_local = 0.9 * ((accel_dist_max + decel_dist_max) /
                    segment_length_inches) * accel_rate
                if accel_dist_max + decel_dist_max == 0:
                    accel_rate_local = accel_rate # prevent possible divide by zero case
                # seg_logger.debug('accel_rate_local changed')
            else:
                accel_rate_local = accel_rate

            if accel_rate_local > 0:  # Edge cases including "already at maximum speed":
                ta = (math.sqrt(2 * vi_inch_per_s * vi_inch_per_s +
                    2 * vf_inch_per_s * vf_inch_per_s +
                    4 * accel_rate_local * segment_length_inches) -
                    2 * vi_inch_per_s) / (2 * accel_rate_local)
            else:
                ta = 0

            vmax = vi_inch_per_s + accel_rate_local * ta
            # seg_logger.debug('vmax: %.3f', vmax)

            intervals = int(math.floor(ta / time_slice)) # Acceleration interval count

            if intervals == 0:
                ta = 0
            if accel_rate_local > 0: # Hnadle edge cases e.g., already at maximum speed
                td = ta - (vf_inch_per_s - vi_inch_per_s) / accel_rate_local
            else:
                td = 0

            d_intervals = int(math.floor(td / time_slice)) # Deceleration interval count

            if intervals + d_intervals > 4:
                if intervals > 0:
                    # seg_logger.debug('Triangle intervals UP: %s', intervals)

                    time_per_interval = ta / intervals
                    velocity_step_size = (vmax - vi_inch_per_s) / (intervals + 1.0)
                    # For six time intervals of acceleration, first interval is at velocity (max/7)
                    # 6th (last) time interval is at 6*max/7
                    # after this interval, we are at full speed.

                    for index in range(0, intervals):  # Calculate acceleration phase
                        velocity += velocity_step_size
                        time_elapsed += time_per_interval
                        position += velocity * time_per_interval
                        duration_array.append(int(round(time_elapsed * 1000.0)))
                        dist_array.append(position)  # Estimated distance along direction of travel
                else:
                    pass
                    # seg_logger.debug('Note: Skipping accel phase in triangle.')

                if d_intervals > 0:
                    # seg_logger.debug('Triangle intervals Down: %s', d_intervals)

                    time_per_interval = td / d_intervals
                    velocity_step_size = (vmax - vf_inch_per_s) / (d_intervals + 1.0)
                    # For six time intervals of acceleration, first interval is at velocity (max/7)
                    # 6th (last) time interval is at 6*max/7
                    # after this interval, we are at full speed.

                    for index in range(0, d_intervals):  # Calculate acceleration phase
                        velocity -= velocity_step_size
                        time_elapsed += time_per_interval
                        position += velocity * time_per_interval
                        duration_array.append(int(round(time_elapsed * 1000.0)))
                        dist_array.append(position)  # Estimated distance along direction of travel
                else:
                    pass
                    # seg_logger.debug('Note: Skipping decel phase in triangle.')
            else:
                """
                Case 3: 'Linear or constant velocity changes'

                Picked for segments that are shorter than 6 time slices.
                Linear velocity interpolation between two endpoints.

                Because these are short segments (not enough time for a good "triangle"), we
                boost the starting speed, by taking its average with vmax for the segment.

                For very short segments (less than 2 time slices), use a single
                    segment with constant velocity.
                """

                # seg_logger.debug('Type 3: Linear \n')
                # xFinal = vi * t  + (1/2) a * t^2, and vFinal = vi + a * t. Combining these
                # (with same t) gives: 2 a x = (vf^2 - vi^2) => a = (vf^2 - vi^2)/2x
                # If 'a' is less than accel_rate, we can linearly interpolate in velocity.

                vi_inch_per_s = (vmax + vi_inch_per_s) / 2
                velocity = vi_inch_per_s  # Boost initial speed for this segment

                local_accel = (vf_inch_per_s * vf_inch_per_s - vi_inch_per_s * vi_inch_per_s) /\
                    (2.0 * segment_length_inches)

                if local_accel > accel_rate:
                    local_accel = accel_rate
                elif local_accel < -accel_rate:
                    local_accel = -accel_rate
                if local_accel == 0:
                    # Initial velocity = final velocity -> Skip to constant velocity routine.
                    constant_vel_mode = True
                else:
                    t_segment = (vf_inch_per_s - vi_inch_per_s) / local_accel

                    intervals = int(math.floor(t_segment / time_slice)) # Number during decel.
                    if intervals > 1:
                        time_per_interval = t_segment / intervals
                        velocity_step_size = (vf_inch_per_s - vi_inch_per_s) / (intervals + 1.0)
                        # For six time intervals of acceleration, first is at velocity (max/7)
                        # 6th (last) time interval is at 6*max/7
                        # after this interval, we are at full speed.

                        for index in range(0, intervals):  # Calculate acceleration phase
                            velocity += velocity_step_size
                            time_elapsed += time_per_interval
                            position += velocity * time_per_interval
                            duration_array.append(int(round(time_elapsed * 1000.0)))
                            dist_array.append(position)  # Distance along direction of travel
                    else: # Short segment; No time for segments at different velocities.
                        vi_inch_per_s = vmax  # These are _slow_ segments;
                        constant_vel_mode = True  #   use fastest possible interpretation.
                        # seg_logger.debug('-> [Min-length segment]\n')

    if constant_vel_mode:
        """ Case 4: 'Constant Velocity mode' """

        # seg_logger.debug('-> [Constant Velocity Mode Segment]\n')

        if ad_ref.options.const_speed and not f_pen_up:
            velocity = ad_ref.speed_pendown  # Constant pen-down speed
        elif vf_inch_per_s > vi_inch_per_s:
            velocity = vf_inch_per_s
        elif vi_inch_per_s > vf_inch_per_s:
            velocity = vi_inch_per_s
        elif vi_inch_per_s > 0:  # Allow case of two are equal, but nonzero
            velocity = vi_inch_per_s
        else:  # Both endpoints are equal to zero.
            velocity = ad_ref.speed_pendown / 10
            # TODO: Check this method. May be better to level it out to same value as others.

        # seg_logger.debug('velocity: %s', velocity)

        time_elapsed = segment_length_inches / velocity
        duration_array.append(int(round(time_elapsed * 1000.0)))
        dist_array.append(segment_length_inches)  # Estimated distance along direction of travel
        position += segment_length_inches

    # The time & distance motion arrays for this path segment are now computed.
    # Next: scale to the correct intended travel distance & round into integer motor steps

    # seg_logger.debug('position/segment_length_inches: %.6f', position / segment_length_inches)

    for index in range(0, len(dist_array)):
        # Scale our trajectory to the "actual" travel distance that we need:
        fractional_distance = dist_array[index] / position # Position along intended path
        dest_array1.append(int(round(fractional_distance * motor_steps1)))
        dest_array2.append(int(round(fractional_distance * motor_steps2)))
        sum(dest_array1)

    # seg_logger.debug('\nSanity check after computing motion:')
    # seg_logger.debug('Final motor_steps1: %s', dest_array1[-1]) # Last element in list
    # seg_logger.debug('Final motor_steps2: %s', dest_array2[-1]) # Last element in list

    prev_motor1 = 0
    prev_motor2 = 0
    prev_time = 0
    move_list = []

    for index in range(0, len(dest_array1)):
        move_steps1 = dest_array1[index] - prev_motor1
        move_steps2 = dest_array2[index] - prev_motor2
        move_time = duration_array[index] - prev_time
        prev_time = duration_array[index]

        move_time = max(move_time, 1) # don't allow zero-time moves.

        if abs(float(move_steps1) / float(move_time)) < 0.002:
            move_steps1 = 0  # don't allow too-slow movements of this axis
        if abs(float(move_steps2) / float(move_time)) < 0.002:
            move_steps2 = 0  # don't allow too-slow movements of this axis

        # Catch rounding errors that could cause an overspeed event:
        while (abs(float(move_steps1) / float(move_time)) >= ad_ref.params.max_step_rate) or\
            (abs(float(move_steps2) / float(move_time)) >= ad_ref.params.max_step_rate):
            move_time += 1
            # seg_logger.debug('Note: Added delay to avoid overspeed event')

        prev_motor1 += move_steps1
        prev_motor2 += move_steps2

        # If at least one motor step is required for this move, do so:
        if move_steps1 != 0 or move_steps2 != 0:
            motor_dist1_temp = float(move_steps1) / (ad_ref.step_scale * 2.0)
            motor_dist2_temp = float(move_steps2) / (ad_ref.step_scale * 2.0)

            x_delta = (motor_dist1_temp + motor_dist2_temp) # X Distance moved, inches
            y_delta = (motor_dist1_temp - motor_dist2_temp) # Y Distance moved, inches
            move_dist_inches = plot_utils.distance(x_delta, y_delta) # Total move, inches

            f_new_x = f_current_x + x_delta
            f_new_y = f_current_y + y_delta

            seg_data = [f_new_x, f_new_y, f_pen_up, move_dist_inches]
            move_list.append(['SM', (move_steps2, move_steps1, move_time), seg_data])

            f_current_x = f_new_x  # Update current position
            f_current_y = f_new_y

    data_list = [f_current_x, f_current_y, f_pen_up]
    return move_list, data_list
