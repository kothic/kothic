#! /bin/bash

rm -f $1 
cat osm.sql | grep -vi "CREATE INDEX" | sqlite3 $1
cat spatial.sql | sqlite3 $1
echo "Importing $2 into $1"
./import_osm.pl $1 < $2
echo "Creating indexes"
cat osm.sql | grep -i "CREATE INDEX" | sqlite3 $1 
echo 'Analyzing' 
sqlite3 $1 'analyze' 
echo 'Creating spatial index'
sqlite3 $1 'insert into way_index (id,minLat,maxLat,minLon,maxLon) select way_id,min(lat),max(lat),min(lon),max(lon) from way_node,node where way_node.node_id=node.id group by way_id'
echo 'Creating way coords'
sqlite3 $1 'insert into way_coord_text (id,lat,lon) select way_id,group_concat(lat),group_concat(lon) from (select way_id,lat,lon from way_node,node where node_id=id order by way_id,node_number) group by way_id'
