-- Годовое число событий M≥6 со скользящим 5-летним средним и изменением к прошлому году
WITH yearly AS (
    SELECT year, COUNT(*) AS n_m6, SUM(mag >= 7.0) AS n_m7
    FROM events
    WHERE mag >= 6.0
    GROUP BY year
)
SELECT
    year,
    n_m6,
    n_m7,
    ROUND(AVG(n_m6) OVER (ORDER BY year ROWS BETWEEN 4 PRECEDING AND CURRENT ROW), 1) AS n_m6_rolling5,
    n_m6 - LAG(n_m6) OVER (ORDER BY year)                                           AS delta_vs_prev,
    SUM(n_m7) OVER (ORDER BY year)                                                   AS m7_cumulative
FROM yearly
ORDER BY year;
