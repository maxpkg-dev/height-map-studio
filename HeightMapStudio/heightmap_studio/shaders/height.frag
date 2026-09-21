#version 330 core
in vec2 uv;
out vec4 color;
uniform sampler2D source;
uniform bool invertHeight;
void main() {
    float h = dot(texture(source, uv).rgb, vec3(0.2126, 0.7152, 0.0722));
    if (invertHeight) h = 1.0 - h;
    color = vec4(h, h, h, 1.0);
}
