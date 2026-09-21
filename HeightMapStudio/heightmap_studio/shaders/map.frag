#version 330 core
in vec2 uv;
out vec4 color;
uniform sampler2D heightMap;
uniform int mode;
uniform vec2 texel, pixelScale;
uniform float strength, contrast, level, radius, aoStrength;
uniform bool directx;
uniform vec2 boundsMin, boundsMax;
uniform bool clampBounds;
float h(vec2 p) {
    if (clampBounds) p = clamp(p, boundsMin, boundsMax);
    return texture(heightMap, p).r;
}
void main() {
    float center = h(uv);
    if (mode == 0) {
        float dx = 0.0, dy = 0.0;
        for (int i=-1; i<=1; ++i) {
            float w = i == 0 ? 10.0 : 3.0;
            dx += w*(h(uv+vec2(texel.x,float(i)*texel.y))-h(uv+vec2(-texel.x,float(i)*texel.y)));
            dy += w*(h(uv+vec2(float(i)*texel.x,texel.y))-h(uv+vec2(float(i)*texel.x,-texel.y)));
        }
        // Image rows go down; OpenGL tangent Y goes up.
        vec3 n = normalize(vec3(-dx / (32.0*pixelScale.x)*strength,
                                dy / (32.0*pixelScale.y)*strength, 1.0));
        if (directx) n.y = -n.y;
        color = vec4(n*0.5+0.5, 1.0);
    } else if (mode == 2) {
        float occlusion = 0.0;
        for (int direction=0; direction<8; ++direction) {
            float a = 6.28318530718 * float(direction) / 8.0;
            vec2 d = vec2(cos(a), sin(a));
            float horizon = 0.0;
            for (int step=1; step<=6; ++step) {
                float distance = max(1.0, radius * float(step) / 6.0);
                float delta = h(uv + d * distance * texel / pixelScale) - center;
                horizon = max(horizon, max(0.0, delta) * radius / distance);
            }
            occlusion += horizon;
        }
        float ao = exp(-aoStrength * occlusion / 8.0);
        color = vec4(vec3(ao), 1.0);
    } else {
        float v = clamp((center-0.5)*contrast+0.5+level, 0.0, 1.0);
        color = vec4(vec3(v), 1.0);
    }
}
