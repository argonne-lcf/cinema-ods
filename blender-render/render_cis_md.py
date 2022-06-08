import argparse
import bpy
import bmesh
import math
import mathutils
import os
import re
import sys
import time

sys.path.append('C:\Program Files\Python39\Lib\site-packages')

import numpy as np
import OpenEXR


def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Python Blender script for rendering MD simulation data to ODS')
    parser.add_argument('-i', '--input-filepattern', type=str, default='data_%d.vtk', help='pattern for names of input XYZ files')
    parser.add_argument('-w', '--resolution', type=int, default=3840, help='horizontal resolution to render image (will always have 2:1 aspect ratio)')
    parser.add_argument('-d', '--device', type=str, default='CPU', help='redner device (CPU, CUDA, OPTIX, OPENCL)')
    parser.add_argument('-n', '--device-num', type=int, default=0, help='device number')
    parser.add_argument('-cp', '--camera-position', type=str, default='(0.0,0.0,1.65)', help='camera position (x,y,z)')
    parser.add_argument('-cd', '--camera-direction', type=str, default='(90,0,90)', help='camera direction in degrees (x,y,z)')
    parser.add_argument('-rs', '--render-styles',type=str, default='atoms', help='list of render styles (atoms,atomsbonds) or all')
    parser.add_argument('-b', '--bonds', action='store_true', default=False, help='show bonds between atoms') 
    parser.add_argument('-o', '--output', type=str, default='output', help='base filename to save rendered output')

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
    sun.location = (0.0, 0.0, 10.0)
    sun.rotation_euler = (math.radians(-15.0), math.radians(20.0), 0.0)
    sun.data.energy = 2.0
    bpy.context.collection.objects.link(sun)
    
    light_data = bpy.data.lights.new('Light', type='POINT')
    light = bpy.data.objects.new('Light', light_data)
    light.location = light_position
    light.data.energy = 75.0
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
    
    # set background to transparent and make output save OpenEXR
    bpy.context.view_layer.use_pass_z = True
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    tree.nodes[0].location = (700, 300)
    tree.nodes[1].location = (0, 200)
    alpha_over = tree.nodes.new(type='CompositorNodeAlphaOver')
    alpha_over.inputs[1].default_value = (0.0, 0.0, 0.0, 0.0)
    alpha_over.location = (400, 300)
    tree.links.new(tree.nodes[1].outputs[0], alpha_over.inputs[2])
    tree.links.new(alpha_over.outputs[0], tree.nodes[0].inputs[0])
    openexr = tree.nodes.new(type='CompositorNodeOutputFile')
    openexr.format.file_format = 'OPEN_EXR_MULTILAYER'
    openexr.format.exr_codec = 'ZIP'
    openexr.format.views_format = 'MULTIVIEW'
    openexr.format.color_depth = '32'
    openexr.layer_slots.new('Depth')
    openexr.base_path = os.path.realpath(args.output)
    openexr.location = (625, 50)
    tree.links.new(alpha_over.outputs[0], openexr.inputs[0])
    tree.links.new(tree.nodes[1].outputs[2], openexr.inputs[1])
    
    # create materials
    materials = []
    colors = [(0.639, 0.090, 0.051, 1.0), (0.831, 0.733, 0.110, 1.0), (0.024, 0.471, 0.173, 1.0), (0.980, 0.980, 0.980, 1.0)]
    for i in range(4):
        mat = bpy.data.materials.new(name=f'material_{i}')
        mat.use_nodes = True
        col = (colors[i][0] ** 2.2, colors[i][1] ** 2.2, colors[i][2] ** 2.2, colors[i][3])
        principled_bsdf = mat.node_tree.nodes.get('Principled BSDF')
        principled_bsdf.inputs['Base Color'].default_value = col
        if i == 1:
            material_output = mat.node_tree.nodes.get('Material Output')
            principled_bsdf.location = (-200, 100)
            principled_bsdf.inputs['Roughness'].default_value = 0.25
            layer_weight = mat.node_tree.nodes.new('ShaderNodeLayerWeight') # facing --> color_ramp fac
            layer_weight.location = (-950, 250)
            color_ramp = mat.node_tree.nodes.new('ShaderNodeValToRGB') # start pos @ 0.2, end pos @ 1.0, color --> rgb_curves color
            color_ramp.location = (-760, 250)
            color_ramp.color_ramp.elements[0].position = (0.2)
            color_ramp.color_ramp.elements[1].position = (1.0)
            rgb_curves = mat.node_tree.nodes.new('ShaderNodeRGBCurve') # x: 0.75, y: 0.28, color --> emission color
            rgb_curves.location = (-475, 250)
            rgb_curves.mapping.curves[3].points.new(0.75, 0.28)
            rgb_curves.mapping.update()
            emission = mat.node_tree.nodes.new('ShaderNodeEmission')
            emission.location = (-200, 250)
            emission.inputs['Strength'].default_value = 0.9
            add = mat.node_tree.nodes.new('ShaderNodeAddShader')
            add.location = (100, 200)
            mat.node_tree.links.new(color_ramp.inputs[0], layer_weight.outputs[1])
            mat.node_tree.links.new(rgb_curves.inputs[1], color_ramp.outputs[0])
            mat.node_tree.links.new(emission.inputs[0], rgb_curves.outputs[0])
            mat.node_tree.links.new(add.inputs[0], emission.outputs[0])
            mat.node_tree.links.new(add.inputs[1], principled_bsdf.outputs[0])
            mat.node_tree.links.new(material_output.inputs[0], add.outputs[0])
            
            
        materials.append(mat)
        
    # load data (1: graphene (red), 2: nanodiamonds (gold), 3: diamond-like carbon (green), 4: diamond-like carbon (white)
    input_filepattern = getFormatString(args.input_filepattern)
    # actual radius is 0.75 angstroms
    base_models_l = [
        icoSphere(2, 0.45),
        icoSphere(2, 1.00),
        icoSphere(2, 0.45),
        icoSphere(2, 1.15)
        
    ]
    base_models_h = [
        icoSphere(3, 0.45),
        icoSphere(3, 1.00),
        icoSphere(3, 0.45),
        icoSphere(3, 1.15)
        
    ]
    base_bond = cylinder(8, 0.2, 1.0)
    atoms_list = []
    bonds_list = []
    for i in range(4):
        # atoms (spheres)
        input_filename = input_filepattern.format(num=i+1)
        xyz_file = open(input_filename, 'r')
        num_atoms = int(xyz_file.readline().strip())
        num_atoms_used = 0
        xyz_file.readline() # throw away next line
        atoms_mesh = {'vertices': [], 'faces': []}
        atom_positions = []
        for _a in range(num_atoms):
            line = xyz_file.readline().strip().split(' ')
            pos = (float(line[1]), float(line[2]), float(line[3]))
            if i < 3 or pos[2] > 8.0: # filter out some of the large white slab
                t_pos = (pos[0] * -0.1 + 35.0, pos[1] * 0.1 - 15.0, pos[2] * -0.1 + 5.0) 
                if (distance2(cam_position, t_pos) < 100.0):
                    appendModelToMesh(atoms_mesh, base_models_h[i], pos)
                else:
                    appendModelToMesh(atoms_mesh, base_models_l[i], pos)
                atom_positions.append(pos)
                num_atoms_used += 1
        print(f'finished reading XYZ into mesh - using {num_atoms_used} atoms')
        mesh = bpy.data.meshes.new(f'atoms_{i}')
        atoms = bpy.data.objects.new(f'atom_{i}', mesh)
        bpy.context.collection.objects.link(atoms)
        mesh.from_pydata(atoms_mesh['vertices'], [], atoms_mesh['faces'])
        for poly in atoms.data.polygons:
            poly.use_smooth = True
        atoms.scale = (0.1, 0.1, 0.1)
        atoms.rotation_euler = (0.0, math.radians(180.0), 0.0)
        atoms.location = (35.0, -15.0, 5.0)
        if len(atoms.data.materials) > 0:
            atoms.data.materials[0] = materials[i]
        else:
            atoms.data.materials.append(materials[i])
        if i == 3:
            atoms.visible_shadow = False
        atoms_list.append(atoms)
        
        # bonds (cylinders)
        if args.bonds:
            if i == 0 or i == 2:
                bond_file = open(input_filename + '.bond', 'r')
                bond_indices = []
                num_bonds = int(bond_file.readline().strip())
                bond_file.readline() # throw away next line
                for _b in range(num_bonds):
                    line = bond_file.readline().strip().split(' ')
                    bond_indices.append((int(line[0]), int(line[1])))
                bond_mesh = bpy.data.meshes.new(f'bond_{i}')
                bonds = bpy.data.objects.new(f'bond_{i}', bond_mesh)
                bpy.context.collection.objects.link(bonds)
                mat3_scale = mathutils.Matrix.Identity(3)
                bonds_mesh = {'vertices': [], 'faces': []}
                for b in bond_indices:
                    direction = mathutils.Vector(atom_positions[b[1]]) - mathutils.Vector(atom_positions[b[0]])
                    mat3_scale[2][2] = direction.length
                    mat3_rotate = direction.to_track_quat('Z', 'Y').to_matrix()
                    verts = [mat3_rotate @ mat3_scale @ v for v in base_bond['vertices']]
                    appendModelToMesh(bonds_mesh, {'vertices': verts, 'faces': base_bond['faces']}, atom_positions[b[0]])
                bond_mesh.from_pydata(bonds_mesh['vertices'], [], bonds_mesh['faces'])
                for poly in bonds.data.polygons:
                    poly.use_smooth = True
                bonds.scale = (0.1, 0.1, 0.1)
                bonds.rotation_euler = (0.0, math.radians(180.0), 0.0)
                bonds.location = (35.0, -15.0, 5.0)
                if len(bonds.data.materials) > 0:
                    bonds.data.materials[0] = materials[i]
                else:
                    bonds.data.materials.append(materials[i])
                bonds_list.append(bonds)
            else:
                bonds_list.append(None)

    # timer checkpoint - finished data loading/processing, about to start rendering
    mid_time = time.time()

    # render styles
    render_times = []
    render_styles = ['atoms', 'atomsbonds']
    if args.render_styles != 'all':
        render_styles = args.render_styles.split(',')

    csv = open('data.csv', 'w')
    csv.write('Time Step,Camera Position,Bonds,CISVersion,CISImage,CISImageWidth,CISImageHeight,CISLayer,CISChannel,CISChannelVar,CISChannelVarType,FILE\n')
    time_step = 510
    cam_pos = 'center'
    for style in render_styles:
        hide_bonds = True
        bonds_str = 'false'
        if style == 'atomsbonds':
            hide_bonds = False
            bonds_str = 'true'
        
        # each layer
        cis_img = f'ts{time_step}_{cam_pos}_{style}'
        mkdir(cis_img)
        for i in range(4):
            cis_layer = f'molecule_{(i+1):02d}'
            csv.write(f'{time_step},{cam_pos},{bonds_str},1.0,{cis_img},{dim_x},{2 * dim_y},{cis_layer},CISColor,rgba,int,{cis_img}/{cis_layer}_RGBA.npz\n')
            csv.write(f'{time_step},{cam_pos},{bonds_str},1.0,{cis_img},{dim_x},{2 * dim_y},{cis_layer},CISDepth,depth,float,{cis_img}/{cis_layer}_Depth.npz\n')
            
            for j in range(4):
                if i == j:
                    atoms_list[j].hide_render = False
                    if bonds_list[j] != None:
                        bonds_list[j].hide_render = hide_bonds
                else:
                    atoms_list[j].hide_render = True
                    if bonds_list[j] != None:
                        bonds_list[j].hide_render = True
                
            
        
            # start render timer
            render_start = time.time()
            
            # render image
            bpy.ops.render.render()
            
            # end timer
            render_end = time.time()
            render_times.append(secondsToMMSS(render_end - render_start))
        
            # read openexr to get color and depth
            exr_filename = f'{os.path.realpath(args.output)}0001.exr'
            image = OpenEXR.InputFile(exr_filename)
            channels = {'left': {}, 'right' :{}}
            for c in channels:
                red = np.asarray(rgbToSrgb(np.frombuffer(image.channel(f'Image.{c}.R'), np.float16)) * 255, dtype=np.uint8)
                green = np.asarray(rgbToSrgb(np.frombuffer(image.channel(f'Image.{c}.G'), np.float16)) * 255, dtype=np.uint8)
                blue = np.asarray(rgbToSrgb(np.frombuffer(image.channel(f'Image.{c}.B'), np.float16)) * 255, dtype=np.uint8)
                alpha = np.asarray(np.frombuffer(image.channel(f'Image.{c}.A'), np.float16) * 255, dtype=np.uint8)
                #channels[c]['R'] = red
                #channels[c]['G'] = green
                #channels[c]['B'] = blue
                #channels[c]['A'] = alpha
                channels[c]['RGBA'] = np.empty(red.size + green.size + blue.size + alpha.size, dtype=np.uint8)
                channels[c]['RGBA'][0::4] = red
                channels[c]['RGBA'][1::4] = green
                channels[c]['RGBA'][2::4] = blue
                channels[c]['RGBA'][3::4] = alpha
                channels[c]['Depth'] = np.asarray(np.frombuffer(image.channel(f'Depth.{c}.V'), np.float16), dtype=np.float32)
            image.close()
            os.remove(exr_filename)
            
            #new_exr_filename = f'{os.path.realpath(args.output)}_part{i:02d}.exr'
            #if os.path.exists(new_exr_filename):
            #    os.remove(new_exr_filename)
            #os.rename(exr_filename, f'{os.path.realpath(args.output)}_part{i:02d}.exr')
            

            #r2 = np.concatenate((channels['left']['R'], channels['right']['R']))
            #g2 = np.concatenate((channels['left']['G'], channels['right']['G']))
            #b2 = np.concatenate((channels['left']['B'], channels['right']['B']))
            #a2 = np.concatenate((channels['left']['A'], channels['right']['A']))
            rgba = np.concatenate((channels['left']['RGBA'], channels['right']['RGBA']))
            depth = np.concatenate((channels['left']['Depth'], channels['right']['Depth']))
            np.savez_compressed(f'{cis_img}/{cis_layer}_RGBA.npz', rgba=rgba)
            #np.savez_compressed(f'{cis_img}/{cis_layer}_rgba.npz', r=r2, g=g2, b=b2, a=a2)
            np.savez_compressed(f'{cis_img}/{cis_layer}_Depth.npz', depth=depth)
        
            """
            rgb = np.delete(rgba, np.arange(3, rgba.size, 4))
            ppm = open(f'{cis_img}/{cis_layer}.ppm', 'wb')
            ppm.write(f'P6\n{2 * dim_y} {dim_x}\n255\n'.encode('utf-8'))
            ppm.write(rgb.tobytes())
            ppm.close()
            """
        
            process_end = time.time()
            print(f'process time: {secondsToMMSS(process_end - render_end)}')
    csv.close()
    #
    #                                                                                                    ** this should match npz array name **
    #                                                                                                    \_________________  _________________/
    #                                                                                                                      \/
    # All | Normal | Columns | ... | CISVersion | CISImage | CISImageWidth | CISImageHeight | CISLayer | CISChannel | CISChannelVar | CISChannelVarType | FILE
    #  -- |     -- |      -- |  -- |        1.0 | image_id |         width |         height | layer_id |   CISColor |          rgba |               int | __RGBA.npz
    #  -- |     -- |      -- |  -- |        1.0 | image_id |         width |         height | layer_id |     CISRed |             r |               int | __rgba.npz
    #  -- |     -- |      -- |  -- |        1.0 | image_id |         width |         height | layer_id |   CISGreen |             g |               int | __rgba.npz
    #  -- |     -- |      -- |  -- |        1.0 | image_id |         width |         height | layer_id |    CISBlue |             b |               int | __rgba.npz
    #  -- |     -- |      -- |  -- |        1.0 | image_id |         width |         height | layer_id |   CISAlpha |             a |               int | __rgba.npz
    #  -- |     -- |      -- |  -- |        1.0 | image_id |         width |         height | layer_id |   CISDepth |         depth |             float | __Depth.npz
    #
    # VIEWER: Time the following:
    #  - download
    #  - unzip and unpack into raw buffers
    #  - composite image from layers
    #    
    
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
    return re.sub(r'%(0?[1-9]*d)', r'{num:\1}', a_string)


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

def cylinder(sides, radius, height):
    model = {'vertices': [], 'faces': []}
    for i in range(sides):
        theta = i / sides * 2 * math.pi
        x = radius * math.cos(theta)
        y = radius * math.sin(theta)
        z = 0.0
        model['vertices'].append(mathutils.Vector((x, y, z)))
    for i in range(sides):
        theta = i / sides * 2 * math.pi
        x = radius * math.cos(theta)
        y = radius * math.sin(theta)
        z = height
        model['vertices'].append(mathutils.Vector((x, y, z)))
    for i in range(sides):
        v0 = i
        v1 = (i + 1) % sides
        v2 = i + sides
        v3 = (i + 1) % sides + sides
        model['faces'].append([v0, v1, v2])
        model['faces'].append([v1, v3, v2])
    return model
    

def appendModelToMesh(mesh, model, pos):
    vert_offset = len(mesh['vertices'])
    for v in model['vertices']:
        new_vert = (v[0] + pos[0], v[1] + pos[1], v[2] + pos[2])
        mesh['vertices'].append(mathutils.Vector(new_vert))
    for f in model['faces']:
        new_face = []
        for i in f:
            new_face.append(i + vert_offset)
        mesh['faces'].append(new_face)


def rgbToSrgb(channel):
    gamma = 1.0 / 2.4
    srgb = np.piecewise(channel, [channel <= 0.0031308, channel > 0.0031308], [lambda c: 12.92 * c, lambda c: 1.055 * (c ** gamma) - 0.055])
    srgb[srgb>1.0] = 1.0
    return srgb


def mkdir(path):
    exists = os.path.exists(path)
    if not exists:
        os.makedirs(path)

def distance2(p0, p1):
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    dz = p1[2] - p0[2]
    return dx * dx + dy * dy + dz * dz

def secondsToMMSS(seconds):
    mins = int(seconds) // 60
    secs = seconds - (60 * mins)
    return f'{mins:02d}:{secs:06.3f}'

main()
