# M1: real OSM corridor network

`python -m signal_lab build-net` succeeds. All five named intersections are located by shared named OSM road nodes, cross-checked against nearby OSM `highway=traffic_signals` nodes, and matched within 65 m to distinct SUMO TLS ids. Coordinates are derived from OSM; none are invented. The bbox uses 150 m padding. Complete OSM ways extend beyond that bbox, so the generated network contains one additional peripheral TLS; the five configured corridor signals remain distinct.

SUMO's osmBuild/netconvert generates the passenger network with actuated defaults, turn lanes, joined junctions/signals, street names, 4 s yellow and 1 s all-red scaffold clearances. The timing-input CSV separately calculates the specified engineering demo inputs; these are not yet applied as an M4 baseline. Detectors come from SUMO's generateTLSE1Detectors tool, twice (stop-bar and upstream); upstream positions are clipped to the edge start on lanes shorter than 40 m.

## Source and fallback

Overpass HPI and overpass-api.de interpreter requests return HTTP 406; private.coffee and kumi endpoints timed out. The official OSM map API worked. `build-net` therefore reads cached discovery OSM or retrieves it from the official map API, computes the bbox, downloads the tighter OSM extract, then uses osmBuild normally. This is an explicit deviation from the osmGet fetch step, using the same underlying OSM primitives. Raw downloads remain gitignored.

Discovery: https://api.openstreetmap.org/api/0.6/map?bbox=-122.06,37.32,-122.03,37.33

Actual bbox: -122.0478341,37.3215501,-122.0306002,37.3242569

SHA256 corridor.osm.xml: `07b4354098a3095f762b2232fc88de808c453169528fc57e07adcfe4133d6c34`.

## Validation

Seven unittest checks pass: CLI verb help, numeric scaffold bench, actual SUMO network load, five TLS/provenance matching, lane counts for three intersections, detector coverage/positions, timing-input equations and basis notes. The lane fixture was hand-entered after inspecting original OSM way tags: De Anza east/west 6/6, Saich 3/4, Stelling 5/4. Counts include turn pockets. This checks OSM-to-SUMO preservation, not surveyed lane geometry or independent field validation.

All child tools now run with nice 15 and serial execution. No demand, actuated rest behavior, optimization, statistics, dashboard or video validation is claimed.
