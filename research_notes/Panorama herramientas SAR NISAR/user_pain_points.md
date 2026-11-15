# SAR user pain points and adoption barriers (state as of November 2026)

Conventions used in these notes:

- **Evidence grades.** **[S]** systematic or measured (quantified evaluation, defined sample). **[C]** counted forum or issue-tracker signal (real counts, non-random sample). **[I]** institutional documentation or expert statement in a peer-reviewed paper (authoritative, but not a measurement of users). **[A]** single anecdote or single thread. **[V]** vendor, market-research or promotional source (low reliability).
- **"(snippet)"** means I saw only a search-engine excerpt of that source because the page could not be opened. Treat those as lower confidence.
- **"[older: YYYY]"** marks information from before 2025 that may be out of date.
- Quotes are almost entirely replaced with paraphrase, under a limit on reproducing source text. Forum and issue titles appear only as link text.

## What is the evidence-backed ranking of unresolved SAR usability problems?

### Takeaway
No source ranks these problems, and I found no survey of SAR users that measures them, so the ranking below is my own judgment from mixed evidence. The best-measured unresolved problem is that automated SAR maps are unreliable or absent exactly where people need them; the most severe but least-measured problem is that a map does not become a decision.

### Cited Findings

Ranking criteria: breadth of people affected, severity for a real decision, strength of evidence, and how unsolved the problem is. Details and URLs for each row are in the sections below.

| Rank | Problem | Who suffers most | Evidence | Status Nov 2026 |
|---|---|---|---|---|
| 1 | Under-detection and blind spots in automated maps (urban, forest, wind), with accuracy varying widely by event | Emergency managers, insurers, humanitarian analysts | **[S]** strong | Open |
| 2 | Last-mile actionability: map does not say what to do | Local responders, NGOs, municipal staff | **[I]** expert statements, mixed survey evidence | Open |
| 3 | Expertise and interpretability gap (non-intuitive imagery, geometry, LOS, phase) | Non-SAR GIS staff, policy users, students | **[I]+[C]** consistent, no controlled study | Partly solved |
| 4 | InSAR end-to-end workflow and phase unwrapping | Geoscientists, graduate students, engineers | **[C]** strong for this population | Partly solved; open outside North America and Europe |
| 5 | Uncertainty not communicated in a usable form | Decision makers using flood or change maps | **[I]**, no SAR user study | Partly solved |
| 6 | Over-detection: dry soil, agriculture, frost, wet snow, soil moisture | Flood and disturbance monitoring users | **[S]+[I]** | Partly solved |
| 7 | Latency and revisit mismatch with events | Responders, sea-ice and maritime operators | **[I]+[A]** | Partly solved |
| 8 | Desktop toolchain fragility (SNAP terrain correction, DEMs, regressions, readers) | Beginners, small teams without cloud | **[C]** | Partly solved |
| 9 | Validation and reference data scarcity | Product developers, anyone needing to trust a product | **[I]** strong | Open |
| 10 | Data volume and compute | Low-resource users, time-series users | **[C]+[I]** | Partly solved |
| 11 | NISAR HDF5 friction and product maturity | Early NISAR users, GIS users | **[I]+[A]** | Partly solved, changing quickly |
| 12 | Analyst capacity shortage | Humanitarian mapping units, national agencies | **[S]** one evaluation, plus **[V]** | Open |
| 13 | Missing standards and guidance for engineering use of InSAR | Civil and geotechnical engineers | **[I]** one thesis, plus **[V]** | Open |
| 14 | Time-series inconsistency across orbits and sensors | Time-series analysts | **[I]+[A]** | Partly solved |
| 15 | Language and connectivity | Global South practitioners | **[S]** on general EO only; no SAR evidence | Partly solved; weak evidence |
| 16 | Speckle and geometric distortion as such | Beginners | **[I]** | Mostly solved mechanically; residual blind spots feed rank 1 |

### Inferences
- The ranking separates what users complain about from what hurts decisions. Forums over-represent people already processing data, so they surface ranks 4 and 8. People who never adopted SAR, or who receive only a final map, do not post there, so ranks 1, 2 and 5 are under-represented in forum counts.
- Speckle ranks last despite being the problem most associated with SAR. Filters and analysis-ready products handle it mechanically; what remains is the broader interpretability gap at rank 3.
- The strongest opening for a new app is likely ranks 1, 2, 3 and 5 together: an interface that states where a map cannot be trusted, why, and what that implies for the decision at hand. Ranks 8, 10 and 11 are being eroded by NASA, ASF and open-source work, so competing on them alone is riskier.

### Gaps
- I found no survey of SAR users, ESA user survey, World Bank report or published NISAR Early Adopter feedback that quantifies any of these problems. The relative order is therefore not empirically established.
- Frequency across populations cannot be compared, because forum counts, operator evaluations and expert statements measure different things.

## What do users complain about in forums and issue trackers?

### Takeaway
Measured forum activity is dominated by InSAR workflow difficulty, phase unwrapping and terrain-correction or DEM failures in SNAP, plus format support and memory limits in MintPy. Coverage is uneven: STEP and GitHub were readable, Reddit was not, and Stack Exchange and Pangeo returned little that was SAR-specific.

### Cited Findings

**STEP forum (SNAP), counted signal [C].** Views accumulate over years, so they favour old threads; the forum's population is mostly people already trying to process SAR. Categories below are my own reading of titles.
- Among the 50 all-time top topics, about 36 are SAR-related, and the largest cluster is the SNAP-to-StaMPS persistent-scatterer workflow — [STEP top topics](https://forum.step.esa.int/top?period=all).
- The heaviest single how-to is [How to prepare Sentinel-1 images stack for PSI/SBAS in SNAP](https://forum.step.esa.int/top?period=all), with 1,333 replies and 115,872 views. [Workflow between SNAP and StaMPS](https://forum.step.esa.int/top?period=all) has 1,081 replies and 80,953 views.
- Phase unwrapping has its own large thread: SNAPHU Unwrapping, 506 replies and 67,457 views; a further SNAPHU import error thread has 103 replies and 20,612 views — [STEP top topics](https://forum.step.esa.int/top?period=all).
- Conceptual confusion is visible at scale: the difference between vertical and line-of-sight displacement (230 replies, 31,193 views), converting phase to displacement units (95 replies, 20,896 views), and fringes and coherence concepts (40 replies, 18,070 views) — [STEP top topics](https://forum.step.esa.int/top?period=all).
- Infrastructure failures also rank highly: an orbit-file timeout from March 2021 (223 replies, 18,614 views) and corrupted SRTM files (59 replies, 9,606 views) — [STEP top topics](https://forum.step.esa.int/top?period=all). [older: 2021]
- In the 29 threads on the first page of the Microwave Toolbox problem reports (roughly February 2025 to October 2026), 13 concern terrain correction or DEM handling by my hand count, or 14 if DEM-assisted coregistration is included — [STEP problem reports](https://forum.step.esa.int/c/microwave-toolbox/problem-reports/12).
- That same page shows regressions after SNAP 13 and format problems: COSMO-SkyMed calibration failing, PAZ unreadable, subsetting before terrain correction failing or giving wrong results, new ICEYE formats unsupported, and a Copernicus DEM reader slower in SNAP 14 than in SNAP 13 — [STEP problem reports](https://forum.step.esa.int/c/microwave-toolbox/problem-reports/12).
- The most-viewed recent problem reports are Blank Image After Terrain Correction (31 replies, 3,532 views) and a Java heap-space error (3 replies, 3,419 views) — [STEP problem reports](https://forum.step.esa.int/c/microwave-toolbox/problem-reports/12).
- The blank-image thread shows a beginner's run finishing in seconds with empty output, traced in the first case to a changed DEM download URL; later reports from 2020 had no confirmed fix on the page I read — [STEP thread](https://forum.step.esa.int/t/blank-image-after-terrain-correction/). **[A]** [older: 2020 and earlier]

**GitHub.**
- MintPy has 380 issues listed under the comment-sorted view. Among the most-discussed issues I could extract (12 or more comments), 8 concern input format or platform support (HyP3, ARIA, GMTSAR, SNAP), 5 concern memory or parallel performance, and 3 concern installation — [MintPy issues](https://github.com/insarlab/MintPy/issues?q=is%3Aissue+sort%3Acomments-desc). **[C]**
- The top MintPy thread is HyP3 support (#540, 60 comments), followed by a KMZ export for HyP3 (#686, 30 comments, open) and a memory error on very large datasets (#216, 25 comments) — [MintPy issues](https://github.com/insarlab/MintPy/issues?q=is%3Aissue+sort%3Acomments-desc). **[C]**
- A January 2026 MintPy report shows the unwrapping-correction step failing on HyP3 burst interferograms in a mountainous, low-coherence area because the connected-component mask came out blank; it had no maintainer reply or fix when I read it — [MintPy #1453](https://github.com/insarlab/MintPy/issues/1453). **[A]**
- A May 2025 HyP3 report describes a misaligned result when combining Sentinel-1A and 1B bursts, while 1A-only processing was fine; it was still open with no response visible — [HyP3 #2774](https://github.com/ASFHyP3/hyp3/issues/2774). **[A]**
- HyP3's tracker has 63 open issues, but most look maintainer-driven (deployment, bucket permissions, tests), so it is a poor proxy for user pain — [HyP3 issues](https://github.com/ASFHyP3/hyp3/issues).

**NASA Earthdata forum.**
- A sea-ice operations user asking about NISAR latency was told data generally appears 36 to 72 hours after acquisition, and a responder suspected their use case would not qualify for urgent processing; this is an informal opinion — [Earthdata forum](https://forum.earthdata.nasa.gov/viewtopic.php?p=26131) (snippet; the page returned 404 when opened). **[A]**
- OPERA DISP users reported correction layers being absent from stacked downloads, and an ASF reply reminded users that values are line-of-sight — [Earthdata forum](https://forum.earthdata.nasa.gov/viewtopic.php?p=25682) (snippet). **[A]**

**Non-expert difficulty with satellite data generally.**
- A case study of seven Georgia Tech researchers new to satellite data found documentation rarely written for non-specialists, few resources for choosing tools, and basic steps such as extracting a .gz file acting as real hurdles; it used night-lights data and has no SAR content — [Data & Policy, 2025](https://www.cambridge.org/core/journals/data-and-policy/article/challenges-in-using-satellite-data-for-nonremote-sensing-specialists-an-exploratory-case-study/D65CFBF5A4B76F1B625D225A6B896C3E). **[S]** small sample

### Inferences
- InSAR complaints concentrate on connecting tools (SNAP to StaMPS, HyP3 to MintPy) rather than on any one algorithm, which suggests that integration and format handoffs are a pain point in their own right.
- Vertical-versus-LOS and phase-to-displacement questions recur at high view counts, so a product that presents only LOS values is likely to be misread.

### Gaps
- **Reddit (r/remotesensing, r/gis, r/geospatial):** my fetch tool refused reddit.com, and searches returned no direct threads. Third-party mirrors appeared in search results, but I did not use them to get around that refusal. These notes contain no Reddit evidence.
- **GIS Stack Exchange:** searches returned no relevant threads, so I have no evidence from it.
- **Pangeo Discourse:** only general HDF5 and cloud-access discussion surfaced, with nothing on SAR user complaints.
- **ASF support tickets** are not public. The **ISCE2** issue list returned no data through my fetch, so ISCE is not assessed.
- Forum signals describe people who already attempted processing. They do not show why others gave up.

## What do papers and institutional reports say about barriers for non-experts?

### Takeaway
Institutions agree that a knowledge gap limits SAR use, and operators admit large capability gaps, but direct measurement of non-expert SAR users is missing. The one strong evaluation of humanitarian map recipients is positive, which cuts against a simple story that maps go unused.

### Cited Findings
- SAR Handbook authors say a knowledge gap has kept the applied remote sensing community from using SAR fully — [Herndon et al., 2019](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20190025152.pdf). **[I]** [older: 2019]
- The Handbook originated in a workshop where scientists, programme managers and country practitioners identified SAR challenges, and it notes radar's historic reputation as costly and complicated — [SAR Handbook](https://gis1.servirglobal.net/TrainingMaterials/SAR/Cover-to-editors.pdf) (snippet). **[I]** [older: 2019]
- ASF states that SAR interpretation is not always straightforward, partly because of side-looking geometry — [ASF](https://asf.alaska.edu/uncategorized/how-do-i-read-sar-images) (snippet). **[I]**
- CEOS publishes a plain-language interpretation guide, which signals recognised demand — [CEOS Layman's Guide 3.0](https://ceos.org/ard/files/Laymans_SAR_Interpretation_Guide_3.0.pdf) (snippet). **[I]**
- Wagner et al. compare three years of GFM operation with operational user requirements and report discrepancies between the two — [Remote Sensing of Environment 333, 2026](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[S]**
- Schumann argues few satellite flood efforts have entered an agency's operational protocols, and names latency as a main reason — [Frontiers in Remote Sensing, 2024](https://www.frontiersin.org/journals/remote-sensing/articles/10.3389/frsen.2023.1280654/full). **[I]** expert opinion
- UNOSAT's mid-term evaluation surveyed 528 product users and got 97 replies (18%). Of respondents, 98% rated quality good or very good, and average timeliness was 3.4 out of 4 — [UNITAR evaluation](https://unitar.org/sites/default/files/media/file/UNOSAT%20Emergency%20Mapping%20service-MTE%20report.pdf). **[S]**, but with low response and only existing recipients
- The same evaluation found limited cumulative impact because products are time-bound, and noted that use is opaque for the peace, justice and human rights workstream — [UNITAR evaluation](https://unitar.org/sites/default/files/media/file/UNOSAT%20Emergency%20Mapping%20service-MTE%20report.pdf). **[S]**
- Requests to UNOSAT grew 13% from 2021 to 2023, the team absorbed this by deprioritising research and development, and hiring and keeping geospatial analysts is getting harder — [UNITAR evaluation](https://unitar.org/sites/default/files/media/file/UNOSAT%20Emergency%20Mapping%20service-MTE%20report.pdf). **[S]**
- A 2023 CEMS workshop reported generally positive product feedback, while users said resampled images were of little use because they need full resolution to see flood extent — [JRC](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC134331/JRC134331_01.pdf) (snippet). **[I]** [older: 2023]
- A TU Delft doctoral thesis combining literature review and interviews with InSAR users and providers identifies phase ambiguity during short-term settlement and C-band limits in permafrost, and recommends better collaboration, communication, training and application-specific guidelines — [Reinders, 2025](https://research.tudelft.nl/en/publications/on-the-application-of-insar-in-civil-geo-engineering-and-natural-/). **[I]** The landing page gives no interview count.
- An industry commentary says InSAR lacks formal guidance and standards in geotechnical practice — [Ground Engineering, 2022](https://www.geplus.co.uk/opinion/highways-assets-the-challenges-of-using-insar-06-04-2022/) (snippet). **[V]** [older: 2022]
- African user needs are described as poorly quantified and documented, alongside inadequate space-science skills and fragmented coordination — [PMC review](https://pmc.ncbi.nlm.nih.gov/articles/PMC9398042) (snippet). **[I]**
- Market reports call the shortage of trained SAR analysts a key restraint — [Verified Market Research](https://www.verifiedmarketresearch.com/product/synthetic-aperture-radar-market/) (snippet). **[V]**
- A geospatial explainer says many SAR companies do not hand raw data to clients because it is hard to process — [Geoawesome](https://geoawesome.com/eo-hub/everything-you-ever-wanted-to-know-about-sar-satellite-data-and-the-ecosystem-but-were-afraid-to-ask/) (snippet). **[V]**

### Inferences
- Positive UNOSAT ratings and sceptical expert statements are compatible. Analyst-curated maps that reach an institutional recipient seem to work; the unmet need is in fully automated products and in users who have no analyst between them and the data.
- The analyst bottleneck may be the sharpest argument for tooling: demand is rising while the supply of trained people is constrained.

### Gaps
- ARSET Q&A files could not be retrieved (the URL redirected to a general page), and ARSET survey results on SAR courses were not found.
- No NISAR Early Adopter feedback report was found; only agendas and workshop listings surfaced — [JPL workshop listing](https://nisar.jpl.nasa.gov/resources/236/asf-nisar-early-adopters-workshop-jan-2024/).
- No ESA, World Bank or HOT post-mortem specifically about SAR adoption was found.

## What is the evidence on each specific pain point?

### Takeaway
Under-detection, over-detection and validation limits are documented with numbers by the GFM operators themselves. Most of the other pain points rest on documentation, single reports or forum counts, and interpretability has no direct user study at all.

### Cited Findings

**Urban, forest and global coverage blind spots (systematic).**
- GFM's exclusion mask covers 69.9% of global land surface. Its non-sensitive sub-mask of forests and urban areas covers 31.98% — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[S]**
- The authors say urban floods are excluded by design, since Sentinel-1 VV intensity cannot capture built-up inundation, and that users need complementary sources there — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[I]**
- Accuracy varied from 11.0% to 81.1% CSI across 12 events, and 7 of 12 met the 70% target, using version v2.1.0 — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[S]**
- In the global evaluation of about 55,000 sample points, the flood class reached 43.7% CSI and 72.0% overall accuracy; the authors caution that reference uncertainty may depress these scores by an unknown amount — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[S]**
- The April 2026 CEMS presentation repeats that SAR has strong urban limits, and that SLC data could help but adds much data volume and is not operationally mature; its proposed route is expanding flood extent with a high-quality terrain model (FLEXTH) — [Salamon, CEMS, 2026](https://global-flood.emergency.copernicus.eu/media/events/9/salamon_evolution_gfm_april2026.pdf). **[I]**
- UrbanSARFloods was built because no suitable large-scale urban SAR flood dataset existed — [arXiv 2406.04111](https://arxiv.org/abs/2406.04111) (snippet). **[I]** [older: 2024]

**Wind-roughened water.**
- CEMS lists wind among the causes of under-detection, and reports that adding VH polarisation strongly improved a wind-affected Portugal 2019 case — [Salamon, 2026](https://global-flood.emergency.copernicus.eu/media/events/9/salamon_evolution_gfm_april2026.pdf). **[I]**
- A Danish study notes that earlier work dropped Sentinel-1 scenes above about 3.33 m/s wind — [ScienceDirect, 2025](https://www.sciencedirect.com/science/article/pii/S1569843225004637) (snippet). **[I]**

**Wet snow, frost and seasonal false positives.**
- GFM's authors name reducing false positives in agricultural, arid and frozen or snow-covered land as a primary challenge — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[I]**
- When temperatures hover near freezing, frost, ice, wet snow and flooding produce similar patches, and the authors concede "it is impossible to decide where the GFM flood map is correct" — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[I]**
- Advisory flags work reasonably for snow and frost, but are typically not raised for agricultural over-detection, which is the more localised failure — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[I]**
- CEMS reports strong overestimation from very dry soils in Hungary 2022 and in US agricultural fields in 2025, each improved by newer methods — [Salamon, 2026](https://global-flood.emergency.copernicus.eu/media/events/9/salamon_evolution_gfm_april2026.pdf). **[I]**
- OPERA's team says soil moisture, rain, snow and floating vegetation can appear as provisional disturbance until later observations clear them — [OPERA blog, February 2026](https://opera-cal-val.github.io/opera-blog/dist-s1/compare_dist_hls_v1/). **[I]**
- The same post says large objects such as ships and parked cars can be flagged, and steep terrain can defeat delineation — [OPERA blog](https://opera-cal-val.github.io/opera-blog/dist-s1/compare_dist_hls_v1/). **[I]**

**Interpretability and speckle.**
- A SAR-to-optical translation paper reports an expert user study in which synthetic optical imagery paired with SAR performed nearly as well as true pairs for flood segmentation; it tested experts, not non-experts — [MDPI, 2025](https://www.mdpi.com/2072-4292/17/13/2260) (snippet). **[S]** small and expert-only

**Geometric distortions.**
- GFM excludes topographic distortion and radar shadow from flood mapping — [GFM manual](https://extwiki.eodc.eu/GFM/PUM/Products) (snippet). **[I]**
- A UN-SPIDER recipe outputs a layover and shadow mask as part of terrain correction — [UN-SPIDER](https://www.un-spider.org/node/13460) (snippet). **[I]**

**Data volume and compute.**
- Sentinel-1 files became up to 60% larger after the September 2023 move to the Copernicus Data Space, because they are no longer compressed — [NASA Earthdata](https://www.earthdata.nasa.gov/news/sentinel-1-data-file-size-increases). **[I]** [older: 2023]
- Sentinel-1 produces up to 6 TB daily — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[I]**
- NASA material puts NISAR near 85 TB per day and up to 140 PB over three years; other estimates differ, and one news figure of 4.37 TB per day looks like an outlier — [Earthdata](https://earthdata.nasa.gov/news/feature-articles/getting-ready-nisar-managing-big-data-using-commercial-cloud) (snippet). **[I]**
- Forum users report memory limits on ordinary laptops, including a thread on opening Sentinel-1 GRD with 4 GB of RAM — [STEP](https://forum.step.esa.int/t/loading-sentinel-1-grd-with-4-gb-of-ram/28616) (snippet). **[A]**
- HyP3 gives 8,000 free credits per month; RTC costs 5 to 60 credits by resolution and InSAR 10 to 15 — [HyP3 docs](https://hyp3-docs.asf.alaska.edu/using/credits/). **[I]**

**HDF5 and format friction (NISAR).**
- ASF describes NISAR files as very large and slow to load in GIS, recommends subsetting, and suggests GCOV over GSLC for GIS newcomers — [ASF NISAR guide](https://hyp3-docs.asf.alaska.edu/nisar-docs/using-overview/). **[I]**
- Dropping an H5 file into QGIS can place it at 0,0 in the ocean; renaming it to .nc fixes georeferencing — [Wu, January 2026](https://gishub.org/blog/nisar-data-qgis/). **[A]** but concrete and reproducible
- The same post reports search results ranging from under 1 GB to nearly 7 GB per file — [Wu, 2026](https://gishub.org/blog/nisar-data-qgis/). **[A]**
- Esri says many GIS users will find the format unfamiliar, and flags long filenames and long internal paths — [Esri StoryMap](https://storymaps.arcgis.com/stories/c8f85d20b73c48fd8e89f8eef49bc60b) (snippet). **[I]**
- India's NRSC released a 2026 HDF-to-GeoTIFF converter, and a FOSS4G 2026 talk describes a GDAL driver for NISAR HDF5 — [NRSC](https://bhoonidhi.nrsc.gov.in/bhoonidhi_resources/tools/HDF_to_GeoTIFF_Manual.pdf) and [FOSS4G NA](https://talks.osgeo.org/foss4g-na-2026/talk/HLR9AC/) (snippets). **[I]**

**NISAR product maturity (current as of November 2026).**
- ASF warns against mixing BETA and PROVISIONAL products. It lists ionospheric degradation at high latitudes, residual RFI, ripples, and a 59-degree polarimetric phase correction — [ASF known issues](https://nisar-docs.asf.alaska.edu/provisional-known-issues/). **[I]**
- About 1 to 2% of products have raw-data processor issues, and SME2 soil moisture is not yet fully calibrated — [ASF known issues](https://nisar-docs.asf.alaska.edu/provisional-known-issues/). **[I]**
- A permanent data gap runs from 27 July to 10 August 2026 — [NASA alert](https://www.earthdata.nasa.gov/data/alerts-outages/permanent-nisar-instrument-data-gap) (snippet). Provisional production was paused from 23 October to 6 November 2026 — [NASA alert](https://www.earthdata.nasa.gov/data/alerts-outages/nisar-provisional-data-production-paused-oct.-23-nov.-6-2026) (snippet). **[I]**

**Latency and revisit.**
- Standard NISAR L1 and L2 products arrive 36 to 72 hours after acquisition; urgent products arrive in 4 to 6 hours but use poorer orbits and fewer corrections, are kept for 30 days, and are requested only by automatic triggers or authorised USGS, NOAA and NASA users — [ASF urgent response](https://nisar-docs.asf.alaska.edu/urgent-response/). **[I]**
- GFM must deliver within 8 hours of acquisition, but Sentinel-1 revisit is 1 to 3 days in Europe and 6 to 12 days on most other land (2016 to 2021 data) — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[S]**
- CEMS lists the Sentinel-1B failure and flash-flood revisit among its challenges — [Salamon, 2026](https://global-flood.emergency.copernicus.eu/media/events/9/salamon_evolution_gfm_april2026.pdf). **[I]**
- OPERA notes Sentinel-1 does not regularly distribute all possible data outside Europe and parts of North America — [OPERA blog](https://opera-cal-val.github.io/opera-blog/dist-s1/compare_dist_hls_v1/). **[I]**

**Time-series consistency across orbits.**
- A STEP user combining ascending and descending passes saw a zig-zag pattern where values correlated only within the same pass direction; replies pointed to terrain flattening and compositing, with no outcome recorded — [STEP, 2022](https://forum.step.esa.int/t/normalising-sentinel-1-ascending-and-descending-pass-values/34552). **[A]** [older: 2022]
- CEMS says its harmonic model needs recalibration, or under- and over-detects, when land cover is highly dynamic or Sentinel-1 orbits change — [Salamon, 2026](https://global-flood.emergency.copernicus.eu/media/events/9/salamon_evolution_gfm_april2026.pdf). **[I]**
- OPERA says confirming a change is harder when it appears in only one viewing geometry — [OPERA blog](https://opera-cal-val.github.io/opera-blog/dist-s1/compare_dist_hls_v1/). **[I]**

**Uncertainty communication.**
- A 2025 review states that missing uncertainty information reduces trust and hampers integration into decisions — [MDPI review](https://www.mdpi.com/2072-4292/17/17/2943) (snippet). **[I]**
- A 2026 preprint says mapping systems usually give a flood map with no indication of per-prediction trustworthiness — [EGUsphere](https://egusphere.copernicus.org/preprints/2026/egusphere-2026-4233/) (snippet). Not peer reviewed.
- GFM does publish a likelihood layer that users can threshold, plus advisory flags, though flagged pixels stay in the map — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[I]**
- The closest user study concerns forecast maps rather than SAR: an online survey found higher decision confidence with some probability map designs — [HESS, 2023](https://hess.copernicus.org/articles/27/3351/2023/) (snippet). **[S]** adjacent field

**Phase unwrapping.**
- Delft's thesis names phase ambiguity as a core technical obstacle for short-term settlement — [Reinders, 2025](https://research.tudelft.nl/en/publications/on-the-application-of-insar-in-civil-geo-engineering-and-natural-/). **[I]**
- Forum and tracker evidence is listed in the previous section. **[C]**

**Validation data.**
- GFM's accuracy assessment relies on expert interpretation of Sentinel-1 images because other systematic reference data are lacking, and human error was not quantified — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[I]**
- UrbanSARFloods says accurate labels are hard to generate because high-resolution optical imagery rarely coincides with a flood — [arXiv 2406.04111](https://arxiv.org/abs/2406.04111) (snippet). **[I]**
- Kuro Siwo's authors say a comprehensive annotated Sentinel-1 flood dataset had been missing, and provide 43 manually annotated events — [arXiv 2311.12056](https://arxiv.org/pdf/2311.12056) (snippet). **[I]**

**Language and connectivity.**
- A study of 1,041 ARSET participants from 117 countries (2013 to 2016) found Spanish-language training a key factor in Latin American participation; it covers remote sensing generally — [IJGI, 2019](https://doi.org/10.3390/ijgi8060261) (snippet). **[S]** [older: 2019]
- Bilingual Spanish SAR courses exist — [ARSET guide](https://earthdata.nasa.gov/s3fs-public/2025-07/OnlineResourceGuide_07_15_2025.pdf?VersionId=2zE5TvaYAqbX2OCME0jbM_CJLWV8r4DT) (snippet). **[I]**
- Limited, costly internet and skills loss are named as structural EO barriers in commentary — [GDI Manchester](https://blog.gdi.manchester.ac.uk/earth-observation-data-for-the-global-south-democratizing-access-or-deepening-inequalities/) and [SDSN TReNDS](https://www.sdsntrends.org/blog/catalyzing-earth-observations-for-sustainable-development-in-africa) (snippets). **[V]**
- A 2026 preprint on African informal cities reports civil society actors having some awareness of EO but lacking interpretive skills — [Preprints.org](https://www.preprints.org/manuscript/202601.0616) (snippet). Not peer reviewed.

**Last-mile actionability.**
- GFM includes an affected-population layer and the next scheduled Sentinel-1 acquisition, which is partial decision support — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). **[I]**
- A UNOSAT evaluation case study was limited by reaching local government use only through OCHA staff, not first-hand — [UNITAR evaluation](https://unitar.org/sites/default/files/media/file/UNOSAT%20Emergency%20Mapping%20service-MTE%20report.pdf). **[S]**
- MapAction says responders can be overwhelmed by data early in an emergency — [MapAction](https://mapaction.org/tag/mapping/) (snippet). **[I]**
- A press report on Nepal notes a mapped building does not show whether anyone inside needs rescue — [OnlineKhabar](https://english.onlinekhabar.com/mapping-help-nepal-flood-response.html) (snippet). **[A]**
- Mali Red Cross's early-action use of a satellite flood map is a positive example, from a promotional source — [Esri](https://www.esri.com/about/newsroom/blog/transforming-humanitarian-response-in-complex-countries) (snippet). **[V]**

### Inferences
- GFM's published numbers are unusually useful, because they turn a vague "SAR is unreliable" into a specific claim: high overall accuracy can hide weak flood-class skill.
- A likelihood layer alone does not solve uncertainty. It still requires the user to choose a threshold, which assumes expertise that many users lack.
- Any translation of SAR to optical-looking imagery carries a risk of inventing detail in an emergency setting. I found no study testing non-experts on this, so it should be treated as untested.

### Gaps
- No controlled study of how non-experts interpret SAR, with or without despeckling, was found.
- No quantitative wet-snow false-positive rate was found. No season-specific DIST-S1 false-alarm rate was found either.
- Search excerpts mentioned that more than 50% of monitored European surface shows over 0.25 dB ascending-descending shift, and that Copernicus EMS products can take 48 to 72 hours. I could not confirm which paper said either, so neither is used as a finding.
- Excerpts also mentioned a 21 GB full NISAR GSLC frame, attributed to a developer's tool, and a SNAP recommendation of 32 GB of RAM. Neither could be confirmed on the source page. The tool's [README](https://github.com/eitanrapa/nisar_tools), when opened, did not contain the related claims.
- Excerpts indicated 2025 papers naming unwrapping failures as a leading time-series error, but I could not match those statements to specific URLs.

## Which problems are solved, partly solved, or still open?

### Takeaway
Access and basic preprocessing have improved greatly through cloud and analysis-ready products, mainly for backscatter and mainly for North America and Europe in the case of displacement. Trust, urban detection, validation and decision translation remain open.

### Cited Findings

| Problem | Status | What exists | What is still missing |
|---|---|---|---|
| Speckle | Mostly solved mechanically | Filters in common workflows; analysis-ready preparation in Earth Engine — [Mullissa et al., 2021](https://mdpi.com/2072-4292/13/10/1954) (snippet) | No evidence on what helps non-expert comprehension |
| Layover and shadow | Solved as a mask, open as a blind spot | Masks in terrain correction and GFM exclusion — [UN-SPIDER](https://www.un-spider.org/node/13460) (snippet) | No measurement in masked terrain |
| Backscatter preprocessing | Largely solved in cloud | HyP3 on-demand RTC — [HyP3 docs](https://hyp3-docs.asf.alaska.edu/using/credits/); OPERA RTC-S1 in Earth Engine — [Google](https://developers.google.com/earth-engine/datasets/catalog/OPERA_RTC_L2_V1_S1?hl=bn) (snippet) | Earth Engine's standard Sentinel-1 collection is GRD only, with no terrain flattening listed — [Google](https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD) |
| SNAP fragility | Partly solved | Cloud alternatives reduce dependence on it | Terrain-correction, DEM and regression reports continue through October 2026 — [STEP](https://forum.step.esa.int/c/microwave-toolbox/problem-reports/12) |
| Analysis-ready standards | Partly solved | CEOS-ARD assessments, including OPERA DISP — [CEOS](https://ceos.org/ard/files/Peer%20Reviews/SAR/v1.2/S1-OPERA-INSAR/OPERA%20DISP%20InSAR%20-%20CEOS%20ARD%20Review%20Summary.pdf) (snippet); continental Sentinel-1 ARD in Africa — [Digital Earth Africa paper](https://mdpi-res.com/d_attachment/remotesensing/remotesensing-14-00351/article_deploy/remotesensing-14-00351.pdf) (snippet) | Uneven regional availability |
| InSAR displacement | Partly solved | OPERA DISP-S1 covers North America, with processing designed to update within hours — [arXiv 2511.12051](https://arxiv.org/abs/2511.12051); reported to meet its requirement at over 96% of validation sites (snippet) | Elsewhere users must process it themselves; EGMS updates yearly — [arXiv 2511.12051](https://arxiv.org/pdf/2511.12051) (snippet) |
| Phase unwrapping | Open in low coherence | Automatic correction in MintPy | Low-coherence failures still reported — [MintPy #1453](https://github.com/insarlab/MintPy/issues/1453) |
| NISAR format | Partly solved, moving fast | NASA Earthdata QGIS plugin — [Wu, 2026](https://gishub.org/blog/nisar-data-qgis/); ArcGIS Pro reader — [Esri](https://storymaps.arcgis.com/stories/c8f85d20b73c48fd8e89f8eef49bc60b) (snippet); GDAL driver work — [FOSS4G](https://talks.osgeo.org/foss4g-na-2026/talk/HLR9AC/) (snippet) | Workarounds such as renaming files; provisional products with known issues — [ASF](https://nisar-docs.asf.alaska.edu/provisional-known-issues/) |
| Data volume | Partly solved | Subsetting, cloud processing — [ASF](https://hyp3-docs.asf.alaska.edu/nisar-docs/using-overview/) | Cloud needs skills and connectivity; dense time series remain costly |
| Latency | Partly solved | GFM within 8 hours of acquisition; NISAR urgent 4 to 6 hours — [ASF](https://nisar-docs.asf.alaska.edu/urgent-response/) | Revisit is physical; urgent access is restricted |
| Over-detection | Partly solved | Advisory flags; recursive filter and deep-learning methods — [Salamon, 2026](https://global-flood.emergency.copernicus.eu/media/events/9/salamon_evolution_gfm_april2026.pdf) | Near-freezing ambiguity, and unflagged agricultural errors — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf) |
| Wind and vegetation under-detection | Partly solved | VH polarisation in next GFM — [Salamon, 2026](https://global-flood.emergency.copernicus.eu/media/events/9/salamon_evolution_gfm_april2026.pdf) | Operational impact not yet reported |
| Urban floods | Open | FLEXTH terrain-based expansion; benchmark datasets — [Salamon, 2026](https://global-flood.emergency.copernicus.eu/media/events/9/salamon_evolution_gfm_april2026.pdf) | Direct urban detection is not operationally mature |
| Uncertainty | Partly solved | GFM likelihood layer and flags; SARFlood uncertainty-aware labels aimed at researchers — [EGU26](https://meetingorganizer.copernicus.org/EGU26/EGU26-6617.html) (snippet) | Plain-language, decision-ready presentation |
| Validation | Open | Kuro Siwo, UrbanSARFloods, S1S2-Water | Independent, timely reference data — [Wagner et al.](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf) |
| Last-mile actionability | Open | Analyst-led services (UNOSAT, MapAction); GFM population layer | Automated translation into local action |
| Language and connectivity | Partly solved | Spanish ARSET courses; Digital Earth Africa's browser-based sandbox — [Infrastructure News](https://infrastructurenews.co.za/2025/05/30/addressing-earth-observation-data-barriers-in-africa-with-digital-earth-africa-and-the-open-data-cube/) (snippet) | SAR-specific evidence; offline delivery |

### Inferences
- Most public investment has gone to the producer side (formats, ARD, cloud), while the consumer side (what this means, how sure we are, what to do) has received far less.
- Ready-made non-expert tools exist but are thin. A search found a proprietary no-code product — [FlyPix](https://flypix.ai/use-cases/synthetic-aperture-radar-software/) (snippet) **[V]** — and research-oriented platforms, but no open tool combining SAR flood mapping with plain-language interpretation. This reflects one search and is not proof of absence.
- An app relying on GFM or OPERA inputs would inherit their blind spots, so the masks and flags should be shown to users as a primary feature and not hidden.

### Gaps
- I did not test any of these tools hands-on, so "solved" reflects documentation and reports, not verified usability.
- The operational benefit of the next GFM release (VH polarisation, SWIM, recursive filter) is known only from selected cases in one presentation.
