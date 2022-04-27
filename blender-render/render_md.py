import argparse
import bpy
import bmesh
import math
import mathutils
import os
import re
import sys
import time


def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Python Blender script for rendering MD simulation data to ODS')
    parser.add_argument('-i', '--input-filepattern', type=str, default='data_%d.vtk', help='pattern for names of input XYZ files')
    parser.add_argument('-w', '--resolution', type=int, default=3840, help='horizontal resolution to render image (will always have 2:1 aspect ratio)')
    parser.add_argument('-d', '--device', type=str, default='CPU', help='redner device (CPU, CUDA, OPTIX, OPENCL)')
    parser.add_argument('-n', '--device-num', type=int, default=0, help='device number')
    parser.add_argument('-cp', '--camera-position', type=str, default='(0.0,0.0,1.65)', help='camera position (x,y,z)')
    parser.add_argument('-cd', '--camera-direction', type=str, default='(90,0,90)', help='camera direction in degrees (x,y,z)')
    parser.add_argument('-rs', '--render-styles',type=str, default='atoms', help='list of render styles (atoms,atomsbonds,atoms-reflection,atomsbonds-reflection) or all')
    parser.add_argument('-o', '--output', type=str, default='output.jpg', help='filename to save rendered output')

    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

    # image resolution (should be 2:1 ratio)
    dim_x = args.resolution
    dim_y = dim_x // 2
    
    # render device
    device_hw = 'CPU'
    device_type = 'CPU'
    render_device = 'NONE'
    if args.device in ['CPU', 'CUDA', 'OPTIX', 'OPENCL']:
        device_type = args.device
        if device_type != 'CPU':
            device_hw = 'GPU'
            render_device = device_type
    else:
        print(f'APP> Warning: render device {args.device} not recognized, using {device_type} instead')
    device_number = args.device_num
    
    # camera and point light location
    cam_position = args.camera_position.strip('()').split(',')
    cam_direction = args.camera_direction.strip('()').split(',')
    if len(cam_position) == 3:
        cam_position = (float(cam_position[0]), float(cam_position[1]), float(cam_position[2]))
    else:
        print(f'APP> Warning: camera position {args.camera_position} does not contain x,y,z coordinates, using 0.0,0.0,1.65 instead')
        cam_position = (0.0, 0.0, 1.65)
    if len(cam_direction) == 3:
        cam_direction = (math.radians(float(cam_direction[0])), math.radians(float(cam_direction[1])), math.radians(float(cam_direction[2])))
    else:
        print(f'APP> Warning: camera direction {args.camera_direction} does not contain x,y,z coordinates, using 90,0,90 instead')
        cam_direction = (0.5 * math.pi, 0.0, 0.5 * math.pi)
    light_position = (cam_position[0], cam_position[1], cam_position[2] + 0.15)

    # start timer
    start_time = time.time()
    
    # remove default objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # change render engine to 'Cycles'
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = device_hw
    bpy.context.scene.cycles.preview_samples = 32
    bpy.context.scene.cycles.samples = 128
    cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        cycles_prefs.compute_device_type = render_device
    except TypeError:
        print(f'APP> Error: render device type \'{device_type}\' not available')
        exit(1)
    cycles_prefs.get_devices()
    selectRenderDevice(cycles_prefs, device_type, device_number)

    # add lights
    sun_data = bpy.data.lights.new('Sun', type='SUN')
    sun = bpy.data.objects.new('Sun', sun_data)
    sun.location = (0.0, 0.0, 20.0)
    sun.data.energy = 5.0
    bpy.context.collection.objects.link(sun)
    
    light_data = bpy.data.lights.new('Light', type='POINT')
    light = bpy.data.objects.new('Light', light_data)
    light.location = light_position
    light.data.energy = 150.0
    light.data.shadow_soft_size = 1.0
    bpy.context.collection.objects.link(light)
    
    # add camera
    cam_data = bpy.data.cameras.new('Camera')
    cam_data.type = 'PANO'
    cam_data.clip_start = 0.305 # 1 ft.
    cam_data.clip_end = 200.0
    cam_data.cycles.panorama_type = 'EQUIRECTANGULAR'
    cam_data.stereo.convergence_mode = 'OFFAXIS'
    cam_data.stereo.interocular_distance = 0.065
    cam_data.stereo.use_spherical_stereo = True
    cam_data.stereo.use_pole_merge = True
    cam_data.stereo.pole_merge_angle_from = math.radians(56.25)
    cam_data.stereo.pole_merge_angle_to = math.radians(78.75)
    cam = bpy.data.objects.new('Camera', cam_data)
    cam.location = cam_position
    cam.rotation_euler = cam_direction
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    
    # enable stereo
    bpy.context.scene.render.use_multiview = True
    bpy.context.scene.render.resolution_x = dim_x
    bpy.context.scene.render.resolution_y = dim_y
    bpy.context.scene.render.image_settings.views_format = 'STEREO_3D'
    bpy.context.scene.render.image_settings.stereo_3d_format.display_mode = 'TOPBOTTOM'
    
    # set background to blue
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    alpha_over = tree.nodes.new(type='CompositorNodeAlphaOver')
    link_1 = tree.links.new(tree.nodes[1].outputs[0], alpha_over.inputs[2])
    link_2 = tree.links.new(alpha_over.outputs[0], tree.nodes[0].inputs[0])
    alpha_over.inputs[1].default_value = (0.0316, 0.1768, 0.4878, 1.0)
    
    # create materials
    materials = []
    colors = [(0.639, 0.090, 0.051, 1.0), (0.831, 0.733, 0.110, 1.0), (0.024, 0.471, 0.173, 1.0), (0.980, 0.980, 0.980, 1.0)]
    for i in range(4):
        mat = bpy.data.materials.new(name=f'material_{i}')
        mat.use_nodes = True
        col = (colors[i][0] ** 2.2, colors[i][1] ** 2.2, colors[i][2] ** 2.2, colors[i][3])
        mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = col
        materials.append(mat)
        
    # load data (1: graphene (red), 2: nanodiamonds (gold), 3: diamond-like carbon (green), 4: diamond-like carbon (white)
    input_filepattern = getFormatString(args.input_filepattern)
    # actual radius is 0.75 angstroms
    base_models = [
        icoSphere(3, 0.60),
        icoSphere(3, 0.90),
        icoSphere(3, 0.45),
        icoSphere(3, 1.25)
        
    ]
    for i in range(4):
        input_filename = input_filepattern.format(i+1)
        xyz_file = open(input_filename, 'r')
        num_atoms = int(xyz_file.readline().strip())
        num_atoms_used = 0
        xyz_file.readline() # throw away next line
        atoms_mesh = {'vertices': [], 'faces': []}
        for atom_id in range(num_atoms):
            line = xyz_file.readline().strip().split(' ')
            pos = (float(line[1]), float(line[2]), float(line[3]))
            if i < 3 or pos[2] > 10.0: # filter out some of the large white slab
                appendModelToMesh(atoms_mesh, base_models[i], pos)
                num_atoms_used += 1
        print(f'finished reading XYZ into mesh - using {num_atoms_used} atoms')
        mesh = bpy.data.meshes.new(f'atoms_{i}')
        atoms = bpy.data.objects.new(f'atom_{i}', mesh)
        bpy.context.collection.objects.link(atoms)
        mesh.from_pydata(atoms_mesh['vertices'], [], atoms_mesh['faces'])
        for poly in atoms.data.polygons:
            poly.use_smooth = True
        atoms.scale = (0.075, 0.075, 0.075)
        atoms.rotation_euler = (0.0, math.radians(180.0), 0.0)
        atoms.location = (29.0, -12.5, 4.0)
        if len(atoms.data.materials) > 0:
            atoms.data.materials[0] = materials[i]
        else:
            atoms.data.materials.append(materials[i])
        
        """
        # NURBS
        for atom_id in range(num_atoms):
            line = xyz_file.readline().strip().split(' ')
            pos = (float(line[1]), float(line[2]), float(line[3]))
            bpy.ops.surface.primitive_nurbs_surface_sphere_add(location=pos)
            if (atom_id % 500) == 0:
                print(f'{atom_id} / {num_atoms}')
        """

    
    # timer checkpoint - finished data loading/processing, about to start rendering
    mid_time = time.time()
    
    # render styles
    render_styles = ['atoms', 'atomsbonds', 'atoms-reflection', 'atomsbonds-reflection']
    if args.render_styles != 'all':
        render_styles = args.render_styles.split(',')
    
    render_times = []
    for style in render_styles:
        """
        # update materials
        mat_rbc = None
        mat_ctc = None
        if style == 'force':
            mat_rbc = bpy.data.materials.get(mat_rbc_force_name)
            mat_ctc = bpy.data.materials.get(mat_ctc_force_name)
        elif style == 'solid-transparent':
            mat_rbc = bpy.data.materials.get(mat_rbc_solid_trans_name)
            mat_ctc = bpy.data.materials.get(mat_ctc_solid_name)
        elif style == 'force-transparent':
            mat_rbc = bpy.data.materials.get(mat_rbc_force_trans_name)
            mat_ctc = bpy.data.materials.get(mat_ctc_force_name)
        else: # solid
            mat_rbc = bpy.data.materials.get(mat_rbc_solid_name)
            mat_ctc = bpy.data.materials.get(mat_ctc_solid_name)
        for model in models:
            mat = None
            if model['type'] == 'rbc':
                mat = mat_rbc
            elif model['type'] == 'ctc':
                mat = mat_ctc
            for obj in model['objs']:
                if mat != None:
                    if len(obj.data.materials) == 0:
                        obj.data.materials.append(mat)
                    else:
                        obj.data.materials[0] = mat
        """
        continue
        
        """
        # start render timer
        render_start = time.time()
        
        # render image JPEG
        bpy.context.scene.render.image_settings.quality = 92
        bpy.context.scene.render.image_settings.file_format = 'JPEG'
        bpy.context.scene.render.filepath = os.path.splitext(os.path.realpath(args.output))[0] + '_' + style + '.jpg'
        bpy.ops.render.render(write_still=1)
        
        # end timer
        render_end = time.time()
        render_times.append(secondsToMMSS(render_end - render_start))
        """
    
    # end timer
    end_time = time.time()
    total_time = secondsToMMSS(end_time - start_time)
    load_time = secondsToMMSS(mid_time - start_time)

    print(f'APP> total,load,', end='')
    for style in render_styles:
        print(f'{style},', end='')
    print('')
    print(f'{total_time},{load_time},', end='')
    for rtime in render_times:
        print(f'{rtime},', end='')
    print('')


def selectRenderDevice(cycles_prefs, device_type, device_number):
    device_count = 0
    device_found = False
    #print('Devices:')
    for device in cycles_prefs.devices:
        if device.type == device_type and device_count == device_number:
            device.use = True
            device_found = True
        else:
            device.use = False
        if device.type == device_type:
            device_count += 1
        #print(f'  {device.name} ({device.type}) {device.use}')
    if not device_found:
        print(f'APP> Error: could not find {device_type} device {device_number}')
        exit(1)
    print(f'APP> Cycles Render Engine using: {device_type} device {device_number}')


def getFormatString(a_string):
    # Change C-style formatting to Python formatting for int substitution
    return re.sub(r'%(0?[1-9]*d)', r'{:\1}', a_string)


def icoSphere(subdivisions, radius):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=radius, calc_uvs=False)
    model = {'vertices': [], 'faces': []}
    for v in bm.verts:
        model['vertices'].append((v.co.x, v.co.y, v.co.z))
    for f in bm.faces:
        indices = []
        for v in f.verts:
            indices.append(v.index)
        model['faces'].append(indices)
    bm.free()
    return model


def appendModelToMesh(mesh, model, pos):
    vert_offset = len(mesh['vertices'])
    for v in model['vertices']:
        new_vert = (v[0] + pos[0], v[1] + pos[1], v[2] + pos[2])
        mesh['vertices'].append(new_vert)
    for f in model['faces']:
        new_face = []
        for i in f:
            new_face.append(i + vert_offset)
        mesh['faces'].append(new_face)
    


def secondsToMMSS(seconds):
    mins = int(seconds) // 60
    secs = seconds - (60 * mins)
    return f'{mins:02d}:{secs:06.3f}'

main()
