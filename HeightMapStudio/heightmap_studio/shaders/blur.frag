#version 330 core
in vec2 uv;
out vec4 color;
uniform sampler2D heightMap;
uniform vec2 axis, texel;
uniform float sigma, filterRadius;
uniform int filterMode;
uniform vec2 boundsMin, boundsMax;
uniform bool clampBounds;
void main() {
    if (filterMode != 0) {
        float value = filterMode == 1 ? 1.0 : 0.0;
        int extent = min(48, int(ceil(filterRadius)));
        for (int i=-48; i<=48; ++i) {
            if (abs(i) > extent) continue;
            vec2 q = uv + axis * texel * clamp(float(i),-filterRadius,filterRadius);
            if (clampBounds) q=clamp(q,boundsMin,boundsMax);
            float sampleHeight=texture(heightMap,q).r;
            value=filterMode == 1 ? min(value,sampleHeight) : max(value,sampleHeight);
        }
        color=vec4(value);
        return;
    }
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
