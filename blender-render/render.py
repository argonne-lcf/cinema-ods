import bpy
import math
import numpy as np
import os
import time


def main():
    # image resolution (should be 2:1 ratio)
    dim_x = 1440
    dim_y = 720
    
    # model list


    # start timer
    start_time = time.time()
    
    # remove default objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # change render engine to 'Cycles'
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'GPU'
    cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
    for compute_device_type in ('CUDA', 'OPENCL', 'NONE'):
        try:
            cycles_prefs.compute_device_type = compute_device_type
            break
        except TypeError:
            pass
    cycles_prefs.get_devices()
    for device in cycles_prefs.devices:
        device.use = True
    print(f'APP> Cycles Render Engine using: {cycles_prefs.compute_device_type}')

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
    cam.rotation_euler = (math.pi / 2.0, 0.0, 0.0)
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
    mat_rbc.use_nodes = True
    mat_rbc.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.168, 0.003, 0.003, 1.0)
    mat_ctc = bpy.data.materials.new(name='Material_CTC')
    mat_ctc.use_nodes = True
    mat_ctc.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.009, 0.077, 0.007, 1.0)
    
    # import OBJ models
    models = [
        {'filename': os.path.join('resrc', 'cell990000.obj'), 'material': mat_rbc},
        {'filename': os.path.join('resrc', 'ctc990000.obj'), 'material': mat_ctc}
    ]
    for model in models:
        bpy.ops.import_scene.obj(filepath=model['filename'], axis_forward='-Z', axis_up='Y', filter_glob="*.obj;*.mtl")
        objs = bpy.context.selected_objects
        for obj in objs:
            obj.data.materials[0] = model['material']
            for poly in obj.data.polygons:
                poly.use_smooth = True
            obj.scale = (0.05, 0.05, 0.05)
            obj.location = (-12.5, 25.0, 0.0)

    # render image
    #with redirect_stdout(devnull), redirect_stderr(devnull):
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    directory = os.path.dirname(os.path.realpath(__file__))
    bpy.context.scene.render.filepath = os.path.join(directory, 'output.png')
    bpy.ops.render.render(write_still=1)
    
    # end timer
    end_time = time.time()
    elapsed_time = end_time - start_time
    elapsed_mins = int(elapsed_time) // 60
    elapsed_secs = elapsed_time - (60 * elapsed_mins)
    print(f'APP> rendered {dim_x}x{dim_y} image in {elapsed_mins} minutes and {elapsed_secs:.3f} seconds')


main()
