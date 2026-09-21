#version 330 core
in vec2 uv;
out vec4 color;
uniform sampler2D heightMap;
uniform vec2 axis, texel;
uniform float sigma;
uniform vec2 boundsMin, boundsMax;
uniform bool clampBounds;
void main() {
    if (sigma < 0.05) { color = texture(heightMap, uv); return; }
    int radius = min(48, int(ceil(sigma * 3.0)));
    float h = 0.0, weights = 0.0;
    for (int i = -48; i <= 48; ++i) {
        if (abs(i) > radius) continue;
        float w = exp(-float(i*i) / (2.0*sigma*sigma));
        vec2 q = uv + axis * texel * float(i);
        if (clampBounds) q = clamp(q, boundsMin, boundsMax);
        h += texture(heightMap, q).r * w;
        weights += w;
    }
    color = vec4(h / weights);
}
