import argparse
import bpy
import math
import os
import sys
import time


def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Python Blender script for rendering blood flow simulation data to ODS')
    parser.add_argument('-m', '--model-dir', type=str, default='.', help='directory where PLY models and materials are stored')
    parser.add_argument('-r', '--rbc-plyfile', type=str, default='rbc.ply', help='name of red blood cell input PLY file')
    parser.add_argument('-c', '--ctc-plyfile', type=str, default='ctc.ply', help='name of circulating tumor cell input PLY file')
    parser.add_argument('-s', '--streamline-plyfile', type=str, default='', help='name of fluid flow streamlines input PLY file (blank to omit)')
    parser.add_argument('-w', '--resolution', type=int, default=3840, help='horizontal resolution to render image (will always have 2:1 aspect ratio)')
    parser.add_argument('-d', '--device', type=str, default='CPU', help='redner device (CPU, CUDA, OPTIX, OPENCL)')
    parser.add_argument('-i', '--device-id', type=int, default=0, help='device id')
    parser.add_argument('-cp', '--camera-position', type=str, default='(0.0,0.0,1.65)', help='camera position (x,y,z)')
    parser.add_argument('-cd', '--camera-direction', type=str, default='(90,0,90)', help='camera direction in degrees (x,y,z)')
    parser.add_argument('-rs', '--render-styles',type=str, default='solid', help='list of render styles (solid,force,solid-transparent,force-transparent) or all')
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
    device_number = args.device_id
    
    # model directory
    model_dir = os.path.realpath(args.model_dir)
    
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
    bpy.context.scene.cycles.preview_samples = 64
    bpy.context.scene.cycles.samples = 256
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
    
    # set background to black
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    alpha_over = tree.nodes.new(type='CompositorNodeAlphaOver')
    link_1 = tree.links.new(tree.nodes[1].outputs[0], alpha_over.inputs[2])
    link_2 = tree.links.new(alpha_over.outputs[0], tree.nodes[0].inputs[0])
    alpha_over.inputs[1].default_value = (0.015, 0.015, 0.015, 1.0)
    
    # load materials from external file
    mat_path = os.path.join(model_dir, 'materials.blend') + '\\Material\\'
    mat_rbc_solid_name = 'RBC_Material_Solid'
    mat_rbc_solid_trans_name = 'RBC_Material_Solid_Transparent'
    mat_rbc_force_name = 'RBC_Material'
    mat_rbc_force_trans_name = 'RBC_Material_Transparent'
    mat_ctc_solid_name = 'CTC_Material_Solid'
    mat_ctc_force_name = 'CTC_Material'
    mat_streamline_name = 'Streamline_Material'
    mat_micropost_name = 'Micropost_Material'
    bpy.ops.wm.append(filename=mat_rbc_solid_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_rbc_solid_trans_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_rbc_force_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_rbc_force_trans_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_ctc_solid_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_ctc_force_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_streamline_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_micropost_name, directory=mat_path)
    mat_streamline = bpy.data.materials.get(mat_streamline_name)
    mat_micropost = bpy.data.materials.get(mat_micropost_name) 
    
    # import PLY models
    models = []
    models.append({'type': 'rbc', 'filename': os.path.join(model_dir, args.rbc_plyfile)})
    models.append({'type': 'ctc', 'filename': os.path.join(model_dir, args.ctc_plyfile)})
    if args.streamline_plyfile != '':
        models.append({'type': 'streamlines', 'filename': os.path.join(model_dir, args.streamline_plyfile)})
    models.append({'type': 'micropost', 'filename': os.path.join(model_dir, 'micropost.ply')})
    for model in models:
        bpy.ops.import_mesh.ply(filepath=model['filename'], filter_glob="*.ply")
        objs = bpy.context.selected_objects
        model['objs'] = objs
        for obj in objs:
            if model['type'] == 'streamlines':
                obj.data.materials.append(mat_streamline)
            elif model['type'] == 'micropost':
                obj.data.materials.append(mat_micropost)
            for poly in obj.data.polygons:
                poly.use_smooth = True
            obj.scale = (0.05, 0.05, 0.05)
            obj.rotation_euler = (math.radians(270.0), 0.0, math.radians(90.0))
            obj.location = (25, -12.5, 2.5)
    bpy.ops.mesh.primitive_plane_add(location=(0.0, 0.5, -1.25), rotation=(0.0, 0.0, 0.0))
    plane = bpy.context.selected_objects
    for obj in plane:
        obj.scale = (25.5, 13.5, 1.0)
        obj.data.materials.append(mat_micropost)
        
    # timer checkpoint - finished data loading/processing, about to start rendering
    mid_time = time.time()
    
    # render styles
    render_styles = ['solid', 'force', 'solid-transparent', 'force-transparent']
    if args.render_styles != 'all':
        render_styles = args.render_styles.split(',')
    
    render_times = []
    for style in render_styles:
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

def secondsToMMSS(seconds):
    mins = int(seconds) // 60
    secs = seconds - (60 * mins)
    return f'{mins:02d}:{secs:06.3f}'

main()
