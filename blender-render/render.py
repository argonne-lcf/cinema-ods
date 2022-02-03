import argparse
import bpy
import math
import os
import sys
import time


def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Python Blender script for rednering blood flow simulation data to ODS')
    parser.add_argument('-m', '--model-dir', type=str, default='.', help='directory where PLY models and materials are stored')
    parser.add_argument('-r', '--rbc-plyfile', type=str, default='rbc.ply', help='name of red blood cell input PLY file')
    parser.add_argument('-c', '--ctc-plyfile', type=str, default='ctc.ply', help='name of circulating tumor cell input PLY file')
    parser.add_argument('-s', '--streamline-plyfile', type=str, default='streamline.ply', help='name of fluid flow streamlines input PLY file')
    parser.add_argument('-w', '--resolution', type=int, default=3840, help='horizontal resolution to render image (will always have 2:1 aspect ratio)')
    parser.add_argument('-d', '--device', type=str, default='CPU', help='redner device (CPU, CUDA, OPTIX, OPENCL)')
    parser.add_argument('-i', '--device-id', type=int, default=0, help='device id')
    parser.add_argument('-cp', '--camera-position', type=str, default='0.0,0.0,1.65', help='camera position (x,y,z)')
    parser.add_argument('-cd', '--camera-direction', type=str, default='90,0,270', help='camera direction in degrees (x,y,z)')
    parser.add_argument('-o', '--output', type=str, default='output.jpg', help='filename to save rendered output')

    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])

    # image resolution (should be 2:1 ratio)
    dim_x = args.resolution
    dim_y = dim_x // 2
    
    # render device
    device_hw = 'CPU'
    device_type = 'CPU'
    if args.device in ['CPU', 'CUDA', 'OPTIX', 'OPENCL']:
        device_type = args.device
        if device_type != 'CPU':
            device_hw = 'GPU'
    else:
        print(f'APP> Warning: render device {args.device} not recognized, using {device_type} instead')
    device_number = args.device_id
    
    # model directory
    model_dir = os.path.realpath(args.model_dir)
    
    # camera and point light location
    cam_position = args.camera_position.split(',')
    cam_direction = args.camera_direction.split(',')
    if len(cam_position) == 3:
        cam_position = (float(cam_position[0]), float(cam_position[1]), float(cam_position[2]))
    else:
        print(f'APP> Warning: camera position {args.camera_position} does not contain x,y,z coordinates, using 0.0,0.0,1.65 instead')
        cam_position = (0.0, 0.0, 1.65)
    if len(cam_direction) == 3:
        cam_direction = (math.radians(float(cam_direction[0])), math.radians(float(cam_direction[1])), math.radians(float(cam_direction[2])))
    else:
        print(f'APP> Warning: camera direction {args.camera_direction} does not contain x,y,z coordinates, using 90,0,270 instead')
        cam_direction = (0.5 * math.pi, 0.0, 1.5 * math.pi)
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
        cycles_prefs.compute_device_type = device_type
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
    cam_data.stereo.use_spherical_stereo = True
    cam_data.stereo.use_pole_merge = True
    cam_data.stereo.pole_merge_angle_from = math.pi / 3.0  # 60 deg
    cam_data.stereo.pole_merge_angle_to = math.pi / 2.0    # 90 deg
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
    
    """
    # create materials
    mat_rbc = bpy.data.materials.new(name='Material_RBC')
    mat_ctc = bpy.data.materials.new(name='Material_CTC')
    mat_streamline = bpy.data.materials.new(name='Material_Streamline')
    mat_rbc.use_nodes = True
    mat_ctc.use_nodes = True
    mat_streamline.use_nodes = True
    if color_by_vertex:
        mat_rbc_vertex_color = mat_rbc.node_tree.nodes.new(type = 'ShaderNodeVertexColor')
        mat_rbc_vertex_color.layer_name = 'Col'
        mat_rbc.node_tree.links.new(mat_rbc_vertex_color.outputs[0], mat_rbc.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        mat_ctc_vertex_color = mat_ctc.node_tree.nodes.new(type = 'ShaderNodeVertexColor')
        mat_ctc_vertex_color.layer_name = 'Col'
        mat_ctc.node_tree.links.new(mat_ctc_vertex_color.outputs[0], mat_ctc.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        mat_streamline_vertex_color = mat_streamline.node_tree.nodes.new(type = 'ShaderNodeVertexColor')
        mat_streamline_vertex_color.layer_name = 'Col'
        mat_streamline.node_tree.links.new(mat_streamline_vertex_color.outputs[0], mat_streamline.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    else:
        mat_rbc.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.168, 0.003, 0.003, 1.0)
        mat_ctc.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.009, 0.077, 0.007, 1.0)
        mat_streamline.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.314, 0.357, 0.671, 1.0)
    mat_rbc.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.0
    mat_ctc.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.0
    mat_streamline.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.25
    """
    
    # load materials from external file
    mat_path = os.path.join(model_dir, 'materials.blend') + '\\Material\\'
    mat_rbc_name = 'RBC_Material'
    mat_ctc_name = 'CTC_Material_Alt'
    mat_streamline_name = 'Streamline_Material'
    mat_micropost_name = 'Micropost_Material'
    bpy.ops.wm.append(filename=mat_rbc_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_ctc_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_streamline_name, directory=mat_path)
    bpy.ops.wm.append(filename=mat_micropost_name, directory=mat_path)
    mat_rbc = bpy.data.materials.get(mat_rbc_name)
    mat_ctc = bpy.data.materials.get(mat_ctc_name)
    mat_streamline = bpy.data.materials.get(mat_streamline_name)
    mat_micropost = bpy.data.materials.get(mat_micropost_name)
    
    # import PLY models
    models = [
        #{'filename': os.path.join(model_dir, args.rbc_plyfile), 'material': mat_rbc},
        #{'filename': os.path.join(model_dir, args.ctc_plyfile), 'material': mat_ctc},
        {'filename': os.path.join(model_dir, args.streamline_plyfile), 'material': mat_streamline},
        {'filename': os.path.join(model_dir, 'micropost.ply'), 'material': mat_micropost}
    ]
    for model in models:
        bpy.ops.import_mesh.ply(filepath=model['filename'], filter_glob="*.ply")
        objs = bpy.context.selected_objects
        for obj in objs:
            obj.data.materials.append(model['material'])
            for poly in obj.data.polygons:
                poly.use_smooth = True
            obj.scale = (0.05, 0.05, 0.05)
            obj.rotation_euler = (1.5 * math.pi, 0.0, 0.5 * math.pi)
            obj.location = (25, -12.5, 2.5)
    bpy.ops.mesh.primitive_plane_add(location=(0.0, 0.5, -1.25), rotation=(0.0, 0.0, 0.0))
    plane = bpy.context.selected_objects
    for obj in plane:
        obj.scale = (25.5, 13.5, 1.0)
        obj.data.materials.append(mat_micropost)

    # timer checkpoint - finished data loading/processing, about to start rendering
    mid_time = time.time()

    # render image PNG
    #bpy.context.scene.render.image_settings.file_format = 'PNG'
    #bpy.context.scene.render.filepath = os.path.join(output_dir, 'output.png')
    #bpy.ops.render.render(write_still=1)
    """
    # render image JPEG
    bpy.context.scene.render.image_settings.quality = 92
    bpy.context.scene.render.image_settings.file_format = 'JPEG'
    bpy.context.scene.render.filepath = os.path.realpath(args.output)
    bpy.ops.render.render(write_still=1)
    
    # end timer
    end_time = time.time()
    total_time = secondsToMMSS(end_time - start_time)
    load_time = secondsToMMSS(mid_time - start_time)
    render_time = secondsToMMSS(end_time - mid_time)

    print(f'APP> total time: {total_time}')
    print(f'       model/scene load time {load_time}')
    print(f'       render {dim_x}x{dim_y} time {render_time}')
    """
    


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
