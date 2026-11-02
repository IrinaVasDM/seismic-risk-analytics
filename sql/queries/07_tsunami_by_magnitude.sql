-- Какая доля сильных неглубоких землетрясений вызывает цунами?
-- Каталог USGS (M≥6.5) связан с NOAA через significant.usgs_event_id;
-- разбивка по магнитуде (шаг 0.5) и классу глубины очага
WITH eq AS (
    SELECT
        e.event_id,
        CAST(e.mag * 2 AS INTEGER) / 2.0      AS mag_bin,      -- шаг 0.5
        e.depth_class,
        s.tsunami_id
    FROM events AS e
    LEFT JOIN significant AS s ON s.usgs_event_id = e.event_id
    WHERE e.mag >= 6.5
)
SELECT
    mag_bin,
    depth_class,
    COUNT(*)                                        AS n_events,
    SUM(tsunami_id IS NOT NULL)                     AS n_tsunami,
    ROUND(100.0 * SUM(tsunami_id IS NOT NULL) / COUNT(*), 1) AS tsunami_pct
FROM eq
GROUP BY mag_bin, depth_class
ORDER BY depth_class, mag_bin;
