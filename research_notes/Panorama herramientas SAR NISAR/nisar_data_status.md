# NISAR data and software status (as of 9 November 2026)

Evidence tags: **[LIVE]** = queried directly on 2026-11-09 (CMR or GitHub API/raw files). **[DOC]** = read on a primary page (ASF, NASA, ISRO, repository). **[SNIPPET]** = seen only in a search-result summary, page not opened. Anything older than the current state is labelled with its date.

## What NISAR products are publicly released, at what maturity, since when, and from where?

### Takeaway
Real on-orbit L-band data is out and is the main thing to use. Validated L0B/RSLC/GSLC/GCOV arrived on 6 November 2026 (acquisitions from 21 October 2026), but validated interferometric collections were still empty on 9 November, so InSAR work today means the PROVISIONAL collections (mostly 17 June to 23 October 2026). S-band is separate, at ISRO Bhoonidhi, from 8 July 2026 onward.

### Cited Findings

**Timeline (L-band)**
- 30 Jul 2025 launch; Aug 2025 continuous L-band collection began over nearly all global landmasses — [ASF availability overview](https://nisar-docs.asf.alaska.edu/availability-overview/) [DOC]
- 23 Jan 2026: 25 pre-calibration sample products. 27 Feb 2026: over 100,000 pre-calibration L1-L3 products (over 500 TB) as BETA. 20 Jul 2026: global PROVISIONAL, first to include L0B RRSD. 6 Nov 2026: VALIDATED L0-L2 — [ASF availability overview](https://nisar-docs.asf.alaska.edu/availability-overview/) [DOC]; Feb batch also in [Earthdata news](https://www.earthdata.nasa.gov/news/nisar-release-over-100000-new-data-product-files); July release in [ASF notice](https://asf.alaska.edu/notices/nisar-l-band-data-now-publicly-available/)
- 2027: reprocessing campaign for data acquired before 21 Oct 2026, with validated products superseding earlier versions and no completion date; validated SME2 also in 2027 — [ASF availability overview](https://nisar-docs.asf.alaska.edu/availability-overview/) [DOC]
- CONFLICT (older statement): the 21 Jul 2026 notice said the full science record was "expected to be available by the end of 2026" — [ASF notice](https://asf.alaska.edu/notices/nisar-l-band-data-now-publicly-available/). The later availability page moves the validated backlog to 2027 — [ASF availability overview](https://nisar-docs.asf.alaska.edu/availability-overview/). Treat the 2027 date as current.

**Maturity meaning and acquisition ranges**
- BETA: pre-calibration, known issues, for workflow development, Oct 17 2025 to Jan 20 2026, subset, up to 8 acquisitions per track. PROVISIONAL (CRID P05023): calibrated and validated at limited sites, from Jun 17 2026 until "partway through October 23, 2026". VALIDATED (CRID P05036): all L-band acquisitions from Oct 21 2026; collection names have no maturity label — [ASF availability overview](https://nisar-docs.asf.alaska.edu/availability-overview/) [DOC]
- Beta catalog text: "Beta products are not intended for use in scientific research" — [Earthdata GCOV beta](https://www.earthdata.nasa.gov/data/catalog/asf-nisar-l2-gcov-beta-v1-1) [DOC]
- CONFLICT: docs say PROVISIONAL starts 17 Jun 2026, but CMR has PROVISIONAL granules before that date: oldest GCOV and GUNW granules start 2025-10-29 (P05023), with 5,637 GCOV, 6,056 RSLC and 5,143 GUNW granules before 17 Jun 2026 — [CMR GCOV provisional](https://cmr.earthdata.nasa.gov/search/granules.json?short_name=NISAR_L2_GCOV_PROVISIONAL_V1&page_size=1&sort_key=start_date) [LIVE]
- Permanent instrument data gap: 2026-07-27T22:03:25Z to 2026-08-10T00:55:27Z — [ASF known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/) [DOC]

**Collections and granule counts, CMR on 2026-11-09 [LIVE]** — [CMR collection listing](https://cmr.earthdata.nasa.gov/search/collections.json?keyword=NISAR&page_size=100); counts from `granules.json?short_name=<name>`. All listed NISAR collections report `cloud_hosted: true`.

| Product | VALIDATED (`NISAR_Lx_yyy_V1`) | PROVISIONAL (`..._PROVISIONAL_V1`) | BETA (`..._BETA_V1`) |
|---|---|---|---|
| L0B RRSD | 7,689 | 52,896 | no collection seen |
| L1 RSLC | 5,317 (newest 2026-11-07) | 164,886 (newest 2026-10-21) | 23,846 |
| L1 RIFG | 0 | 27,192 | not counted |
| L1 RUNW | 0 | 27,192 | not counted |
| L1 ROFF | 0 | 27,717 | not counted |
| L2 GSLC | 5,129 | 162,907 | 23,450 |
| L2 GCOV | 5,225 | 163,672 | 23,527 |
| L2 GUNW | 0 | 94,150 | 10,217 |
| L2 GOFF | 0 | 27,717 | not counted |
| L3 SME2 | no collection seen | 103,943 | collection exists, not counted |

- Concept IDs: GCOV V1 C3622241360-ASF; GSLC V1 C3622244601-ASF; GUNW V1 C3622247503-ASF; RSLC V1 C3622236985-ASF; GUNW provisional C2854335566-ASF; GCOV provisional C2854338529-ASF — [CMR collection listing](https://cmr.earthdata.nasa.gov/search/collections.json?keyword=NISAR&page_size=100) [LIVE]
- Urgent Response collections: `NISAR_UR_L0B_RRSD`, `NISAR_UR_L1` (5,737 granules), `NISAR_UR_L2` (6,381 granules); newest UR L1/L2 granules acquired 2026-11-09T12:22Z — [CMR UR L1](https://cmr.earthdata.nasa.gov/search/granules.json?short_name=NISAR_UR_L1&page_size=1&sort_key=-start_date) [LIVE]
- Supporting collections: `NISAR_OE` (orbit), `NISAR_RP` (pointing), `NISAR_TEC`, `NISAR_DEM` (modified Copernicus), `NISAR_WATERMASK`, `NISAR_VWC`, `NISAR_ANC_AUX`, `NISAR_COP`, `NISAR_OROST`, `NISAR_STUF` — [CMR collection listing](https://cmr.earthdata.nasa.gov/search/collections.json?keyword=NISAR&page_size=100) [LIVE]
- CRID identifies the software release; mixing CRIDs may introduce processing differences — [ASF availability overview](https://nisar-docs.asf.alaska.edu/availability-overview/) [DOC]

**Where to get it**
- Earthdata Search, Vertex, ASF SearchAPI, `asf_search`; all L-band products free — [ASF notice](https://asf.alaska.edu/notices/nisar-l-band-data-now-publicly-available/); [Earthdata news](https://www.earthdata.nasa.gov/news/nisar-l-band-data-released-expanding-record-surface-changes) [DOC]
- Earthdata Login is required for download and streaming — [ASF earthaccess guide](https://nisar-docs.asf.alaska.edu/earthaccess/) [DOC]
- Reference: NISAR Data User Guide, DOI 10.5281/zenodo.20075813 — [ASF guide](https://nisar-docs.asf.alaska.edu/) [DOC]

### Inferences
- Validated GUNW/RUNW/RIFG/ROFF/GOFF being empty is probably a timing effect: pair products need a 12-day partner after 21 Oct, so the earliest pairs would be from about 2 Nov, plus processing. Not confirmed by ASF.
- Validated `time_start` in collection metadata (2025-10-28) is earlier than the first actual validated granule (2026-10-21, [CMR](https://cmr.earthdata.nasa.gov/search/granules.json?short_name=NISAR_L1_RSLC_V1&page_size=1&sort_key=start_date)), likely anticipating the 2027 reprocessing.
- For a hackathon needing time series: use PROVISIONAL (June to October 2026, roughly 9 to 10 repeat passes per track after the gap, my estimate from 12-day cycles). For single-scene polarimetry or backscatter with best calibration: VALIDATED from 21 Oct 2026, which offers only one or two cycles so far.

### Gaps
- Why PROVISIONAL granules exist from Oct 2025 to Jun 2026 and whether they are scientifically equivalent is not explained in the docs.
- No published date for when validated pair products will first appear.

## What are the coverage, repeat cycle, latency, polarization modes, posting and granule sizes? What about S-band via Bhoonidhi?

### Takeaway
12-day repeat, about 240 km swath, global land and ice in L-band with roughly 1.5 to 3 day standard latency; L2 posting ranges from 5 m (GSLC) to 80 m (GUNW unwrapped), with single files commonly 1 to 25 GB. S-band is mainly India-focused and only reachable through registered Bhoonidhi accounts.

### Cited Findings

**Mission and coverage**
- 747 km Sun-synchronous orbit, 12-day repeat, about 240 km swath, 12 m reflector, SweepSAR — [ISRO S-band release](https://www.isro.gov.in/NISARS_Band_SAR_Data_Products_Release.html) [DOC]
- Repeats coverage twice every 12 days — [Earthdata news](https://www.earthdata.nasa.gov/news/nisar-l-band-data-released-expanding-record-surface-changes) [DOC]
- L-band: global over most landmasses and sea ice, Antarctica fully covered, gap around the North Pole; left-looking; about 7 m along-track, 2 to 8 m cross-track. S-band (9.3 cm): select areas, mainly India — [ASF intro](https://nisar-docs.asf.alaska.edu/nisar-intro/) [DOC]
- L-band wavelength given as 24 cm by [ASF intro](https://nisar-docs.asf.alaska.edu/nisar-intro/) and "about 25 cm" by [Earthdata news](https://www.earthdata.nasa.gov/news/nisar-l-band-data-released-expanding-record-surface-changes) (minor source difference)
- Tracks 001-173, frames 001-176 per track — [ASF GCOV](https://nisar-docs.asf.alaska.edu/gcov/) [DOC]
- Reference observation plan is reviewed every six months and intended to be geographically static, with seasonal changes such as polar sea ice — [ASF observation plan](https://nisar-docs.asf.alaska.edu/observation-plan/) [DOC]

**Polarization and modes**
- SH, SV, DH, DV, QP, compact (RH/RV); Frequency A is primary, Frequency B (5 MHz) mainly supports atmospheric correction — [ASF intro](https://nisar-docs.asf.alaska.edu/nisar-intro/) [DOC]
- Mode/pol codes in the latest 200 granules per collection: dominant `4005/DHDH`, `2005/DHDH`, `2005/QPDH`, `2005/DVDV`, `0005/NASV`, `7700/SHNA`; GUNW `2000/SH`, `4000/SH`; RIFG/GOFF also `7700/SH` — [CMR](https://cmr.earthdata.nasa.gov/search/granules.json?short_name=NISAR_L2_GCOV_V1&page_size=200&sort_key=-start_date) [LIVE]
- GUNW is generated only for Frequency A and only co-pol (HH or VV), nearest-neighbour 12-day pairs — [ASF GUNW](https://nisar-docs.asf.alaska.edu/gunw/) [DOC]

**Posting per product** — [ASF products overview](https://nisar-docs.asf.alaska.edu/products-overview/) [DOC], [ASF GCOV](https://nisar-docs.asf.alaska.edu/gcov/), [ASF GUNW](https://nisar-docs.asf.alaska.edu/gunw/)

| Product | Geometry | Posting |
|---|---|---|
| RSLC | Range-Doppler, zero-Doppler | native |
| RIFG | Range-Doppler | 30 m |
| RUNW | Range-Doppler | 80 m |
| ROFF | Range-Doppler | 90 m |
| GSLC | UTM/polar | 5 to 40 m by bandwidth |
| GCOV | UTM/polar | Freq A: 10 m (40 MHz) or 20 m (20 or 77 MHz); Freq B: 80 m (5 MHz) |
| GUNW | UTM/polar | unwrapped 80 m; wrapped 20 m; coherence 20 and 80 m |
| GOFF | UTM/polar | 80 m |
| SME2 | EASE-Grid 2.0 | 200 m (500 m over Sahara) |

- GCOV values are gamma-0, area-based RTC using Copernicus 30/90 m DEM; `rtcGammaToSigmaFactor` converts to sigma-0; dual-pol users needing off-diagonal terms must derive them from GSLC — [ASF GCOV](https://nisar-docs.asf.alaska.edu/gcov/) [DOC]

**Observed file size (median of latest 200 granules, MB), 2026-11-09** [LIVE, from CMR `granule_size`; mode mix differs by collection so treat as indicative]

| Product | VALIDATED (mostly 40+5 MHz) | PROVISIONAL (mostly 20+5 MHz) |
|---|---|---|
| RSLC | 24,421 (805-28,200) | 5,984 (326-27,183) |
| GSLC | 20,967 | 5,222 |
| GCOV | 6,132 | 887 |
| GUNW | none | 2,204 |
| RIFG / RUNW / ROFF / GOFF | none | 1,205 / 348 / 944 / 1,069 |
| SME2 | none | 53 |
| L0B RRSD | 4,616 (up to 178,352) | 3,540 (up to 149,403) |

- Example: a validated GCOV granule's `.h5` is 4,991,221,760 bytes, with PNG/KML/etc. sidecars — [CMR UMM granule](https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name=NISAR_L2_GCOV_V1&page_size=1&sort_key=-start_date) [LIVE]
- A beta GCOV sample grid was about 36,720 x 37,080 pixels, about 5 GB per large variable — [NASA MAAP guide](https://docs.maap-project.org/en/hub/science/NISAR/NISAR_access.html) [DOC, March 2026, beta data]

**Latency**
- Production (PR) L0 2-10 h; L1 and L2 36-72 h. Urgent Response L0 about 2 h, L1 about 4 h, L2 about 6 h, kept 30 days, no L3 — [ASF urgent response](https://nisar-docs.asf.alaska.edu/urgent-response/) [DOC]
- UR uses forecast orbit and pointing, with no ionospheric/tropospheric corrections; triggered largely by USGS PAGER and volcano alerts — [ASF urgent response](https://nisar-docs.asf.alaska.edu/urgent-response/) [DOC]
- Measured CMR `updated` minus acquisition start on latest granules: L1/L2 median 42-65 h; L0B 4-5 h; pair products about 333-336 h against the first date (about 12 days plus 45-48 h after the second acquisition) — [CMR](https://cmr.earthdata.nasa.gov/search/granules.json?short_name=NISAR_L2_GCOV_PROVISIONAL_V1&page_size=200&sort_key=-start_date) [LIVE; `updated` is a metadata proxy]

**S-band (ISRO Bhoonidhi)**
- Sample products released 9 Jun 2026; daily processed S-SAR available from 8 Jul 2026 (Cycle 25); bulletin dated 15 Jul 2026 — [Bhoonidhi NISAR](https://bhoonidhi.nrsc.gov.in/NISAR) [DOC]
- Products: L1-RSLC, RIFG, RUNW, ROFF; L2-GSLC, GCOV, GUNW, GOFF. Baseline v1.4.0, CRID P00500. Pre-Cycle-25 data to be reprocessed in phases. Registered users order through Browse&Order; Bhoonidhi API for authorized users only — [ISRO release](https://www.isro.gov.in/NISARS_Band_SAR_Data_Products_Release.html) [DOC]
- Vista daily visualisation is currently India-only — [Bhoonidhi NISAR](https://bhoonidhi.nrsc.gov.in/NISAR) [DOC]
- Vertex serves only L-band; it has a "Joint Observation Only" filter for simultaneous L+S takes — [ASF Vertex](https://nisar-docs.asf.alaska.edu/vertex/) [DOC]

### Inferences
- Filename `2005`/`4005`/`7700` appears to encode Frequency A + B bandwidth (20+5, 40+5, 77 MHz), consistent with [ASF GCOV](https://nisar-docs.asf.alaska.edu/gcov/) mode codes; `DHDH` = A and B polarization. The field table is in figures I could not read.
- Trailing `_F_`/`_P_` likely mean full/partial frame, matching Vertex's Frame Coverage filter. Full-frame spans of about 33-39 s imply roughly 240 km along-track at about 7 km/s ground speed (my estimate).
- For hackathon laptops, GCOV at 20+5 MHz (about 1 GB) is the most tractable radiometric product; validated 40 MHz GCOV is about 6 GB and validated RSLC about 24 GB.

### Gaps
- Official frame dimensions in km and exact file-size specifications (in the Product Specification PDF, not read).
- Registration terms, cost and eligibility for non-Indian Bhoonidhi users were not found. S-band spatial posting per product not stated on the ISRO pages read.

## What is the HDF5 structure, and are cloud-optimized access options available?

### Takeaway
Everything is HDF5 (no native COG or Zarr product). It can be streamed by HTTPS range requests from anywhere with Earthdata Login, or by S3 from AWS us-west-2 only. Harmony can extract GCOV layers as (Cloud-Optimized) GeoTIFF. Real data has replaced simulated samples.

### Cited Findings
- Structure: nothing at root; paths such as `/science/LSAR/GCOV/grids/frequencyA/HHHH`, CF-style metadata; older HDF5 drivers may struggle — [ASF data format](https://nisar-docs.asf.alaska.edu/data-format/) [DOC]
- GCOV ancillary layers under the frequency group: `numberOfLooks`, `mask`, `rtcGammaToSigmaFactor` — [ASF GCOV](https://nisar-docs.asf.alaska.edu/gcov/) [DOC]
- Direct S3: bucket `sds-n-cumulus-prod-nisar-products` (browse `-browse`, UR `-ur-products`); us-west-2 only; credentials at `https://nisar.asf.earthdatacloud.nasa.gov/s3credentials`, valid one hour; access outside the region returns Access Denied; no bucket-to-bucket copy — [ASF S3 access](https://nisar-docs.asf.alaska.edu/aws-s3-access/) [DOC]
- Granule links confirm both HTTPS (`nisar.asf.earthdatacloud.nasa.gov`) and `s3://` paths — [CMR UMM granule](https://cmr.earthdata.nasa.gov/search/granules.umm_json?short_name=NISAR_L2_GCOV_V1&page_size=1&sort_key=-start_date) [LIVE]
- Streaming with xarray: `xr.open_datatree(f, engine='h5netcdf', decode_timedelta=False, phony_dims='access')` over `earthaccess` fsspec, with example `cache_type='background'`, 16 MB block — [ASF earthaccess](https://nisar-docs.asf.alaska.edu/earthaccess/) [DOC]
- `asf_search` streaming example reads a value from a 30 GB RSLC without full download — [ASF asf_search](https://nisar-docs.asf.alaska.edu/asf-search/) [DOC]
- MAAP tuning for GCOV: fsspec `blockcache` 8 MB, h5py `page_buf_size` 16 MB, `rdcc_nbytes` 4 MB; these are runtime settings; no benchmarks given — [NASA MAAP guide](https://docs.maap-project.org/en/hub/science/NISAR/NISAR_access.html) [DOC, March 2026]
- Harmony: dataset extraction to GeoTIFF for GCOV, GUNW, GOFF, SME2, through Earthdata Search or harmony-py — [ASF Harmony](https://nisar-docs.asf.alaska.edu/harmony/) [DOC]
- Roadmap: GCOV layer extraction as COG complete (Jun 2026); Worldview daily GCOV RGB complete (Jul 2026); GCOV Earthdata GIS image service and GCOV spatial subset/reprojection pending Q4 2026; full-file GCOV spatial subsetting 2027; COG for other L2/L3 unscheduled — [ASF roadmap](https://nisar-docs.asf.alaska.edu/roadmap/) [DOC]
- A talk by Oleg Pariser scheduled at FOSS4G NA (3 Nov 2026) describes a new GDAL driver that uses HDF5 only as a metadata index and does concurrent multi-range reads of chunks over `/vsis3/` and `/vsicurl/` — [FOSS4G NA 2026](https://talks.osgeo.org/foss4g-na-2026/talk/HLR9AC/) [DOC]
- Real versus simulated: simulated/sample workflows are older material (e.g., [ASF sample data post, 2024](https://asf.alaska.edu/working-with-nisar-sample-data-update-6-27-24/)); over 160,000 real granules per main L1/L2 type are now in CMR (table above) [LIVE]

### Inferences
- Off-AWS teams should expect HTTPS range-request streaming to be the practical path; the chunk-level read pattern matters more than bandwidth, per MAAP.
- ASF's Harmony page says "GeoTIFF" and the roadmap says "Cloud-Optimized GeoTIFF" for GCOV. COG output for GCOV is likely but should be tested.

### Gaps
- Actual HDF5 chunk shapes, page-aggregation use, and compression: not stated on the pages read (likely in the Product Specification).
- No official Kerchunk, VirtualiZarr or Zarr store for NISAR found. A VirtualiZarr demo reportedly used a GUNW granule ([demo](https://virtual-zarr.github.io/connected-data-products-demo/), [SNIPPET]). No quantitative NISAR benchmark found.

## Which tools officially or practically support NISAR now?

### Takeaway
Search and reading work well today: `asf_search`, `earthaccess`, Vertex, GDAL 3.13+, QGIS 4.x, ArcGIS Pro, xarray via h5netcdf. MintPy has a real `prep_nisar` path for GUNW but it is still being fixed, ISCE3 is the mission processor, and HyP3's NISAR jobs are emerging rather than general-purpose. No SNAP reader is confirmed.

### Cited Findings

| Tool | Latest / status | NISAR support | Source |
|---|---|---|---|
| asf_search | v14.1.0, 2026-10-14 [LIVE] | `dataset='NISAR'`, `processingLevel`, `dataMaturity` filters; Python streaming | [ASF guide](https://nisar-docs.asf.alaska.edu/asf-search/); [repo](https://github.com/asfadmin/Discovery-asf_search) |
| earthaccess | v0.19.0, 2026-09-04 [LIVE]; repo now `earthaccess-dev` | Search/download/stream by `short_name`. For S3 use `endpoint=` NISAR URL; `daac='ASF'` errors | [ASF guide](https://nisar-docs.asf.alaska.edu/earthaccess/); [releases](https://github.com/earthaccess-dev/earthaccess/releases) |
| Vertex | live | Science product, maturity (Validated/Provisional/Beta), Production vs Urgent Response, track/frame, bandwidth, polarization, Antarctic projection; L-band only | [ASF Vertex](https://nisar-docs.asf.alaska.edu/vertex/) |
| ISCE3 | v0.25.22, 2026-10-15 [LIVE] | Mission code for L1/L2 generation; `nisarqa`, PLAnT-ISCE3 companions | [ASF tools](https://nisar-docs.asf.alaska.edu/using-open-source/); [repo](https://github.com/isce-framework/isce3) |
| MintPy | v1.6.4, 2026-07-25 [LIVE] | `prep_nisar.py` "Prepare NISAR GUNW products for MintPy" exists in v1.6.4 | [prep_nisar CLI](https://github.com/insarlab/MintPy/blob/main/src/mintpy/cli/prep_nisar.py) |
| GDAL | v3.13.3, 2026-08-18 [LIVE] | L2 georeferencing in HDF5 driver since 3.13.0 ([PR 13953](https://github.com/OSGeo/gdal/pull/13953)); older versions use `NETCDF:` prefix | [NEWS](https://raw.githubusercontent.com/OSGeo/gdal/master/NEWS.md); [ASF GDAL](https://nisar-docs.asf.alaska.edu/gdal/) |
| gdal-driver-nisar (JPL) | not in main GDAL; Unix only (no Windows) | Streaming, block-optimized reads | [ASF GDAL](https://nisar-docs.asf.alaska.edu/gdal/); [conda](https://anaconda.org/channels/nisar-forge/packages/gdal-driver-nisar/overview) |
| QGIS | 4.x native; 3.x workaround | 3.x: rename to `.nc` or prefix `NETCDF:`; complex data needs amplitude/phase extraction; no plugin mentioned | [ASF QGIS](https://nisar-docs.asf.alaska.edu/using-qgis/) |
| ArcGIS Pro | 3.4 (Nov 2024) format; 3.7 (May 2026) GCOV | Whole-file add limited; statistics slow | [ASF ArcGIS](https://nisar-docs.asf.alaska.edu/using-arcgis/) |
| xarray | via h5netcdf `open_datatree` | No dedicated backend listed by ASF | [ASF earthaccess](https://nisar-docs.asf.alaska.edu/earthaccess/) |
| nisar_pytools | active, pushed 2026-11-04 [LIVE] | Lazy xarray open plus RSLC-to-GUNW pipeline; third party | [repo](https://github.com/ZachHoppinen/nisar_pytools); [ASF tools](https://nisar-docs.asf.alaska.edu/using-open-source/) |
| HyP3 | v10.18.2, 2026-11-06 [LIVE] | Job specs `NISAR_CV.yml` and `NISAR_GUNW.yml` present in main | [job_spec](https://github.com/ASFHyP3/hyp3/tree/main/job_spec) |
| hyp3-isce3 | active | Issue: `NISAR_GUNW` job in VolcSARvatory deployments, other deployments TBD | [issue 15](https://github.com/ASFHyP3/hyp3-isce3/issues/15) |
| GMTSAR | active | ASF: "A GMT-based InSAR processor with NISAR support" | [ASF tools](https://nisar-docs.asf.alaska.edu/using-open-source/) |
| dolphin, sweets, PolSARtools, openSEPPO, nisarHDF | active | Listed by ASF; NISAR level of support not stated except openSEPPO "focused on NISAR products" | [ASF tools](https://nisar-docs.asf.alaska.edu/using-open-source/) |
| ISRO HDF to GTiff, SARPOL | ISRO tools | S-band oriented: HDF5 to GeoTIFF/COG; SARPOL is QGIS-integrated polarimetric suite | [ISRO release](https://www.isro.gov.in/NISARS_Band_SAR_Data_Products_Release.html) |

- MintPy detail: PR [#1519](https://github.com/insarlab/MintPy/pull/1519) (`prep_nisar` azimuth angle 90 degree offset) closed 2026-11-07, after v1.6.4; [#1514](https://github.com/insarlab/MintPy/pull/1514) (prep_aria NISAR tropo/SET) and [#1507](https://github.com/insarlab/MintPy/pull/1507) (loader tests) open — [LIVE]
- ASF's own tool list describes MintPy generically, without stating NISAR support — [ASF tools](https://nisar-docs.asf.alaska.edu/using-open-source/) [DOC]
- hyp3-isce3 tracking issue has a completed checklist item for running a MintPy time-series analysis on its GUNW outputs, and notes conda-forge ISCE3 packages "lag releases in GitHub significantly" — [issue 15](https://github.com/ASFHyP3/hyp3-isce3/issues/15) [LIVE]
- ASF roadmap lists HyP3 custom-pair GUNW (with VolcSARvatory) and on-demand L3 as unscheduled — [ASF roadmap](https://nisar-docs.asf.alaska.edu/roadmap/) [DOC]
- Harmony-gdal open issue for very large outputs ("Maximum TIFF file size exceeded") and a closed BigTIFF PR — [issue 54](https://github.com/ASFHyP3/harmony-gdal/issues/54); [PR 56](https://github.com/ASFHyP3/harmony-gdal/pull/56) [LIVE; merge state of PR not checked]
- QGIS version CONFLICT inside ASF docs: [QGIS page](https://nisar-docs.asf.alaska.edu/using-qgis/) says GDAL 3.13 support starts at QGIS 4.0, while [data-format page](https://nisar-docs.asf.alaska.edu/data-format/) says QGIS 4.2 and later.
- SNAP: a STEP forum thread reports users still asking; a reply mentions NISAR branch retargeted to SNAP 14; no confirmed released reader found — [STEP thread](https://forum.step.esa.int/t/nisar-data-support/42229) [SNIPPET]

**Tutorials**
- NISAR Cookbook (ASF): access, GCOV, GSLC; being updated to provisional data; GUNW, RSLC subsetting and application notebooks are listed as planned — [Cookbook](https://asfopensarlab.github.io/NISAR_Cookbook/), [repo](https://github.com/ASFOpenSARlab/NISAR_Cookbook) [DOC]
- OpenSARLab for in-region AWS work; NISAR Science Algorithms notebooks ([GitLab](https://gitlab.com/nisar-science-algorithms), [GitHub](https://github.com/NISAR-Science-Algorithms)); ISCE+ August 2026 course notebooks — [ASF Python tutorials](https://nisar-docs.asf.alaska.edu/python-tutorials/) [DOC]
- NASA ARSET 2026 NISAR training — [ARSET part 2 PDF](https://www.earthdata.nasa.gov/s3fs-public/2026-07/arset-2026-nisar-part2.pdf) [SNIPPET; PDF text not extracted]

### Inferences
- Lowest-friction hackathon stack: `earthaccess` or `asf_search` + xarray/h5netcdf + rioxarray on GCOV; Harmony for GeoTIFF layers without HDF5 code.
- Windows users should use conda GDAL 3.13+ or QGIS 4.x, since the JPL plugin is Unix-only ([ASF GDAL](https://nisar-docs.asf.alaska.edu/gdal/)).
- MintPy on NISAR GUNW is feasible but should be run from the main branch given post-v1.6.4 fixes; budget debugging time. Public HyP3 on-demand NISAR InSAR should not be assumed; ASF lists it as unscheduled.

### Gaps
- Whether `NISAR_CV` and `NISAR_GUNW` are enabled on the public hyp3-api deployment was not verified; PR [#3212](https://github.com/ASFHyP3/hyp3/pull/3212) was changing NISAR_CV inputs on 6 Nov.
- ISCE+ repository URL returned no GitHub metadata when queried (private, moved, or under a different owner).
- No Openscapes NISAR-specific material found. No NISAR-specific 2026 Space Apps challenge resources found, although the event runs 14-15 Nov 2026 ([Space Apps](https://www.spaceappschallenge.org/2026/), [SNIPPET]).

## What known limitations, calibration caveats, notices and complaints exist?

### Takeaway
Validated products have a short known-issues list so far, but it is only days old. Provisional products carry substantive caveats, notably high-latitude ionosphere, residual RFI, an uncalibrated H/V phase term needing a 59 degree correction for coherent polarimetry, and about 1-2% of products affected by incomplete L0B data.

### Cited Findings

**VALIDATED (page entries dated Aug-Nov 2026)**
- Incomplete L0B timestamp issue resolved with CRID P05036; permanent data gap applies — [ASF known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/) [DOC]

**PROVISIONAL (page dated 30 Jul 2026)** — [ASF provisional known issues](https://nisar-docs.asf.alaska.edu/provisional-known-issues/) [DOC]
- High latitudes: geolocation errors, patterned decorrelation bands and phase residuals even after ionospheric estimation.
- RFI filter can leave residual RFI or remove real high-contrast features.
- Low-level ripples in SLC data over dark areas, within requirements.
- Freq B (5 MHz): larger systematic radiometric residuals; no radiometric requirement.
- Polarimetric phase not fully calibrated. Apply theta = 59 degrees: RSLC/GSLC multiply HV and VV by exp(+j theta); GCOV multiply HVVH by exp(+j theta) and HHHV, HHVV, VHVV by exp(-j theta); leave HHVH, HVVV and diagonal terms unchanged.
- Incomplete L0B: roughly 1-2% of products affected, causing defocused RSLC, misplaced products, decorrelation; check L0B quality flags.
- Diagnostic-mode frames unusable (tracks/frames 161/174, 161/175, 169/090, 169/091), to be fixed from Aug 2026 acquisitions.
- Joint L+S 40 MHz: visibly larger residual radiometric bands, within requirements.
- SME2 not fully calibrated; quad-pol areas show 3 to 6 swath gaps.

**BETA (Feb 2026, older)**
- Not fully calibrated; RFI blobs and bands, swath-edge artifacts from subswath mask issues, GUNW wrapped-phase geogrid bug affecting 77 MHz noted in release materials — [ASF beta known issues](https://nisar-docs.asf.alaska.edu/product-known-issues) [SNIPPET]

**Product behaviour**
- GUNW ionospheric phase screen is included but not applied by default; external phase corrections (tides, troposphere) are provided as layers and not removed — [ASF GUNW](https://nisar-docs.asf.alaska.edu/gunw/) [DOC]
- Urgent Response uses forecast orbit/pointing and fewer corrections — [ASF urgent response](https://nisar-docs.asf.alaska.edu/urgent-response/) [DOC]
- BETA and PROVISIONAL should not be mixed casually — [ASF provisional known issues](https://nisar-docs.asf.alaska.edu/provisional-known-issues/) [DOC]

**S-band** — residual radiometric banding in low-SNR areas; residual RFI; calibration parameters will change with baseline updates — [ISRO release](https://www.isro.gov.in/NISARS_Band_SAR_Data_Products_Release.html) [DOC]

**User-reported problems**
- MintPy issue [#1485](https://github.com/insarlab/MintPy/issues/1485): `KeyError` for missing `slantRange` in NISAR GUNW; still open on 2026-11-09, last updated 2026-07-31 [LIVE]
- S3 access: ASF documents an Access Denied error when using credentials outside us-west-2 — [ASF S3](https://nisar-docs.asf.alaska.edu/aws-s3-access/) [DOC]
- Earthdata Forum has NISAR availability questions, including a February 2026 question about only descending data appearing — [forum](https://forum.earthdata.nasa.gov/viewforum.php?f=7&keywords=NISAR) [SNIPPET; thread not opened]

### Inferences
- Polarimetric decompositions on provisional GSLC/GCOV without the 59-degree correction will have biased cross-channel phase; single-channel backscatter and co-pol InSAR are unaffected by this particular issue.
- Provisional data are best suited to low and mid latitudes for InSAR, given the ionosphere caveat.

### Gaps
- Whether the polarimetric 59-degree correction is still required for VALIDATED products is not stated on the known-issues page read.
- Quantified absolute radiometric/geolocation accuracy for validated products was not found.
- Public user complaints are sparse; absence on the forum may reflect the recency of the release, not absence of problems.
