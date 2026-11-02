-- Активность сейсмических зон: годовая частота сильных событий и ранги
WITH span AS (
    SELECT MAX(year) - MIN(year) + 1 AS years FROM events
),
per_zone AS (
    SELECT
        z.zone_id,
        z.name                                         AS zone,
        z.boundary_type,
        COUNT(*)                                       AS n_events,
        SUM(e.mag >= 6.0)                              AS n_m6,
        SUM(e.mag >= 7.0)                              AS n_m7,
        MAX(e.mag)                                     AS max_mag,
        ROUND(AVG(e.depth_km), 1)                      AS mean_depth_km,
        ROUND(100.0 * SUM(e.depth_class = 'глубокофокусное') / COUNT(*), 1) AS deep_share_pct
    FROM events AS e
    JOIN zones  AS z USING (zone_id)
    GROUP BY z.zone_id
)
SELECT
    p.*,
    ROUND(1.0 * p.n_m7 / s.years, 3)                   AS m7_per_year,
    RANK() OVER (ORDER BY p.n_m7 DESC)                 AS rank_m7,
    ROUND(100.0 * p.n_events / SUM(p.n_events) OVER (), 1) AS share_of_catalog_pct
FROM per_zone AS p
CROSS JOIN span AS s
ORDER BY rank_m7;
