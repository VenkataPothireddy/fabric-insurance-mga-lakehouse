CREATE TABLE dim.date (
    date_key            INT             NOT NULL,
    full_date           DATE            NOT NULL,
    day_of_month        INT             NOT NULL,
    day_name            VARCHAR(10)     NOT NULL,
    day_of_week         INT             NOT NULL,
    week_of_year        INT             NOT NULL,
    month_number        INT             NOT NULL,
    month_name          VARCHAR(10)     NOT NULL,
    quarter_number      INT             NOT NULL,
    quarter_name        VARCHAR(2)      NOT NULL,
    year_number         INT             NOT NULL,
    year_month          VARCHAR(7)      NOT NULL,
    is_weekend          BIT             NOT NULL,
    is_month_end        BIT             NOT NULL
);


SELECT name 
FROM sys.tables 
WHERE schema_id = SCHEMA_ID('dim');

SELECT 
    c.name AS column_name,
    t.name AS data_type,
    c.max_length,
    c.is_nullable
FROM sys.columns c
JOIN sys.types t ON c.user_type_id = t.user_type_id
WHERE c.object_id = OBJECT_ID('dim.date')
ORDER BY c.column_id;



WITH 
digits AS (
    SELECT 0 AS n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 
    UNION ALL SELECT 4 UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 
    UNION ALL SELECT 8 UNION ALL SELECT 9
),
numbers AS (
    SELECT (d1.n + d2.n * 10 + d3.n * 100 + d4.n * 1000) AS n
    FROM digits d1
    CROSS JOIN digits d2
    CROSS JOIN digits d3
    CROSS JOIN digits d4
),
date_spine AS (
    SELECT DATEADD(DAY, n, CAST('2020-01-01' AS DATE)) AS d
    FROM numbers
    WHERE n <= DATEDIFF(DAY, '2020-01-01', '2030-12-31')
)
INSERT INTO dim.date (
    date_key,
    full_date,
    day_of_month,
    day_name,
    day_of_week,
    week_of_year,
    month_number,
    month_name,
    quarter_number,
    quarter_name,
    year_number,
    year_month,
    is_weekend,
    is_month_end
)
SELECT
    YEAR(d) * 10000 + MONTH(d) * 100 + DAY(d)        AS date_key,
    d                                                AS full_date,
    DAY(d)                                           AS day_of_month,
    DATENAME(WEEKDAY, d)                             AS day_name,
    DATEPART(WEEKDAY, d)                             AS day_of_week,
    DATEPART(WEEK, d)                                AS week_of_year,
    MONTH(d)                                         AS month_number,
    DATENAME(MONTH, d)                               AS month_name,
    DATEPART(QUARTER, d)                             AS quarter_number,
    CONCAT('Q', DATEPART(QUARTER, d))                AS quarter_name,
    YEAR(d)                                          AS year_number,
    CONCAT(YEAR(d), '-', RIGHT(CONCAT('0', MONTH(d)), 2)) AS year_month,
    CASE 
        WHEN DATEPART(WEEKDAY, d) IN (1, 7) THEN 1 
        ELSE 0 
    END                                              AS is_weekend,
    CASE 
        WHEN d = EOMONTH(d) THEN 1 
        ELSE 0 
    END                                              AS is_month_end
FROM date_spine;







-- Check 1: row count and date range
SELECT 
    COUNT(*) AS total_rows,
    MIN(full_date) AS earliest,
    MAX(full_date) AS latest
FROM dim.date;


-- Check 2: spot-check a known date (today, 2026-06-04, is a Thursday)
SELECT *
FROM dim.date
WHERE full_date = '2026-06-04';


-- Check 3: confirm weekend logic and month-end logic look right
SELECT TOP 10
    full_date, day_name, is_weekend, is_month_end
FROM dim.date
WHERE is_month_end = 1
ORDER BY full_date;

ALTER TABLE dim.date 
ADD CONSTRAINT PK_dim_date PRIMARY KEY NONCLUSTERED (date_key) NOT ENFORCED;