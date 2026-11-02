-- Распределение глубин очагов по зонам (доли, %)
SELECT
    z.name AS zone,
    COUNT(*) AS n_events,
    ROUND(100.0 * AVG(e.depth_class = 'мелкофокусное'),   1) AS shallow_pct,
    ROUND(100.0 * AVG(e.depth_class = 'промежуточное'),   1) AS intermediate_pct,
    ROUND(100.0 * AVG(e.depth_class = 'глубокофокусное'), 1) AS deep_pct,
    MAX(e.depth_km) AS max_depth_km
FROM events AS e
JOIN zones  AS z USING (zone_id)
GROUP BY z.zone_id
ORDER BY deep_pct DESC;
