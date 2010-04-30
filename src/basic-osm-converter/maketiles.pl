#!/usr/bin/perl -w
use DBI;
use Time::HiRes qw(gettimeofday tv_interval);
use strict;
use File::Spec;
use navigator_lib;

my $dbname = $ARGV[0] or die "Usage: ./maketiles.pl database.db";
my $dbargs = {AutoCommit => 0,
	PrintError => 1,
};


my $latmin;
my $latmax;
my $lonmin;
my $lonmax;

my $latcenter = 55.75; 
my $loncenter = 37.62; 
#lat=55.7543&lon=37.6211
#my ( $width, $height ) = ( 240, 320 );
#my ( $width, $height ) = ( 640,480 );
#my $zoom = $width/0.02;

my $dbh = DBI->connect("dbi:SQLite:dbname=$dbname","","",$dbargs);
#$dbh->do("PRAGMA synchronous = OFF");
if ($dbh->err()) { die "$DBI::errstr\n"; }

my $i;
my $j;
my $n = 50;
my $tile_step = 0.01;
for($i=-$n;$i<=$n;$i+=1){
for($j=-$n;$j<=$n;$j+=1){
	$latmin = $latcenter + $i*$tile_step;
	$latmax = $latmin + $tile_step; 
	$lonmin = $loncenter + $j*$tile_step;
	$lonmax = $lonmin + $tile_step; 
	my $filename = latlon_to_filename($latmin, $lonmin);
	my ($vol, $dir, $fname) = File::Spec->splitpath($filename);
#	print $vol,$dir," xxx\n";
	my $p = '.';
	foreach my $cd (File::Spec->splitdir($dir)){
		$p = File::Spec->catdir($p, $cd);
		mkdir $p;
	}
	open my $file, '>', $filename or die "create map file: $!";
   my $q = 'select way_coord_text.id,lat,lon,key,value from way_index,way_tag,way_coord_text where maxLat >= '.$latmin.' and minLat <= '.$latmax.' and maxLon >= '.$lonmin.' and minLon <= '.$lonmax.' and way_index.id=way_coord_text.id and way_coord_text.id = way_tag.id and (key like \'highway\' or key = \'natural\' or key = \'landuse\'or key=\'building\' or key=\'waterway\' or key=\'leisure\' )';
   print $q,"\n";
   my  $t0 = [gettimeofday];
   my $res = $dbh->selectall_arrayref($q);
   my  $el1 = tv_interval ( $t0, [gettimeofday]);
   if ($dbh->err()) { die "$DBI::errstr\n"; }
   my $r;
   my $way_count=0;
   my $node_count=0;
   foreach $r (@$res){
   	my @wlat = split(',', $r->[1]);
   	my @wlon = split(',', $r->[2]);
	my @coord;
	$way_count += 1;
	while(@wlat){
		my ($sx, $sy) = ((shift @wlat), (shift @wlon));
		push @coord, $sx, $sy;
		$node_count += 1;
	}
	my $k = $r->[3];
	my $v = $r->[4];
	if($k eq 'highway' and ($v eq 'primary' or $v eq 'motorway' or $v eq 'trunk')){
		line1($file, $r->[0], 1, @coord);
	}
	elsif($k eq 'highway' and ($v eq 'motorway_link' or $v eq 'trunk_link' or $v eq 'primary_link')){
		line1($file, $r->[0], 2, @coord);
	}
	elsif($k eq 'highway' and $v eq 'secondary'){
		line1($file, $r->[0], 3, @coord);
	}
	elsif($k eq 'highway' and ($v eq 'tertiary' or $v eq 'residential' or $v eq 'living_street')){
		line1($file, $r->[0], 4, @coord);
	}
	elsif($k eq 'highway' and ($v eq 'service' or $v eq 'unclassified')){
		line1($file, $r->[0], 5, @coord);
	}
	elsif($k eq 'building' and $v eq 'yes'){
		poly($file, $r->[0], 6, @coord);
	}
	elsif($k eq 'highway' and $v eq 'footway' or $v eq 'path' or $v eq 'track'){
	}
	elsif(($k eq 'natural' and $v eq 'wood') or ($k eq 'landuse' and $v eq 'forest') or ($k eq 'leisure' and $v eq 'park')){
		poly($file, $r->[0], 7, @coord);
	}
	elsif($k eq 'highway'){
		line1($file, $r->[0], 8, @coord);
	}
	elsif($k eq 'landuse' and $v eq 'industrial'){
		poly($file, $r->[0], 9, @coord);
	}
	elsif(($k eq 'natural' and $v eq 'water') or ($k eq 'waterway' and $v eq 'riverbank')){
		poly($file, $r->[0], 10, @coord);
	}
	elsif($k eq 'landuse' and $v eq 'residential'){
		poly($file, $r->[0], 11, @coord);
	}
	elsif(($k eq 'waterway' and $v eq 'river')){
		line1($file, $r->[0], 12, @coord);
	}
	elsif(($k eq 'waterway' and $v eq 'stream')){
		line1($file, $r->[0], 13, @coord);
	}
	elsif(($k eq 'landuse' and $v eq 'allotments')){
		poly($file, $r->[0], 14, @coord);
	}
	elsif(($k eq 'landuse')){
		poly($file, $r->[0], 15, @coord);
	}
   }
   my  $el2 = tv_interval ( $t0, [gettimeofday]);
   print "Ways: $way_count nodes: $node_count\n";
   print "SQL: $el1 draw: ",$el2-$el1,"\n";
   close $file;
}
}

sub line1{
	my $a;
	my $f = shift;
	my $id = shift;
	my $t = shift;
	print $f "L $id $t";
	foreach $a (@_){
		print $f " $a";
	}
	print $f "\n";
	return 0;
}

sub poly{
	my $a;
	my $f = shift;
	my $id = shift;
	my $t = shift;
	print $f "P $id $t";
	foreach $a (@_){
		print $f " $a";
	}
	print $f "\n";
	return 0;
}
