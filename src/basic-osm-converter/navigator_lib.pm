package navigator_lib;
use Exporter;
use base Exporter;

@EXPORT = qw(latlon_to_filename);

sub latlon_to_filename{
        my ($i, $j) = @_;
        $i = int($i*100+0.5);
        $j = int($j*100+0.5);
        return "data/".int($i/100).'/'.int($j/100).'/'.($i%100).'/'.($j%100).'.map';
}

1;
