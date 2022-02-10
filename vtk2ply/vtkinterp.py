import argparse
import math
import os
import sys

def main():
    parser = argparse.ArgumentParser(description='Python VTK script for interpolating blood flow simulation data')
    parser.add_argument('-s', '--t0-filename', type=str, default='data0.vtk', help='name of input VTK file at time step 0')
    parser.add_argument('-e', '--t1-filename', type=str, default='data1.vtk', help='name of input VTK file at time step 1')
    parser.add_argument('-t', '--timestep', type=float, default=0.5, help='time step')
    parser.add_argument('-d', '--max-distance', type=float, default=9.9e12, help='max distance between time steps (changes larger will not be interpolated)')
    parser.add_argument('-o', '--output-filename', type=str, default='output.vtk', help='name of output VTK file')
    
    args = parser.parse_args(sys.argv[1:])
    t = args.timestep
    
    polydata0 = open(args.t0_filename, 'r')
    polydata1 = open(args.t1_filename, 'r')
    polydata_out = open(args.output_filename, 'w')
    state = 'HEADER'
    pt_idx = 0
    num_pts = -1
    for line0 in polydata0:
        line0 = line0.strip()
        line1 = polydata1.readline().strip()
        line0_cols = line0.split(' ')
        if state == 'HEADER':
            polydata_out.write(line0 + '\n')
            if line0_cols[0] == 'POINTS':
                state = 'POINTS'
                num_pts = int(line0_cols[1])
        elif state == 'POINTS':
            line1_cols = line1.split(' ')
            p0 = (float(line0_cols[0]), float(line0_cols[1]), float(line0_cols[2]))
            p1 = (float(line1_cols[0]), float(line1_cols[1]), float(line1_cols[2]))
            if distance(p0, p1) <= args.max_distance:
                p_interp_x = (1.0 - t) * p0[0] + t * p1[0]
                p_interp_y = (1.0 - t) * p0[1] + t * p1[1]
                p_interp_z = (1.0 - t) * p0[2] + t * p1[2]
                polydata_out.write('{:.4f} {:.4f} {:.4f}\n'.format(p_interp_x, p_interp_y, p_interp_z))
            else:
                polydata_out.write('{:.4f} {:.4f} {:.4f}\n'.format(p0[0], p0[1], p0[2]))
            pt_idx = pt_idx + 1
            if pt_idx == num_pts:
                state = 'POLYGONS'
        else:
            polydata_out.write(line0 + '\n')
    polydata0.close()
    polydata1.close()
    polydata_out.close()


def distance(p0, p1):
    sq_sum = 0
    for i in range(len(p0)):
        sq_sum = sq_sum + ((p1[i] - p0[i]) * (p1[i] - p0[i]))
    return math.sqrt(sq_sum)


main()
