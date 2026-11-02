-- Последствия землетрясений M≥7 (1973–2025) по зонам: LEFT JOIN каталога с NOAA
SELECT
    z.name                                                AS zone,
    COUNT(*)                                              AS n_m7,
    SUM(s.noaa_id IS NOT NULL)                            AS n_in_noaa,
    SUM(COALESCE(s.deaths, 0) > 0)                        AS n_fatal,
    ROUND(100.0 * SUM(COALESCE(s.deaths, 0) > 0) / COUNT(*), 1) AS fatal_pct,
    SUM(COALESCE(s.deaths, 0))                            AS deaths,
    SUM(s.tsunami_id IS NOT NULL)                         AS n_tsunami
FROM events AS e
JOIN zones  AS z USING (zone_id)
LEFT JOIN significant AS s ON s.usgs_event_id = e.event_id
WHERE e.mag >= 7.0
GROUP BY z.zone_id
ORDER BY deaths DESC;
