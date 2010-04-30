CREATE VIRTUAL TABLE way_index USING rtree(
		id,                  -- Integer primary key
		minLat, maxLat,      -- Minimum and maximum X coordinate
		minLon, maxLon       -- Minimum and maximum Y coordinate
		);

CREATE TABLE way_coord(
	        id INTEGER PRIMARY KEY,
		coord BLOB
);

CREATE TABLE way_coord_text(
		id INTEGER PRIMARY KEY,
		lat TEXT,
		lon TEXT
);
