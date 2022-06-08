#version 300 es

precision mediump float;
precision highp sampler2DArray;

in vec2 texcoord;

uniform int num_layers;
uniform int layer_idx[32];
uniform vec4 background;
uniform sampler2DArray color;
uniform sampler2DArray depth;

out vec4 FragColor;

void main() {
    int i, j;
    vec4 layer_color[32];
    float layer_depth[32];
    
    // sample all layers to get colors and depths
    for (i = 0; i < num_layers; i++) {
        layer_color[i] = texture(color, vec3(texcoord, layer_idx[i]));
        layer_depth[i] = texture(depth, vec3(texcoord, layer_idx[i])).r;
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
