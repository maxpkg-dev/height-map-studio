#version 330 core
in vec2 uv;
out vec4 color;
uniform sampler2D resultMap, normalMap, aoMap, specMap, dispMap;
uniform vec2 viewportSize, imageSize, pan, rotation;
uniform float zoom, lightAngle;
uniform int view3d, shape;
uniform bool directx;
mat3 rotateY(float a) { return mat3(cos(a),0,-sin(a), 0,1,0, sin(a),0,cos(a)); }
mat3 rotateX(float a) { return mat3(1,0,0, 0,cos(a),sin(a), 0,-sin(a),cos(a)); }
void main() {
    vec3 background = vec3(0.085,0.095,0.11);
    vec2 p = (uv-0.5)*viewportSize;
    if (view3d == 0) {
        float fit = min(viewportSize.x/imageSize.x, viewportSize.y/imageSize.y);
        vec2 q = (p-pan)/(imageSize*fit*zoom)+0.5;
        q.y = 1.0-q.y;
        if (any(lessThan(q,vec2(0))) || any(greaterThan(q,vec2(1)))) { color=vec4(background,1); return; }
        color=vec4(texture(resultMap,q).rgb,1);
        return;
    }
    vec2 screen = p/(min(viewportSize.x,viewportSize.y)*0.41*zoom);
    mat3 rot = rotateY(rotation.x)*rotateX(rotation.y);
    vec3 position, normal, tangent, bitangent;
    vec2 q;
    if (shape == 1) {
        float r2 = dot(screen,screen);
        if (r2 >= 1.0) { color=vec4(background,1); return; }
        vec3 n = transpose(rot)*vec3(screen,sqrt(1.0-r2));
        q=vec2(atan(n.z,n.x)/6.2831853+0.5, acos(clamp(n.y,-1.0,1.0))/3.14159265);
        normal=rot*n;
        tangent=normalize(rot*vec3(-n.z,0,n.x));
        // Map v increases downwards, while the normal's green axis points north.
        bitangent=normalize(cross(tangent,normal));
        position=normal;
    } else if (shape == 2) {
        // Intersect an orthographic ray with the rotated cube's local slabs.
        vec3 origin = transpose(rot)*vec3(screen,4.0);
        vec3 ray = transpose(rot)*vec3(0,0,-1);
        float nearHit = -1e20;
        float farHit = 1e20;
        const float extent = 0.72;
        for (int axis=0; axis<3; ++axis) {
            if (abs(ray[axis]) < 1e-6) {
                if (abs(origin[axis]) > extent) { color=vec4(background,1); return; }
            } else {
                float a = (-extent-origin[axis])/ray[axis];
                float b = (extent-origin[axis])/ray[axis];
                nearHit = max(nearHit,min(a,b));
                farHit = min(farHit,max(a,b));
            }
        }
        if (farHit < max(nearHit,0.0)) { color=vec4(background,1); return; }
        vec3 hit = origin + ray*max(nearHit,0.0);
        vec3 side = abs(hit);
        vec3 localNormal, localTangent, localBitangent;
        if (side.x >= side.y && side.x >= side.z) {
            float s = sign(hit.x);
            localNormal=vec3(s,0,0); localTangent=vec3(0,0,-s); localBitangent=vec3(0,1,0);
        } else if (side.y >= side.z) {
            float s = sign(hit.y);
            localNormal=vec3(0,s,0); localTangent=vec3(1,0,0); localBitangent=vec3(0,0,-s);
        } else {
            float s = sign(hit.z);
            localNormal=vec3(0,0,s); localTangent=vec3(s,0,0); localBitangent=vec3(0,1,0);
        }
        // Each face receives a complete map and a right-handed tangent frame.
        q=clamp(vec2(dot(hit,localTangent),-dot(hit,localBitangent))/(2.0*extent)+0.5,vec2(0),vec2(1));
        normal=rot*localNormal;
        tangent=rot*localTangent;
        bitangent=rot*localBitangent;
        position=rot*hit;
    } else {
        normal=rot*vec3(0,0,1);
        vec3 rayOrigin=vec3(screen,4.0);
        vec3 ray=vec3(0,0,-1);
        float denom=dot(normal,ray);
        if (abs(denom)<1e-6) { color=vec4(background,1); return; }
        position=rayOrigin-ray*dot(normal,rayOrigin)/denom;
        vec3 local=transpose(rot)*position;
        // Present a right-handed texture frame on either side of the sheet.
        float faceSign = normal.z >= 0.0 ? 1.0 : -1.0;
        q=vec2(local.x*faceSign,-local.y)*0.5+0.5;
        if (any(lessThan(q,vec2(0))) || any(greaterThan(q,vec2(1)))) { color=vec4(background,1); return; }
        tangent=rot*vec3(faceSign,0,0); bitangent=rot*vec3(0,1,0);
        normal*=faceSign;
        // Lightweight parallax preview; exported displacement remains unmodified data.
        vec3 viewLocal=transpose(rot)*vec3(0,0,1);
        float height=texture(dispMap,q).r-0.5;
        q += vec2(viewLocal.x*faceSign,-viewLocal.y)*height*0.06/max(0.25,abs(viewLocal.z));
        q=clamp(q,vec2(0),vec2(1));
    }
    vec3 detail=texture(normalMap,q).xyz*2.0-1.0;
    if (directx) detail.y=-detail.y;
    vec3 n=normalize(tangent*detail.x+bitangent*detail.y+normal*detail.z);
    vec3 light=normalize(vec3(sin(lightAngle)*0.85,0.65,cos(lightAngle)*0.85));
    float diffuse=max(0.0,dot(n,light));
    float ao=texture(aoMap,q).r;
    float spec=pow(max(0.0,dot(n,normalize(light+vec3(0,0,1)))),48.0)*texture(specMap,q).r;
    vec3 shaded=vec3(0.46,0.52,0.60)*(0.16*ao+0.84*diffuse)+spec*0.6;
    color=vec4(pow(max(shaded,vec3(0)),vec3(1.0/2.2)),1);
}
