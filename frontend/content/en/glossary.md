# Glossary

Each term has a stable identifier (`id`) so the interface can link to it. These texts claim nothing the API does not support: if the API changes, this file changes with it.

## The answers

<a id="change_probable"></a>
### Probable change

The radar signal changed between two dates over a part of the area larger than the minimum we set. It says **where** the signal changed, not what caused it or whether there was damage. The minimum is an initial value not yet calibrated with real data.

<a id="no_detectable_change"></a>
### No detectable change

The area was observed, but the change did not reach the minimum. It does not mean nothing happened: a small change, or one that happened and reversed between the two dates, may not show.

<a id="not_observable"></a>
### Not observable

We cannot answer. Either too little of the area was seen, or no pass coincided with the event. This is different from "no change": information is missing, it is not a negative answer.

<a id="cause"></a>
### Cause of not observable

Why the area could not be observed. It can be:

- **Outside the pass:** the area fell outside the strip the satellite swept.
- **Invalid or partially focused data:** mission processing flagged those pixels as unreliable.
- **Input data anomaly:** the mission recorded a problem in the original data.
- **Too few samples per pixel:** the value was computed from so few measurements that it is unreliable.
- **No usable data:** the pixel has no value.
- **Terrain:** mountains that hide or distort the signal. Reserved: GCOV data does not include it and we do not compute it yet.
- **No pass during the event:** the satellite did not pass while the event lasted.
- **Outside the period with data:** the date falls before the first pass or after the last pass of the series.

<a id="hypothesis"></a>
### Hypothesis

A possible explanation of the change, based on how HH and HV varied. It guides, but proves nothing: confirming it needs another source or a field visit.

<a id="signature"></a>
### Polarization signature

The combination of how HH and HV changed, for example "HH up, HV stable". Each combination suggests a different hypothesis. If the signature is mixed, we propose no cause.

## The signal

<a id="backscatter"></a>
### Echo or backscatter

The part of the radar signal that returns to the satellite. It depends on the roughness, shape and moisture of what it hits.

<a id="db"></a>
### Decibel (dB)

The scale we use for the echo and its change. It is logarithmic: a rise of 3 dB roughly doubles the echo's energy.

<a id="hh"></a>
### HH

The satellite sends and receives horizontally. It is more sensitive to ground, moisture and water.

<a id="hv"></a>
### HV

The satellite sends horizontally and receives vertically. The echo grows when the signal bounces many times, as inside vegetation.

<a id="l_band"></a>
### L-band

The kind of wave used by the NISAR radar we analyze, about 24 cm long. A wave that long partly passes through vegetation.

<a id="threshold"></a>
### Threshold

The minimum change, in dB, to mark a pixel as changed. It is fitted to each pair of dates and never goes below a fixed minimum. It is an initial value, not yet calibrated with real data.

<a id="observed_fraction"></a>
### Observed share

The percentage of the area with valid data on both dates. If it is too low, the answer is "not observable".

<a id="changed_fraction"></a>
### Changed share

The percentage of the **observed** area that exceeded the threshold.

## Time

<a id="pass"></a>
### Pass

Each time the satellite sweeps the area and takes an image. Within one series, passes repeat every 12 days.

<a id="interval_days"></a>
### Days between dates

How many days separate the two images being compared. The more days, the more can happen and reverse without being recorded.

<a id="pair_kind"></a>
### Consecutive pair and full window

A consecutive pair compares one pass with the next. The full window compares the first and last dates of the series.

<a id="persistence"></a>
### Assumed persistence

How long we assume an event stays visible, for example standing water for 24 hours. If no pass falls within that time, the event is "not observable". It is an assumption of the query, not a measured value.

<a id="data_gap"></a>
### Acquisition gap

A period without images. Between 27 July and 10 August 2026 the mission acquired no data. Pairs that cross it say so.

<a id="utc"></a>
### UTC

Universal time. Every date in the application is in UTC, which is 6 hours ahead of local time in Parral.

## Data and its origin

<a id="nisar"></a>
### NISAR

A radar satellite from NASA and ISRO (the Indian space agency), launched on 30 July 2025.

<a id="gcov"></a>
### GCOV

The NISAR product we use: images of the radar echo already placed on the map, one per date.

<a id="granule"></a>
### Granule

A data file from a single pass. The receipt lists the exact granules behind each answer.

<a id="series"></a>
### Series

A set of passes taken with the same geometry, which can be compared with each other. It is identified by its track, direction and frame.

<a id="track"></a>
### Track, direction and frame

The track is the orbit the satellite repeats. The direction says whether it was heading north (ascending) or south (descending). The frame is the stretch of that orbit that covers the area.

<a id="mode"></a>
### Mode and polarization

The settings the radar used to take the image, such as the bandwidth and the orientations it sent and received. We only compare dates with the same mode and polarization.

<a id="crid"></a>
### CRID

A code that identifies the version of the mission's processing. We only compare dates with the same CRID, so a processing change is not mistaken for a real change.

<a id="maturity"></a>
### Maturity: provisional or validated

Provisional data is published before the mission finishes validating it. Validated data has been reviewed. We never mix the two in one comparison.

<a id="receipt"></a>
### Receipt

The detail of where each answer comes from: granules, series, CRID, maturity and notices. It lets anyone check the answer.

<a id="notices"></a>
### Notices

Warnings that come with every answer: for example, that the data is provisional, that the series has an acquisition gap, or that thresholds are estimated from the scene itself.

<a id="data_kind"></a>
### Synthetic or real data

Synthetic data is made up to test the application and does not describe any real place. The application always shows when data is synthetic.

<a id="aoi"></a>
### Area

The region being analyzed, for example Hidalgo del Parral, in Chihuahua.

<a id="optical"></a>
### Optical reference image

An ordinary satellite photo (Sentinel-2, from the Copernicus programme) from a nearby date. It helps interpret the map, but clouds may cover it.
