#version 300 es

precision highp float;

in vec3 vertex_position;
in vec2 vertex_texcoord;

out vec2 texcoord;

void main() {
    gl_Position = vec4(vertex_position, 1.0);
    texcoord = vertex_texcoord;
}
