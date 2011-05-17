function pathGeoJSON(ctx, val, ws, hs, gran, dashes, fill){
  ctx.beginPath();
  //alert(val.type);
  if (val.type == "Polygon"){
    var firstpoint = val.coordinates[0][0]
    for (coordseq in val.coordinates) {
      coordseq = val.coordinates[coordseq];
      ctx.moveTo(ws*coordseq[0][0], hs*(gran-coordseq[0][1]));
      var prevcoord = coordseq[0];
      if (fill){
        for (coord in coordseq) {
          coord = coordseq[coord];
          ctx.lineTo(ws*coord[0], hs*(gran-coord[1]));
        };
      }
      else {
        for (coord in coordseq) {
          coord = coordseq[coord];
          if ((prevcoord[0]==coord[0]&&(coord[0]==0||coord[0]==gran)) ||(prevcoord[1]==coord[1]&&(coord[1]==0||coord[1]==gran))) //hide boundaries
            {ctx.moveTo(ws*coord[0], hs*(gran-coord[1]));}
          else
            {ctx.lineTo(ws*coord[0], hs*(gran-coord[1]));};
        };
      };
      ctx.moveTo(ws*firstpoint[0], hs*(gran-firstpoint[1]));
    };
  }
  if (val.type == "LineString"){
      if (dashes!="aaa"){ctx.dashTo(ws*val.coordinates[0][0], hs*(gran-val.coordinates[0][1]),dashes);};
      for (coord in val.coordinates) {
        coord = val.coordinates[coord];
        if (dashes=="aaa")     {ctx.lineTo(ws*coord[0], hs*(gran-coord[1]));}
        else                   {ctx.dashTo(ws*coord[0], hs*(gran-coord[1]));}
      };
  }
}
/*function textOnGeoJSON(ctx, val, ws, hs, gran, dashes){
  if (val.type == "LineString"){
      $.each(val.coordinates,function(key, val) {
          if (dashes=="aaa"){ctx.lineTo(ws*val[0], hs*(gran-val[1]));
          }
          else {ctx.dashTo(ws*val[0], hs*(gran-val[1]));}
      });
  }
}*/