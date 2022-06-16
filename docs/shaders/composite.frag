#version 300 es

precision mediump float;
precision highp sampler2DArray;

#define FLT_MAX 3.402823466e+38

in vec2 texcoord;

uniform vec2 resolution;         // overall image resolution
uniform int num_layers;          // total number of layers
uniform int layer_idx[32];       // array of layer indices that are visibile
uniform vec4 background;         // background color
uniform sampler2DArray color;    // array of 2D rgba layers (textures)
uniform sampler2DArray depth;    // array of 2D depth layers (textures)
uniform vec4 bbox[32];           // bounding box of each layer (x_min, y_min, x_max, y_max)

out vec4 FragColor;

void main() {
    int i, j;
    vec4 layer_color[32];
    float layer_depth[32];
    
    // sample all layers to get colors and depths
    for (i = 0; i < num_layers; i++) {
        vec2 pixel = texcoord * resolution;
        if (pixel.x < bbox[layer_idx[i]].x || pixel.x > bbox[layer_idx[i]].z || pixel.y < bbox[layer_idx[i]].y || pixel.y > bbox[layer_idx[i]].w) {
            layer_color[i] = vec4(0.0, 0.0, 0.0, 0.0);
            layer_depth[i] = FLT_MAX;
        }
        else {
            layer_color[i] = texture(color, vec3(texcoord, layer_idx[i]));
            layer_depth[i] = texture(depth, vec3(texcoord, layer_idx[i])).r;
        }
    }
    
    // sort by depth (furthest to closest)
    for (i = 0; i < num_layers - 1; i++) {
        for (j = 0; j < num_layers - i - 1; j++) {
            if (layer_depth[j] < layer_depth[j+1]) {
                vec4 tmp_color = layer_color[j];
                float tmp_depth = layer_depth[j];
                layer_color[j] = layer_color[j+1];
                layer_depth[j] = layer_depth[j+1];
                layer_color[j+1] = tmp_color;
                layer_depth[j+1] = tmp_depth;
            }
        }
    }
    
    // composite
    vec4 composite = background;
    for (i = 0; i < num_layers; i++) {
        composite *= (1.0 - layer_color[i].a);
        composite += vec4(layer_color[i].rgb * layer_color[i].a, layer_color[i].a);
    }
    
    FragColor = composite;
}
