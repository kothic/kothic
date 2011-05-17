CanvasRenderingContext2D.prototype.dashTo = function (X2, Y2, Ptrn) { // segment of dasked line set
    // X2 Y2 : X & Y to go TO ; internal X1 Y1 to go FROM
    // Ptrn as [6,4, 1,4] // mark-space pairs indexed by Seg
    // supply Ptrn only for the first point of a dashed line set

    if (Ptrn) {
      this.Obj = {Patn:Ptrn, Seg:0, Phs:0, X1:X2, Y1:Y2} ; return }
    var XDis, YDis, Dist, X, More, T, Ob = this.Obj
    XDis = X2 - Ob.X1                             // DeltaX
    YDis = Y2 - Ob.Y1                             // DeltaY
    Dist = Math.sqrt(XDis*XDis + YDis*YDis)       // length
    //if (Dist<0.00000001){return}
    this.save()
    this.translate(Ob.X1, Ob.Y1)
    this.rotate(Math.atan2(YDis, XDis))
    this.moveTo(0, 0) ; X = 0 // Now dash pattern from 0,0 to Dist,0
    do {
      T = Ob.Patn[Ob.Seg] // Full segment
      X += T - Ob.Phs     // Move by unused seg
      More = X < Dist     // Not too far?
      if (!More) { Ob.Phs = T - (X - Dist) ; X = Dist } // adjust
      Ob.Seg%2 ? this.moveTo(X, 0) : this.lineTo(X, 0)
      if (More) { Ob.Phs = 0 ; Ob.Seg = ++Ob.Seg % Ob.Patn.length }
      } while (More)
    Ob.X1 = X2 ; Ob.Y1 = Y2
  this.restore() };