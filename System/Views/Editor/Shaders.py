from __future__ import annotations

# Scene Shader Definitions

SCENE_VERTEX_SHADER_SOURCE = """#version 330 core
layout (location = 0) in vec3 attributePosition;
layout (location = 1) in vec3 attributeNormal;
layout (location = 2) in vec2 attributeTextureCoordinates;
layout (location = 3) in float attributeWallType;

out vec3 FragmentPosition;
out vec3 SurfaceNormal;
out vec2 TextureCoordinates;
flat out float WallType;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform float time;
uniform float lobotomyIntensity;

void main() {
    vec3 calculatedPosition = attributePosition;

    if (lobotomyIntensity > 0.02 && attributeWallType < 2.0) {
        float wave = sin(time * 3.0 + calculatedPosition.y * 2.5 + calculatedPosition.x * 1.8) * 0.06 * lobotomyIntensity;
        calculatedPosition += attributeNormal * wave;
    }

    if (abs(attributeWallType - 53.0) < 0.1) {
        float snapTime = floor(time * 16.0);
        float jitterX = (fract(sin(snapTime * 12.9898) * 43758.5453) - 0.5) * 0.08;
        float jitterY = (fract(sin(snapTime * 78.233) * 43758.5453) - 0.5) * 0.05;
        float jitterZ = (fract(sin(snapTime * 45.164) * 43758.5453) - 0.5) * 0.08;
        calculatedPosition += attributeNormal * jitterX + vec3(0.0, jitterY, jitterZ);
    }

    if (abs(attributeWallType - 301.0) < 0.1) {
        float animationStep = floor(time * 12.0);
        float compressionStep = mod(animationStep, 14.0);
        float heightScale = compressionStep < 7.0 ? 0.965 : 1.0;
        calculatedPosition.y *= heightScale;
    }

    FragmentPosition = vec3(model * vec4(calculatedPosition, 1.0));
    SurfaceNormal = mat3(model) * attributeNormal;
    TextureCoordinates = attributeTextureCoordinates;
    WallType = attributeWallType;
    gl_Position = projection * view * vec4(FragmentPosition, 1.0);
}
"""

SCENE_FRAGMENT_SHADER_SOURCE = """#version 330 core
out vec4 FragmentColor;

in vec3 FragmentPosition;
in vec3 SurfaceNormal;
in vec2 TextureCoordinates;
flat in float WallType;

uniform vec3 viewPos;
uniform vec3 flashlightPosition;
uniform vec3 flashlightDirection;
uniform float time;
uniform float lightFlicker;
uniform float madness;
uniform float realityTear;
uniform float emergencyRed;
uniform float lobotomyIntensity;

uniform vec3 lampPositions[8];
uniform vec3 lampColors[8];
uniform int activeLampCount;

uniform sampler2D decalAtlas;
uniform sampler2D paintingsAtlas;
uniform sampler2D chipsTexture;
uniform sampler2D memoryAtlas;
uniform sampler2D televisionAtlas;
uniform sampler2D cctvTexture;
uniform sampler2D proceduralNoiseTexture;

float calculateNoiseHash(vec2 position) {
    vec2 noiseCoordinates = fract(position * vec2(123.34, 456.21));
    return texture(proceduralNoiseTexture, noiseCoordinates).r;
}

void main() {
    float floorPuddleMask = -1.0;
    vec3 baseSurfaceColor;

    if (abs(WallType - 84.0) < 0.1) {
        float dustShape = 1.0 - length(TextureCoordinates - vec2(0.5, 0.5)) * 2.0;
        dustShape = clamp(dustShape, 0.0, 1.0);
        dustShape = pow(dustShape, 2.2);
        FragmentColor = vec4(vec3(0.85, 0.82, 0.72) * dustShape * 0.45 * lightFlicker, dustShape * 0.45);
        return;
    }

    else if (abs(WallType - 3.0) < 0.1) {
        vec3 tubeGlowColor = vec3(1.4, 1.35, 1.05) * (0.15 + 0.85 * lightFlicker) * (1.0 - 0.7 * madness);

        if (emergencyRed > 0.05) {
            tubeGlowColor = mix(tubeGlowColor, vec3(2.5, 0.15, 0.05) * 1.8, emergencyRed);
        }

        if (realityTear > 0.1) {
            tubeGlowColor = mix(tubeGlowColor, vec3(1.4, 0.05, 0.05) * 2.5, realityTear);
        }

        FragmentColor = vec4(tubeGlowColor, 1.0);
        return;
    }

    else if (abs(WallType - 4.0) < 0.1) {
        baseSurfaceColor = vec3(0.10, 0.09, 0.08);
    }

    else if (abs(WallType - 5.0) < 0.1) {
        vec3 scannerColor = vec3(0.1, 1.0, 0.4) * (1.5 + 0.6 * sin(time * 10.0));
        FragmentColor = vec4(scannerColor, 1.0);
        return;
    }

    else if (abs(WallType - 6.0) < 0.1) {
        baseSurfaceColor = vec3(0.16, 0.11, 0.07) * (0.8 + 0.2 * calculateNoiseHash(FragmentPosition.xy * 12.0));
    }

    else if (abs(WallType - 78.0) < 0.1) {
        float verticalStripe = sin(TextureCoordinates.x * 60.0);
        vec3 wallpaperColor = vec3(0.72, 0.65, 0.38) * (0.92 + 0.08 * verticalStripe) * (1.0 - 0.65 * madness);

        vec2 normalizedCoordinates = TextureCoordinates;
        float bodyCenter = 0.5 + sin(normalizedCoordinates.y * 2.5) * 0.03;
        float bodyWidth = smoothstep(0.0, 0.7, normalizedCoordinates.y) * 0.15 + 0.06;
        float shadowMask = smoothstep(bodyWidth, bodyWidth * 0.4, abs(normalizedCoordinates.x - bodyCenter));

        float headDistance = length(vec2((normalizedCoordinates.x - 0.5) * 1.4, normalizedCoordinates.y - 0.84));
        float headMask = smoothstep(0.14, 0.05, headDistance);

        float totalShadow = clamp(shadowMask + headMask, 0.0, 1.0) * 0.84;
        baseSurfaceColor = mix(wallpaperColor, wallpaperColor * 0.08, totalShadow);
    }

    else if (abs(WallType - 80.0) < 0.1) {
        float cabinetNoise = calculateNoiseHash(FragmentPosition.xy * 24.0 + FragmentPosition.yz * 16.0);
        baseSurfaceColor = vec3(0.42, 0.43, 0.41) * (0.90 + 0.18 * cabinetNoise);
    }

    else if (abs(WallType - 81.0) < 0.1) {
        vec2 staticCoordinates = TextureCoordinates * 140.0 + vec2(time * 50.0, time * 95.0);
        float noiseValue = calculateNoiseHash(staticCoordinates);
        float scanlineEffect = sin(TextureCoordinates.y * 360.0) * 0.14;
        float screenCurvature = 1.0 - length((TextureCoordinates - vec2(0.5, 0.5)) * 1.25);
        screenCurvature = clamp(screenCurvature, 0.35, 1.0);
        vec3 televisionColor = vec3(noiseValue * 0.9 + 0.1 - scanlineEffect) * screenCurvature;
        televisionColor *= vec3(0.85, 0.95, 1.10) * (0.85 + 0.15 * sin(time * 40.0));
        FragmentColor = vec4(televisionColor * 1.8, 1.0);
        return;
    }

    else if (abs(WallType - 86.0) < 0.1) {
        baseSurfaceColor = vec3(0.08, 0.09, 0.10);
    }

    else if (abs(WallType - 87.0) < 0.1) {
        vec3 screenColor = vec3(0.12, 0.28, 0.45) * (0.85 + 0.15 * sin(time * 18.0));
        FragmentColor = vec4(screenColor, 1.0);
        return;
    }

    else if (WallType >= 85.0 && WallType < 101.0) {
        int channelIndex = int(round(WallType - 85.0));
        int column = channelIndex % 4;
        int row = channelIndex / 4;

        vec2 screenCoordinates = TextureCoordinates;
        float vhsTrackingJitter = (fract(sin(floor(screenCoordinates.y * 120.0 + time * 18.0)) * 43758.5453) - 0.5) * 0.006;
        screenCoordinates.x += vhsTrackingJitter;

        vec2 atlasCoordinates = vec2((float(column) + screenCoordinates.x) / 4.0, (float(row) + screenCoordinates.y) / 4.0);
        vec4 broadcastSample = texture(televisionAtlas, atlasCoordinates);

        float scanline = sin(screenCoordinates.y * 360.0) * 0.12;
        float staticNoise = calculateNoiseHash(screenCoordinates * 120.0 + vec2(time * 60.0, time * 90.0)) * 0.10;
        float screenCurvature = 1.0 - length((screenCoordinates - vec2(0.5, 0.5)) * 1.25);
        screenCurvature = clamp(screenCurvature, 0.38, 1.0);

        vec3 broadcastColor = (broadcastSample.rgb * 1.35 + vec3(staticNoise) - scanline) * screenCurvature;
        broadcastColor *= (0.92 + 0.08 * sin(time * 30.0));

        FragmentColor = vec4(broadcastColor * (1.0 - 0.35 * madness), 1.0);
        return;
    }

    else if (abs(WallType - 82.0) < 0.1) {
        vec3 sparkColor = vec3(2.8, 1.9, 0.6) * (1.5 + 0.5 * sin(time * 60.0));
        FragmentColor = vec4(sparkColor, 1.0);
        return;
    }

    else if (abs(WallType - 77.0) < 0.1) {
        FragmentColor = vec4(0.002, 0.002, 0.002, 1.0);
        return;
    }

    else if (abs(WallType - 160.0) < 0.1) {
        vec4 cctvSample = texture(cctvTexture, TextureCoordinates);
        baseSurfaceColor = cctvSample.rgb * vec3(0.7, 0.85, 0.65) * (0.85 + 0.15 * sin(time * 24.0));
        FragmentColor = vec4(baseSurfaceColor, 1.0);
        return;
    }

    else if (abs(WallType - 300.0) < 0.1) {
        vec2 atlasCoordinates = vec2(TextureCoordinates.x / 4.0, TextureCoordinates.y / 4.0);
        vec4 spriteSample = texture(paintingsAtlas, atlasCoordinates);

        if (spriteSample.a < 0.2) {
            discard;
        }

        baseSurfaceColor = spriteSample.rgb * (1.1 - 0.2 * madness);
    }

    else if (abs(WallType - 301.0) < 0.1) {
        vec4 spriteSample = texture(chipsTexture, TextureCoordinates);

        if (spriteSample.a < 0.2) {
            discard;
        }

        baseSurfaceColor = spriteSample.rgb * (1.1 - 0.2 * madness);
    }

    else if (abs(WallType - 50.0) < 0.1) {
        vec2 staticCoordinates = TextureCoordinates * 180.0 + vec2(time * 35.0, time * 80.0);
        float noiseValue = calculateNoiseHash(staticCoordinates);
        baseSurfaceColor = vec3(noiseValue * 0.95) * (0.6 + 0.4 * lightFlicker);
        FragmentColor = vec4(baseSurfaceColor, 1.0);
        return;
    }

    else if (abs(WallType - 51.0) < 0.1) {
        vec2 jitterCoordinates = TextureCoordinates;
        jitterCoordinates.x += sin(time * 85.0) * 0.035;
        jitterCoordinates.y += cos(time * 95.0) * 0.035;
        float verticalStripe = sin(jitterCoordinates.x * 60.0);
        baseSurfaceColor = vec3(0.72, 0.65, 0.38) * (0.88 + 0.12 * verticalStripe) * (1.0 - 0.65 * madness);
    }

    else if (abs(WallType - 52.0) < 0.1) {
        vec2 tileCoordinate = floor(FragmentPosition.xz * 0.42) + floor(FragmentPosition.y * 0.35) * vec2(17.3, 43.7);
        float hashAlpha = calculateNoiseHash(tileCoordinate + vec2(1.23, 3.45));
        float hashBeta = calculateNoiseHash(tileCoordinate + vec2(8.71, 5.19));
        float hashGamma = calculateNoiseHash(tileCoordinate + vec2(19.3, 11.9));

        vec2 holeCenter = vec2(0.5, 0.5) + (vec2(hashAlpha, hashBeta) - 0.5) * 0.32;
        vec2 deltaPosition = TextureCoordinates - holeCenter;
        float distanceLength = length(deltaPosition);
        float polarAngle = atan(deltaPosition.y, deltaPosition.x);

        float lobeCount = 3.0 + floor(hashAlpha * 5.0);
        float baseRadius = 0.17 + hashBeta * 0.15;
        float wobbleAmplitude = 0.03 + hashGamma * 0.05;
        float holeRadius = baseRadius + wobbleAmplitude * sin(polarAngle * lobeCount + hashAlpha * 6.28) + (wobbleAmplitude * 0.4) * cos(polarAngle * (lobeCount + 3.0));

        if (distanceLength < holeRadius) {
            discard;
        }

        else if (distanceLength < holeRadius + 0.038) {
            baseSurfaceColor = vec3(0.008, 0.006, 0.006);
        }

        else {
            float verticalStripe = sin(TextureCoordinates.x * 60.0);
            baseSurfaceColor = vec3(0.72, 0.65, 0.38) * (0.92 + 0.08 * verticalStripe) * (1.0 - 0.65 * madness);
        }
    }

    else if (abs(WallType - 53.0) < 0.1) {
        float verticalStripe = sin(TextureCoordinates.x * 60.0);
        baseSurfaceColor = vec3(0.72, 0.65, 0.38) * (0.92 + 0.08 * verticalStripe) * (1.0 - 0.65 * madness);
    }

    else if (abs(WallType - 54.0) < 0.1) {
        float surfaceGrime = calculateNoiseHash(FragmentPosition.xz * 6.0 + vec2(FragmentPosition.y * 3.0, 0.0));
        vec3 panelColor;

        if (FragmentPosition.y < 1.18) {
            panelColor = vec3(0.16, 0.28, 0.22) * (0.88 + 0.24 * surfaceGrime);
        }

        else if (FragmentPosition.y < 1.24) {
            panelColor = vec3(0.08, 0.06, 0.04);
        }

        else {
            panelColor = vec3(0.68, 0.66, 0.60) * (0.85 + 0.15 * surfaceGrime);
        }

        baseSurfaceColor = panelColor * (1.0 - 0.65 * madness);
    }

    else if (abs(WallType - 55.0) < 0.1) {
        float concreteGrain = calculateNoiseHash(FragmentPosition.xy * 18.0);
        float moistureSeepage = smoothstep(0.25, 0.75, calculateNoiseHash(vec2(floor(FragmentPosition.x * 5.0), 1.0)) * (2.8 - FragmentPosition.y) * 0.45);
        vec3 concreteColor = mix(vec3(0.35, 0.36, 0.33), vec3(0.18, 0.21, 0.16), moistureSeepage);
        baseSurfaceColor = concreteColor * (0.82 + 0.18 * concreteGrain) * (1.0 - 0.70 * madness);
    }

    else if (abs(WallType - 56.0) < 0.1) {
        vec2 brickCoordinates = fract(vec2(FragmentPosition.x * 2.2, FragmentPosition.y * 5.2));
        float mortarMask = step(0.08, brickCoordinates.x) * step(0.12, brickCoordinates.y);
        vec3 brickColor = mix(vec3(0.12, 0.11, 0.10), vec3(0.30, 0.15, 0.10), mortarMask);
        float tearNoise = calculateNoiseHash(floor(FragmentPosition.xy * 1.6) + vec2(4.2, 7.1));
        float distanceToTear = length(TextureCoordinates - vec2(0.5 + 0.2 * sin(tearNoise * 6.28), 0.5));
        float tearMask = smoothstep(0.26, 0.36, distanceToTear);
        float verticalStripe = sin(TextureCoordinates.x * 60.0);
        vec3 wallpaperColor = vec3(0.72, 0.65, 0.38) * (0.92 + 0.08 * verticalStripe);
        baseSurfaceColor = mix(brickColor, wallpaperColor, tearMask) * (1.0 - 0.65 * madness);
    }

    else if (abs(WallType - 57.0) < 0.1) {
        vec2 tileGrid = fract(FragmentPosition.xy * 4.0);
        float groutLine = step(0.06, tileGrid.x) * step(0.06, tileGrid.y);
        float tileVariance = calculateNoiseHash(floor(FragmentPosition.xy * 4.0));
        vec3 tileColor = mix(vec3(0.09, 0.11, 0.12), vec3(0.55, 0.60, 0.58) * (0.94 + 0.12 * tileVariance), groutLine);
        baseSurfaceColor = tileColor * (1.0 - 0.60 * madness);
    }

    else if (WallType >= 200.0 && WallType < 250.0) {
        int memoryIndex = int(round(WallType - 200.0));
        int column = memoryIndex % 4;
        int row = memoryIndex / 4;
        vec2 atlasCoordinates = vec2((float(column) + TextureCoordinates.x) / 4.0, (float(row) + TextureCoordinates.y) / 4.0);
        vec4 memorySample = texture(memoryAtlas, atlasCoordinates);

        vec2 carpetTile = fract(FragmentPosition.xz * 6.0);
        float noise = calculateNoiseHash(carpetTile);
        vec3 carpetColor = vec3(0.45, 0.40, 0.25) * (0.85 + 0.2 * noise) * (1.0 - 0.55 * madness);
        baseSurfaceColor = mix(carpetColor, memorySample.rgb, memorySample.a);
    }

    else if (WallType >= 100.0 && WallType < 150.0) {
        int pictureIndex = int(round(WallType - 100.0));
        int column = pictureIndex % 4;
        int row = pictureIndex / 4;
        vec2 atlasCoordinates = vec2((float(column) + TextureCoordinates.x) / 4.0, (float(row) + TextureCoordinates.y) / 4.0);
        vec4 paintingSample = texture(paintingsAtlas, atlasCoordinates);
        baseSurfaceColor = paintingSample.rgb * (1.0 - 0.65 * madness);
    }

    else if (WallType >= 10.0 && WallType < 50.0) {
        int decalIndex = int(round(WallType - 10.0));
        float horizontalCoordinate = (float(decalIndex % 4) + TextureCoordinates.x) / 4.0;
        float verticalCoordinate = (float(decalIndex / 4) + TextureCoordinates.y) / 4.0;
        vec4 decalSample = texture(decalAtlas, vec2(horizontalCoordinate, verticalCoordinate));

        if (decalSample.a < 0.05) {
            discard;
        }

        baseSurfaceColor = decalSample.rgb;
    }

    else if (abs(SurfaceNormal.y) > 0.8) {
        if (SurfaceNormal.y < 0.0) {
            vec2 ceilingCoordinates = FragmentPosition.xz * 0.4;
            vec2 ceilingFractional  = fract(ceilingCoordinates);
            vec2 ceilingIndex       = floor(ceilingCoordinates);
            float tileNoiseHash     = calculateNoiseHash(ceilingIndex + vec2(13.7, 29.3));

            if (tileNoiseHash < 0.045) {
                vec3 voidColor = vec3(0.004, 0.003, 0.002);

                if (ceilingFractional.x < 0.04 || ceilingFractional.y < 0.04 || ceilingFractional.x > 0.96 || ceilingFractional.y > 0.96) {
                    voidColor = vec3(0.10, 0.07, 0.04);
                }

                baseSurfaceColor = voidColor;
            }

            else if (tileNoiseHash < 0.09) {
                float stain = smoothstep(0.1, 0.45, length(ceilingFractional - vec2(0.5, 0.5)));
                vec3 moldColor = mix(vec3(0.18, 0.15, 0.09), vec3(0.52, 0.50, 0.42), stain);
                baseSurfaceColor = moldColor * (1.0 - 0.6 * madness);

                if (ceilingFractional.x < 0.03 || ceilingFractional.y < 0.03) {
                    baseSurfaceColor *= 0.45;
                }
            }

            else {
                baseSurfaceColor = vec3(0.68, 0.66, 0.58) * (1.0 - 0.6 * madness);

                if (ceilingFractional.x < 0.03 || ceilingFractional.y < 0.03) {
                    baseSurfaceColor *= 0.45;
                }
            }
        }

        else {
            vec2 carpetTile = fract(FragmentPosition.xz * 6.0);
            float noise = calculateNoiseHash(carpetTile);
            vec3 dryCarpet = vec3(0.45, 0.40, 0.25) * (0.85 + 0.2 * noise) * (1.0 - 0.55 * madness);

            float puddleNoise = calculateNoiseHash(floor(FragmentPosition.xz * 0.85) + vec2(7.1, 3.4));
            float puddleMask = smoothstep(0.70, 0.80, puddleNoise);
            floorPuddleMask = puddleMask;

            vec3 wetCarpet = dryCarpet * 0.28;
            baseSurfaceColor = mix(dryCarpet, wetCarpet, puddleMask);
        }
    }

    else {
        float verticalStripe = sin(TextureCoordinates.x * 60.0);
        baseSurfaceColor = vec3(0.72, 0.65, 0.38) * (0.92 + 0.08 * verticalStripe) * (1.0 - 0.65 * madness);
    }

    vec3 fragmentToCamera = viewPos - FragmentPosition;
    float inverseCameraDistance = inversesqrt(dot(fragmentToCamera, fragmentToCamera));
    float distanceToCamera = 1.0 / inverseCameraDistance;
    vec3 cameraLightDirection = fragmentToCamera * inverseCameraDistance;
    vec3 normalizedNormal = SurfaceNormal;

    vec3 lampDiffuseTotal = vec3(0.0);

    for (int lampIndex = 0; lampIndex < 8; ++lampIndex) {
        if (lampIndex >= activeLampCount) {
            break;
        }

        vec3 lampOffset = lampPositions[lampIndex] - FragmentPosition;
        float inverseLampDistance = inversesqrt(dot(lampOffset, lampOffset));
        float lampDistance = 1.0 / inverseLampDistance;
        vec3 lampDirection = lampOffset * inverseLampDistance;
        float surfaceDiffuse = max(dot(normalizedNormal, lampDirection), 0.0);

        if (normalizedNormal.y < -0.6) {
            surfaceDiffuse = 0.45;
        }

        float lampAttenuation = 1.0 / (1.0 + 0.85 * lampDistance + 0.95 * lampDistance * lampDistance);
        lampDiffuseTotal += lampColors[lampIndex] * surfaceDiffuse * lampAttenuation;
    }

    vec3 fragmentToFlashlight = flashlightPosition - FragmentPosition;
    float inverseFlashlightDistance = inversesqrt(dot(fragmentToFlashlight, fragmentToFlashlight));
    float distanceToFlashlight = 1.0 / inverseFlashlightDistance;
    vec3 lightDirectionFlashlight = fragmentToFlashlight * inverseFlashlightDistance;

    vec3 flashlightToFragment = -lightDirectionFlashlight;
    vec3 normalizedFlashlightDirection = normalize(flashlightDirection);
    float spotCosine = dot(flashlightToFragment, normalizedFlashlightDirection);

    float innerConeAngle = 0.965;
    float outerConeAngle = 0.82;
    float spotAngleFactor = clamp((spotCosine - outerConeAngle) / (innerConeAngle - outerConeAngle), 0.0, 1.0);
    spotAngleFactor = pow(spotAngleFactor, 1.8);

    float flashlightFalloff = 1.0 / (1.0 + 0.18 * distanceToFlashlight + 0.065 * distanceToFlashlight * distanceToFlashlight);
    float flashlightDiffuse = max(dot(normalizedNormal, lightDirectionFlashlight), 0.0);

    vec3 flashlightHalfVector = normalize(lightDirectionFlashlight + cameraLightDirection);
    float flashlightSpecularBase = max(dot(normalizedNormal, flashlightHalfVector), 0.0);
    float flashlightSpecularSquared = flashlightSpecularBase * flashlightSpecularBase;
    float flashlightSpecularFourth = flashlightSpecularSquared * flashlightSpecularSquared;
    float flashlightSpecularEighth = flashlightSpecularFourth * flashlightSpecularFourth;
    float flashlightSpecularSixteenth = flashlightSpecularEighth * flashlightSpecularEighth;
    float flashlightSpecular = flashlightSpecularSixteenth * flashlightSpecularEighth * flashlightSpecularFourth;

    vec3 flashlightColor = vec3(1.22, 1.18, 1.08) * 2.8 * (0.85 + 0.15 * lightFlicker);
    vec3 flashlightComponent = flashlightColor * (flashlightDiffuse + flashlightSpecular * 0.42) * spotAngleFactor * flashlightFalloff;

    float minimalCorridorAmbient = mix(0.002, 0.0005, madness);
    vec3 lightTint = mix(vec3(1.0, 0.96, 0.84), vec3(2.0, 0.15, 0.05), emergencyRed);
    vec3 ambientComponent = minimalCorridorAmbient * lightTint * lightFlicker;

    vec3 totalIllumination = ambientComponent + lampDiffuseTotal + flashlightComponent;
    vec3 illuminatedColor = totalIllumination * baseSurfaceColor;

    if (normalizedNormal.y > 0.8) {
        float puddleMask = floorPuddleMask;

        if (puddleMask < 0.0) {
            float puddleNoise = calculateNoiseHash(floor(FragmentPosition.xz * 0.85) + vec2(7.1, 3.4));
            puddleMask = smoothstep(0.70, 0.80, puddleNoise);
        }

        vec3 floorReflectedVector = reflect(-cameraLightDirection, normalizedNormal);
        float floorGlossBase = max(dot(floorReflectedVector, cameraLightDirection), 0.0);
        float floorGlossSquared = floorGlossBase * floorGlossBase;
        float floorGlossFourth = floorGlossSquared * floorGlossSquared;
        float floorGlossEighth = floorGlossFourth * floorGlossFourth;
        float floorGlossSixteenth = floorGlossEighth * floorGlossEighth;
        float floorGloss = floorGlossSixteenth * floorGlossEighth * floorGlossSquared * puddleMask * (0.2 + 0.8 * spotAngleFactor) * lightFlicker;
        illuminatedColor += vec3(0.55, 0.62, 0.58) * floorGloss;
    }

    float fogPiercingFactor = 1.0 + spotAngleFactor * 2.4;
    float effectiveFogDistance = distanceToCamera / fogPiercingFactor;
    float fogDensity = mix(0.085, 0.16, madness);
    float fogFactor = 1.0 - exp(-pow(effectiveFogDistance * fogDensity, 1.7));
    fogFactor = clamp(fogFactor, 0.0, 1.0);

    vec3 darkCorridorFog = vec3(0.002, 0.002, 0.003);
    vec3 redEmergencyFog = vec3(0.18, 0.01, 0.01);
    vec3 fogColor = mix(darkCorridorFog, redEmergencyFog, emergencyRed);

    float beamScattering = spotAngleFactor * clamp(1.0 - distanceToFlashlight / 16.0, 0.0, 1.0) * 0.032 * lightFlicker;
    illuminatedColor += flashlightColor * beamScattering;

    illuminatedColor = mix(illuminatedColor, fogColor, fogFactor);
    FragmentColor = vec4(illuminatedColor, 1.0);
}
"""

# Monster Shader Definitions

MONSTER_VERTEX_SHADER_SOURCE = """#version 330 core
layout (location = 0) in vec3 attributePosition;
layout (location = 1) in vec3 attributeNormal;
layout (location = 2) in float attributeMaterialType;

out vec3 FragmentPosition;
out vec3 SurfaceNormal;
flat out float MaterialType;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform float time;
uniform float twitchIntensity;

void main() {
    vec3 calculatedPosition = attributePosition;
    float twitch = sin(time * 65.0 + calculatedPosition.y * 30.0) * 0.035 * twitchIntensity;
    float spasm = step(0.94, sin(time * 12.0 + calculatedPosition.y * 5.0)) * 0.08 * sin(time * 120.0);

    if (calculatedPosition.y > 0.8 && calculatedPosition.y < 2.0 && attributeMaterialType < 1.5) {
        float breathe = sin(time * 8.0) * 0.04;
        calculatedPosition.x += attributeNormal.x * breathe;
        calculatedPosition.z += attributeNormal.z * breathe;
    }

    calculatedPosition.x += twitch + spasm;
    calculatedPosition.z += cos(time * 55.0 + calculatedPosition.y * 22.0) * 0.035 * twitchIntensity;

    FragmentPosition = vec3(model * vec4(calculatedPosition, 1.0));
    SurfaceNormal = mat3(model) * attributeNormal;
    MaterialType = attributeMaterialType;

    gl_Position = projection * view * vec4(FragmentPosition, 1.0);
}
"""

MONSTER_FRAGMENT_SHADER_SOURCE = """#version 330 core
out vec4 FragmentColor;

in vec3 FragmentPosition;
in vec3 SurfaceNormal;
flat in float MaterialType;

uniform vec3 viewPos;
uniform float time;

void main() {
    vec3 normalizedNormal = normalize(SurfaceNormal);
    vec3 viewDirection = normalize(viewPos - FragmentPosition);

    if (abs(MaterialType - 2.0) < 0.1) {
        FragmentColor = vec4(vec3(2.8, 0.2, 0.1) * (1.3 + 0.5 * sin(time * 25.0)), 1.0);
        return;
    }

    if (abs(MaterialType - 1.0) < 0.1) {
        float diffuseIntensity = max(dot(normalizedNormal, viewDirection), 0.0);
        FragmentColor = vec4(mix(vec3(0.85, 0.82, 0.70) * (0.2 + 0.8 * diffuseIntensity), vec3(0.4, 0.02, 0.02), 0.45), 1.0);
        return;
    }

    float diffuseIntensity = max(dot(normalizedNormal, viewDirection), 0.0);
    vec3 halfVector = normalize(viewDirection + viewDirection);
    float specularHighlight = pow(max(dot(normalizedNormal, halfVector), 0.0), 48.0);
    float fresnelFactor = pow(1.0 - max(dot(normalizedNormal, viewDirection), 0.0), 3.5);

    vec3 baseFlesh = vec3(0.04, 0.035, 0.03);
    vec3 slimeSpecular = vec3(0.7, 0.65, 0.6) * specularHighlight * 1.8;
    vec3 rimLight = vec3(0.2, 0.25, 0.22) * fresnelFactor * 2.2;

    FragmentColor = vec4(baseFlesh * (0.15 + 0.85 * diffuseIntensity) + slimeSpecular + rimLight, 1.0);
}
"""

# HUD Shader Definitions

HUD_VERTEX_SHADER_SOURCE = """#version 330 core
layout (location = 0) in vec2 attributePosition;
out vec2 TextureCoordinates;
uniform vec4 uRect;

void main() {
    TextureCoordinates = vec2(attributePosition.x, 1.0 - attributePosition.y);
    vec2 screenPosition = uRect.xy + attributePosition * uRect.zw;
    gl_Position = vec4(screenPosition, 0.0, 1.0);
}
"""

HUD_FRAGMENT_SHADER_SOURCE = """#version 330 core
out vec4 FragmentColor;
in vec2 TextureCoordinates;
uniform sampler2D hudTexture;

void main() {
    vec4 textureColor = texture(hudTexture, TextureCoordinates);

    if (textureColor.a < 0.02) {
        discard;
    }

    FragmentColor = textureColor;
}
"""

# Post Processing Shader Definitions

QUAD_VERTEX_SHADER_SOURCE = """#version 330 core
layout (location = 0) in vec2 attributePosition;
layout (location = 1) in vec2 attributeTextureCoordinates;
out vec2 TextureCoordinates;

void main() {
    TextureCoordinates = attributeTextureCoordinates;
    gl_Position = vec4(attributePosition.x, attributePosition.y, 0.0, 1.0);
}
"""

VHS_FRAGMENT_SHADER_SOURCE = """#version 330 core
out vec4 FragmentColor;
in vec2 TextureCoordinates;

uniform sampler2D screenTexture;
uniform float time;
uniform float glitchMultiplier;
uniform float introPhase;
uniform float cutToBlack;
uniform float realityTear;
uniform float jumpscareBlood;
uniform float derealization;
uniform float lobotomyIntensity;
uniform float heavyEyelids;
uniform float whiteBloom;
uniform float coldDesat;
uniform vec2 cameraTurnVector;
uniform float cameraTurnBlur;

float smoothMetaball(vec2 samplePoint, vec2 centerPoint, float radius) {
    float distanceLength = length(samplePoint - centerPoint);
    return smoothstep(radius, radius * 0.4, distanceLength);
}

vec3 cameraLensSample(vec2 coordinates) {
    vec3 centerSample = texture(screenTexture, clamp(coordinates, vec2(0.002), vec2(0.998))).rgb;
    vec2 motionOffset = cameraTurnVector * cameraTurnBlur * vec2(0.008, 0.008);
    vec3 motionBlurred = (
        texture(screenTexture, clamp(coordinates - motionOffset, vec2(0.002), vec2(0.998))).rgb +
        centerSample * 2.0 +
        texture(screenTexture, clamp(coordinates + motionOffset, vec2(0.002), vec2(0.998))).rgb
    ) * 0.25;

    return mix(centerSample, motionBlurred, cameraTurnBlur * 0.65);
}

void main() {
    if (cutToBlack > 0.5) {
        FragmentColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    vec2 coordinates = TextureCoordinates;

    if (lobotomyIntensity > 0.01) {
        coordinates.x += sin(coordinates.y * 14.0 + time * 3.5) * 0.012 * lobotomyIntensity;
        coordinates.y += cos(coordinates.x * 12.0 + time * 4.0) * 0.012 * lobotomyIntensity;
    }

    float totalGlitch = glitchMultiplier;

    if (totalGlitch > 1.2) {
        float rowJitter = step(0.92, fract(sin(floor(coordinates.y * 50.0) + time * 20.0) * 43758.5453));
        coordinates.x += (fract(sin(time * 30.0) * 43758.5453) - 0.5) * 0.04 * rowJitter * (totalGlitch - 1.0);
    }

    vec3 baseColor = (introPhase > 0.5) ? vec3(0.015, 0.02, 0.03) : cameraLensSample(coordinates);
    vec2 displacementDirection = coordinates - 0.5;
    float chromaticShift = 0.006 + 0.0015 * totalGlitch + lobotomyIntensity * 0.004;
    float redChannel = (introPhase > 0.5) ? baseColor.r :
                       mix(baseColor.r, texture(screenTexture, clamp(coordinates + displacementDirection * chromaticShift, vec2(0.002), vec2(0.998))).r, 0.88);
    float greenChannel = baseColor.g;
    float blueChannel = (introPhase > 0.5) ? baseColor.b :
                        mix(baseColor.b, texture(screenTexture, clamp(coordinates - displacementDirection * chromaticShift, vec2(0.002), vec2(0.998))).b, 0.88);
    vec3 resolvedColor = vec3(redChannel, greenChannel, blueChannel);

    if (coldDesat > 0.01) {
        float grayscale = dot(resolvedColor, vec3(0.299, 0.587, 0.114));
        vec3 coldTint = vec3(grayscale * 0.65, grayscale * 0.85, grayscale * 0.70);
        resolvedColor = mix(resolvedColor, coldTint, coldDesat);
    }

    if (derealization > 0.005) {
        vec3 shiftedColor = resolvedColor;
        shiftedColor.r = mix(resolvedColor.r, resolvedColor.r * 0.94 + resolvedColor.g * 0.09, derealization);
        shiftedColor.g = mix(resolvedColor.g, resolvedColor.g * 1.05 + resolvedColor.b * 0.05, derealization);
        shiftedColor.b = mix(resolvedColor.b, resolvedColor.b * 0.89 + resolvedColor.r * 0.11, derealization);
        shiftedColor = pow(shiftedColor, vec3(1.0 - 0.10 * derealization, 1.0 + 0.07 * derealization, 1.0 - 0.04 * derealization));
        resolvedColor = mix(resolvedColor, shiftedColor, clamp(derealization, 0.0, 1.0));
    }

    if (jumpscareBlood > 0.02) {
        vec2 bloodAspectCoordinates = coordinates;
        bloodAspectCoordinates.x *= 1.4;
        float bloodMetaballShape = smoothMetaball(bloodAspectCoordinates, vec2(0.7, 0.5), 0.38 * jumpscareBlood) +
                                   smoothMetaball(bloodAspectCoordinates, vec2(0.55, 0.65), 0.28 * jumpscareBlood);
        float dripEffect = smoothstep(0.7, 0.2, bloodAspectCoordinates.y + sin(bloodAspectCoordinates.x * 25.0) * 0.03) * 0.5 * jumpscareBlood;
        float totalBloodDensity = clamp(bloodMetaballShape + dripEffect, 0.0, 1.0);

        if (totalBloodDensity > 0.05) {
            resolvedColor = mix(resolvedColor, vec3(0.35, 0.01, 0.01) + vec3(0.3, 0.1, 0.1) * pow(totalBloodDensity, 4.0), totalBloodDensity * 0.95);
        }
    }

    if (heavyEyelids > 0.01) {
        float upperEyelid = smoothstep(0.0, 0.5, coordinates.y / (heavyEyelids * 0.75));
        float lowerEyelid = smoothstep(0.0, 0.5, (1.0 - coordinates.y) / (heavyEyelids * 0.75));
        resolvedColor *= clamp(upperEyelid * lowerEyelid, 0.0, 1.0);
    }

    if (whiteBloom > 0.01) {
        resolvedColor = mix(resolvedColor, vec3(1.15, 1.10, 1.02), whiteBloom);
    }

    if (int(gl_FragCoord.y) % 2 == 0) {
        resolvedColor *= 0.95;
    }

    float vignetteDistance = length((coordinates - 0.5) * vec2(1.0, 1.15));
    float vignetteFactor = 1.0 - 0.28 * smoothstep(0.30, 0.85, vignetteDistance);

    float distanceToRadarCorner = length(coordinates - vec2(1.0, 0.0));
    float radarProtectionMask = 1.0 - smoothstep(0.10, 0.88, distanceToRadarCorner);
    vignetteFactor = mix(vignetteFactor, 1.0, radarProtectionMask * 0.90);

    resolvedColor *= clamp(vignetteFactor, 0.0, 1.0);
    FragmentColor = vec4(pow(resolvedColor, vec3(1.0 / 1.05)), 1.0);
}
"""