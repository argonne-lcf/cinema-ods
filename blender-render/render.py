import bpy
import math
import numpy as np
import os
import time


def main():
    # image resolution (should be 2:1 ratio)
    dim_x = 3840
    dim_y = 1920
    
    # render device
    #device_type = 'CUDA'
    device_type = 'OPTIX' # OptiX requires Blender 3.0 and best with RTX GPU
    device_number = 0
    
    # solid color vs. color with per-vertex property
    color_by_vertex = True
    
    # data directories
    data_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    model_dir = os.path.join(data_dir, 'models')
    output_dir = os.path.join(data_dir, 'output')


    # start timer
    start_time = time.time()
    
    # remove default objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # change render engine to 'Cycles'
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'GPU'
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
    light.location = (0.0, 0.0, 1.5)
    light.data.energy = 100.0
    bpy.context.collection.objects.link(light)
    
    # add camera
    cam_data = bpy.data.cameras.new('Camera')
    cam_data.type = 'PANO'
    cam_data.clip_start = 0.01
    cam_data.clip_end = 200
    cam_data.cycles.panorama_type = 'EQUIRECTANGULAR'
    cam_data.stereo.convergence_mode = 'OFFAXIS'
    cam_data.stereo.use_spherical_stereo = True
    cam_data.stereo.use_pole_merge = True
    cam_data.stereo.pole_merge_angle_from = math.pi / 3.0  # 60 deg
    cam_data.stereo.pole_merge_angle_to = math.pi / 2.0    # 90 deg
    cam = bpy.data.objects.new('Camera', cam_data)
    cam.location = (0.0, 0.0, 1.35)
    cam.rotation_euler = (0.5 * math.pi, 0.0, 1.5 * math.pi)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    
    # enable stereo
    bpy.context.scene.render.use_multiview = True
    bpy.context.scene.render.resolution_x = dim_x
    bpy.context.scene.render.resolution_y = dim_y
    bpy.context.scene.render.image_settings.views_format = 'STEREO_3D'
    bpy.context.scene.render.image_settings.stereo_3d_format.display_mode = 'TOPBOTTOM'
    
    # create materials
    mat_rbc = bpy.data.materials.new(name='Material_RBC')
    mat_ctc = bpy.data.materials.new(name='Material_CTC')
    mat_rbc.use_nodes = True
    mat_ctc.use_nodes = True
    if color_by_vertex:
        mat_rbc_vertex_color = mat_rbc.node_tree.nodes.new(type = 'ShaderNodeVertexColor')
        mat_rbc_vertex_color.layer_name = 'Col'
        mat_rbc.node_tree.links.new(mat_rbc_vertex_color.outputs[0], mat_rbc.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        mat_ctc_vertex_color = mat_ctc.node_tree.nodes.new(type = 'ShaderNodeVertexColor')
        mat_ctc_vertex_color.layer_name = 'Col'
        mat_ctc.node_tree.links.new(mat_rbc_vertex_color.outputs[0], mat_ctc.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    else:
        mat_rbc.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.168, 0.003, 0.003, 1.0)
        mat_ctc.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.009, 0.077, 0.007, 1.0)
    mat_rbc.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.0
    mat_ctc.node_tree.nodes['Principled BSDF'].inputs['Specular'].default_value = 0.0
    
    #mat_path = 'C:/Users/tmarrinan/Desktop/materials.blend\\Material\\'
    #mat_name = 'TestMaterial01'
    #bpy.ops.wm.append(filename=mat_name, directory=mat_path)
    #mat_ctc = bpy.data.materials.get(mat_name)
    
    # import OBJ models
    #models = [
    #    {'filename': os.path.join(model_dir, 'cell990000.obj'), 'material': mat_rbc},
    #    {'filename': os.path.join(model_dir, 'ctc990000.obj'), 'material': mat_ctc}
    #]
    # import PLY models
    models = [
        {'filename': os.path.join(model_dir, 'cell_force_att_1300000.ply'), 'material': mat_rbc},
        {'filename': os.path.join(model_dir, 'ctc_force_att_1300000.ply'), 'material': mat_ctc}
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

    # timer checkpoint - finished data loading/processing, about to start rendering
    mid_time = time.time()

    """
    # render image PNG
    #bpy.context.scene.render.image_settings.file_format = 'PNG'
    #bpy.context.scene.render.filepath = os.path.join(output_dir, 'output.png')
    #bpy.ops.render.render(write_still=1)
    
    # render image JPEG
    bpy.context.scene.render.image_settings.quality = 92
    bpy.context.scene.render.image_settings.file_format = 'JPEG'
    bpy.context.scene.render.filepath = os.path.join(output_dir, 'output.jpg')
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
