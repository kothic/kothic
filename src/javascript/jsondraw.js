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
function textOnGeoJSON(ctx, val, ws, hs, gran, halo, collide, text){
  if (val.type == "LineString"){
    var projcoords = new Array();
    var textwidth = 0;
    var i = 0;
    while (i<text.length){
      var letter = text.substr(i,1);
      textwidth += ctx.measureText(letter).width;
      i++;
    };
    var aspect = textwidth / ctx.measureText(text).width;
    for (coord in val.coordinates) {
      coord = val.coordinates[coord];
      projcoords.push([ws*coord[0], hs*(gran-coord[1])]);
    };
    //projcoords = ST_Simplify(projcoords, 1);
    var linelength = ST_Length(projcoords);

    if (linelength>textwidth) {
      //alert("text: "+text+" width:"+textwidth+" space:"+linelength);
      var widthused = 0;
      var i = 0;
      var prevangle = "aaa";
      var positions = new Array();
      var solution = 0;

      var flipcount = 0;
      var flipped = false;
      while (solution < 2) {
        if (solution == 0)   widthused = linelength-textwidth/2;
        if (solution == 1)   widthused = 0;
        flipcount = 0;
        i = 0;
        prevangle = "aaa";
        positions = new Array();
        while (i<text.length){
          var letter = text.substr(i,1);
          var letterwidth = ctx.measureText(letter).width/aspect;
          var axy = ST_AngleAndCoordsAtLength(projcoords, widthused);
          if (widthused>=linelength || !axy){
            //alert("cannot fit text: "+text+" widthused:"+ widthused +" width:"+textwidth+" space:"+linelength+" letter:"+letter+" aspect:"+aspect);
            solution++;
            positions = new Array();
            if (flipped) {projcoords.reverse(); flipped=false;}
            break;
          } // cannot fit
          if (prevangle=="aaa") prevangle = axy[0];
          if (
              collide.checkPointWH([axy[1], axy[2]],
                                   2.5*letterwidth,
                                   2.5*letterwidth)
              || Math.abs(prevangle-axy[0])>0.2){
              i = 0;
              positions = new Array();
              letter = text.substr(i,1);
              widthused += letterwidth;
              continue;
            }
          /*while (letterwidth > axy[3] && i<text.length){
            i++;
            letter += text.substr(i,1);
            letterwidth = ctx.measureText(letter).width;
            if (
              collide.checkPointWH([axy[1]+0.5*Math.cos(axy[3])*letterwidth,
                                   axy[2]+0.5*Math.sin(axy[3])*letterwidth],
                                   2.5*letterwidth,
                                   2.5*letterwidth)
              || Math.abs(prevangle-axy[0])>0.2){
              i = 0;
              positions = new Array();
              letter = text.substr(i,1);
              break;
            }

          }*/
          if (axy[0]>Math.PI/2||axy[0]<-Math.PI/2){flipcount+=letter.length};
          prevangle = axy[0];
          axy.push(letter);
          positions.push(axy);
          widthused += letterwidth;
          i++;
        }
        if (flipped && flipcount>text.length/2) {projcoords.reverse(); flipped=false;positions = new Array(); solution++; flipcount=0;}
        if (!flipped && flipcount>text.length/2) {projcoords.reverse(); flipped=true;positions = new Array();}
        if (solution>=2){ return}
        if (positions.length>0) {break}
      }
      if (solution>=2){ return}
      i = 0;

      while (halo && i<positions.length){
        var axy = positions[i];
        var letter = axy[4];
        ctx.save();
        ctx.translate(axy[1],axy[2]);
        ctx.rotate(axy[0]);
        ctx.strokeText(letter, 0, 0);
        ctx.restore();
        i++;
      }
      i=0;
      while (i<positions.length){
        var axy = positions[i];
        var letter = axy[4];
        var letterwidth = ctx.measureText(letter).width;
        ctx.save();
        ctx.translate(axy[1],axy[2]);
        ctx.rotate(axy[0]);
                      collide.addPointWH([axy[1]+0.5*Math.cos(axy[3])*letterwidth,
                                   axy[2]+0.5*Math.sin(axy[3])*letterwidth],
                                   2.5*letterwidth,
                                   2.5*letterwidth)
        //collide.addPointWH([axy[1],axy[2]],2.5*letterwidth+20,2.5*letterwidth+20);
        ctx.fillText(letter, 0, 0);
        ctx.restore();
        i++;
      }
    };
  }
}

