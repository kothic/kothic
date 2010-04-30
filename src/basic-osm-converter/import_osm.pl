#! /usr/bin/perl -w

use XML::Parser;
use DBI;
use strict;
    
my $dbname = shift;
my $count = 0;

my $parser = new XML::Parser(ErrorContext => 2);

$parser->setHandlers(Char => \&char_handler,
		     Start => \&start_handler,
		     End => \&end_handler);
#		     Default => \&default_handler);

my $file = shift;

my $dbargs = {AutoCommit => 0,
	PrintError => 1,
	};

my $dbh = DBI->connect("dbi:SQLite:dbname=$dbname","","",$dbargs);
$dbh->do("PRAGMA synchronous = OFF");
if ($dbh->err()) { die "$DBI::errstr\n"; }

print "*\n";

if(defined $file and -f $file){
	$parser->parsefile($file);
}
else{
	$parser->parse(\*STDIN);
}

$dbh->commit();
$dbh->disconnect();

################
## End of main
################

my $id;
my %tags;
my %node_attrs;
my $node_count = 0;
my $node_id;
my $relation_count = 0;
my $sequence;
my $node_count;
my $way_count;
my $relation_count;
my $way_id;
my $relation_id;
my $node_number;

sub start_handler
{
	my( $parseinst, $element, %attrs ) = @_;
	SWITCH: {
              if ($element eq "node") {
		     $dbh->do("insert into node (id, lat, lon) values ($attrs{id},$attrs{lat},$attrs{lon})");
		     if ($dbh->err()) { die "$DBI::errstr\n"; }
		     $node_count += 1;
		     if($node_count % 1000 == 0){
		     	print "nodes: ",$node_count,"\n";
		     }
		     $node_id = $attrs{id};
		     if($node_count % 100000 == 0){
			     $dbh->commit();
			     if ($dbh->err()) { die "$DBI::errstr\n"; }
#			     $dbh->begin();
#			     if ($dbh->err()) { die "$DBI::errstr\n"; }
		     }

                     last SWITCH;
              }
              if ($element eq "way") {
		     $dbh->do("insert into way (id) values ($attrs{id})");
		     if ($dbh->err()) { die "$DBI::errstr\n"; }
		     $way_id = $attrs{id};
		     $node_number = 0;
		     $way_count += 1;
		     if($way_count % 1000 == 0){
		     	print "ways: ",$way_count,"\n";
		     }
                     last SWITCH;
	      }
              if ($element eq "relation") {
		     $dbh->do("insert into relation (id) values ($attrs{id})");
		     if ($dbh->err()) { die "$DBI::errstr\n"; }
		     $relation_id = $attrs{id};
		     $relation_count += 1;
		     $sequence = 0;
		     if($relation_count % 1000 == 0){
		     	print "relations: ",$relation_count,"\n";
		     }
                     last SWITCH;
	      }
              if ($element eq "nd" and defined $way_id) {
		     $dbh->do("insert into way_node (way_id,node_id,node_number) values ($way_id,$attrs{ref},$node_number)");
		     if ($dbh->err()) { die "$DBI::errstr\n"; }
		     $node_number += 1;
                     last SWITCH;
	      }
              if ($element eq "tag" ) {
		      if(defined $way_id){
			      my $q = "insert into way_tag (id,key,value) values ($way_id,".$dbh->quote($attrs{k}).",".$dbh->quote($attrs{v}).")";
			      $dbh->do("$q");
			      if ($dbh->err()) { print $q,"\n"; die "$DBI::errstr\n"; }
		      }
		      elsif(defined $node_id){
			      my $q = "insert into node_tag (id,key,value) values ($node_id,".$dbh->quote($attrs{k}).",".$dbh->quote($attrs{v}).")";
			      $dbh->do("$q");
			      if ($dbh->err()) { print $q,"\n"; die "$DBI::errstr\n"; }
		      }
		      elsif(defined $relation_id){
			      my $q = "insert into relation_tag (id,key,value) values ($relation_id,".$dbh->quote($attrs{k}).",".$dbh->quote($attrs{v}).")";
			      $dbh->do("$q");
			      if ($dbh->err()) { print $q,"\n"; die "$DBI::errstr\n"; }
		      }
		      last SWITCH;
	      }
              if ($element eq "member" ) {
	      		my $q;
	      		if($attrs{type} eq 'node'){
			      $q = "insert into relation_member_node (id,node_id,role,sequence_number) values ($relation_id,".$dbh->quote($attrs{ref}).",".$dbh->quote($attrs{role}).",$sequence)";
			}
	      		if($attrs{type} eq 'way'){
			      $q = "insert into relation_member_way (id,way_id,role,sequence_number) values ($relation_id,".$dbh->quote($attrs{ref}).",".$dbh->quote($attrs{role}).",$sequence)";
			}
	      		if($attrs{type} eq 'relation'){
			      $q = "insert into relation_member_relation (id,relation_id,role,sequence_number) values ($relation_id,".$dbh->quote($attrs{ref}).",".$dbh->quote($attrs{role}).",$sequence)";
			}
			$sequence += 1;
			if(defined $q){
				$dbh->do("$q");
				if ($dbh->err()) { print $q,"\n"; die "$DBI::errstr\n"; }
			}
	      }

       }
       return;
}

sub end_handler
{
	my( $parseinst, $element ) = @_;
	if($element eq 'way'){
		undef $way_id;
	}elsif($element eq 'node'){
		undef $node_id;
	}elsif($element eq 'relation'){
		undef $relation_id;
	}
	return;
}

sub char_handler
{
    # This is just here to reduce the noise seen by
    # the default handler
    return;
}   # End of char_handler
