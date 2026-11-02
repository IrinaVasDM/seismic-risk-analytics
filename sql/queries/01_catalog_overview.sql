-- Структура каталога: число событий по десятилетиям и классам магнитуды
-- (условная агрегация вместо PIVOT, которого нет в SQLite)
SELECT
    (year / 10) * 10                                   AS decade,
    COUNT(*)                                           AS total,
    SUM(CASE WHEN mag <  5.0             THEN 1 ELSE 0 END) AS m4_5_4_9,
    SUM(CASE WHEN mag >= 5.0 AND mag < 6 THEN 1 ELSE 0 END) AS m5,
    SUM(CASE WHEN mag >= 6.0 AND mag < 7 THEN 1 ELSE 0 END) AS m6,
    SUM(CASE WHEN mag >= 7.0 AND mag < 8 THEN 1 ELSE 0 END) AS m7,
    SUM(CASE WHEN mag >= 8.0             THEN 1 ELSE 0 END) AS m8_plus,
    ROUND(MAX(mag), 1)                                 AS max_mag
FROM events
GROUP BY decade
ORDER BY decade;
