draw = function () {
 imagesQ.queue_images(imagesToLoad);
 imagesQ.process_queue();
 $.getJSON('/z12.json',function(data) {

  var start = new Date().getTime();
  var ctxa = document.getElementById('canvas');
  ctxa.width = ctxa.width;
  ctxa.height = ctxa.height;
  var ctx = ctxa.getContext('2d');
  var ws = ctxa.width/data.granularity;
  var hs = ctxa.height/data.granularity;
  var zoom = 12;
  var style = restyle({}, zoom, "canvas")["default"];
  if ("fill-color" in style){ctx.fillStyle = style["fill-color"];};
  if ("opacity" in style){ctx.globalAlpha = style["opacity"];};
  if ("fill-opacity" in style){ctx.globalAlpha = style["fill-opacity"];};
  var style = restyle({"natural":"coastline"}, zoom, "Polygon")["default"];
  if ("fill-color" in style){ctx.fillStyle = style["fill-color"];};
  if ("opacity" in style){ctx.globalAlpha = style["opacity"];};
  if ("fill-opacity" in style){ctx.globalAlpha = style["fill-opacity"]};

  ctx.fillRect (-1, -1, ctxa.width+1, ctxa.height+1);

  ctx.strokeStyle = "rgba(0,0,0,0.5)";
  ctx.fillStyle = "rgba(0,0,0,0.5)";
  ctx.lineWidth = 1;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  var styledfeatures = new Array();

  
  $.each(data.features, function(key, val) {
    if (!("layer" in val.properties )){val.properties.layer=0};
    $.each(restyle(val.properties, zoom, val.type), function(k,v){
      var newObject = jQuery.extend({}, val);
      newObject.style = v;
      if ("z-index" in newObject.style) {newObject.style["z-index"] = parseFloat(newObject.style["z-index"]);}
      else {newObject.style["z-index"] = 0;}
      styledfeatures.push(newObject);
    });
  });
  
  data.features = styledfeatures
  data.features.sort(function (a,b){
    //if ("layer" in a.properties && "layer" in b.properties && a.properties.layer!=b.properties.layer){return a.properties.layer-b.properties.layer};
    return a.style["z-index"]-b.style["z-index"];
    });
  var zlayers = new Object();
  var layerlist = new Array();
  $.each(data.features, function(key, val) {
    val.properties.layer=parseFloat(val.properties.layer);
    if (isNaN(val.properties.layer)){val.properties.layer=0;};
    if (val.style["-x-mapnik-layer"]=="top" ){val.properties.layer=10000};
    if (val.style["-x-mapnik-layer"]=="bottom" ){val.properties.layer=-10000};
    if (!(val.properties.layer in zlayers)) {
      zlayers[val.properties.layer] = new Array();
      layerlist.push(val.properties.layer);
    };
    zlayers[val.properties.layer].push(val);
  });
  layerlist.sort();
  $.each(layerlist, function(key, sublay){ // polygons pass
   var dat = zlayers[sublay];
   $.each(dat, function(key, val) {
    ctx.save()
    style = val.style;
    if ("fill-color" in style) {
      ctx.fillStyle = style["fill-color"];
      if ("opacity" in style){ctx.globalAlpha = style["opacity"]};
      if ("fill-opacity" in style){ctx.globalAlpha = style["fill-opacity"]};
      pathGeoJSON(ctx, val, ws, hs, data.granularity, "aaa", true);
      ctx.fill();
     };
   ctx.restore();
  });
  ctx.lineCap = "butt";

  $.each(dat, function(key, val) { // casings pass
    
    ctx.save()
    style = val.style;
    if ("casing-width" in style) {
      var width = 2*style["casing-width"];
      var dashes = "aaa";
      if ("width" in style){width += style["width"]};
      ctx.lineWidth = width;
      if ("color" in style){ctx.strokeStyle = style["color"]};
      if ("linecap" in style){ctx.lineCap = style["linecap"]};
      if ("linejoin" in style){ctx.lineJoin = style["linejoin"]};
      if ("dashes" in style){dashes = style["dashes"].split(",")};
      if ("opacity" in style){ctx.globalAlpha = style["opacity"]};
      if ("casing-color" in style){ctx.strokeStyle = style["casing-color"]};
      if ("casing-linecap" in style){ctx.lineCap = style["casing-linecap"]};
      if ("casing-linejoin" in style){ctx.lineJoin = style["casing-linejoin"]};
      if ("casing-dashes" in style){dashes = style["casing-dashes"].split(",")};
      if ("casing-opacity" in style){ctx.globalAlpha = style["casing-opacity"]};
      pathGeoJSON(ctx, val, ws, hs, data.granularity, dashes);
      ctx.stroke();
    };
    ctx.restore();
  });
  ctx.lineCap = "round";
  $.each(dat, function(key, val) { // lines pass
    ctx.save()
    style = val.style;
    if ("width" in style) {
      var dashes = "aaa";
      if ("color" in style){ctx.strokeStyle = style["color"]};
      if ("linecap" in style){ctx.lineCap = style["linecap"]};
      if ("linejoin" in style){ctx.lineJoin = style["linejoin"]};
      if ("dashes" in style){dashes = style["dashes"].split(",")};
      if ("opacity" in style){ctx.globalAlpha = style["opacity"]};
      ctx.lineWidth = style["width"];
      pathGeoJSON(ctx, val, ws, hs, data.granularity, dashes);
      ctx.stroke();
    };
    ctx.restore();
  });
  });
  var collides = new collisionBuffer();
  layerlist.reverse();
  $.each(layerlist, function(key, sublay){ 
    var dat = zlayers[sublay];
    dat.reverse();
    $.each(dat, function(key, val) { // icons pass
     ctx.save()
     style = val.style;
     if ("icon-image" in style) {
      var img = new Image();
      img.src = 'icons/'+style["icon-image"];
      var offset = 0;
      var opacity = 1;
      var mindistance = 0;
      var textwidth = 0;
      if ("text-offset" in style){offset = style["text-offset"]};
      if ("text-color" in style){ctx.fillStyle = style["text-color"];};
      if ("text-halo-radius" in style){ctx.lineWidth = style["text-halo-radius"]+2};
      if ("text-halo-color" in style){ctx.strokeStyle = style["text-halo-color"]};
      if ("opacity" in style){opacity = style["opacity"]};
      if ("text-opacity" in style){opacity = style["text-opacity"]};
      if ("-x-mapnik-min-distance" in style){mindistance = style["-x-mapnik-min-distance"]};
      
      var point;
      if (val.type == "Point"){ point = [ws*val.coordinates[0],hs*(data.granularity-val.coordinates[1])]};
      if (val.type == "Polygon"){ point = [ws*val.reprpoint[0],hs*(data.granularity-val.reprpoint[1])]};
      //alert(collides.checkPointWH(point, img.width, img.height));
      if (style["text"]){ctx.font = fontString(style["font-family"],style["font-size"]);};
      if (collides.checkPointWH(point, img.width, img.height)){return;}
      if (style["text"]){
        textwidth = ctx.measureText(style["text"]).width;
        if (!(style["text-allow-overlap"]=="true")&&collides.checkPointWH([point[0],point[1]+offset], textwidth, 10)){return;}
      }
      if (opacity <1){
        ctx.fillStyle = new RGBColor(ctx.fillStyle, opacity).toRGBA();
        ctx.strokeStyle = new RGBColor(ctx.strokeStyle, opacity).toRGBA();
      }
      
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      if(style["text"]){
        if ("text-halo-radius" in style)
          ctx.strokeText(style["text"], point[0],point[1]+offset);
        ctx.fillText(style["text"], point[0],point[1]+offset);
      }
      ctx.drawImage(img, point[0]-img.width/2,point[1]-img.height/2);
      collides.addPointWH(point, img.width, img.height,mindistance);
      collides.addPointWH([point[0],point[1]+offset], textwidth, 10, mindistance);
     };
     ctx.restore();
    });
    $.each(dat, function(key, val) { // text pass
     ctx.save()
     style = val.style;
     if ("text" in style && !("icon-image" in style)) {
      var offset = 0;
      var opacity = 1;
      var mindistance = 0;
      if ("text-offset" in style){offset = style["text-offset"]};
      if ("text-color" in style){ctx.fillStyle = style["text-color"];};
      if ("text-halo-radius" in style){ctx.lineWidth = style["text-halo-radius"]+2};
      if ("text-halo-color" in style){ctx.strokeStyle = style["text-halo-color"]};
      if ("opacity" in style){opacity = style["opacity"]};
      if ("text-opacity" in style){opacity = style["text-opacity"]};
      if ("-x-mapnik-min-distance" in style){mindistance = style["-x-mapnik-min-distance"]};

      var point;
      if (val.type == "Point"){ point = [ws*val.coordinates[0],hs*(data.granularity-val.coordinates[1])]};
      if (val.type == "Polygon"){ point = [ws*val.reprpoint[0],hs*(data.granularity-val.reprpoint[1])]};
      if (val.type == "LineString"){return; point = [ws*val.coordinates[0][0],hs*(data.granularity-val.coordinates[0][1])]};
      if (style["text"]){ctx.font = fontString(style["font-family"],style["font-size"]);};
      textwidth = ctx.measureText(style["text"]).width;
      if (!(style["text-allow-overlap"]=="true")&&collides.checkPointWH([point[0],point[1]+offset], textwidth, 5)) return;
      
      if (opacity <1){
        ctx.fillStyle = new RGBColor(ctx.fillStyle, opacity).toRGBA();
        ctx.strokeStyle = new RGBColor(ctx.strokeStyle, opacity).toRGBA();
      }
      
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      if ("text-halo-radius" in style)
        ctx.strokeText(style["text"], point[0],point[1]+offset);
      ctx.fillText(style["text"], point[0],point[1]+offset);
      
      collides.addPointWH([point[0],point[1]+offset], textwidth, 10, mindistance);
     };
     ctx.restore();
    });
    /*for (poly in collides.buffer){
      poly = collides.buffer[poly];
      ctx.fillRect(poly[0],poly[1],poly[2]-poly[0],poly[3]-poly[1])
    }*/
  });
  var elapsed = new Date().getTime()-start;
  alert(elapsed);
 });
};
fontString = function(name, size){
  
  var weight = "400";
  var family = "sans";
  var italic = "";
  if (!size) size = 9;
  if (!name) name = "sans";
  name = name.toLowerCase();
  if (name.indexOf("italic")>=0) italic = "italic";
  if (name.indexOf("oblique")>=0) italic = "italic";
  //alert(name);
  if (name.indexOf("serif")>=0) family = "sans-serif";
  if (name.indexOf("dejavu sans")>=0) family = '"DejaVu Sans", Arial, sans';
  if (name.indexOf("dejavu sans book")>=0) family = '"DejaVu Sans Book", "DejaVu Sans", Arial, sans';
  //if (name.indexOf("dejavu sans oblique")>=0) family = '"Deja Vu Sans Oblique", sans-serif';
  if (name.indexOf("dejavu sans extralight")>=0) family = '"DejaVu Sans ExtraLight", "DejaVu Sans", Arial, sans';
  if (name.indexOf("dejavu serif")>=0) family = '"DejaVu Serif", "Times New Roman", sans-serif';
  if (name.indexOf("dejavu sans mono")>=0) family = '"DejaVu Sans Mono", Terminal, monospace';
  if (name.indexOf("dejavu sans mono book")>=0) family = '"DejaVu Sans Mono Book", "DejaVu Sans Mono", Terminal, monospace';
  font =  weight + " " + italic + " " + size +"px " + family;
  //alert(font);
  return font;
  
}


function collisionBuffer(){
  this.buffer = new Array();
  this.addBox = function(box){
    this.buffer.push(box);
  }
  this.addPointWH = function(point, w, h, d){
    if (!d)d=0;
    this.buffer.push([point[0]-w/2-d, point[1]-h/2-d, point[0]+w/2-d, point[1]+w/2-d]);
  }
  this.checkBox = function(b){
    for (i in this.buffer){
      c = this.buffer[i];
      //alert([b,c])
      if ((c[0]<=b[2] && c[1]<=b[3] && c[2]>=b[0] && c[3]>=b[1])){return true;};
    }
    return false;
  }
  this.checkPointWH = function(point, w, h){
    return this.checkBox([point[0]-w/2, point[1]-h/2, point[0]+w/2, point[1]+w/2]);
  }
}