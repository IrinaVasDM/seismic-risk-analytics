-- Самые смертоносные землетрясения XX–XXI вв. и высота вызванных ими цунами
SELECT
    s.year,
    s.country,
    s.location,
    s.mag,
    s.depth_km,
    s.deaths,
    t.max_water_height_m                        AS tsunami_height_m,
    RANK() OVER (ORDER BY s.deaths DESC)        AS rank_deaths
FROM significant AS s
LEFT JOIN tsunamis AS t ON t.tsunami_id = s.tsunami_id
WHERE s.deaths IS NOT NULL
ORDER BY s.deaths DESC
LIMIT :top_n;
