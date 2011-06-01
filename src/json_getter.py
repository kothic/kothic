# -*- coding: utf-8 -*-
from twms import projections
from libkomapnik import pixel_size_at_zoom
import json
import psycopg2
from mapcss import MapCSS
import cgi
import os
import sys
reload(sys)
sys.setdefaultencoding("utf-8")          # a hack to support UTF-8 

try:
  import psyco
  psyco.full()
except ImportError:
  pass
  #print >>sys.stderr, "Psyco import failed. Program may run slower. If you run it on i386 machine, please install Psyco to get best performance."

def get_vectors(bbox, zoom, style, vec = "polygon"):
  bbox_p = projections.from4326(bbox, "EPSG:3857")
  geomcolumn = "way"
  
  database = "dbname=gis user=gis"
  pxtolerance = 1.5
  intscalefactor = 10000
  ignore_columns = set(["way_area", "osm_id", geomcolumn, "tags", "z_order"])
  table = {"polygon":"planet_osm_polygon", "line":"planet_osm_line","point":"planet_osm_point", "coastline": "coastlines"}
  
  a = psycopg2.connect(database)
  b = a.cursor()
  if vec != "coastline":
    b.execute("SELECT * FROM %s LIMIT 1;" % table[vec])
    names = [q[0] for q in b.description]
    for i in ignore_columns:
      if i in names:
        names.remove(i)
    names = ",".join(['"'+i+'"' for i in names])


    taghint = "*"
    types = {"line":"line","polygon":"area", "point":"node"}
    adp = ""
    if "get_sql_hints" in dir(style):
      sql_hint = style.get_sql_hints(types[vec], zoom)
      adp = []
      for tp in sql_hint:
        add = []
        for j in tp[0]:
          if j not in names:
            break
        else:
          add.append(tp[1])
        if add:
          add = " OR ".join(add)
          add = "("+add+")"
          adp.append(add)
      adp = " OR ".join(adp)
      if adp:
        adp = adp.replace("&lt;", "<")
        adp = adp.replace("&gt;", ">")


  if vec == "polygon":
    query = """select ST_AsGeoJSON(ST_TransScale(ST_ForceRHR(ST_Intersection(way,SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913))),%s,%s,%s,%s),0) as %s,
                      ST_AsGeoJSON(ST_TransScale(ST_ForceRHR(ST_PointOnSurface(way)),%s,%s,%s,%s),0) as reprpoint, %s from
              (select (ST_Dump(ST_Multi(ST_SimplifyPreserveTopology(ST_Buffer(way,-%s),%s)))).geom as %s, %s from
                (select ST_Union(way) as %s, %s from
                  (select ST_Buffer(way, %s) as %s, %s from
                     %s
                     where (%s)
                       and way && SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913)
                       and way_area > %s
                  ) p
                 group by %s
                ) p
                where ST_Area(way) > %s
                order by ST_Area(way)
              ) p
      """%(bbox_p[0],bbox_p[1],bbox_p[2],bbox_p[3],
          -bbox_p[0],-bbox_p[1],intscalefactor/(bbox_p[2]-bbox_p[0]),intscalefactor/(bbox_p[3]-bbox_p[1]),
          geomcolumn,
          -bbox_p[0],-bbox_p[1],intscalefactor/(bbox_p[2]-bbox_p[0]),intscalefactor/(bbox_p[3]-bbox_p[1]),
          names,
          pixel_size_at_zoom(zoom, pxtolerance),pixel_size_at_zoom(zoom, pxtolerance),
          geomcolumn, names,
          geomcolumn, names,
          pixel_size_at_zoom(zoom, pxtolerance),
          geomcolumn, names,
          table[vec],
          adp,
          bbox_p[0],bbox_p[1],bbox_p[2],bbox_p[3],
          (pixel_size_at_zoom(zoom, pxtolerance)**2)/pxtolerance,
          names,
          pixel_size_at_zoom(zoom, pxtolerance)**2
          )
  elif vec == "line":
    query = """select ST_AsGeoJSON(ST_TransScale(ST_Intersection(way,SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913)),%s,%s,%s,%s),0) as %s, %s from
              (select (ST_Dump(ST_Multi(ST_SimplifyPreserveTopology(ST_LineMerge(way),%s)))).geom as %s, %s from
                (select ST_Union(way) as %s, %s from
                     %s
                     where (%s)
                       and way && SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913)
                      
                 group by %s
                ) p
                
              ) p
      """%(bbox_p[0],bbox_p[1],bbox_p[2],bbox_p[3],
          -bbox_p[0],-bbox_p[1],intscalefactor/(bbox_p[2]-bbox_p[0]),intscalefactor/(bbox_p[3]-bbox_p[1]),
          geomcolumn, names,
          pixel_size_at_zoom(zoom, pxtolerance),
          geomcolumn, names,
          geomcolumn, names,
          table[vec],
          adp,
          bbox_p[0],bbox_p[1],bbox_p[2],bbox_p[3],
          
          names,
          
          )
  elif vec == "point":
    query = """select ST_AsGeoJSON(ST_TransScale(way,%s,%s,%s,%s),0) as %s, %s
                from planet_osm_point where
                (%s)
                and way && SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913)
               limit 10000
             """%(
             -bbox_p[0],-bbox_p[1],intscalefactor/(bbox_p[2]-bbox_p[0]),intscalefactor/(bbox_p[3]-bbox_p[1]),
             geomcolumn, names,
             adp,
             bbox_p[0],bbox_p[1],bbox_p[2],bbox_p[3],

             )
  elif vec == "coastline":
    query = """select ST_AsGeoJSON(ST_TransScale(ST_ForceRHR(ST_Intersection(way,SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913))),%s,%s,%s,%s),0) as %s, 'coastline' as "natural" from
              (select (ST_Dump(ST_Multi(ST_SimplifyPreserveTopology(ST_Buffer(way,-%s),%s)))).geom as %s from
                (select ST_Union(way) as %s from
                  (select ST_Buffer(SetSRID(the_geom,900913), %s) as %s from
                     %s
                     where 
                        SetSRID(the_geom,900913) && SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913)
                  ) p
                ) p
                where ST_Area(way) > %s
              ) p
      """%(bbox_p[0],bbox_p[1],bbox_p[2],bbox_p[3],
          -bbox_p[0],-bbox_p[1],intscalefactor/(bbox_p[2]-bbox_p[0]),intscalefactor/(bbox_p[3]-bbox_p[1]),
          geomcolumn,
          pixel_size_at_zoom(zoom, pxtolerance),pixel_size_at_zoom(zoom, pxtolerance),
          geomcolumn,
          geomcolumn,
          pixel_size_at_zoom(zoom, pxtolerance),
          geomcolumn,
          table[vec],
          bbox_p[0],bbox_p[1],bbox_p[2],bbox_p[3],
          pixel_size_at_zoom(zoom, pxtolerance)**2
          )
  #print query
  a = psycopg2.connect(database)
  b = a.cursor()
  b.execute(query)
  names = [q[0] for q in b.description]

  ROWS_FETCHED = 0
  polygons = []

  for row in b.fetchall():
    ROWS_FETCHED += 1
    geom = dict(map(None,names,row))
    for t in geom.keys():
      if not geom[t]:
        del geom[t]
    geojson = json.loads(geom[geomcolumn])
    del geom[geomcolumn]
    if geojson["type"] == "GeometryCollection":
      continue
    if "reprpoint" in geom:
      geojson["reprpoint"] = json.loads(geom["reprpoint"])["coordinates"]
      del geom["reprpoint"]
    prop = {}
    for k,v in geom.iteritems():
      prop[k] = v
      try:
        if int(v) == float(v):
          prop[k] = int(v)
        else:
          prop[k] = float(v)
        if str(prop[k]) != v:  # leading zeros etc.. should be saved
          prop[k] = v
      except:
        pass
    geojson["properties"] = prop
    polygons.append(geojson)
  return {"bbox": bbox, "granularity":intscalefactor, "features":polygons}




print "Content-Type: text/html"
print

form = cgi.FieldStorage()
if "z" not in form:
  print "need z"
  exit()
if "x" not in form:
  print "need x"
  exit()
if "y" not in form:
  print "need y"
  exit()
z = int(form["z"].value)
x = int(form["x"].value)
y = int(form["y"].value)
if z>22:
  exit()
callback = "onKothicDataResponse"

bbox = projections.bbox_by_tile(z+1,x,y,"EPSG:3857")

style = MapCSS(0,30)
style.parse(open("styles/osmosnimki-maps.mapcss","r").read())
zoom = z+2
aaaa = get_vectors(bbox,zoom,style,"coastline")
aaaa["features"].extend(get_vectors(bbox,zoom,style,"polygon")["features"])
aaaa["features"].extend(get_vectors(bbox,zoom,style,"line")["features"])
aaaa["features"].extend(get_vectors(bbox,zoom,style,"point")["features"])

aaaa = callback+"("+json.dumps(aaaa,True,False,separators=(',', ':'))+",%s,%s,%s);"%(z,x,y)
print aaaa

dir = "/var/www/vtile/%s/%s/"%(z,x)
file = "%s.js"%y

try:
  if not os.path.exists(dir):
    os.makedirs(dir)
except:
  pass

file = open(dir+file,"w")
file.write(aaaa)
file.flush()
file.close()

