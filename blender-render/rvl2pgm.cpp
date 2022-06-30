#include <iostream>
#include <chrono>

typedef std::chrono::high_resolution_clock::time_point ChronoTime;


void readRvl(const char *filename, uint16_t*& buffer, int *width, int *height, double *near, double *far);
int32_t readFile(const char* filename, char** data_ptr);
int decodeVle(int*& pBuffer, int& word, int& nibblesWritten);
void decompressRvl(char *input, short *output, int numPixels);
void writePgm(const char *filename, uint16_t *values, int width, int height);


int main(int argc, char **argv)
{
    int width, height;
    double near, far;
    uint16_t *depth_buffer;

    // Read RVL file
    readRvl("MdSuperlubricityRVL.cdb/ts510_center_atoms/molecule_01_Depth.rvl", depth_buffer, &width, &height, &near, &far);

    std::cout << "Read RVL file: " << width << "x" << height << " 16-bit depth (" << near << "-" << far << ")" << std::endl;
    
    // Convert back to linear space
    for (int i = 0; i < width * height; i++)
    {
        double depth = 1.0 - ((double)depth_buffer[i] / 65535.0);
        double ndc = (depth * 2.0) - 1.0;
        double o_depth = (2.0 * near * far) / (far + near - ndc * (far - near));
        double n_depth = (o_depth - near) / (far - near);
        //std::cout << depth << ", " << ndc << ", " << o_depth << ", " << n_depth << std::endl;
        depth_buffer[i] = (uint16_t)(n_depth * 65535.0);
    }
    
    // Write PGM grayscale image file
    writePgm("test_depth_m01.pgm", depth_buffer, width, height);

    std::cout << "Finished!" << std::endl;
    
    return 0;
}

void readRvl(const char *filename, uint16_t*& buffer, int *width, int *height, double *near, double *far)
{
    char *rvl;
    int32_t rvl_length = readFile(filename, &rvl);
    if (rvl[0] != 'R' || rvl[1] != 'V' || rvl[2] != 'L' || rvl[3] != '\n')
    {
        std::cerr << "Error: file not RVL format" << std::endl;
        exit(1);
    }
    
    // start decode timer
    ChronoTime t1 = std::chrono::high_resolution_clock::now();
    
    *width = rvl[4] | (rvl[5] << 8) | (rvl[6] << 16) | (rvl[7] << 24);
    *height = rvl[8] | (rvl[9] << 8) | (rvl[10] << 16) | (rvl[11] << 24);
    float *rvl_zclip = (float*)(rvl + 12);
    *near = rvl_zclip[0];
    *far = rvl_zclip[1];
    
    int num_pixels = (*width) * (*height);
    
    short *depth = (short*)malloc(num_pixels * sizeof(short));
    decompressRvl(rvl + 20, depth, num_pixels);
    
    free(rvl);
    
    buffer = (uint16_t*)depth;
    
    // stop decode timer
    ChronoTime t2 = std::chrono::high_resolution_clock::now();
    uint64_t duration = std::chrono::duration_cast<std::chrono::microseconds>(t2 - t1).count();
    std::cout << "RVL decompress (" << (*width) << "x" << (*height) << "): " << ((double)duration / 1000.0) << " ms" << std::endl;
}

int32_t readFile(const char* filename, char** data_ptr)
{
    FILE *fp;
    int err = 0;
#ifdef _WIN32
    err = fopen_s(&fp, filename, "rb");
#else
    fp = fopen(filename, "rb");
#endif
    if (err != 0 || fp == NULL)
    {
        fprintf(stderr, "Error: cannot open %s\n", filename);
        return -1;
    }

    fseek(fp, 0, SEEK_END);
    int32_t fsize = ftell(fp);
    fseek(fp, 0, SEEK_SET);

    *data_ptr = (char*)malloc(fsize);
    size_t read = fread(*data_ptr, fsize, 1, fp);
    if (read != 1)
    {
        fprintf(stderr, "Error: cannot read %s\n", filename);
        return -1;
    }

    fclose(fp);

    return fsize;
}

int decodeVle(int*& pBuffer, int& word, int& nibblesWritten)
{
    uint32_t nibble;
    int value = 0, bits = 29;
    do
    {
        if (!nibblesWritten)
        {
            word = *pBuffer++; // load word
            nibblesWritten = 8;
        }
        nibble = word & 0xf0000000;
        value |= (nibble << 1) >> bits;
        word <<= 4;
        nibblesWritten--;
        bits -= 3;
    } while (nibble & 0x80000000);
    return value;
}

void decompressRvl(char *input, short *output, int numPixels)
{
    int *buffer, *pBuffer;
    buffer = pBuffer = (int*)input;
    
    std::cout << "pBuffer: " << pBuffer[0] << "," << pBuffer[1] << std::endl;

    int word = 0;
    int nibblesWritten = 0;
    short current, previous = 0;

    int numPixelsToDecode = numPixels;
    int test = 0;
    while (numPixelsToDecode)
    {
        int zeros = decodeVle(pBuffer, word, nibblesWritten); // number of zeros
        std::cout << "zeros: " << zeros << std::endl;
        numPixelsToDecode -= zeros;
        for (; zeros; zeros--)
        {
            *output++ = 0;
        }
        int nonzeros = decodeVle(pBuffer, word, nibblesWritten); // number of nonzeros
        std::cout << "nonzeros: " << nonzeros << std::endl;
        numPixelsToDecode -= nonzeros;
        for (; nonzeros; nonzeros--)
        {
            int positive = decodeVle(pBuffer, word, nibblesWritten); // nonzero value
            std::cout << "  pos: " << positive << std::endl;
            int delta = (positive >> 1) ^ -(positive & 1);
            current = previous + delta;
            *output++ = current;
            previous = current;
        }
        
        test++;
        if (test >= 3) exit(1);
    }
}

void writePgm(const char *filename, uint16_t *values, int width, int height)
{
    int i, j;
    FILE *fp = fopen(filename, "wb");
    fprintf(fp, "P5\n%d %d\n65535\n", width, height);
    for (j = 0; j < height; j++)
    {
        for (i = 0; i < width; i++)
        {
            uint16_t val = values[j * width + i];
            fprintf(fp, "%c%c", (uint8_t)(val >> 8), (uint8_t)(val & 0xff));
        }
    }
    fclose(fp);
} 