-- Интервалы (в сутках) между последовательными землетрясениями M ≥ :min_mag
SELECT
    event_id,
    time_utc,
    mag,
    zone_id,
    julianday(time_utc) - LAG(julianday(time_utc)) OVER (ORDER BY time_utc) AS days_since_prev
FROM events
WHERE mag >= :min_mag
ORDER BY time_utc;
