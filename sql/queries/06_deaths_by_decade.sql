-- Гибель людей при землетрясениях по десятилетиям, с накопленным итогом
-- и долей самого смертоносного события десятилетия
WITH by_decade AS (
    SELECT
        (year / 10) * 10                    AS decade,
        COUNT(*)                            AS n_significant,
        SUM(COALESCE(deaths, 0))            AS deaths,
        MAX(COALESCE(deaths, 0))            AS worst_event_deaths
    FROM significant
    GROUP BY decade
)
SELECT
    decade,
    n_significant,
    deaths,
    ROUND(100.0 * worst_event_deaths / NULLIF(deaths, 0), 1) AS worst_event_share_pct,
    SUM(deaths) OVER (ORDER BY decade)                       AS deaths_cumulative
FROM by_decade
ORDER BY decade;
