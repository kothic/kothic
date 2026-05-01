const fs = require('fs');
const vm = require('vm');

const [, , runtimePath, stylePath, styleName, casesJson] = process.argv;

const context = {
    Image: function () {
        this.width = 0;
        this.height = 0;
    },
    console: console
};

vm.createContext(context);
vm.runInContext(fs.readFileSync(runtimePath, 'utf8'), context, {filename: runtimePath});
vm.runInContext(fs.readFileSync(stylePath, 'utf8'), context, {filename: stylePath});

const cases = JSON.parse(casesJson);
const results = cases.map((item) => context.MapCSS.restyle(
    [styleName],
    item.tags,
    item.zoom,
    item.type,
    item.selector
));

process.stdout.write(JSON.stringify({
    availableStyles: context.MapCSS.availableStyles,
    presenceTags: context.MapCSS.presence_tags,
    valueTags: context.MapCSS.value_tags,
    results: results
}, null, 2));
