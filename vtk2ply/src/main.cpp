#include <iostream>
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
#include <vtkXMLPolyDataReader.h>

int main(int argc, char **argv)
{
    int i;
    std::string rbc_filename = "../data/vtk/cell_force_att_1300000.vtp";
    std::string rbc_plyname = "../data/models/cell_force_att_1300000.ply";
    
    // Read in red blood cell data
    vtkNew<vtkXMLPolyDataReader> rbc_reader;
    rbc_reader->SetFileName(rbc_filename.c_str());
    rbc_reader->Update();
    
    vtkSmartPointer<vtkPolyData> rbc_polydata = rbc_reader->GetOutput();
    
    std::cout << "RBC: " << rbc_polydata->GetNumberOfPoints() << " points, ";
    std::cout << rbc_polydata->GetPointData()->GetNumberOfArrays() << " arrays" << std::endl;
    for (i = 0; i < rbc_polydata->GetPointData()->GetNumberOfArrays(); i++) {
        vtkSmartPointer<vtkAbstractArray> array = rbc_polydata->GetPointData()->GetAbstractArray(i);
        printf("  %s (%d)\n", array->GetName(), array->GetNumberOfComponents());
    }
    
    double rand_vector_values[3];
    vtkSmartPointer<vtkDataArray> rand_vectors = vtkDataArray::FastDownCast(rbc_polydata->GetPointData()->GetAbstractArray("RandomPointVectors"));
    vtkNew<vtkFloatArray> rand_texcoords;
    rand_texcoords->SetName("randTexCoords");
    rand_texcoords->SetNumberOfComponents(2);
    rand_texcoords->SetNumberOfTuples(rbc_polydata->GetNumberOfPoints());
    for (i = 0; i < rbc_polydata->GetNumberOfPoints(); i++) {
        rand_vectors->GetTuple(i, rand_vector_values);
        rand_texcoords->SetTuple2(i, rand_vector_values[0], rand_vector_values[1]);
    }
    rbc_polydata->GetPointData()->SetTCoords(rand_texcoords);
    rbc_polydata->GetPointData()->SetActiveTCoords("randTexCoords");
    
    int num_cols = 1024;
    double color_map[7][3] = {
        {0.306, 0.008, 0.035},
        {0.463, 0.031, 0.016},
        {0.580, 0.165, 0.024},
        {0.604, 0.353, 0.137},
        {0.647, 0.502, 0.314},
        {0.851, 0.596, 0.243},
        {0.996, 0.737, 0.169}
    };
    double color[3];
    vtkNew<vtkLookupTable> rbc_lut;
    rbc_lut->SetTableRange(0.0, 0.002872); // global min/max for entire simulation
    rbc_lut->SetNumberOfTableValues(num_cols);
    for (i = 0; i < num_cols; i++) {
        double t = (double)i / (double)num_cols;
        int left_idx = t * 6;
        int right_idx = left_idx + 1;
        t = t * 6.0 - left_idx;
        color[0] = (1.0 - t) * color_map[left_idx][0] + t * color_map[right_idx][0];
        color[1] = (1.0 - t) * color_map[left_idx][1] + t * color_map[right_idx][1];
        color[2] = (1.0 - t) * color_map[left_idx][2] + t * color_map[right_idx][2];
        rbc_lut->SetTableValue(i, color[0], color[1], color[2], 1.0);
    }
    rbc_lut->Build();
    
    vtkNew<vtkPLYWriter> rbc_plywriter;
    rbc_plywriter->SetFileName(rbc_plyname.c_str());
    rbc_plywriter->SetInputData(rbc_polydata);
    rbc_plywriter->SetArrayName("forceMag");
    rbc_plywriter->SetLookupTable(rbc_lut);
    rbc_plywriter->SetFileTypeToBinary();
    rbc_plywriter->Update();

    /*
    std::string rbc_filename = "../resrc/cell990000.vtk";
    std::string ctc_filename = "../resrc/ctc990000.vtk";
    std::string rbc_objname = "../resrc/cell990000.obj";
    std::string ctc_objname = "../resrc/ctc990000.obj";
    
    // Read in red blood cell data
    vtkNew<vtkGenericDataObjectReader> rbc_reader;
    rbc_reader->SetFileName(rbc_filename.c_str());
    rbc_reader->Update();
    
    // Read in cancer cell data
    vtkNew<vtkGenericDataObjectReader> ctc_reader;
    ctc_reader->SetFileName(ctc_filename.c_str());
    ctc_reader->Update();
    
    // Verify data type is poly data
    if(rbc_reader->IsFilePolyData() && ctc_reader->IsFilePolyData())
    {
        vtkSmartPointer<vtkPolyData> rbc_polydata = rbc_reader->GetPolyDataOutput();
        vtkSmartPointer<vtkPolyData> ctc_polydata = ctc_reader->GetPolyDataOutput();
        
        std::cout << "RBC: " << rbc_polydata->GetNumberOfPoints() << " points, ";
        std::cout << rbc_polydata->GetPointData()->GetNumberOfArrays() << " arrays" << std::endl;
        std::cout << "CTC: " << ctc_polydata->GetNumberOfPoints() << " points, ";
        std::cout << ctc_polydata->GetPointData()->GetNumberOfArrays() << " arrays" << std::endl;
        
        
        // TODO:
        // vtkPLYWriter method `SetArrayName` to select RGB array or array of scalars
        //    * if scalars, use method `SetLookupTable` with vtkLookupTable to convert to color
        // vtkPLYWriter method `SetTextureCoordinatesName` to select array for 2D texture coordinates
        vtkNew<vtkPLYWriter> rbc_plywriter;
        rbc_plywriter->SetFileName(rbc_objname.c_str());
        rbc_plywriter->SetInputData(rbc_polydata);
        rbc_plywriter->Update();
        
        vtkNew<vtkPLYWriter> ctc_plywriter;
        ctc_plywriter->SetFileName(ctc_objname.c_str());
        ctc_plywriter->SetInputData(ctc_polydata);
        ctc_plywriter->Update();
    }
    else
    {
        std::cout << "1 or more files do not contain polydata" << std::endl;
    }
    */
    
    return EXIT_SUCCESS;
}