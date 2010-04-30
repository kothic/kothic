create table node (
	id INTEGER PRIMARY KEY,
	lat FLOAT,
	lon FLOAT
);

create table way(
	id INTEGER PRIMARY KEY
);

create table way_node (
	node_number INTEGER,
	way_id INTEGER,
	node_id INTEGER,
	FOREIGN KEY(way_id) REFERENCES way(id),
	FOREIGN KEY(node_id) REFERENCES node(id) 
);

CREATE INDEX way_node_way_id_idx on way_node (way_id);
CREATE INDEX way_node_node_id_idx on way_node (node_id);

create table way_tag(
	id INTEGER,
	key VARCHAR(20),
	value VARCHAR(20),
	FOREIGN KEY(id) REFERENCES way(id)
);

CREATE INDEX way_tag_id_idx on way_tag (id);
CREATE INDEX way_tag_key_idx on way_tag (key);
CREATE INDEX way_tag_value_idx on way_tag (value);
CREATE INDEX way_tag_key_value_idx on way_tag (key,value);

create table node_tag(
	id INTEGER,
	key VARCHAR(20),
	value VARCHAR(20),
	FOREIGN KEY(id) REFERENCES node(id)
);

CREATE INDEX node_tag_id_idx on node_tag (id);
CREATE INDEX node_tag_key_idx on node_tag (key);
CREATE INDEX node_tag_value_idx on node_tag (value);
CREATE INDEX node_tag_key_value_idx on node_tag (key,value);

create table relation(
	id INTEGER PRIMARY KEY
);

create table relation_tag(
	id INTEGER,
	key VARCHAR(20),
	value VARCHAR(20),
	FOREIGN KEY(id) REFERENCES relation(id)
);

CREATE INDEX relation_tag_id_idx on relation_tag (id);
CREATE INDEX relation_tag_key_idx on relation_tag (key);
CREATE INDEX relation_tag_value_idx on relation_tag (value);
CREATE INDEX relation_tag_key_value_idx on relation_tag (key,value);

create table relation_member_node(
	id INTEGER,
	node_id INTEGER,
	sequence_number INTEGER NOT NULL,
	role VARCHAR(20) NOT NULL,
	FOREIGN KEY(id) REFERENCES relation(id)
	FOREIGN KEY(node_id) REFERENCES node(id)
);

CREATE INDEX relation_member_node_id_idx on relation_member_node (id);
CREATE INDEX relation_member_node_node_id_idx on relation_member_node (node_id);
CREATE INDEX relation_member_node_role_idx on relation_member_node (role);

create table relation_member_way(
	id INTEGER,
	way_id INTEGER,
	sequence_number INTEGER NOT NULL,
	role VARCHAR(20) NOT NULL,
	FOREIGN KEY(id) REFERENCES relation(id)
	FOREIGN KEY(way_id) REFERENCES way(id)
);

CREATE INDEX relation_member_way_id_idx on relation_member_way (id);
CREATE INDEX relation_member_way_way_id_idx on relation_member_way (way_id);
CREATE INDEX relation_member_way_role_idx on relation_member_way (role);

create table relation_member_relation(
	id INTEGER,
	relation_id INTEGER,
	sequence_number INTEGER NOT NULL,
	role VARCHAR(20) NOT NULL,
	FOREIGN KEY(id) REFERENCES relation(id)
	FOREIGN KEY(relation_id) REFERENCES relation(id)
);

CREATE INDEX relation_member_relation_id_idx on relation_member_relation (id);
CREATE INDEX relation_member_relation_relation_id_idx on relation_member_relation (relation_id);
CREATE INDEX relation_member_relation_role_idx on relation_member_relation (role);

-- CREATE VIEW pt_route AS SELECT id,value AS type FROM relation_tag WHERE key = 'route' AND value IN ('bus', 'trolleybus', 'tram');
create view pt_route as select id,value as type from relation_tag where key = 'route' and value in ('bus', 'trolleybus', 'tram') and id in (select id from relation_tag where key = 'type' and value = 'route');
-- create view pt_route_ref as select pt_route.id as id, pt_route.type as type,value as ref from pt_route,relation_tag where pt_route.id = relation_tag.id and key='ref';
create view pt_route_ref as select pt_route.id as id, pt_route.type as type,value as ref from pt_route,relation_tag where relation_tag.id in (select id from pt_route) and pt_route.id = relation_tag.id and key='ref';
-- create view pt_way as select distinct way_id as id,type,ref from relation_member_way,pt_route_ref where relation_member_way.id = pt_route_ref.id;
create view pt_way_ref as select distinct way_id as id,type,ref from pt_route_ref,relation_member_way where relation_member_way.id = pt_route_ref.id;
create view pt_way_id as select distinct way_id as id from pt_route_ref,relation_member_way where relation_member_way.id = pt_route_ref.id;
--create view pt_way_node as select way_id,node_id from way_node where way_id in (select id from pt_way_id);
create view pt_way_node as select way_id,node_id,node_number from way_node where way_id in (select id from pt_way_id);
create view pt_stop as select distinct id,node_id from relation_member_node where id in (select id from pt_route) and role in ('forward:stop','backward:stop','stop');
create view pt_stop_ref as select distinct node_id as id,type,ref from pt_route_ref,relation_member_node where relation_member_node.id = pt_route_ref.id;
