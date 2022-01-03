#include <iostream>
#include <string>
#include <vtkGenericDataObjectReader.h>
#include <vtkNew.h>
#include <vtkOBJWriter.h>
#include <vtkPointData.h>
#include <vtkPolyData.h>
#include <vtkSmartPointer.h>

int main(int argc, char **argv)
{
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
        
        vtkNew<vtkOBJWriter> rbc_objwriter;
        rbc_objwriter->SetFileName(rbc_objname.c_str());
        rbc_objwriter->SetInputData(rbc_polydata);
        rbc_objwriter->Update();
        
        vtkNew<vtkOBJWriter> ctc_objwriter;
        ctc_objwriter->SetFileName(ctc_objname.c_str());
        ctc_objwriter->SetInputData(ctc_polydata);
        ctc_objwriter->Update();
    }
    else
    {
        std::cout << "1 or more files do not contain polydata" << std::endl;
    }
    
    return EXIT_SUCCESS;
}