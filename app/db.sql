
CREATE SEQUENCE imports_serial;

CREATE TABLE Imports (
    id      integer PRIMARY KEY DEFAULT nextval('imports_serial')
    ,shard  varchar
);

CREATE TYPE gender AS ENUM ('female', 'male');


CREATE TABLE Citizens (
    import_id   integer NOT NULL
    ,citizen_id integer NOT NULL
    ,town       varchar NOT NULL CHECK (town <> '')
    ,birth_date date    NOT NULL
    ,gender     gender  NOT NULL
    ,fields     json    NOT NULL    
    
    ,PRIMARY KEY (import_id, citizen_id)
    ,FOREIGN KEY (import_id) REFERENCES Imports(id) ON DELETE CASCADE
);


/* 1:1 undirected connections */
CREATE TABLE Relatives (
    import_id   integer NOT NULL
    ,low        integer NOT NULL  /* citizen with lower id */
    ,high       integer NOT NULL  /* citizen with higher id */
    
    ,PRIMARY KEY (import_id, low, high)
    ,FOREIGN KEY (import_id) REFERENCES Imports(id) ON DELETE CASCADE
    ,FOREIGN KEY (import_id, low ) REFERENCES Citizens(import_id, citizen_id) ON DELETE CASCADE
    ,FOREIGN KEY (import_id, high) REFERENCES Citizens(import_id, citizen_id) ON DELETE CASCADE

);


CREATE TYPE citizen_fields AS (
    street VARCHAR
    , building VARCHAR
    , apartment INT
    , name VARCHAR
);


/* Json fields -> table columns */
CREATE VIEW Citizens_fields AS
SELECT C.import_id, C.citizen_id, town, to_char(birth_date, 'DD.MM.YYYY') as birth_date, gender, f.* 
from Citizens as C
, JSON_POPULATE_RECORD(NULL::citizen_fields, C.fields) f;


/* Relatives in both directions */
CREATE VIEW Relatives_all AS
SELECT import_id, low AS citizen_id, high AS rel
FROM relatives
UNION
SELECT import_id, high AS citizen_id, low AS rel
FROM relatives;


/* Relatives table -> Arrays of relatives */
CREATE VIEW Relatives_agg AS
SELECT import_id, citizen_id, ARRAY_AGG(rel) as relatives
FROM Relatives_all as R
GROUP BY R.import_id, R.citizen_id;


/* Citizens */
CREATE VIEW Citizens_view AS
SELECT CF.*, COALESCE(R.relatives, ARRAY[]::integer[]) as relatives
FROM Citizens_fields CF
LEFT JOIN Relatives_agg AS R
ON CF.citizen_id = R.citizen_id
AND CF.import_id = R.import_id;


/* Birthdays (we exploit Merge Join here) */
CREATE VIEW Birthdays_view AS
SELECT R.import_id, C."month", R.citizen_id, COUNT(*) AS presents
FROM
  (SELECT import_id, citizen_id, rel
   FROM Relatives_all
   ORDER BY rel) AS R,

  (SELECT import_id, citizen_id, date_part('month', birth_date) AS "month"
   FROM Citizens
   ORDER BY citizen_id) AS C
WHERE R.rel = C.citizen_id
  AND C.import_id = R.import_id
GROUP BY R.import_id, "month", R.citizen_id
ORDER BY "month";


/* Date --> age in UTC time zone */
CREATE FUNCTION utc_age(param_date DATE)
    RETURNS int 
AS $$ SELECT EXTRACT('YEAR' FROM age(NOW() at time zone 'UTC', param_date))::int $$
LANGUAGE SQL;


/* Number of citizens with certan age (per town)*/
CREATE VIEW Towns_age_view AS
SELECT import_id, town, utc_age(birth_date) as "age",
       count(*) as "count"
FROM Citizens
GROUP BY import_id, town, age 
ORDER BY town, age;
