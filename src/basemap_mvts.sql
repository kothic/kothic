create table basemap_mvts (
    tile_z integer not null,
    tile_x integer not null,
    tile_y integer not null,
    mvt bytea,
    dirty boolean default false not null,
    render_time interval,
    updated_at timestamp with time zone default now() not null
);
