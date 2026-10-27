-- Thêm các tham số tán xạ / mây / sao của shader Sky.
-- Nguồn giá trị: `threeJS_skySet` trong `apps/frontend/features/tour/tapestry.html`.
--
-- Áp dụng cho DB đã tồn tại:
--   psql "$DATABASE_URL" -f apps/backend/migrations/2026-10-27_sky_preset_scattering.sql
--
-- Idempotent: chạy lại nhiều lần không lỗi. Preset đã có (theo `name`) sẽ được giữ nguyên;
-- muốn ghi đè thì bỏ comment khối `ON CONFLICT ... DO UPDATE` bên dưới.

ALTER TABLE sky_preset
    ADD COLUMN IF NOT EXISTS mie_coefficient DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS mie_directional_g DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cloud_coverage DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS cloud_density DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS stars DOUBLE PRECISION;

INSERT INTO sky_preset (
    name,
    turbidity,
    rayleigh,
    mie_coefficient,
    mie_directional_g,
    elevation,
    azimuth,
    exposure,
    cloud_coverage,
    cloud_density,
    stars,
    light_settings
) VALUES
    (
        'sunrise',
        4,
        3.0,
        0.008,
        0.8,
        1.8,
        -90,
        0.68,
        0.25,
        0.45,
        0,
        '{"dir":{"color":"#FFB16A","position":{"x":-1000,"y":500,"z":0},"intensity":2.21},"fog":{"color":"#584341"},"hemi":{"color":"#FFB98A","intensity":2.21,"groundColor":"#5A3427"}}'::jsonb
    ),
    (
        'sunny-morning',
        10,
        2.4,
        0.005,
        0.8,
        35,
        -90,
        0.35,
        0.25,
        0.45,
        0,
        '{"dir":{"color":"#FFE3B0","position":{"x":-1000,"y":750,"z":0},"intensity":4},"fog":{"color":"#bbc4c6"},"hemi":{"color":"#bfdfff","intensity":6,"groundColor":"#6b5a43"}}'::jsonb
    ),
    (
        'rainy-afternoon',
        20,
        0.6,
        0.02,
        0.6,
        42,
        90,
        0.30,
        0.95,
        0.90,
        0,
        '{"dir":{"color":"#ffd49a","position":{"x":1000,"y":750,"z":0},"intensity":0.6},"fog":{"color":"#eaecec"},"hemi":{"color":"#c9e2ff","intensity":2,"groundColor":"#7a5a3e"}}'::jsonb
    ),
    (
        'sunset',
        8,
        3.5,
        0.005,
        0.75,
        1.2,
        90,
        1.5,
        0.30,
        0.50,
        0,
        '{"dir":{"color":"#ff7a3d","position":{"x":1000,"y":500,"z":0},"intensity":2},"fog":{"color":"#271721"},"hemi":{"color":"#ff9a6b","intensity":0.67,"groundColor":"#4a241f"}}'::jsonb
    ),
    (
        'night',
        5,
        0.1,
        0.001,
        0.8,
        -10,
        0,
        0.10,
        0,
        0,
        0.75,
        '{"dir":{"color":"#527fc7","position":{"x":0,"y":1000,"z":0},"intensity":1.05},"fog":{"color":"#151e27"},"hemi":{"color":"#527fc7","intensity":7.2,"groundColor":"#25416f"}}'::jsonb
    )
ON CONFLICT (name) DO NOTHING;

-- Muốn ghi đè giá trị đã có, thay `ON CONFLICT (name) DO NOTHING` ở trên bằng:
-- ON CONFLICT (name) DO UPDATE SET
--     turbidity = EXCLUDED.turbidity,
--     rayleigh = EXCLUDED.rayleigh,
--     mie_coefficient = EXCLUDED.mie_coefficient,
--     mie_directional_g = EXCLUDED.mie_directional_g,
--     elevation = EXCLUDED.elevation,
--     azimuth = EXCLUDED.azimuth,
--     exposure = EXCLUDED.exposure,
--     cloud_coverage = EXCLUDED.cloud_coverage,
--     cloud_density = EXCLUDED.cloud_density,
--     stars = EXCLUDED.stars,
--     light_settings = EXCLUDED.light_settings;
