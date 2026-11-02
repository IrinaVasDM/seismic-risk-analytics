-- Три сильнейших землетрясения каждой зоны (ROW_NUMBER по разделам)
WITH ranked AS (
    SELECT
        z.name AS zone,
        e.time_utc,
        e.mag,
        e.depth_km,
        e.place,
        ROW_NUMBER() OVER (PARTITION BY e.zone_id ORDER BY e.mag DESC, e.time_utc) AS rn
    FROM events AS e
    JOIN zones  AS z USING (zone_id)
    WHERE e.zone_id <> 99
)
SELECT zone, rn, SUBSTR(time_utc, 1, 10) AS date, mag, depth_km, place
FROM ranked
WHERE rn <= 3
ORDER BY zone, rn;
