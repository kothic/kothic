def komap_js(mfile, style):
    subjs = {"canvas": ("canvas",), "way": ("Polygon", "LineString"), "line": ("Polygon", "LineString"), "area": ("Polygon",), "node": ("Point",), "*": ("Point", "Polygon", "LineString"), "": ("Point", "Polygon", "LineString"), }
    mfile.write("function restyle (prop, zoom, type){")
    mfile.write("style = new Object;")
    mfile.write('style["default"] = new Object;')
    for chooser in style.choosers:
        condition = ""
        subclass = "default"
        for i in chooser.ruleChains:
            if condition:
                condition += "||"
            rule = " zoom >= %s && zoom <= %s" % (i.minZoom, i.maxZoom)
            for z in i.conditions:
                t = z.type
                params = z.params
                if params[0] == "::class":
                    subclass = params[1][2:]
                    continue
                if rule:
                    rule += " && "
                if t == 'eq':
                    rule += 'prop["%s"] == "%s"' % (params[0], params[1])
                if t == 'ne':
                    rule += 'prop["%s"] != "%s"' % (params[0], params[1])
                if t == 'regex':
                    rule += 'prop["%s"].match(RegExp("%s"))' % (params[0], params[1])
                if t == 'true':
                    rule += 'prop["%s"] == "yes"' % (params[0])
                if t == 'untrue':
                    rule += 'prop["%s"] != "yes"' % (params[0])
                if t == 'set':
                    rule += '"%s" in prop' % (params[0])
                if t == 'unset':
                    rule += '!("%s"in prop)' % (params[0])
                if t == '<':
                    rule += 'prop["%s"] < %s' % (params[0], params[1])
                if t == '<=':
                    rule += 'prop["%s"] <= %s' % (params[0], params[1])
                if t == '>':
                    rule += 'prop["%s"] > %s' % (params[0], params[1])
                if t == '>=':
                    rule += 'prop["%s"] >= %s' % (params[0], params[1])
            if rule:
                rule = "&&" + rule
            condition += "((" + "||".join(['type == "%s"' % z for z in subjs[i.subject]]) + ") " + rule + ")"
        styles = ""
        if subclass != "default":
            styles = 'if(!("%s" in style)){style["%s"] = new Object;}' % (subclass, subclass)
        for k, v in chooser.styles[0].iteritems():
            if type(v) == str:
                try:
                    v = str(float(v))
                    styles += 'style["' + subclass + '"]["' + k + '"] = ' + v + ';'
                except:
                    styles += 'style["' + subclass + '"]["' + k + '"] = "' + v + '";'
        mfile.write("if(%s) {%s};\n" % (condition, styles))
    mfile.write("return style;}")
