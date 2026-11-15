# Platforms, viewers and derived-product services that turn SAR into Earth surface change information (state as of 9 November 2026)

Conventions used in these notes:
- **NISAR status labels:** EVIDENCED = a primary or repository source shows it. NOT EVIDENCED = I looked and found nothing, which is not proof of absence. PLANNED = stated as future only.
- **[OLD]** marks information from before 2025 that I could not refresh.
- **[SNIPPET]** marks a claim seen only in a search-result excerpt, because the page itself could not be opened.

## For each tool: what does it do best, who uses it, is it free/open, what are its limits, and does it support NISAR?

### Takeaway
As of November 2026, NISAR is usable mainly through NASA/ASF discovery tools (Vertex, Earthdata Search, Worldview, plus the JPL Eyes on the Earth app), and ISRO's Bhoonidhi for S-band. I found no evidence of NISAR in the thematic services (GFM, GFW/RADD, EGMS, DETER) or in Google Earth Engine, Planetary Computer, Copernicus Browser, Climate Engine or Digital Earth Africa. HyP3 On-Demand NISAR support was uncommitted at last evidence. The niche is open: no official public-facing application yet converts NISAR into plain-language change information.

### Cited Findings

#### NISAR baseline facts (context for every "NISAR support" judgment)
- Data maturity tiers: BETA (sample on 23 Jan 2026, over 100,000 Level 1-3 files on 27 Feb 2026; not fully calibrated), PROVISIONAL (from 20 Jul 2026, Levels 0-3, acquisitions from 17 Jun 2026), VALIDATED (from 6 Nov 2026, Levels 0-2, acquisitions from 21 Oct 2026). Data before 21 Oct 2026 is to be reprocessed to validated in 2027 — [ASF NISAR availability overview](https://nisar-docs.asf.alaska.edu/availability-overview/)
- Conflict in timing: the July 2026 ASF notice expected the "full science record" by end of 2026 — [ASF notice](https://asf.alaska.edu/notices/nisar-l-band-data-now-publicly-available/). The availability page now places validated reprocessing of earlier data in 2027 — [ASF availability overview](https://nisar-docs.asf.alaska.edu/availability-overview/). The availability page is newer and should take precedence.
- There is a permanent instrument data gap from 27 Jul to 10 Aug 2026 — [ASF availability overview](https://nisar-docs.asf.alaska.edu/availability-overview/)
- ASF staff reported GUNWs missing over Northern Europe in the provisional release, with only RSLC, GSLC and GCOV present — [Earthdata Forum, SNIPPET](https://forum.earthdata.nasa.gov/viewtopic.php?t=8100)
- NISAR files are HDF5, downloading needs Earthdata Login, and S-band is hosted by ISRO on Bhoonidhi (described as beta) — [NISAR Data User Guide, access](https://nisar-docs.asf.alaska.edu/access-overview/)
- GCOV products carry Cloud Optimized GeoTIFF sidecars for selected terms, to ease web visualization (seen in the beta GCOV description) — [CEOS FedEO record, SNIPPET](https://fedeo.ceos.org/series/eo:platform/NISAR/nisar-l2-gcov-beta-v1?httpAccept=text%2Fhtml)

#### ASF Vertex
- **Best at:** map-based search optimized for NASA SAR holdings, including L-band — [NISAR Data User Guide](https://nisar-docs.asf.alaska.edu/access-overview/). Recommended by NASA for finding Urgent Response data — [Earthdata NISAR tools](https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/nisar/data-access-tools). Includes Baseline and SBAS tools for choosing InSAR pairs — [ASF SBAS docs](https://docs.asf.alaska.edu/vertex/sbas/). Also has a Displacement search type — [ASF Displacement docs](https://docs.asf.alaska.edu/vertex/displacement/).
- **Who:** SAR-literate researchers and analysts (inference from tool design; I found no user breakdown).
- **Cost/openness:** data search is public; NISAR download requires a free Earthdata Login — [NISAR Data User Guide](https://nisar-docs.asf.alaska.edu/access-overview/).
- **Limits:** it is a discovery and ordering tool, and I found no change-interpretation layer documented for it.
- **NISAR: EVIDENCED** — [ASF notice, 21 Jul 2026](https://asf.alaska.edu/notices/nisar-l-band-data-now-publicly-available/).

#### ASF HyP3 / On-Demand / HyP3+
- **Best at:** cloud production of Sentinel-1 RTC and InSAR with no local processing. Over 12 million Sentinel-1 products since October 2020, about 500,000 per month, for more than 1,000 users — [HyP3 What's New, 26 Nov 2025](https://hyp3-docs.asf.alaska.edu/whats_new/).
- **Who:** the >1,000 users above; I found no breakdown by sector.
- **Cost/openness:** free but capped at 8,000 credits per user per month since 1 Dec 2025, reduced because of NASA budget cuts. HyP3+ (20 Oct 2025) lets users buy credits — [HyP3 What's New](https://hyp3-docs.asf.alaska.edu/whats_new/). HyP3+ outputs are kept 30 days versus 14 — [HyP3+ intro, SNIPPET](https://hyp3-docs.asf.alaska.edu/news/hyp3_plus_introduction/).
- **Limits:** reduced capacity, and ASF itself steers users to ARIA GUNW archives and OPERA RTC-S1 as alternatives — [HyP3 What's New](https://hyp3-docs.asf.alaska.edu/whats_new/).
- **NISAR: NOT EVIDENCED as a production offering.** The February 2026 forum thread said ASF was "actively evaluating" it as high priority, dependent on resources, and a later reply said it could not yet commit — [Earthdata Forum, SNIPPET](https://forum.earthdata.nasa.gov/viewtopic.php?p=25372). The What's New page shows no 2026 entries and no NISAR job type — [HyP3 What's New](https://hyp3-docs.asf.alaska.edu/whats_new/). A plugin `hyp3-nisar-cv` (GCOV coefficient of variation and crop or water masks) exists as a fork of an ASFHyP3 repository, which suggests prototyping, not a public service — [GitHub fork, SNIPPET](https://github.com/gchang/hyp3-nisar-cv).

#### NASA Worldview
- **Best at:** browse-and-compare for over 1,200 NASA products, handing off to Earthdata Search for source rasters — [NISAR Data User Guide](https://nisar-docs.asf.alaska.edu/access-overview/).
- **Interaction:** time slider with a custom 12-day step, GIF animation, and Swipe/Opacity/Spy comparison — [NISAR Worldview guide](https://nisar-docs.asf.alaska.edu/worldview/).
- **Who:** general; no usage data retrieved (see usage question).
- **Limits:** cannot animate or download in comparison mode, NISAR layers cannot be displayed in polar view, and different land covers can look alike in the false colour — [NISAR Worldview guide](https://nisar-docs.asf.alaska.edu/worldview/). Experts in a 5-person study criticized its "extensive buffer loading time" — [SalienTime, arXiv 2403.03449](https://arxiv.org/html/2403.03449).
- **NISAR: EVIDENCED.** "NISAR Normalized Radar Backscatter" daily and rolling 12-day mosaics of PROVISIONAL GCOV at 15.625 m — [NISAR Worldview guide](https://nisar-docs.asf.alaska.edu/worldview/). This is backscatter imagery; no NISAR change product is documented there.

#### NASA Earthdata Search
- **Best at:** cross-NASA search across all Earth observation datasets, including NISAR L-band — [NISAR Data User Guide](https://nisar-docs.asf.alaska.edu/access-overview/).
- **Limits and audience:** no independent evaluation found (see Gaps).
- **NISAR: EVIDENCED** — [ASF notice](https://asf.alaska.edu/notices/nisar-l-band-data-now-publicly-available/).

#### NASA Eyes on the Earth (JPL) — public-facing
- A JPL web app that has added a NISAR GCOV layer, with a dedicated NISAR radar page; the documentation request was opened 1 Oct 2026 and sits in backlog — [ua-asf/nisar-docs issue #192](https://github.com/ua-asf/nisar-docs/issues/192); [Eyes NISAR page](https://eyes.nasa.gov/apps/earth/#/vital-signs/radar/nisar-radar).
- **NISAR: EVIDENCED** (visualization only; features not documented in what I could read).

#### NASA OPERA products and viewers
| Product | Status and scope | Evidence |
|---|---|---|
| RTC-S1 | In production, near-global, from 2016 at 30 m | [OPERA announcements](https://www.jpl.nasa.gov/go/opera/announcements); [HyP3 What's New](https://hyp3-docs.asf.alaska.edu/whats_new/) |
| CSLC-S1 | In production over North America | [OPERA announcements](https://www.jpl.nasa.gov/go/opera/announcements) |
| DSWx-S1 | V1 released; near-global in production. Release date conflict: 16 Aug 2024 on the docs page, 25 Oct 2024 on the data notice | [OPERA docs](https://nasa-opera.github.io/docs/products); [Earthdata notice](https://www.earthdata.nasa.gov/data/alerts-outages/opera-dynamic-surface-water-extent-from-sentinel-1-version-1-dataset-released) |
| DISP-S1 | North America, Sentinel-1 from mid-2016, line-of-sight time series | [Earthdata news](https://www.earthdata.nasa.gov/news/opera-project-releases-level-3-displacement-products); [ASF Displacement docs](https://docs.asf.alaska.edu/vertex/displacement/) |
| DIST-ALERT-S1 | Production collection released 27 Oct 2026; COG/XML/PNG; 10 layers; validation led by UMD GLAD; designed to pair with optical DIST-ALERT-HLS | [Earthdata notice](https://www.earthdata.nasa.gov/data/alerts-outages/opera-dist-alert-s1-data-released-earthdata-production-collection) |

- **Best at:** analysis-ready products that remove SAR preprocessing.
- **Viewers:** the ASF Displacement Portal displays DISP (short-wavelength displacement layer) — [ASF docs](https://docs.asf.alaska.edu/vertex/displacement/). DSWx and DIST are explorable in Worldview, with RTC-S1 "coming soon" as of Sept 2025 — [5th OPERA workshop deck, SNIPPET](https://d2pn8kiwq2w21t.cloudfront.net/documents/5th_OPERA_workshop_NASA_Worldview.pdf). Sentinel-1 RTC and DSWx-S1 tiles stream from NASA GIBS as of Oct 2026 — [nisar-water-viewer README](https://github.com/OPERA-Cal-Val/nisar-water-viewer). The September 2026 workshop demonstrated access via Google Earth Engine, QGIS, ArcGIS (OPERA Toolbox), Earthdata, Python and AWS — [OPERA announcements](https://www.jpl.nasa.gov/go/opera/announcements).
- **Cost/openness:** NASA-funded products; DIST-ALERT-S1 is distributed through Earthdata Search — [Earthdata notice](https://www.earthdata.nasa.gov/data/alerts-outages/opera-dist-alert-s1-data-released-earthdata-production-collection).
- **Limits:** the DIST-ALERT-S1 release notice does not state geographic extent or latency and says coverage expansion is ongoing — [Earthdata notice](https://www.earthdata.nasa.gov/data/alerts-outages/opera-dist-alert-s1-data-released-earthdata-production-collection). The project page lists near-global excluding Antarctica — [OPERA project, SNIPPET](https://www.earthdata.nasa.gov/data/projects/opera).
- **Stale source warning:** the OPERA docs page still lists DIST-S1 as "expected in 2026" and DISP-S1 as "expected in 2025" — [OPERA docs](https://nasa-opera.github.io/docs/products).
- **NISAR: PLANNED.** DSWx-NI and DISP-NI were listed as "2026 upcoming releases" at the 10 Sept 2026 workshop — [OPERA announcements](https://www.jpl.nasa.gov/go/opera/announcements). A Cal/Val prototype viewer already compares DSWx-NI with other water products, but that is not a public release — [nisar-water-viewer](https://github.com/OPERA-Cal-Val/nisar-water-viewer).

#### Google Earth Engine
- **Best at:** planetary-scale analysis. Catalog holds Sentinel-1 GRD (COPERNICUS/S1_GRD), ALOS-2 PALSAR-2 and OPERA RTC-S1 — [EE SAR tag](https://developers.google.com/earth-engine/datasets/tags/sar).
- **Who/cost:** free access is tied to non-commercial use, and projects registered before 15 Apr 2025 had to verify eligibility — [EE Sentinel-1 guide, SNIPPET](https://developers.google.cn/earth-engine/guides/sentinel1?hl=it).
- **Limits:** the Sentinel-1 collection is GRD (amplitude) only, so no phase or InSAR in the official catalog listing I reviewed. Requires coding.
- **NISAR: NOT EVIDENCED.** The SAR tag page lists no NISAR dataset when fetched on 9 Nov 2026 — [EE SAR tag](https://developers.google.com/earth-engine/datasets/tags/sar). I checked the tag listing, not a full-catalog search.

#### Copernicus Browser / Sentinel Hub / EO Browser
- **EO Browser is gone.** Sentinel Hub web apps including EO Browser became inaccessible on 20 Mar 2026; Planet points public-data users to Copernicus Browser and states the APIs are not affected — [Planet community notice](https://community.planet.com/product-updates/important-update-sunset-of-eo-browser-and-sentinel-hub-dashboard-6426).
- **Copernicus Browser best at:** Sentinel-1 visualization (SW, IW, EW) and search with orbit, mode and polarization filters; Compare with Split or Opacity; Timelapse export to GIF or MPEG4; area time-series statistics; AOI drawing or upload (KML, GPX, WKT, GeoJSON) — [CDSE docs](https://documentation.dataspace.copernicus.eu/Applications/Browser.html).
- **Cost:** requires a free account — [CDSE docs](https://documentation.dataspace.copernicus.eu/Applications/Browser.html).
- **Limits:** visualization needs sufficient zoom, and search returns 50 results per page — [CDSE docs](https://documentation.dataspace.copernicus.eu/Applications/Browser.html). The Spectral Explorer works only for Sentinel-2 — same source.
- **NISAR: NOT EVIDENCED.** A third-party guide describes Copernicus Browser as limited to Sentinel data — [EOSDA blog, SNIPPET; vendor source](https://eos.com/blog/sentinel-hub-eo-browser-alternatives/).

#### Microsoft Planetary Computer
- **Best at:** open STAC catalog; the Sentinel-1 RTC collection is published with CC BY 4.0 — [PC STAC record](https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-1-rtc).
- **Limits:** the free Hub compute environment was retired on 6 Jun 2024 — [GitHub discussion #347](https://github.com/microsoft/PlanetaryComputer/discussions/347). Planetary Computer Pro is a separate enterprise product — [Azure blog](https://azure.microsoft.com/en-us/blog/microsoft-planetary-computer-pro-unlocking-ai-powered-geospatial-insights-for-enterprises-across-industries/).
- **NISAR: NOT EVIDENCED.** No 2026 status notice was found either.

#### Global Flood Monitoring (GFM / CEMS)
- **Best at:** automated, no-activation Sentinel-1 flood mapping. Launched 2021, ensemble of three algorithms with majority voting — [Remote Sensing of Environment paper via DLR](https://elib.dlr.de/218412/1/1-s2.0-S0034425725005127-main.pdf). No user activation is required — [JRC report, SNIPPET](https://publications.jrc.ec.europa.eu/repository/bitstream/JRC138200/JRC138200_01.pdf).
- **Latency:** typically about five hours, with an eight-hour target in a 2025 presentation — [CEMS GFM intro, SNIPPET](https://european-flood.emergency.copernicus.eu/sites/default/files/AM/AM2025/AM2025pdf/CEMS%20GFM%20Introduction.pdf).
- **Quality:** JRC annual assessments, 12 flood use cases in the 2025 report — [JRC146857](https://publications.jrc.ec.europa.eu/repository/handle/JRC146857). Critical Success Index 80.4% for August 2022 Pakistan floods — [GFM QA report 2022, OLD-ish](https://global-flood.emergency.copernicus.eu/news/150-cems-global-flood-monitoring-annual-product-and-service-quality-assessment-report-2022/).
- **Limits:** lower accuracy for small floods and arid environments in early evaluations — [core.ac.uk, SNIPPET](https://core.ac.uk/outputs/678987141). An EGU 2026 study examined how the Exclusion Layer separates unobserved from non-flooded areas — [EGU26-20728](https://meetingorganizer.copernicus.org/EGU26/EGU26-20728.html).
- **NISAR: NOT EVIDENCED.**

#### Global Forest Watch and RADD
- **Best at:** cloud-penetrating deforestation alerts at 10 m in humid tropics; Integrated alerts combine GLAD-L, GLAD-S2 and RADD for faster, more confident detection — [GFW blog](https://globalforestwatch.org/blog/data-and-tools/integrated-deforestation-alerts).
- **Who:** organizations that stage patrols and pursue illegal loggers from alerts — [Reuters via Eco-Business, 2021](https://www.eco-business.com/news/satellite-alerts-seen-helping-fight-deforestation-in-africa). Journalists are targeted through a Google News Initiative training — [GNI](https://newsinitiative.withgoogle.com/resources/trainings/data-source-global-forest-watch/).
- **Limits:** RADD can miss clearing on wet soils (peat swamps) and where large wood debris remains, and can falsely flag steep terrain — [Nusantara Atlas](https://nusantara-atlas.org/decoding-deforestation-alerts-in-nusantara-atlas/). Alerts are not recommended for trend or area estimates, and do not separate human from other causes — [GFW dataset metadata](https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts). Limited to certain forest types and regions, which GFW says newer all-vegetation alerts aim to address — [GFW blog](https://globalforestwatch.org/blog/data-and-tools/integrated-deforestation-alerts).
- **NISAR: NOT EVIDENCED.**

#### Brazil's DETER family
- DETER-R applies thresholds to Sentinel-1 C-band backscatter time series for the Amazon, processing new images daily, and produced 88,572 warnings in its first year — [DETER-R 2022 summary](https://restoration.elti.yale.edu/resource/deter-r-operational-near-real-time-tropical-forest-disturbance-warning-system-based).
- **Status is uncertain.** A 2025 excerpt called it "recently discontinued" — [search excerpt attributed to the 2025 Revista Brasileira de Cartografia paper, SNIPPET, not confirmed on the landing page](https://seer.ufu.br/index.php/revistabrasileiracartografia/article/view/79446). DETER-RT, combining DETER-R and TropiSCO, is presented as new, published 20 Dec 2025, tested on 2022-2023 data — [same article](https://seer.ufu.br/index.php/revistabrasileiracartografia/article/view/79446).
- TerraBrasilis is INPE's portal for PRODES and DETER data — [TerraBrasilis](https://terrabrasilis.dpi.inpe.br/?p=1825).
- **NISAR: NOT EVIDENCED.**

#### SERVIR tools
- **HydroSAR:** Sentinel-1 flood service for the Hindu Kush Himalaya; HYDRO30 delivers flood extent within hours; reported accuracy >90% for extent and <1 m for depth; co-developed for transfer to an in-region partner — [Remote Sensing 2024](https://doaj.org/article/93507c2ef5c24e5d9f74e57a07b031c8). ICIMOD trained users in August 2021 [OLD] — [ICIMOD event](https://servir.icimod.org/events/servir-flood-inundation-mapping-service/).
- **SAR Handbook:** training resource from SERVIR and SilvaCarbon on forest monitoring and biomass; it has no flood chapter according to the search review — [SERVIR](https://servirglobal.net/resources/sar-handbook).
- **NISAR: NOT EVIDENCED.**

#### UNOSAT
- **Best at:** analyst-produced rapid mapping for UN agencies, Member States and humanitarian partners, since 2003 — [UNITAR 2018 review, OLD](https://unitar.org/about/news-stories/news/how-unosat-rapid-mapping-service-contributed-humanitarian-response-natural-disasters-2018).
- Floods were 61% of 95 products in 2018, and more than 85% of survey respondents found products useful or very useful (self-reported) — same source, [OLD].
- Built Sentinel-1 flood segmentation with UN Global Pulse from 15 historic flood events — [UNITAR](https://unitar.org/about/news-stories/news/fusing-ai-satellite-image-analysis-inform-rapid-response-floods). Code and dataset are public — [GitHub](https://www.github.com/UNITAR-UNOSAT/UNOSAT-AI-Based-Rapid-Mapping-Service).
- **NISAR: NOT EVIDENCED.**

#### Commercial open data (ICEYE, Capella, Umbra)
- **Umbra:** over twenty time-series sites, CC BY 4.0, S3 listing without an AWS account — [Umbra](https://umbra.space/?p=21212); [AWS Registry](https://registry.opendata.aws/umbra-open-data/).
- **Capella:** free imagery via Console or AWS, CC BY 4.0 — [Capella support](https://support.capellaspace.com/what-is-the-capella-open-data-program).
- **ICEYE:** no registration, STAC browser with SLC, GRD and COG — [ICEYE](https://www.iceye.com/open-data-initiative). Older docs warn the catalog may include experimental products — [ICEYE docs](https://sar.iceye.com/6.0.6/opendata/opendata/). I did not find its license.
- **Limits:** curated samples, not systematic monitoring (inference from the catalogs' descriptions). NASA CSDA access is restricted to authorized users under EULAs — [NASA CSDA](https://www.earthdata.nasa.gov/news/nasas-csda-program-announces-eight-new-data-agreements).
- **NISAR:** not applicable.

#### ASF OpenSARLab
- **Best at:** hosted Jupyter environment for SAR teaching and analysis — [OpenSARLab docs](https://opensarlab-docs.asf.alaska.edu/user-guides/opensarlab).
- **Access:** NASA-funded projects are granted access on request; others apply, reviewed weekly, month-to-month and as budget allows; accounts deactivate after 30 days of inactivity — [OpenSARLab accounts](https://opensarlab-docs.asf.alaska.edu/opensarlab-accounts).
- **NISAR:** A 2024 early-adopter workshop recipe book exists — [GitHub](https://www.github.com/ASFOpenSARlab/opensarlab_NISAR_EA_Workshop_2024_1_Recipe_Book/blob/main/intro.md). Current NISAR support: NOT EVIDENCED.

#### EGMS (European Ground Motion Service)
- **Best at:** continental-scale ground motion in a single harmonized product. Persistent Scatterer Interferometry on Sentinel-1, standardized across borders — [Crosetto et al. 2026, RSE](https://nora.nerc.ac.uk/id/eprint/541547/).
- **Current release:** 2020-2024, with upgraded Explorer and a machine-to-machine API — [EGMS update news](https://land.copernicus.eu/en/news/egms-annual-update-brings-new-data-improvements-to-egms-explorer). Annual cadence; only the two latest releases are in the Explorer — [Copernicus Land](https://land.copernicus.eu/en/products/european-ground-motion-service).
- **Limits:** annual latency makes it unsuitable for rapid alerts (inference). The FAQ says the next update (Q4 2026) covers 2020-2024, which duplicates the current period and looks like an error — [EGMS FAQ](https://land.copernicus.eu/en/faq/products/european-ground-motion-service).
- **NISAR: PLANNED only.** The 2026 review names future L-band use (ROSE-L and NISAR) and a stepwise path to a Copernicus Global Ground Motion Service, with no timeline in the abstract — [Crosetto et al. 2026](https://nora.nerc.ac.uk/id/eprint/541547/).

#### InSAR subsidence viewers (no product named "InSAR.Explorer" found)
- California DWR: Sentinel-1 monthly subsidence from 2015, quarterly updates, plus a public dashboard — [California open data](https://data.cnra.ca.gov/dataset/calgw-live/resource/fb3e0d93-7b3e-4bd1-aba7-195554a3d7eb); [Story map](https://storymaps.arcgis.com/stories/41574a6d980b4e5d8d4ed7b90f9698d2).
- Arizona ADWR launched an interactive statewide ArcGIS map in April 2026 — [ADWR](https://www.azwater.gov/news/articles/2026-04-28).
- Harris-Galveston (Texas): InSAR with GPS stations — [HGSD](https://hgsubsidence.org/science-research/district-research/monitoring-the-land-surface-from-space/).
- Norway: nationwide free InSAR service — [NGU](https://www.ngu.no/en/geological-mapping/about-insar-norge-map-subsidence-and-unstable-rock-formations).
- Iran: interactive Sentinel-1 map with time series for 99 subsiding regions (Leibniz University Hannover and GFZ) — [aggregator page, SNIPPET](https://www.sustainabilityaid.net/landslidesandlandsubsidence).
- **Pattern:** agency viewers pair InSAR with GPS validation.
- **NISAR: NOT EVIDENCED** in any of these.

#### Climate Engine
- A dataset explorer built on app.climateengine.org. The only radar-related product I verified is MRRMaid, a Sentinel-1/2 fusion of monthly surface water and mesic vegetation at 10 m for the Sagebrush biome, June-September 2016-2025 — [Climate Engine Substack](https://climateengine.substack.com/p/exploring-mrrmaid-dataset-applications).
- **NISAR: NOT EVIDENCED.** Cost and audience are in Gaps.

#### Digital Earth Africa
- Offers Sentinel-1 Analysis Ready Data and a Sandbox. A former World Bank consultant ran Chad and Niger flood analysis, cutting processing from 10 days to hours, but datasets exceeded the Sandbox's default capacity — [Digital Earth Africa](https://digitalearthafrica.org/en_za/joel-rhines-breakthrough-solution-for-national-scale-flood-analysis-with-sentinel-1-data/).
- **NISAR: NOT EVIDENCED.**

#### Apps built specifically for NISAR (as of Nov 2026)
**Official or institutional**
- Worldview NISAR layers and Eyes on the Earth (above).
- ASF Reference Observation Plan web apps filter planned acquisitions and export footprints — [NISAR Observation Plan](https://nisar-docs.asf.alaska.edu/observation-plan/).
- ISRO Bhoonidhi NISAR page, with Reference Observation Plan viewer and S-band data — [Bhoonidhi](https://bhoonidhi.nrsc.gov.in/NISAR/).
- nisar-water-viewer (OPERA-Cal-Val prototype): MapLibre comparison of nisar-water and DSWx-NI against DSWx-HLS and DSWx-S1. Pairs each NISAR scene with the nearest reference within ±7 days. Its GCOV RGB tiles are reliable only to zoom 10 — [GitHub](https://github.com/OPERA-Cal-Val/nisar-water-viewer).

**Third-party**
- ArcGIS Pro NISAR reader, first in release 3.4.0 — [Esri blog, SNIPPET](https://www.esri.com/arcgis-blog/products/arcgis-pro/imagery/nisar-in-arcgis).
- SkyTruth `nisar-toolbox`: Python search and GeoTIFF conversion for GSLC, GCOV, GUNW and SME2, built to bring NISAR into incident response; early-stage — [GitHub](https://github.com/SkyTruth/nisar-toolbox).
- OpenSAR Explorer: compares NISAR GUNW and Sentinel-1 ground motion with GNSS checks, written for non-specialists; v0.1.0, Ground Motion module only; code published with no license granted; hosted app is limited in area and pair count — [GitHub](https://github.com/Dkashkush/OpenSAR-Explorer).

### Inferences
- There is a clear gap between "NISAR discoverable" and "NISAR understandable": the official public layers show false-colour backscatter, while the change-oriented thematic services remain on Sentinel-1 or optical inputs.
- OPERA DIST-ALERT-S1 (Oct 2026) and the upcoming DSWx-NI/DISP-NI are the natural backbone for a new end-user app, since they spare it from SAR processing.
- EO Browser's closure leaves Copernicus Browser as the main free Sentinel-1 viewer, and older journalist guides now point to a dead tool.
- HyP3's budget-driven cap is a dependency risk for any product that relies on on-demand NISAR processing.

### Gaps
- Earthdata Search limits and audience: no independent review retrieved.
- Whether GFM, GFW, Digital Earth Africa and SERVIR tools are free: not confirmed on the pages I could read, although I would expect them to be. Should be checked before asserting.
- Climate Engine pricing, audience, and whether standalone Sentinel-1 is offered.
- HyP3 NISAR status after about April 2026: forum pages returned 404 on direct fetch.
- Whether DISP-S1 is in Worldview; the sources I saw only point to the ASF Displacement Portal.
- Current DETER-R operational status and DETER-RT deployment.
- UNOSAT current SAR practice and activation process (best sources are 2018-2019).
- Latency, spatial extent and Worldview availability of DIST-ALERT-S1 at release.
- Full-catalog check of NISAR in Earth Engine and Planetary Computer.

## Are there winning or notable NASA Space Apps projects or similar hackathon projects on SAR/NISAR? What did they build?

### Takeaway
I found no SAR or NISAR global winner. The 2025 global winners list names no SAR project, and the 2026 event (14-15 Nov) has not happened yet at this cutoff, so all "Dancing with the SARs" repositories are pre-event or in progress. Many of them lean on demo data.

### Cited Findings
- 2025 had a SAR challenge, "Through the Radar Looking Glass: Revealing Earth Processes with SAR" — [Space Apps 2025](https://www.spaceappschallenge.org/2025/challenges/through-the-radar-looking-glass-revealing-earth-processes-with-sar/?tab=teams).
- None of the ten 2025 global winners explicitly mentions SAR or radar — [NASA announcement](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/).
- Scale, with differing units: more than 11,500 project submissions according to NASA — [NASA](https://www.nasa.gov/learning-resources/stem-engagement-at-nasa/nasa-announces-2025-international-space-apps-challenge-global-winners/). A participant's blog reports 18,860 teams, 1,294 nominees, 45 finalists and 10 winners — [DevStory](https://blog.devstory.co.kr/en/post/nasa-space-app-challenge/index.html).
- A University of Waterloo team reportedly won a PCI Geomatics Young Scholar Award for AI ship detection in SAR (sponsor award, not a global award; the page gives a date that may not match 2025) — [CATALYST, SNIPPET](https://catalyst.earth/supporting-the-next-generation-catalyst-at-the-nasa-space-apps-challenge/).
- 2026 challenge "Dancing with the SARs" uses NISAR radar data to track surface change; event weekend 14-15 Nov 2026 — [The Recursive](https://www.therecursive.com/nasa-space-apps-challenge-2026-where-to-join-it-in-cee/).
- Notable 2026 repositories, all pre-judging:
  - **NISAR Hazard Watch:** CesiumJS globe of 16,663 real NISAR frames with live passes and a drag-to-compare view; its burn, deformation, flood, forest-loss and validation numbers are labelled demo data — [GitHub](https://github.com/cris-eci/nisar-hazard-watch).
  - **dancing-with-the-sars (dmanpark):** plans an L-band vs C-band flood-under-vegetation comparison for the Gandak floodplain using PROVISIONAL GCOV, with a single slider and sonified radar signal; status 3 Nov 2026 was pre-event with "No submission code" — [GitHub](https://github.com/dmanpark/dancing-with-the-sars).
  - **NISAR SAR Scientific Analysis Platform (Narayana1729):** CesiumJS console across five domains; lists Sentinel, ALOS-2 and Landsat inputs, and does not establish use of real NISAR data — [GitHub](https://github.com/Narayana1729/NISAR).
  - **Terracascade:** self-described NISAR-powered change forecasting (not inspected) — [GitHub](https://github.com/1obayed/Terracascade).

### Inferences
- Hackathon teams converge on a 3D globe and multi-hazard scope, often with synthetic results. A narrow, honest, single-question tool would stand out.
- Truthful labelling of demo versus real data, as in NISAR Hazard Watch, is worth copying.

### Gaps
- The official 2026 challenge statement could not be opened (certificate error on spaceappschallenge.org), so its exact wording is unverified.
- 2025 finalist and nominee lists for the SAR challenge were not retrievable; a SAR finalist may exist.
- 2026 winners will only be known after judging.
- Other hackathons (ESA, ISRO Bharatiya Antariksh) were not surveyed.

## Which of these do the general public, journalists and resource managers actually use? What is the usage evidence?

### Takeaway
Hard usage data is scarce and mostly self-reported. The strongest impact evidence is for GFW alerts (Africa). Agency InSAR viewers reach resource managers by design, and journalist use of SAR centres on niche OSINT rather than general monitoring.

### Cited Findings
- **Resource managers and enforcement:** GFW alerts were associated with an 18% average drop in deforestation across nine central African countries, with no overall decline in South America or Asia — [GFW blog on the Nature Climate Change study](https://www.globalforestwatch.org/blog/data-and-tools/glad-alerts-reduce-deforestation-africa/); [Eco-Business](https://www.eco-business.com/news/satellite-alerts-seen-helping-fight-deforestation-in-africa). This concerns GLAD optical alerts, not RADD radar specifically [OLD: 2021].
- **Water managers:** California's DWR publishes InSAR subsidence through groundwater management channels — [California open data](https://data.cnra.ca.gov/dataset/calgw-live/resource/fb3e0d93-7b3e-4bd1-aba7-195554a3d7eb); Arizona ADWR published a statewide map in 2026 — [ADWR](https://www.azwater.gov/news/articles/2026-04-28).
- **EGMS:** a Copernicus user survey had 73 respondents, with nearly all of 50 respondents using the Explorer — [survey report, SNIPPET; date unclear](https://land.copernicus.eu/en/technical-library/survey-evaluation-report-european-ground-motion-service/@@download/file). The 2026 review covers downloads, publications and non-academic use — [Crosetto et al. 2026](https://nora.nerc.ac.uk/id/eprint/541547/), but I could not extract figures.
- **HyP3:** more than 1,000 users — [HyP3 What's New](https://hyp3-docs.asf.alaska.edu/whats_new/).
- **GFM:** a 2022 survey found many users did not know documentation existed, with nearly 60% satisfied with it — [CEMS survey](https://global-flood.emergency.copernicus.eu/user_feedback/user_feedback-file/2) [OLD].
- **Humanitarians:** UNOSAT's own 2018 survey reported more than 85% useful or very useful — [UNITAR](https://unitar.org/about/news-stories/news/how-unosat-rapid-mapping-service-contributed-humanitarian-response-natural-disasters-2018) [OLD].
- **Incident response NGOs:** SkyTruth is building NISAR tooling to bring it into its Sentinel-based incident workflows — [GitHub](https://github.com/SkyTruth/nisar-toolbox).
- **Journalists:** GIJN's satellite guide points to Sentinel-1 via EO Browser — [GIJN](https://gijn.org/resource/resources-for-finding-and-using-satellite-images/), a tool that closed in March 2026 — [Planet](https://community.planet.com/product-updates/important-update-sunset-of-eo-browser-and-sentinel-hub-dashboard-6426). Bellingcat's Radar Interference Tracker uses Sentinel-1 interference to locate military radars — [Bellingcat](https://www.bellingcat.com/resources/2022/02/11/radar-interference-tracker-a-new-open-source-tool-to-locate-active-military-radar-systems/). Google News Initiative trains reporters on GFW — [GNI](https://newsinitiative.withgoogle.com/resources/trainings/data-source-global-forest-watch/).

### Inferences
- Thematic, answer-shaped services (GFW, GFM, subsidence dashboards) reach non-specialists; raw-data portals mostly serve specialists.
- The general public likely meets SAR indirectly via news and agency maps. I found no public usage figures to support this directly.

### Gaps
- No current user or traffic numbers for Vertex, Worldview, Earthdata Search, Copernicus Browser, GEE or EGMS. NASA publishes [annual DAAC metrics](https://earthdata.nasa.gov/about/data-metrics/annual-metrics-reports), which I did not open.
- No user numbers for GFM, GFW or RADD specifically.
- No documented newsroom examples of flood or subsidence reporting built on these SAR tools.
- No studies of general-public use of any SAR tool.

## Which interaction patterns are considered best in class?

### Takeaway
No study ranks these patterns for SAR. The practical bar set by current tools is: a time control matched to the sensor's revisit, a two-date compare, point or AOI time series, an honest confidence and provenance trail, and alerts on saved areas. Plain-language explanation is the weakest area among institutional tools and the main opportunity.

### Cited Findings
| Pattern | Strongest exemplar | Evidence and caveats |
|---|---|---|
| Time slider matched to revisit | Worldview, custom 12-day step for NISAR | [NISAR Worldview guide](https://nisar-docs.asf.alaska.edu/worldview/) |
| Date-range slider on a chart | ASF Displacement Portal | [ASF docs](https://docs.asf.alaska.edu/vertex/displacement/) |
| Swipe / opacity / spy | Worldview; Copernicus Browser has Split and Opacity | [Worldview comparison](https://www.earthdata.nasa.gov/news/blog/introducing-worldviews-comparison-feature); [CDSE docs](https://documentation.dataspace.copernicus.eu/Applications/Browser.html). Worldview cannot animate or download while comparing — [NISAR guide](https://nisar-docs.asf.alaska.edu/worldview/) |
| Pixel/AOI time series | ASF Displacement Portal (multiple AOIs, hover linking, "Shift to Zero"); Copernicus Browser area statistics | [ASF docs](https://docs.asf.alaska.edu/vertex/displacement/); [CDSE docs](https://documentation.dataspace.copernicus.eu/Applications/Browser.html) |
| Alerts on saved area | GFW email alerts for drawn or uploaded areas | [Atlas, secondary source](https://atlas.co/data-sources/global-forest-watch/) |
| Plain-language result first | OpenSAR Explorer "In short" summary, guided three-step flow, glossary | [GitHub](https://github.com/Dkashkush/OpenSAR-Explorer) |
| Interpreting colours | Worldview NISAR colour key is documented in the user guide | [NISAR Worldview guide](https://nisar-docs.asf.alaska.edu/worldview/) |
| Provenance to source data | Worldview Data tab opens source products in Earthdata Search; nisar-water-viewer links scenes to granules | [NISAR guide](https://nisar-docs.asf.alaska.edu/worldview/); [GitHub](https://github.com/OPERA-Cal-Val/nisar-water-viewer) |
| Shareable state and export | nisar-water-viewer URL state and PNG with legend and credits; Copernicus Browser GIF/MP4 | [GitHub](https://github.com/OPERA-Cal-Val/nisar-water-viewer); [CDSE docs](https://documentation.dataspace.copernicus.eu/Applications/Browser.html) |
| Validation shown in the UI | Agency viewers pairing InSAR with GPS stations | [HGSD](https://hgsubsidence.org/science-research/district-research/monitoring-the-land-surface-from-space/) |

- In a 5-expert study, users struggled to choose which time step to visit and navigated mostly at random. A contextual timeline scored System Usability Scale 85.5 versus Worldview 77.5, MetoceanView 74.5 and EO Browser 62.5. Sample is small and experts only — [SalienTime, arXiv 2403.03449](https://arxiv.org/html/2403.03449).
- Experts also reported response times above 10 seconds hindering navigation — [same study](https://arxiv.org/html/2403.03449).
- An older web-mapping study found sliders reduced task time compared with drop-down menus — [Nivala et al., SNIPPET, OLD](https://www.researchgate.net/publication/228624275_Usability_Evaluation_of_Web_Mapping_Sites).

### Inferences
- A plain timeline is not enough: marking which dates carry acquisitions or detected changes should beat a bare slider for SAR, whose time series are sparse.
- The strongest combination for a NISAR app would be OPERA-style products with a 12-day step, two-date swipe, plain-language result with uncertainty, and a link to source granules. AOI alerts would differentiate it, since I found no NASA viewer offering them.
- Interpretive caveats (the colour key, line-of-sight meaning, what a change does not prove) currently live in documentation; moving them into the map is an unclaimed opportunity.

### Gaps
- No controlled study of swipe versus side-by-side for non-experts on satellite imagery was found.
- No user research with journalists or resource managers specifically on SAR interfaces.
- EGMS Explorer's interaction features could not be confirmed from the pages I read.
- I could not confirm alert-subscription features in GFM from accessible sources.
