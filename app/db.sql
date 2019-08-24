DROP TYPE IF EXISTS citizen_fields;
DROP TABLE IF EXISTS Relatives CASCADE;
DROP TABLE IF EXISTS Citizens CASCADE;
DROP TABLE IF EXISTS Imports;
DROP SEQUENCE IF EXISTS imports_serial;
DROP TYPE IF EXISTS gender;


CREATE SEQUENCE imports_serial;


CREATE TABLE Imports (
	id   	integer PRIMARY KEY DEFAULT nextval('imports_serial')
	,shard	varchar
);


CREATE TYPE gender AS ENUM ('female', 'male');


CREATE TABLE Citizens (
	import_id	integer NOT NULL
	,citizen_id 	integer NOT NULL
	,town    	varchar	NOT NULL CHECK (town <> '')
	,birth_date	date	NOT NULL
	,gender    	gender	NOT NULL
	,fields    	json	NOT NULL	
	
	,PRIMARY KEY (import_id, citizen_id)
	,FOREIGN KEY (import_id) REFERENCES Imports(id) ON DELETE CASCADE
);


/* 1:1 undirected connections */
CREATE TABLE Relatives (
	import_id	integer NOT NULL
	,low      	integer NOT NULL  /* citizen with lower id */
	,high     	integer NOT NULL  /* citizen with higher id */
	
	,PRIMARY KEY (import_id, low, high)
	,FOREIGN KEY (import_id) REFERENCES Imports(id) ON DELETE CASCADE
/*	,FOREIGN KEY (import_id, low ) REFERENCES Citizens(import_id, citizen_id) ON DELETE CASCADE
	,FOREIGN KEY (import_id, high) REFERENCES Citizens(import_id, citizen_id) ON DELETE CASCADE
*/
);


CREATE TYPE citizen_fields AS (
	street VARCHAR
	, building VARCHAR
	, apartment INT
	, name VARCHAR
);


/* Json fields -> table columns */
CREATE OR REPLACE VIEW Citizens_fields AS
SELECT C.import_id, C.citizen_id, town, to_char(birth_date, 'DD.MM.YYYY') as birth_date, gender, f.* 
from Citizens as C
, JSON_POPULATE_RECORD(NULL::citizen_fields, C.fields) f;


/* Relatives table -> Arrays of relatives */
CREATE OR REPLACE VIEW Relatives_agg AS
SELECT import_id, citizen_id, ARRAY_AGG(rel) as relatives FROM (
	SELECT import_id, low AS citizen_id, high AS rel
	FROM relatives
	UNION
	SELECT import_id, high AS citizen_id, low AS rel
	FROM relatives
	) as sub
GROUP BY sub.import_id, sub.citizen_id;


/* Citizens */
CREATE OR REPLACE VIEW Citizens_view AS
SELECT CF.*, COALESCE(R.relatives, ARRAY[]::integer[]) as relatives
FROM Citizens_fields CF
LEFT JOIN Relatives_agg AS R
ON CF.citizen_id = R.citizen_id
AND CF.import_id = R.import_id;

