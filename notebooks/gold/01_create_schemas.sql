CREATE SCHEMA dim;
GO

CREATE SCHEMA fact;
GO


SELECT name 
FROM sys.schemas 
WHERE name IN ('dim', 'fact');
