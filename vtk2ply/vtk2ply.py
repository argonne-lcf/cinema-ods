import argparse
import math
import os
import sys
import vtk
from PIL import Image

def main():
    parser = argparse.ArgumentParser(description='Python VTK script for processing blood flow simulation data and outputting PLY models')
    parser.add_argument('-t', '--tex-dir', type=str, default='.', help='directory where input texture coordinate CSV files exist')
    parser.add_argument('-o', '--ply-dir', type=str, default='.', help='directory where output PLY files will be saved')
    parser.add_argument('-r', '--rbc-filename', type=str, default='rbc.vtk', help='name of red blood cell input VTK file')
    parser.add_argument('-c', '--ctc-filename', type=str, default='ctc.vtk', help='name of circulating tumor cell input VTK file')
    parser.add_argument('-f', '--fluid-filename', type=str, default='fluid.vti', help='name of fluid flow input VTK file')
    parser.add_argument('-vr', '--num-verts-rbc', type=int, default=642, help='number of vertices per red blood cell model')
    parser.add_argument('-vc', '--num-verts-ctc', type=int, default=2562, help='number of vertices per circulating tumor cell model')
    parser.add_argument('-s', '--num-streamlines', type=int, default=25, help='number streamlines to generate from fluid data')

    args = parser.parse_args(sys.argv[1:])
    
    # Read in red blood cell and circulating tumor cell data
    rbc_polydata = readVtkFileAsPolyData(args.rbc_filename)
    ctc_polydata = readVtkFileAsPolyData(args.ctc_filename)
    
    """
    # Generate 3D "texture coordinates" based on a single objects normalized location
    generate3DTexCoords(rbc_polydata, args.num_verts_rbc)
    generate3DTexCoords(ctc_polydata, args.num_verts_ctc)
    """
    
    # Add 3D texcoords -- TODO: cmd line arg for these files?
    rbc_texcoords3d = [
        readCsvTexCoordsAsUint8(os.path.join(args.tex_dir, 'rbc_tex_0.csv')),
        readCsvTexCoordsAsUint8(os.path.join(args.tex_dir, 'rbc_tex_1.csv')),
        readCsvTexCoordsAsUint8(os.path.join(args.tex_dir, 'rbc_tex_2.csv')),
    ]
    ctc_texcoords3d = [
        readCsvTexCoordsAsUint8(os.path.join(args.tex_dir, 'ctc_tex_0.csv')),
        readCsvTexCoordsAsUint8(os.path.join(args.tex_dir, 'ctc_tex_1.csv')),
        readCsvTexCoordsAsUint8(os.path.join(args.tex_dir, 'ctc_tex_2.csv')),
    ]
    add3DTexCoordsToPolyData(rbc_polydata, args.num_verts_rbc, rbc_texcoords3d)
    add3DTexCoordsToPolyData(ctc_polydata, args.num_verts_ctc, ctc_texcoords3d)
    
    # Generate normal vectors
    rbc_polydata_w_norms = vtk.vtkPolyDataNormals()
    rbc_polydata_w_norms.SetInputData(rbc_polydata)
    rbc_polydata_w_norms.ComputePointNormalsOn()
    rbc_polydata_w_norms.ComputeCellNormalsOff()
    ctc_polydata_w_norms = vtk.vtkPolyDataNormals()
    ctc_polydata_w_norms.SetInputData(ctc_polydata)
    ctc_polydata_w_norms.ComputePointNormalsOn()
    ctc_polydata_w_norms.ComputeCellNormalsOff()
    
    # Read in fluid flow image data
    fluid = readVtiFile(args.fluid_filename)
    print('Fluid VTI arrays:')
    for i in range(fluid.GetPointData().GetNumberOfArrays()):
        array = fluid.GetPointData().GetAbstractArray(i)
        print(f'  {array.GetName()} ({array.GetNumberOfComponents()} components)')
    fluid.GetPointData().SetActiveVectors('velocity')
    
    # Generate streamlines
    seeds = vtk.vtkLineSource()
    seeds.SetPoint1([0.0, 25.0, 150.0])
    seeds.SetPoint2([520.0, 25.0, 150.0])
    seeds.SetResolution(args.num_streamlines)
    
    fluid_streamlines = vtk.vtkStreamTracer()
    fluid_streamlines.SetInputData(fluid)
    fluid_streamlines.SetSourceConnection(seeds.GetOutputPort())
    fluid_streamlines.SetIntegratorTypeToRungeKutta4()
    fluid_streamlines.SetMaximumPropagation(2000.0)
    fluid_streamlines.SetInitialIntegrationStep(0.75)
    fluid_streamlines.SetIntegrationDirectionToBoth()
    
    # Calculate velocity magnitude
    magnitude_func = 'mag(velocity_vec)'
    fluid_streamlines_velocity_mag = vtk.vtkArrayCalculator()
    fluid_streamlines_velocity_mag.SetInputConnection(fluid_streamlines.GetOutputPort())
    fluid_streamlines_velocity_mag.SetAttributeTypeToPointData()
    fluid_streamlines_velocity_mag.AddVectorVariable('velocity_vec', 'velocity')
    fluid_streamlines_velocity_mag.SetFunction(magnitude_func)
    fluid_streamlines_velocity_mag.SetResultArrayName('velocityMag')
    
    # Convert streamlines to tubes
    fluid_streamtubes = vtk.vtkTubeFilter()
    fluid_streamtubes.SetInputConnection(fluid_streamlines_velocity_mag.GetOutputPort())
    fluid_streamtubes.SetNumberOfSides(16)
    fluid_streamtubes.SetRadius(1.0)
    fluid_streamtubes.CappingOff()
    fluid_streamtubes.Update()
    
    # Calculate strain (based on velocity)
    fluid_w_strain = vtk.vtkCellDerivatives()
    fluid_w_strain.SetInputData(fluid)
    fluid_w_strain.SetVectorModeToPassVectors()
    fluid_w_strain.SetTensorModeToComputeStrain()
    
    # Convert Strain from cell to point property
    fluid_pt_strain = vtk.vtkCellDataToPointData()
    fluid_pt_strain.SetInputConnection(fluid_w_strain.GetOutputPort())
    fluid_pt_strain.AddCellDataArray('Strain')
    fluid_pt_strain.PassCellDataOff()
    
    # Clip cell data to fluid bounding box
    fluid_box = vtk.vtkBox()
    fluid_box.SetBounds(fluid.GetBounds())
    rbc_clip = vtk.vtkClipPolyData()
    rbc_clip.SetInputConnection(rbc_polydata_w_norms.GetOutputPort())
    rbc_clip.SetClipFunction(fluid_box)
    rbc_clip.InsideOutOn()
    ctc_clip = vtk.vtkClipPolyData()
    ctc_clip.SetInputConnection(ctc_polydata_w_norms.GetOutputPort())
    ctc_clip.SetClipFunction(fluid_box)
    ctc_clip.InsideOutOn()
    
    # Resample strain from fluid data at vertex locations in cell data
    #rbc_cell_locator = vtk.vtkStaticCellLocator()
    rbc_polydata_w_strain = vtk.vtkResampleWithDataSet()
    rbc_polydata_w_strain.SetInputConnection(rbc_clip.GetOutputPort())
    rbc_polydata_w_strain.SetSourceConnection(fluid_pt_strain.GetOutputPort())
    rbc_polydata_w_strain.PassPointArraysOn()
    rbc_polydata_w_strain.MarkBlankPointsAndCellsOff()
    #rbc_polydata_w_strain.SetCellLocatorPrototype(rbc_cell_locator)
    ctc_polydata_w_strain = vtk.vtkResampleWithDataSet()
    #ctc_cell_locator = vtk.vtkStaticCellLocator()
    ctc_polydata_w_strain.SetInputConnection(ctc_clip.GetOutputPort())
    ctc_polydata_w_strain.SetSourceConnection(fluid_pt_strain.GetOutputPort())
    ctc_polydata_w_strain.PassPointArraysOn()
    #ctc_polydata_w_strain.SetCellLocatorPrototype(ctc_cell_locator)
    
    # Calculate force on cell membrane
    force_func = ('((Normals_X*Strain_0)+(Normals_Y*Strain_1)+(Normals_Z*Strain_2))*iHat+'
                  '((Normals_X*Strain_3)+(Normals_Y*Strain_4)+(Normals_Z*Strain_5))*jHat+'
                  '((Normals_X*Strain_6)+(Normals_Y*Strain_7)+(Normals_Z*Strain_8))*kHat')
    rbc_polydata_w_force = vtk.vtkArrayCalculator()
    rbc_polydata_w_force.SetInputConnection(rbc_polydata_w_strain.GetOutputPort())
    rbc_polydata_w_force.SetAttributeTypeToPointData()
    rbc_polydata_w_force.AddScalarVariable('Strain_0', 'Strain', 0)
    rbc_polydata_w_force.AddScalarVariable('Strain_1', 'Strain', 1)
    rbc_polydata_w_force.AddScalarVariable('Strain_2', 'Strain', 2)
    rbc_polydata_w_force.AddScalarVariable('Strain_3', 'Strain', 3)
    rbc_polydata_w_force.AddScalarVariable('Strain_4', 'Strain', 4)
    rbc_polydata_w_force.AddScalarVariable('Strain_5', 'Strain', 5)
    rbc_polydata_w_force.AddScalarVariable('Strain_6', 'Strain', 6)
    rbc_polydata_w_force.AddScalarVariable('Strain_7', 'Strain', 7)
    rbc_polydata_w_force.AddScalarVariable('Strain_8', 'Strain', 8)
    rbc_polydata_w_force.AddScalarVariable('Normals_X', 'Normals', 0)
    rbc_polydata_w_force.AddScalarVariable('Normals_Y', 'Normals', 1)
    rbc_polydata_w_force.AddScalarVariable('Normals_Z', 'Normals', 2)
    rbc_polydata_w_force.SetFunction(force_func)
    rbc_polydata_w_force.SetResultArrayName('force')
    ctc_polydata_w_force = vtk.vtkArrayCalculator()
    ctc_polydata_w_force.SetInputConnection(ctc_polydata_w_strain.GetOutputPort())
    ctc_polydata_w_force.SetAttributeTypeToPointData()
    ctc_polydata_w_force.AddScalarVariable('Strain_0', 'Strain', 0)
    ctc_polydata_w_force.AddScalarVariable('Strain_1', 'Strain', 1)
    ctc_polydata_w_force.AddScalarVariable('Strain_2', 'Strain', 2)
    ctc_polydata_w_force.AddScalarVariable('Strain_3', 'Strain', 3)
    ctc_polydata_w_force.AddScalarVariable('Strain_4', 'Strain', 4)
    ctc_polydata_w_force.AddScalarVariable('Strain_5', 'Strain', 5)
    ctc_polydata_w_force.AddScalarVariable('Strain_6', 'Strain', 6)
    ctc_polydata_w_force.AddScalarVariable('Strain_7', 'Strain', 7)
    ctc_polydata_w_force.AddScalarVariable('Strain_8', 'Strain', 8)
    ctc_polydata_w_force.AddScalarVariable('Normals_X', 'Normals', 0)
    ctc_polydata_w_force.AddScalarVariable('Normals_Y', 'Normals', 1)
    ctc_polydata_w_force.AddScalarVariable('Normals_Z', 'Normals', 2)
    ctc_polydata_w_force.SetFunction(force_func)
    ctc_polydata_w_force.SetResultArrayName('force')
    
    # Calculate force magnitude
    magnitude_func = 'mag(force_vec)'
    rbc_polydata_w_force_mag = vtk.vtkArrayCalculator()
    rbc_polydata_w_force_mag.SetInputConnection(rbc_polydata_w_force.GetOutputPort())
    rbc_polydata_w_force_mag.SetAttributeTypeToPointData()
    rbc_polydata_w_force_mag.AddVectorVariable('force_vec', 'force')
    rbc_polydata_w_force_mag.SetFunction(magnitude_func)
    rbc_polydata_w_force_mag.SetResultArrayName('forceMag')
    rbc_polydata_w_force_mag.Update()
    ctc_polydata_w_force_mag = vtk.vtkArrayCalculator()
    ctc_polydata_w_force_mag.SetInputConnection(ctc_polydata_w_force.GetOutputPort())
    ctc_polydata_w_force_mag.SetAttributeTypeToPointData()
    ctc_polydata_w_force_mag.AddVectorVariable('force_vec', 'force')
    ctc_polydata_w_force_mag.SetFunction(magnitude_func)
    ctc_polydata_w_force_mag.SetResultArrayName('forceMag')
    ctc_polydata_w_force_mag.Update()

    # Write Cells and Streamlines to PLY model file
    rbc_plyname = os.path.join(args.ply_dir, os.path.splitext(os.path.basename(args.rbc_filename))[0] + '.ply')
    rbc_colormapname = os.path.join(args.ply_dir, 'rbc_colormap.png')
    rbc_options = {
        'color_array_name': 'forceMag',
        'color_array_min': 0.0,
        'color_array_max': 0.0018, # 0.002872
        'write_texcoords': True,
        'texcoord_array_name': 'texCoords3dAsColor',
        'write_colormap_png': True,
        'colormap_filename': rbc_colormapname,
        'colormap_hcl_start': [5.2, 64.5, 22.0], # HCL(5.2, 64.5, 22.0) --> RGB(95, 8, 37)  [dark red-purple]
        'colormap_hcl_end': [62.9, 97.2, 80.9] # HCL(62.9, 97.2, 80.9) --> RGB(232, 193, 32)  [yellow-gold]
    }
    writeVtkPolyDataToPly(rbc_polydata_w_force_mag.GetOutput(), rbc_plyname, rbc_options)
    
    ctc_plyname = os.path.join(args.ply_dir, os.path.splitext(os.path.basename(args.ctc_filename))[0] + '.ply')
    ctc_colormapname = os.path.join(args.ply_dir, 'ctc_colormap.png')
    ctc_options = {
        'color_array_name': 'forceMag',
        'color_array_min': 0.0,
        'color_array_max': 0.0010, # 0.001047
        'write_texcoords': True,
        'texcoord_array_name': 'texCoords3dAsColor',
        'write_colormap_png': True,
        'colormap_filename': ctc_colormapname,
        'colormap_hcl_start': [177.0, 26.4, 22.2], # HCL(177.0, 26.4, 22.2) --> RGB(16, 66, 58)  [dark teal]
        'colormap_hcl_end': [116.7, 116.7, 84.1] # HCL(116.7, 116.7, 84.1) --> RGB(167, 235, 30)  [yellow-green]
    }
    writeVtkPolyDataToPly(ctc_polydata_w_force_mag.GetOutput(), ctc_plyname, ctc_options)
    
    streamline_plyname = os.path.join(args.ply_dir, f'streamline_{os.path.splitext(os.path.basename(args.fluid_filename))[0]}_{args.num_streamlines}.ply')
    streamline_colormapname = os.path.join(args.ply_dir, 'streamline_colormap.png')
    streamline_options = {
        'color_array_name': 'velocityMag',
        'color_array_min': 0.0,
        'color_array_max': 0.025,
        'write_texcoords': False,
        'write_colormap_png': True,
        'colormap_filename': streamline_colormapname,
        'colormap_hcl_start': [295.3, 61.0, 28.2], # HCL(295.3, 61.0, 28.2) --> RGB(94, 32, 125)  [dark purple]
        'colormap_hcl_end': [239.8, 84.8, 55.6] # HCL(239.8, 84.8, 55.6) --> RGB(60, 142, 212)  [light blue]
    }
    writeVtkPolyDataToPly(fluid_streamtubes.GetOutput(), streamline_plyname, streamline_options)


def readVtkFileAsPolyData(filename):
    # Read file
    reader = vtk.vtkGenericDataObjectReader()
    reader.SetFileName(filename)
    reader.Update()
    
    # Verify data type is poly data
    if not reader.IsFilePolyData():
        print('Error: VTK file does not contain vtkPolyData')
        exit()
    
    # Return vtkPolyData
    return reader.GetPolyDataOutput()


def readVtiFile(filename):
    # Read file
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(filename)
    reader.Update()
    
    # Return vtkImageData
    return reader.GetOutput()


def generate3DTexCoords(polydata, num_verts_per_obj):
    num_objs = polydata.GetNumberOfPoints() // num_verts_per_obj
    obj_indexes = [num_objs // 4, num_objs // 2, 3 * num_objs // 4]
    for i in range(len(obj_indexes)):
        writeObj3DTexCoordsToCsv(i, obj_indexes[i], polydata, num_verts_per_obj)


def writeObj3DTexCoordsToCsv(index, obj_index, polydata, num_verts_per_obj):
    # Get coordinates and bounds for a single object
    single_obj_coords = []
    single_obj_bounds = [9.9e12, -9.9e12, 9.9e12, -9.9e12, 9.9e12, -9.9e12]
    start = obj_index * num_verts_per_obj
    for i in range(start, start + num_verts_per_obj):
        coord = polydata.GetPoints().GetPoint(i)
        if coord[0] < single_obj_bounds[0]:
            single_obj_bounds[0] = coord[0]
        if coord[0] > single_obj_bounds[1]:
            single_obj_bounds[1] = coord[0]
        if coord[1] < single_obj_bounds[2]:
            single_obj_bounds[2] = coord[1]
        if coord[1] > single_obj_bounds[3]:
            single_obj_bounds[3] = coord[1]
        if coord[2] < single_obj_bounds[4]:
            single_obj_bounds[4] = coord[2]
        if coord[2] > single_obj_bounds[5]:
            single_obj_bounds[5] = coord[2]
        single_obj_coords.append([coord[0], coord[1], coord[2]])
    single_obj_center = [
        (single_obj_bounds[0] + single_obj_bounds[1]) / 2,
        (single_obj_bounds[2] + single_obj_bounds[3]) / 2,
        (single_obj_bounds[4] + single_obj_bounds[5]) / 2
    ]
    single_obj_lens = [
        single_obj_bounds[1] - single_obj_bounds[0],
        single_obj_bounds[3] - single_obj_bounds[2],
        single_obj_bounds[5] - single_obj_bounds[4]
    ]
    single_obj_max_len = max(single_obj_lens)
    
    # Normalize coordinates - translate center to origin, scale 1/max_len, translate 0.5 - and write to CSV
    file = open('tex_' + str(index) + '.csv', 'w')
    file.write('s,t,r\n')
    for i in range(len(single_obj_coords)):
        tex_s = min(max((single_obj_coords[i][0] - single_obj_center[0]) / single_obj_max_len + 0.5, 0.0), 1.0)
        tex_t = min(max((single_obj_coords[i][1] - single_obj_center[1]) / single_obj_max_len + 0.5, 0.0), 1.0)
        tex_r = min(max((single_obj_coords[i][2] - single_obj_center[2]) / single_obj_max_len + 0.5, 0.0), 1.0)
        file.write(f'{tex_s},{tex_t},{tex_r}\n')
    file.close()


def readCsvTexCoordsAsUint8(filename):
    file = open(filename, 'r')
    
    data = []
    first = True
    keys = []
    for line in file:
        if first:
            keys = line.strip().split(',')
            first = False
        else:
            values = line.strip().split(',')
            entry = {}
            for i in range(len(keys)):
                entry[keys[i]] = int(255.0 * float(values[i]) + 0.5)
            data.append(entry)
    
    file.close()
    
    return data


def add3DTexCoordsToPolyData(polydata, num_verts_per_obj, texcoords3d):
    # Add array for 3D texture coordinates -- uchar since it will be later saved as "color" in PLY
    tex3d_array = vtk.vtkUnsignedCharArray()
    tex3d_array.SetName('texCoords3dAsColor')
    tex3d_array.SetNumberOfComponents(3)
    tex3d_array.SetNumberOfTuples(polydata.GetNumberOfPoints())
    
    vertex_id = 0
    tex_id = 0
    for i in range(polydata.GetNumberOfPoints()):
        values = texcoords3d[tex_id][vertex_id]
        tex3d_array.SetTuple3(i, values['s'], values['t'], values['r'])
        
        vertex_id += 1
        if vertex_id == num_verts_per_obj:
            vertex_id = 0
            tex_id = (tex_id + 1) % len(texcoords3d)
    
    polydata.GetPointData().AddArray(tex3d_array)


def writeVtpFile(polydata, vtpname):
    # Save vtkPolyData
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(vtpname)
    writer.SetInputData(polydata)
    writer.Write()


def writeVtkPolyDataToPly(polydata, ply_filename, options):
    """
    # Print vtk polygon data contents
    print(f'vtkPolyData: {polydata.GetNumberOfPoints()} points, ', end='')
    print(f'{polydata.GetNumberOfPolys()} polygons, ', end='')
    print(f'{polydata.GetNumberOfCells()} cells, ', end='')
    print(f'{polydata.GetPointData().GetNumberOfArrays()} arrays')
    for i in range(polydata.GetPointData().GetNumberOfArrays()):
        array = polydata.GetPointData().GetAbstractArray(i)
        print(f'  {array.GetName()} ({array.GetNumberOfComponents()} components)')
    """
    
    # Triangulate if polygon data doesn't exist
    if polydata.GetNumberOfPolys() == 0:
        triangulate = vtk.vtkTriangleFilter()
        triangulate.SetInputData(polydata)
        triangulate.Update()
        polydata = triangulate.GetOutput()
    
    # Normalize specified vector attribute for colors to use as texture coordinates for color map image
    color_scalars = vtk.vtkDataArray.FastDownCast(polydata.GetPointData().GetAbstractArray(options['color_array_name']))
    texcoords = vtk.vtkFloatArray()
    texcoords.SetName('texCoords')
    texcoords.SetNumberOfComponents(2)
    texcoords.SetNumberOfTuples(polydata.GetNumberOfPoints())
    min_max = [9.9e12, -9.9e12]
    for i in range(polydata.GetNumberOfPoints()):
        scalar_values = color_scalars.GetTuple(i)
        if scalar_values[0] < min_max[0]:
            min_max[0] = scalar_values[0]
        if scalar_values[0] > min_max[1]:
            min_max[1] = scalar_values[0]
        tex_s = min(max((scalar_values[0] - options['color_array_min']) / (options['color_array_max'] - options['color_array_min']), 0.0), 1.0)
        texcoords.SetTuple2(i, tex_s, 0.5)
    polydata.GetPointData().AddArray(texcoords);
    polydata.GetPointData().SetActiveTCoords('texCoords')
    print(f'{options["color_array_name"]}: [{min_max[0]}, {min_max[1]}]')
    
    # Create image for specified colormap
    if options['write_colormap_png']:
        num_cols = 1024
        cmap = Image.new(mode='RGB', size=(1024, 1))
        pixels = []
        for i in range(num_cols):
            t = i / (num_cols - 1)
            hue = (1.0 - t) * options['colormap_hcl_start'][0] + t * options['colormap_hcl_end'][0]
            chroma = (1.0 - t) * options['colormap_hcl_start'][1] + t * options['colormap_hcl_end'][1]
            luminance = (1.0 - t) * options['colormap_hcl_start'][2] + t * options['colormap_hcl_end'][2]
            rgb = hcl2Rgb(hue, chroma, luminance)
            if rgb[0] < 0.0 or rgb[1] < 0.0 or rgb[2] < 0.0 or rgb[0] > 1.0 or rgb[1] > 1.0 or rgb[2] > 1.0:
                print(f'Warning: RGB out of range ({i}) - [{int(255.0 * rgb[0])}, {int(255.0 * rgb[1])}, {int(255.0 * rgb[2])}]')
            pixels.append([int(255.0 * rgb[0]), int(255.0 * rgb[1]), int(255.0 * rgb[2])])
        cmap.putdata(list(map(tuple, pixels)))
        cmap.save(options['colormap_filename'], format='png')
    
    # Write PLY file
    plywriter = vtk.vtkPLYWriter()
    plywriter.SetFileName(ply_filename)
    plywriter.SetInputData(polydata)
    if options['write_texcoords']:
        plywriter.SetArrayName(options['texcoord_array_name'])
    plywriter.SetTextureCoordinatesNameToUV()
    plywriter.SetFileTypeToBinary()
    plywriter.Write()
    modifyPlyTexCoordNamesToST(ply_filename)


def modifyPlyTexCoordNamesToST(ply_filename):
    tmp_filename = ply_filename + '-tmp.ply';
    inply = open(ply_filename, 'rb');
    outply = open(tmp_filename, 'wb');
    
    line = ''
    while line != 'end_header\n':
        line = inply.readline().decode('utf-8')
        if line == 'property float u\n':
            line = 'property float s\n'
        elif line == 'property float v\n':
            line = 'property float t\n'
        outply.write(line.encode('utf-8'))
    
    copy_done = False
    while not copy_done:
        chunk = inply.read(4096)
        if len(chunk) > 0:
            outply.write(chunk)
        else:
            copy_done = True
    
    inply.close()
    outply.close()
    
    os.remove(ply_filename)
    os.rename(tmp_filename, ply_filename)


def hcl2Rgb(hue, chroma, luminance):
    """
    HCL to RGB
      - Uses Adobe RGB 1988
      - D65 as whitepoint
      - 2.2 as gamma
    """
    # HCL to Luv
    while hue < 0.0:
        hue += 360.0
    while hue >= 360.0:
        hue -= 360.0
    hue = hue * math.pi / 180.0
    l = luminance
    u = chroma * math.cos(hue)
    v = chroma * math.sin(hue)
    
    # Luv to XYZ
    d65_whitepoint = [0.9504, 1.0000, 1.0888]
    u0 = (4.0 * d65_whitepoint[0]) / (d65_whitepoint[0] + 15.0 * d65_whitepoint[1] + 3.0 * d65_whitepoint[2])
    v0 = (9.0 * d65_whitepoint[1]) / (d65_whitepoint[0] + 15.0 * d65_whitepoint[1] + 3.0 * d65_whitepoint[2])
    kappa = 903.3;
    epsilon = 0.008856;
    y = l / kappa
    if l > (kappa * epsilon):
        y = ((l + 16.0) / 116.0) ** 3
    a = (1.0 / 3.0) * (((52.0 * l) / (u + 13.0 * l * u0)) - 1.0)
    b = -5.0 * y
    c = -(1.0 / 3.0)
    d = y * (((39.0 * l) / (v + 13 * l * v0)) - 5.0)
    x = (d - b) / (a - c)
    z = x * a + b
    
    # XYZ to RGB
    inv_m = [
        [ 2.0413690, -0.5649464, -0.3446944],
        [-0.9692660,  1.8760108,  0.0415560],
        [ 0.0134474, -0.1183897,  1.0154096]
    ]
    inv_gamma = 1.0 / 2.2
    red = x * inv_m[0][0] + y * inv_m[0][1] + z * inv_m[0][2]
    green = x * inv_m[1][0] + y * inv_m[1][1] + z * inv_m[1][2]
    blue = x * inv_m[2][0] + y * inv_m[2][1] + z * inv_m[2][2]
    rgb = [red ** inv_gamma, green ** inv_gamma, blue ** inv_gamma]
    return rgb

main()
