#include <iostream>
#include <cmath>
#include <string>
#include <vtkAbstractArray.h>
#include <vtkDataArray.h>
#include <vtkFloatArray.h>
#include <vtkLookupTable.h>
#include <vtkNew.h>
#include <vtkPLYWriter.h>
#include <vtkPointData.h>
#include <vtkPolyData.h>
#include <vtkSmartPointer.h>
#include <vtkTriangleFilter.h>
#include <vtkXMLPolyDataReader.h>

typedef struct PlyOptions {
    std::string color_array_name;
    double color_array_min;
    double color_array_max;
    bool write_texcoords;
    std::string texcoord_array_name;
    double colormap_hcl_start[3];
    double colormap_hcl_end[3];
    bool write_colormap_ppm;
    std::string colormap_filename;
} PlyOptions;

void convertVtpToPly(std::string vtp_filename, std::string ply_filename, PlyOptions& options);
void hcl2Rgb(double hcl[3], double rgb[3]);

int main(int argc, char **argv)
{
    // Red Blood Cells
    std::string rbc_vtpname = "../data/vtk/cell_force_att_1300000.vtp";
    std::string rbc_plyname = "../data/models/cell_force_att_1300000.ply";
    std::string rbc_colormapname = "../data/rbc_colormap.ppm";
    
    PlyOptions rbc_options;
    rbc_options.color_array_name = "forceMag";
    rbc_options.color_array_min = 0.0;
    rbc_options.color_array_max = 0.0018; // 0.002872
    rbc_options.write_texcoords = true;
    rbc_options.texcoord_array_name = "RandomPointVectors";
    rbc_options.write_colormap_ppm = true;
    rbc_options.colormap_filename = rbc_colormapname;
    // color map start: HCL(5.2, 64.5, 22.0) --> RGB(95, 8, 37)  [dark red-purple]
    rbc_options.colormap_hcl_start[0] = 5.2;
    rbc_options.colormap_hcl_start[1] = 64.5;
    rbc_options.colormap_hcl_start[2] = 22.0;
    // color map end: HCL(62.9, 97.2, 80.9) --> RGB(232, 193, 32)  [yellow-gold]
    rbc_options.colormap_hcl_end[0] = 62.9;
    rbc_options.colormap_hcl_end[1] = 97.2;
    rbc_options.colormap_hcl_end[2] = 80.9;
    
    convertVtpToPly(rbc_vtpname, rbc_plyname, rbc_options);
    
    
    // Circulating Tumor Cells
    std::string ctc_vtpname = "../data/vtk/ctc_force_att_1300000.vtp";
    std::string ctc_plyname = "../data/models/ctc_force_att_1300000.ply";
    std::string ctc_colormapname = "../data/ctc_colormap.ppm";
    
    PlyOptions ctc_options;
    ctc_options.color_array_name = "forceMag";
    ctc_options.color_array_min = 0.0;
    ctc_options.color_array_max = 0.0010; // 0.001047
    ctc_options.write_texcoords = true;
    ctc_options.texcoord_array_name = "RandomPointVectors";
    ctc_options.write_colormap_ppm = true;
    ctc_options.colormap_filename = ctc_colormapname;
    // color map start: HCL(275.0, 57.0, 27.0) --> RGB(70, 50, 127)  [dark purple)
    // color map start: HCL(177.0, 26.4, 22.2) --> RGB(16, 66, 58)  [dark teal)
    ctc_options.colormap_hcl_start[0] = 177.0;
    ctc_options.colormap_hcl_start[1] = 26.4;
    ctc_options.colormap_hcl_start[2] = 22.2;
    // color map end: HCL(103.8, 109.0, 89.1) --> RGB(205, 242, 36)  [yellow-green]
    // color map end: HCL(116.7, 116.7, 84.1) --> RGB(167, 235, 30)  [yellow-green]
    ctc_options.colormap_hcl_end[0] = 116.7;
    ctc_options.colormap_hcl_end[1] = 116.7;
    ctc_options.colormap_hcl_end[2] = 84.1;
    
    convertVtpToPly(ctc_vtpname, ctc_plyname, ctc_options);
    
    
    // Fluid Streamlines
    std::string streamline_vtpname = "../data/vtk/streamline_mag_1300000.vtp";
    std::string streamline_plyname = "../data/models/streamline_mag_1300000.ply";
    std::string streamline_colormapname = "../data/streamline_colormap.ppm";
    
    PlyOptions streamline_options;
    streamline_options.color_array_name = "velMag";
    streamline_options.color_array_min = 0.0;
    streamline_options.color_array_max = 0.025;
    streamline_options.write_texcoords = false;
    streamline_options.write_colormap_ppm = true;
    streamline_options.colormap_filename = streamline_colormapname;
    // color map start: HCL(295.3, 61.0, 28.2) --> RGB(94, 32, 125)  [dark purple)
    streamline_options.colormap_hcl_start[0] = 295.3;
    streamline_options.colormap_hcl_start[1] = 61.0;
    streamline_options.colormap_hcl_start[2] = 28.2;
    // color map end: HCL(239.8, 84.8, 55.6) --> RGB(60, 142, 212)  [light blue]
    streamline_options.colormap_hcl_end[0] = 239.8;
    streamline_options.colormap_hcl_end[1] = 84.8;
    streamline_options.colormap_hcl_end[2] = 55.6;
    
    convertVtpToPly(streamline_vtpname, streamline_plyname, streamline_options);
    
    
    
    return EXIT_SUCCESS;
}

void convertVtpToPly(std::string vtp_filename, std::string ply_filename, PlyOptions& options)
{
    int i;
    
    // Read in vtk polygon data
    vtkNew<vtkXMLPolyDataReader> reader;
    reader->SetFileName(vtp_filename.c_str());
    reader->Update();
    
    vtkSmartPointer<vtkPolyData> polydata = reader->GetOutput();
    
    std::cout << "vtkPolyData: " << polydata->GetNumberOfPoints() << " points, ";
    std::cout << polydata->GetNumberOfPolys() << " polygons, ";
    std::cout << polydata->GetNumberOfCells() << " cells, ";
    std::cout << polydata->GetPointData()->GetNumberOfArrays() << " arrays" << std::endl;
    for (i = 0; i < polydata->GetPointData()->GetNumberOfArrays(); i++)
    {
        vtkSmartPointer<vtkAbstractArray> array = polydata->GetPointData()->GetAbstractArray(i);
        std::cout << "  " << array->GetName() << " (" << array->GetNumberOfComponents() << " components)" << std::endl;
    }
    
    // Triangulate if polygon data doesn't exist
    if (polydata->GetNumberOfPolys() == 0)
    {
        vtkNew<vtkTriangleFilter> triangulate;
        triangulate->SetInputData(polydata);
        triangulate->Update();
        polydata = triangulate->GetOutput();
    }
    
    // Copy specified vector attribute to texture coordinate array
    if (options.write_texcoords)
    {
        double vector_values[3];
        vtkSmartPointer<vtkDataArray> vectors = vtkDataArray::FastDownCast(polydata->GetPointData()->GetAbstractArray(options.texcoord_array_name.c_str()));
        vtkNew<vtkFloatArray> texcoords;
        texcoords->SetName("texCoords");
        texcoords->SetNumberOfComponents(2);
        texcoords->SetNumberOfTuples(polydata->GetNumberOfPoints());
        for (i = 0; i < polydata->GetNumberOfPoints(); i++)
        {
            vectors->GetTuple(i, vector_values);
            texcoords->SetTuple2(i, vector_values[0], vector_values[1]);
        }
        polydata->GetPointData()->SetTCoords(texcoords);
        polydata->GetPointData()->SetActiveTCoords("texCoords");
    }
    
    // Create lookup table for specified colormap
    int num_cols = 1024;
    double hcl[3], rgb[3];
    FILE *ppm = NULL;
    vtkNew<vtkLookupTable> lut;
    lut->SetTableRange(options.color_array_min, options.color_array_max);
    lut->SetNumberOfTableValues(num_cols);
    if (options.write_colormap_ppm)
    {
        ppm = fopen(options.colormap_filename.c_str(), "wb");
        fprintf(ppm, "P6\n%d 1\n255\n", num_cols);
    }
    for (i = 0; i < num_cols; i++)
    {
        double t = (double)i / (double)(num_cols - 1);
        hcl[0] = (1.0 - t) * options.colormap_hcl_start[0] + t * options.colormap_hcl_end[0];
        hcl[1] = (1.0 - t) * options.colormap_hcl_start[1] + t * options.colormap_hcl_end[1];
        hcl[2] = (1.0 - t) * options.colormap_hcl_start[2] + t * options.colormap_hcl_end[2];
        hcl2Rgb(hcl, rgb);
        if (rgb[0] < 0.0 || rgb[1] < 0.0 || rgb[2] < 0.0 || rgb[0] > 1.0 || rgb[1] > 1.0 || rgb[2] > 1.0)
        {
            std::cout << "Warning: RGB out of range (" << i << ") - [" << (int)(255.0 * rgb[0]) << ", " << (int)(255.0 * rgb[1]) << ", " << (int)(255.0 * rgb[2]) << "]" << std::endl;
        }
        lut->SetTableValue(i, rgb[0], rgb[1], rgb[2], 1.0);
        if (options.write_colormap_ppm)
        {
            fprintf(ppm, "%c%c%c", (unsigned char)(255.0 * rgb[0]), (unsigned char)(255.0 * rgb[1]), (unsigned char)(255.0 * rgb[2]));
        }
    }
    if (options.write_colormap_ppm)
    {
        fclose(ppm);
    }
    lut->Build();
    
    // Write PLY file
    vtkNew<vtkPLYWriter> plywriter;
    plywriter->SetFileName(ply_filename.c_str());
    plywriter->SetInputData(polydata);
    plywriter->SetArrayName(options.color_array_name.c_str());
    plywriter->SetLookupTable(lut);
    plywriter->SetFileTypeToBinary();
    plywriter->Update();
}

void hcl2Rgb(double hcl[3], double rgb[3])
{
    // HCL to Luv
    double hue = hcl[0];
    while (hue < 0.0) hue += 360.0;
    while (hue >= 360.0) hue -= 360.0;
    hue *= M_PI / 180.0;
    double l = hcl[2];
    double u = hcl[1] * cos(hue);
    double v = hcl[1] * sin(hue);
    
    // Luv to XYZ
    double d65_whitepoint[3] = {0.9504, 1.0000, 1.0888};
    double u0 = (4.0 * d65_whitepoint[0]) / (d65_whitepoint[0] + 15.0 * d65_whitepoint[1] + 3.0 * d65_whitepoint[2]);
    double v0 = (9.0 * d65_whitepoint[1]) / (d65_whitepoint[0] + 15.0 * d65_whitepoint[1] + 3.0 * d65_whitepoint[2]);
    double kappa = 903.3;
    double epsilon = 0.008856;
    double y = l / kappa;
    if (l > (kappa * epsilon))
    {
        y = ((l + 16.0) / 116.0);
        y = y * y * y;
    }
    double a = (1.0 / 3.0) * (((52.0 * l) / (u + 13.0 * l * u0)) - 1.0);
    double b = -5.0 * y;
    double c = -(1.0 / 3.0);
    double d = y * (((39.0 * l) / (v + 13 * l * v0)) - 5.0);
    double x = (d - b) / (a - c);
    double z = x * a + b;
    
    // XYZ to RGB
    double inv_m[3][3] = {
        { 2.0413690, -0.5649464, -0.3446944},
        {-0.9692660,  1.8760108,  0.0415560},
        { 0.0134474, -0.1183897,  1.0154096}
    };
    double gamma = 2.2;
    double red = x * inv_m[0][0] + y * inv_m[0][1] + z * inv_m[0][2];
    double green = x * inv_m[1][0] + y * inv_m[1][1] + z * inv_m[1][2];
    double blue = x * inv_m[2][0] + y * inv_m[2][1] + z * inv_m[2][2];
    rgb[0] = pow(red, 1.0 / gamma);
    rgb[1] = pow(green, 1.0 / gamma);
    rgb[2] = pow(blue, 1.0 / gamma);
}