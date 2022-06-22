#include <iostream>


void readRvl(const char *filename, uint16_t*& buffer, int *width, int *height);
int32_t readFile(const char* filename, char** data_ptr);
int decodeVle(int*& pBuffer, int& word, int& nibblesWritten);
void decompressRvl(char *input, short *output, int numPixels);
void writePgm(const char *filename, uint16_t *values, int width, int height);


int main(int argc, char **argv)
{
    int width, height;
    uint16_t *depth_buffer;
    
    std::cout << "about to read" << std::endl;
    readRvl("ts510_center_atomsbonds/molecule_02_Depth.rvl", depth_buffer, &width, &height);
    
    std::cout << "finished reading... about to write pgm" << std::endl;
    
    writePgm("test_depth_m02.pgm", depth_buffer, width, height);
    
    std::cout << "finished writing pgm" << std::endl;
    
    return 0;
}

void readRvl(const char *filename, uint16_t*& buffer, int *width, int *height)
{
    char *rvl;
    int32_t rvl_length = readFile(filename, &rvl);
    if (rvl[0] != 'R' || rvl[1] != 'V' || rvl[2] != 'L' || rvl[3] != '\n')
    {
        std::cerr << "Error: file not RVL format" << std::endl;
        exit(1);
    }
    
    int i = 0;
    int j = 4;
    char width_str[10], height_str[10];
    bool first = true
    while (rvl[j] != '\n')
    {
        if (first)
        {
            if (rvl[j] == ' ')
            {
                width_str[i] = '\0';
                first = false;
            }
            else {
                width_str[i] = rvl[j];
            }
        }
        else
        {
            height_str[i] = rvl[j];
        }
        i++;
        j++;
    }
    height_str[i] = '\0';
    
    *width = atoi(width_str);
    *height = atoi(height_str);
    int num_pixels = (*width) * (*height);
    
    short *depth = (short*)malloc(num_pixels * sizeof(short));
    std::cout << "read in file... about to decompress" << std::endl;
    decompressRvl(rvl + (i+5), depth, num_pixels);
    
    free(rvl);
    
    std::cout << "finished decompressing" << std::endl;
    buffer = (uint16_t*)depth;
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

    int word = 0;
    int nibblesWritten = 0;
    short current, previous = 0;

    int numPixelsToDecode = numPixels;
    while (numPixelsToDecode)
    {
        int zeros = decodeVle(pBuffer, word, nibblesWritten); // number of zeros
        std::cout << zeros << " zeros, ";
        numPixelsToDecode -= zeros;
        for (; zeros; zeros--)
        {
            *output++ = 0;
        }
        int nonzeros = decodeVle(pBuffer, word, nibblesWritten); // number of nonzeros
        numPixelsToDecode -= nonzeros;
        std::cout << nonzeros << " non-zeros (" << numPixelsToDecode << " pixels remaining)" << std::endl;
        for (; nonzeros; nonzeros--)
        {
            int positive = decodeVle(pBuffer, word, nibblesWritten); // nonzero value
            int delta = (positive >> 1) ^ -(positive & 1);
            current = previous + delta;
            *output++ = current;
            previous = current;
        }
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