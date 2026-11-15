# Open-source SAR processing and serving stack, as of November 2026

Method notes for the report writer:
- Repository figures (stars, last push, latest release) were measured directly from the GitHub API on 2026-11-09. "Open" counts come from the API field `open_issues_count`, which includes open pull requests, so treat them as an upper bound on issues.
- Items tagged **[older]** predate 2025 and may no longer hold. Items tagged **[snippet]** were seen only in a search result summary, not read in full.
- Issue evidence was read directly through the GitHub API unless tagged otherwise.

## What do scientists and engineers actually use to process SAR into ARD and serve it, what does each do well, and what is painful?

### Takeaway
The stack has split into two generations. The older desktop and HPC tools (SNAP, ISCE2, GAMMA) remain the working baseline, while a NASA/OPERA line (ISCE3, Dolphin, MintPy, HyP3) and a Python/xarray/Zarr line (sarsen, xarray-sentinel, InSAR.dev, odc-stac, TiTiler) are taking over new pipeline work. For a backend team the main pain points are heavy compiled or JVM dependencies with conda-only Linux installs, RAM blowups on NISAR-sized scenes, and local-POSIX-file assumptions in processors, rather than missing algorithms.

### Cited Findings

#### Activity snapshot (2026-11-09)

| Project | Stars | Open | Last push | Latest release | Source |
|---|---|---|---|---|---|
| snap-engine | 216 | 24 | 2026-11-09 | SNAP 14.0.0 listed as current [snippet] | [repo](https://github.com/senbox-org/snap-engine), [download page](https://step.esa.int/main/download/snap-download/) |
| s1tbx | 240 | 11 | 2024-08-07 | **Archived** | [repo](https://github.com/senbox-org/s1tbx) |
| esa-snappy | 34 | 9 | 2026-08-11 | none on GitHub | [repo](https://github.com/senbox-org/esa-snappy) |
| ISCE2 | 675 | 254 (issue tracker disabled) | 2026-06-30 | v2.6.5 (2026-06-30) | [repo](https://github.com/isce-framework/isce2) |
| ISCE3 | 252 | 158 | 2026-11-05 | v0.25.22 (2026-10-15) | [repo](https://github.com/isce-framework/isce3) |
| MintPy | 842 | 72 | 2026-11-07 | v1.6.4 (2026-07-25) | [repo](https://github.com/insarlab/MintPy) |
| PyGMTSAR | 608 | 96 | 2026-10-02 | v2023.3.11 is the last GitHub release object | [repo](https://github.com/AlexeyPechnikov/pygmtsar) |
| Dolphin | 161 | 34 | 2026-11-09 | v0.42.9 (2026-10-27) | [repo](https://github.com/isce-framework/dolphin) |
| LiCSBAS (original) | 287 | 4 | 2024-11-29 | v1.5.11 (2021) | [repo](https://github.com/yumorishita/LiCSBAS) |
| LiCSBAS (COMET fork) | 68 | 5 | 2026-10-30 | not checked | [repo](https://github.com/comet-licsar/LiCSBAS) |
| licsar_proc | 17 | 0 | 2026-11-07 | not checked | [repo](https://github.com/comet-licsar/licsar_proc) |
| sarsen | 318 | 12 | 2026-11-09 | v0.9.6 (2026-06-23) | [repo](https://github.com/bopen/sarsen) |
| xarray-sentinel | 249 | 21 | 2026-11-09 | v0.9.7 (2026-11-04) | [repo](https://github.com/bopen/xarray-sentinel) |
| sarpy | 338 | 5 | 2026-10-23 | v2.1.1 (2026-08-23) | [repo](https://github.com/ngageoint/sarpy) |
| pyroSAR | 615 | 47 | 2026-10-30 | v0.40.0 (2026-10-30) | [repo](https://github.com/johntruckenbrodt/pyroSAR) |
| S1Tiling (GitHub mirror) | 23 | 1 | 2026-03-25 | 1.4.0 (2026-03-18) | [repo](https://github.com/CNES/S1Tiling) |
| OpenSARLab notebooks | 187 | not checked | 2026-05-04 | not checked | [repo](https://github.com/ASFOpenSARlab/opensarlab-notebooks) |
| stackstac | 272 | 60 | 2024-08-10 | v0.5.1 (2024-08-10) | [repo](https://github.com/gjoseph92/stackstac) |
| odc-stac | 207 | 18 | 2026-10-27 | v0.5.3 (2026-07-29) | [repo](https://github.com/opendatacube/odc-stac) |
| TiTiler | 1206 | 29 | 2026-11-09 | 2.4.0 (2026-09-21) | [repo](https://github.com/developmentseed/titiler) |
| rio-tiler | 594 | 21 | 2026-11-09 | 9.4.13 (2026-11-02) | [repo](https://github.com/cogeotiff/rio-tiler) |
| titiler-multidim | 88 | 29 | 2026-11-06 | v0.11.0 (2026-10-20) | [repo](https://github.com/developmentseed/titiler-multidim) |
| GDAL | 6145 | 612 | 2026-11-09 | v3.13.3 (2026-08-18) | [repo](https://github.com/OSGeo/gdal) |
| zarr-python | 2085 | 462 | 2026-11-09 | v3.4.2 (2026-10-27) | [repo](https://github.com/zarr-developers/zarr-python) |
| geozarr-spec | 220 | 37 | 2026-11-08 | none | [repo](https://github.com/zarr-developers/geozarr-spec) |
| Kerchunk | 367 | 135 | 2026-09-15 | maintenance mode | [repo](https://github.com/fsspec/kerchunk) |
| VirtualiZarr | 309 | 187 | 2026-11-09 | v2.8.0 (2026-10-14) | [repo](https://github.com/zarr-developers/VirtualiZarr) |
| Icechunk | 702 | not checked | 2026-11-09 | v2.3.1 (2026-10-27) | [repo](https://github.com/earth-mover/icechunk) |
| STAC spec | 941 | 54 | 2026-11-04 | v1.1.0 (2024-09-11) | [repo](https://github.com/radiantearth/stac-spec) |
| pygeoapi | 632 | 45 | 2026-11-06 | 0.24.0 (2026-07-28) | [repo](https://github.com/geopython/pygeoapi) |

#### Processors: SNAP family
- SNAP 14.0.0 is listed as the current version on the download page [snippet] — [STEP download](https://step.esa.int/main/download/snap-download/). SNAP 13 added Sentinel-1C product library support and beta BIOMASS support [snippet] — [STEP](https://step.esa.int/main/download/snap-download/). Microwave Toolbox patch notes reached at least 13.0.3 — [release notes](https://step.esa.int/main/wp-content/releasenotes/Microwave/Microwave_13.0.3.html).
- The `s1tbx` GitHub repository is archived (API flag, last push 2024-08) — [repo](https://github.com/senbox-org/s1tbx).
- Headless install of esa_snappy was undocumented enough that a user had to report the fix in an issue: `./snap --nosplash --nogui --modules --install eu.esa.snap.esa.snappy`. The reporter calls it "very difficult to figure out" — [esa-snappy #9](https://github.com/senbox-org/esa-snappy/issues/9). A general install help issue is still open from 2024 — [esa-snappy #2](https://github.com/senbox-org/esa-snappy/issues/2).
- esa_snappy minimum Python was raised to 3.9 for SNAP 12+ [snippet]. The confirmed upper bound for SNAP 13/14 was not found — [SNAP wiki](https://senbox.atlassian.net/wiki/spaces/SNAP/pages/3114106881/Installation+and+configuration+of+the+SNAP-Python+esa_snappy+interface+SNAP+version+12).
- A user reports Python-driven SNAP as "way worse" than the GUI and links it to a critical JIRA issue left without updates for over a year [snippet] — [STEP forum](https://forum.step.esa.int/t/snappy-performance-issues/44898). pyroSAR's own docs state it avoids snappy because of install limits and processing performance **[older, v0.15 docs]** — [pyroSAR docs](https://github.com/johntruckenbrodt/pyroSAR/blob/v0.15.0/docs/general/snap.rst).
- Per-product anomalies occur. One forum report has a Sentinel-1 IW reprojection at roughly 45 s typically but about 50 minutes for an anomalous product under SNAP 13, down from hours under SNAP 12 [snippet, single thread] — [STEP forum](https://forum.step.esa.int/t/excessively-long-hours-to-reproject-some-sentinel-1-iw-products/45471). Another user reports SNAP 13 stopping mid-processing on Windows 11 [snippet] — [STEP forum](https://forum.step.esa.int/t/snap-13-getting-interrupted-while-processing/45446).
- Heap tuning through `-Xmx`/`-Xms` is the main documented lever [snippet] — [SeaDAS performance docs](https://seadas.gsfc.nasa.gov/help-9.2.0/performanceparameters/PerformanceParameters.html); ESA also publishes a limited-memory guide — [STEP tutorial](https://step.esa.int/docs/tutorials/SNAP%20Processing%20with%20Limited%20Memory.pdf).
- pyroSAR gives a Python interface to SNAP and GAMMA workflows — [README](https://github.com/johntruckenbrodt/pyroSAR). Its reported pains are the same underlying SNAP problems: geocode runs that never complete ([#191](https://github.com/johntruckenbrodt/pyroSAR/issues/191) **[older, 2022]**), SNAP detection failures ([#304](https://github.com/johntruckenbrodt/pyroSAR/issues/304) **[older, 2024]**) and a still-open thread on AWS processing ([#107](https://github.com/johntruckenbrodt/pyroSAR/issues/107)).

#### Processors: ISCE and the OPERA line
- ISCE2 is on conda-forge for linux-64 and osx-64 only — [conda-forge API](https://api.anaconda.org/package/conda-forge/isce2). Its GitHub issue tracker is disabled (CLI error when listing issues), so public pain-point evidence is scarce — [repo](https://github.com/isce-framework/isce2).
- ISCE3 is on conda-forge for linux-64, linux-aarch64, osx-64 and osx-arm64, with CPU-only and GPU builds. Its README still warns it "is in early development" — [conda-forge API](https://api.anaconda.org/package/conda-forge/isce3), [README](https://github.com/isce-framework/isce3).
- ISCE3 pain points: no pip or virtualenv install path as reported ([#26](https://github.com/isce-framework/isce3/issues/26), open since 2024), failed source compiles ([#17](https://github.com/isce-framework/isce3/issues/17) **[older]**), and GDAL version coupling ([#25](https://github.com/isce-framework/isce3/issues/25) **[older]**). The repository was for a long time a mirror of an internal project; external contribution status was still being discussed in 2025 — [#29](https://github.com/isce-framework/isce3/issues/29).
- MintPy reads interferogram stacks from ISCE, ARIA, FRInGE, HyP3, GMTSAR, SNAP, GAMMA and ROI_PAC and produces 3D displacement (2D space, 1D time), driven by `smallbaselineApp.py` — [README](https://github.com/insarlab/MintPy). Coherence and SNAPHU connected components are used as inputs when available — [README](https://github.com/insarlab/MintPy).
- MintPy's pain is scaling. An issue on Dask failures with many workers is still open from 2021, with "Timed out during handshake" recurring on HPC — [#518](https://github.com/insarlab/MintPy/issues/518). Very large stacks hit memory errors **[older]** — [#216](https://github.com/insarlab/MintPy/issues/216).
- Dolphin is on conda-forge and PyPI, but its README warns GDAL and similar dependencies "are more easily set up through conda" — [README](https://github.com/isce-framework/dolphin). OPERA's DISP-S1 product code imports directly from Dolphin — [disp-s1 product_info.py](https://github.com/opera-adt/disp-s1/blob/main/src/disp_s1/product_info.py).
- **Key NISAR scaling evidence.** Six NISAR L-band 40 MHz GSLCs gave a `(6, 69696, 70560)` ministack and Dolphin tried to allocate about 9 TB. Strides of 6x6 worked. Unwrapping took about 7 hours and just under 50 GB of RAM per interferogram, and the reporter advises using the subset feature for higher-resolution NISAR work — [dolphin #712](https://github.com/isce-framework/dolphin/issues/712).
- Other Dolphin issues: a phase-linking double-free crash ([#686](https://github.com/isce-framework/dolphin/issues/686), closed 2026), JAX version crashes ([#253](https://github.com/isce-framework/dolphin/issues/253) **[older]**). S3 support remains an open meta-issue, though outputs can already be COGs through the `add_overviews` flag — [#173](https://github.com/isce-framework/dolphin/issues/173).
- HyP3 offers RTC, OPERA RTC-S1, InSAR, Burst InSAR and ARIA S1 GUNW products; 8,000 free credits per month on Basic, and 1 credit = $0.05 on HyP3+. Products expire after 14 days (Basic) or 30 days (HyP3+) — [HyP3 docs](https://hyp3-docs.asf.alaska.edu/).

#### Processors: PyGMTSAR, LiCSAR, Python-native
- PyGMTSAR's README announces **InSAR.dev** as its successor: pure Python, NISAR and Sentinel-1, Zarr v3, "avoiding the NetCDF-related issues affecting PyGMTSAR". PyGMTSAR is limited to single-polarization scenes along one orbital path — [README](https://github.com/AlexeyPechnikov/pygmtsar).
- PyGMTSAR's strength is Colab-runnable end-to-end notebooks with automatic data retrieval, and a Docker image — [README](https://github.com/AlexeyPechnikov/pygmtsar). Its issues include GeoTIFF export ([#126](https://github.com/AlexeyPechnikov/pygmtsar/issues/126)), long processing times ([#108](https://github.com/AlexeyPechnikov/pygmtsar/issues/108)) and multilook bugs ([#191](https://github.com/AlexeyPechnikov/pygmtsar/issues/191)) **[all 2024]**.
- The original LiCSBAS repository states it "cannot be updated since 2022" and that its step01 download has been broken since a June 2024 portal change. It directs users to LiCSBAS2 or the COMET fork — [README](https://github.com/yumorishita/LiCSBAS).
- LiCSBAS runs time series analysis on LiCSAR's unwrapped interferograms and coherence from the COMET portal, so it is tied to that catalogue — [README](https://github.com/yumorishita/LiCSBAS).
- sarsen does GTC and RTC (gamma flattening) with Dask for larger-than-memory work, and can run on fully remote CDSE S3 and Earth Data Hub DEM data. It describes itself as **beta** — [README](https://github.com/bopen/sarsen).
- sarsen had a high unmanaged memory problem. The maintainer says it "should be fixed, or at least greatly improved" in 0.9.6 (June 2026) with new rasterio access and dask-aware `map_overlap` — [sarsen #75](https://github.com/bopen/sarsen/issues/75).
- xarray-sentinel opens Sentinel-1 SAFE products in xarray as EOPF DataTrees or classic Datasets, and converts to EOPF Zarr with one command (`xarray-sentinel to-eopf-zarr`) — [README](https://github.com/bopen/xarray-sentinel).
- sarpy 2.0 merges legacy SarPy with NGA's sarkit, adding fast SICD, SIDD, CPHD and CRSD readers. It targets NGA complex SAR standards rather than Sentinel-style ARD — [README](https://github.com/ngageoint/sarpy).
- S1Tiling orthorectifies Sentinel-1 onto the Sentinel-2 MGRS grid using Orfeo Toolbox, ships a Docker image and pulls data through EODAG. It claims to be "considerably faster" than SNAP orthorectification (self-reported) and is used for Amazon deforestation detection. Real development is on GitLab — [README](https://github.com/CNES/S1Tiling).
- OpenSARLab is ASF's JupyterHub on Kubernetes in AWS us-west-2, beside NASA data, deployable to your own AWS account **[older, 2022 talk]** — [LPS 2022](https://earth.esa.int/living-planet-symposium-2022-presentations/26.05.Thursday/Santiago_del_Chile/1330-1510/06_Kennedy.pdf). Docs warn that misconfiguration can orphan volumes on deletion, and accounts deactivate after 30 days of inactivity [snippet] — [OpenSARLab docs](https://opensarlab-docs.asf.alaska.edu/dev-guides/cluster/build-and-deploy-opensarlab-cluster).

#### Commercial
- GAMMA is commercial and requires a licence; prices are on request only — [GAMMA](https://gamma-rs.com/gamma-software). A NASA-authored abstract calls it the "gold standard" commercial software **[older, 2022]** — [AGU 2022](https://ntrs.nasa.gov/api/citations/20220017945/downloads/AGU2022_RTC_v2.pdf).
- SARscape (NV5 Geospatial) is supported only in floating/server licence mode — [NV5](https://www.nv5geospatialsoftware.com/Support/Self-Help-Tools/Help-Articles/how-to-install-and-license-envi-6x-and-sarscape-6x). Version 6.3.0 is dated 2026-07-31 [snippet] — [NV5](https://www.nv5geospatialsoftware.com/Support/Self-Help-Tools/Help-Articles/whats-new-in-envi-sarscape-63). No public price list was found.
- An RTC benchmark of GAMMA, ISCE2 and SNAP 8 found no significant radiometric calibration differences; the main differences were in geolocation quality **[older, 2022-2023]** — [Remote Sensing 15(21) 5110](https://www.mdpi.com/2072-4292/15/21/5110), [AGU 2022](https://ntrs.nasa.gov/api/citations/20220017945/downloads/AGU2022_RTC_v2.pdf).
- Different InSAR methods give non-identical velocities and time series, so inter-comparison needs a defined method **[older, 2021]** — [Sadeghi et al., RSE](https://nora.nerc.ac.uk/id/eprint/529560).

#### Stacking and catalogues
- stackstac has had no commit since 2024-08-10. A March 2026 issue asks whether it is abandoned — [#270](https://github.com/gjoseph92/stackstac/issues/270). A community PR (still open, not merged) proposes a README notice that it is "not actively maintained" and points to odc-stac and lazycogs — [PR #271](https://github.com/gjoseph92/stackstac/pull/271).
- odc-stac loads STAC items into xarray, locally or through Dask — [README](https://github.com/opendatacube/odc-stac). Recent issues include nodata handling during downsampling ([#260](https://github.com/opendatacube/odc-stac/issues/260), closed 2026) and Dask pickling crashes ([#237](https://github.com/opendatacube/odc-stac/issues/237), closed 2025).
- The latest STAC spec release is still v1.1.0 from September 2024 — [repo](https://github.com/radiantearth/stac-spec). The SAR extension is at v1.3.2, with `sar:product_type` and `sar:instrument_mode` deprecated in favour of `product:type` and `instrument_modes` — [STAC SAR extension](https://github.com/stac-extensions/sar).
- pygeoapi is a Python server for the OGC API suite — [README](https://github.com/geopython/pygeoapi).

#### Formats and virtualisation
- Kerchunk's README declares **maintenance mode** with no new features planned, and recommends VirtualiZarr with Icechunk for new projects — [README](https://github.com/fsspec/kerchunk).
- VirtualiZarr separates parsing, concatenation and serialisation, writing to kerchunk-json, kerchunk-parquet or Icechunk — [VirtualiZarr FAQ](https://virtualizarr.readthedocs.io/en/stable/explanation/faq.html). Icechunk tracks the last-modified time of source chunks, so it can detect when referenced data has changed — [CNG guide](https://guide.cloudnativegeo.org/zarr/virtual-zarr.html).
- VirtualiZarr's GeoTIFF path is still maturing: the 2026-10-14 release notes mention sparse TIFF tiles (offset 0, byteCount 0) that committed successfully and failed only on read [snippet] — [release notes](https://virtualizarr.readthedocs.io/en/stable/about/releases.html).
- GeoZarr is no longer one monolithic spec. The repo says the work focuses on separate conventions (multiscales, projection and others) and that "the GeoZarr specification will be produced once a set of mature conventions forms a coherent and recommended suite" — [README](https://github.com/zarr-developers/geozarr-spec). The SWG's February 2026 roadmap targeted OGC Architecture Board review in summer 2026 [snippet]; the outcome is unconfirmed — [V1 roadmap](https://deploy-preview-6--geozarr.netlify.app/roadmap).
- The spec targets Zarr v3, but a December 2025 EOPF FAQ says Sentinel Zarr samples still used v2 with migration planned [snippet] — [EOPF FAQ](https://zarr.eopf.copernicus.eu/wp-content/uploads/2025/12/EOPF-Sentinel-Zarr-Samples_FAQ.pdf). I could not determine whether that migration has happened.
- NISAR context: ASF released PROVISIONAL datasets on 2026-07-20, with validated reprocessing expected in Q4 2026 [snippet] — [ASF NISAR availability](https://nisar-docs.asf.alaska.edu/availability-overview/). A third-party tool, openseppo, subsets NISAR RSLC from S3/HTTPS and converts GCOV to COG [snippet] — [openseppo docs](https://openseppo.readthedocs.io/en/latest/).

#### Time series handling, by tool

| Tool | Time series model | Source |
|---|---|---|
| MintPy | Network inversion of interferogram stacks to displacement time series | [README](https://github.com/insarlab/MintPy) |
| Dolphin | Phase linking on ministacks, then unwrapping | [#712](https://github.com/isce-framework/dolphin/issues/712) |
| LiCSBAS | Time series from LiCSAR portal interferograms | [README](https://github.com/yumorishita/LiCSBAS) |
| PyGMTSAR / InSAR.dev | Internal time series analysis; InSAR.dev packages SLCs as cloud-ready bursts in Zarr v3 | [README](https://github.com/AlexeyPechnikov/pygmtsar) |
| S1Tiling | Dated, filtered backscatter stacks on fixed MGRS tiles | [README](https://github.com/CNES/S1Tiling) |
| odc-stac / stackstac | Lazy xarray cube built from STAC items | [odc-stac](https://github.com/opendatacube/odc-stac) |
| TiTiler / titiler.xarray | Time selection per request on xarray datasets | [titiler-multidim #193](https://github.com/developmentseed/titiler-multidim/issues/193) |

### Inferences
- For a new backend, the lowest-risk path is to consume existing ARD (OPERA RTC-S1, DISP-S1, HyP3 products) first and only run processors when a product gap forces it.
- If you must run processing, containerise on Linux with conda-forge. ISCE2/ISCE3 have no Windows conda builds, and the install issues above suggest a bare pip path is not realistic for ISCE3.
- Build new InSAR time series around Dolphin plus MintPy, budget RAM per interferogram rather than per scene, and subset NISAR frames. The 50 GB per interferogram figure is a single user's run, so benchmark your own configuration.
- sarsen is the most natural RTC candidate for a Dask/xarray pipeline, but its beta status and recent memory fix mean you should test it against OPERA RTC before relying on it.
- Choose odc-stac over stackstac for new work. Treat InSAR.dev as promising but unproven, since I found no independent evaluation.
- The RTC benchmark suggests processor choice matters more for geolocation than radiometry, so geolocation QA deserves more attention than radiometric cross-checking. That benchmark used SNAP 8, so re-verify for SNAP 13/14.
- Avoid new Kerchunk investments. Plan for GeoZarr conventions to keep moving and pin the versions you depend on.

### Gaps
- No independent 2025-2026 head-to-head runtime or RAM benchmark across SNAP, ISCE3, sarsen and GAMMA was found.
- LiCSAR's dependence on GAMMA is my recollection and was not verified in this session; confirm before stating it.
- ISCE2 pain points could not be drawn from GitHub because issues are disabled. The STEP or other forums would need a separate pass.
- Exact Python support for esa_snappy on SNAP 13/14 was not confirmed. The S1 changelog for SNAP 14 was not read.
- Whether HyP3 RTC still uses GAMMA was not confirmed; the docs landing page does not say. Per-job credit costs were not retrieved.
- InSAR.dev maturity, licensing and adoption were not assessed. S1Tiling's own GitLab issue tracker was not reviewed.
- No SARscape or GAMMA price was found publicly.

## What are the state-of-the-art speckle, change detection, flood and deforestation algorithms in practical use, and which suit a hackathon?

### Takeaway
Operational systems favour simple statistics over dense time series (Bayesian, changepoint, CuSum, ensemble thresholding), and deep learning remains mostly a despeckling or research layer. For a hackathon, refined Lee or a multi-temporal filter, plus Otsu or log-ratio thresholding, or CuSum on a Sentinel-1 RTC stack, is realistic within a day.

### Cited Findings

#### Speckle filtering
- The Mullissa et al. Earth Engine ARD framework offers mono-temporal filters (boxcar, Lee, Gamma MAP, Refined Lee, Lee Sigma) and multi-temporal filters, requiring linear-scale input — [Mullissa et al. 2021](https://edepot.wur.nl/547171), [code](https://github.com/adugnag/gee_s1_ard). A Python port is `ee-s1-ard`, with defaults of Gamma MAP, kernel 7, and 10 images — [PyPI](https://pypi.org/project/ee-s1-ard/1.0.5/).
- Canty et al. (2020) derive an adaptive temporal filter (ATSF) as a by-product of sequential change detection and report that only the Quegan filter was comparable in visual quality — [Remote Sensing 12(15) 2454](https://mdpi.com/2072-4292/12/15/2454/xml).
- MERLIN is self-supervised, training from single SLC images by splitting real and imaginary parts, and accounts for sensor-specific spatial correlation — [MERLIN paper](https://arxiv.org/abs/2110.13148). SAR2SAR targets Sentinel-1 GRD, and needs only a single GRD at inference — [SAR2SAR](https://arxiv.org/pdf/2207.11095.pdf). The `deepdespeckling` package ships both — [package](https://awesome.ecosyste.ms/projects/github.com%2Fhi-paris%2Fdeepdespeckling).
- A 2026 preprint reports higher PSNR and SSIM than MERLIN, while MERLIN retains higher ENL, showing a fidelity versus smoothing trade-off [snippet] — [arXiv 2605.29088](https://arxiv.org/pdf/2605.29088).

#### Change detection
- Canty et al. (2019) implement a sequential omnibus likelihood-ratio test for equal complex Wishart covariance matrices on Sentinel-1 in Earth Engine, with p-values and a factorised test statistic, and provide Python and Docker code — [Remote Sensing 12(1) 46](https://www.mdpi.com/2072-4292/12/1/46).
- CuSum on dual-pol Sentinel-1 GRD was used for clear-cut monitoring — [Ruiz-Ramos et al. 2020](https://www.storre.stir.ac.uk/handle/1893/31760).

#### Deforestation
- In one comparison CuSum detected 504 ha against 348 ha for Global Forest Watch's tree cover loss product, and picked up low-intensity disturbance that GFW and RADD largely missed [snippet] — [Frontiers 2022](https://www.frontiersin.org/articles/10.3389/ffgc.2022.1018762).
- Ygorra et al. (2024) built a near-real-time CuSum with a 0.03 ha minimum mapping unit for tropical alerts — [Frontiers in Remote Sensing](https://frontiersin.org/articles/10.3389/frsen.2024.1416550/full).
- RADD alerts work at about 10 m but only in primary humid tropical forest, per the Global Forest Watch description **[check for updates]** — [GFW](https://www.globalforestwatch.org/blog/data/radd-radar-alerts).
- Bayesian online changepoint detection is the newest thread, with a 2026 ISPRS paper fusing Sentinel-1 and Sentinel-2 and comparing against VH-only BOCD and RADD over the Brazilian Amazon — [ISPRS Annals 2026](https://isprs-annals.copernicus.org/articles/XI-3-2026/507/2026/isprs-annals-XI-3-2026-507-2026.pdf).

#### Flood
- Copernicus GFM combines three independently developed algorithms (DLR, LIST, TU Wien) and takes the ensemble likelihood as the mean of the individual likelihoods, harmonised to 0-100 — [Krullikowski et al.](https://quarxiv.authorea.com/doi/full/10.36227/techrxiv.22688101.v1).
- The LIST algorithm uses change detection, with Otsu's method providing first-guess values for Gaussian class parameters — [GFM wiki](https://extwiki.eodc.eu/GFM/PDD/GFM_algorithms/LIST_algorithm).
- The TU Wien algorithm is datacube-based Bayesian inference, exploiting orbit repetition and pre-computed flood and non-flood probability parameters — [Remote Sensing 15(5) 1200](https://mdpi.com/2072-4292/15/5/1200). In a change detection comparison, Bayes showed the least sensitivity to parametrisation and best accuracy [snippet] — [Remote Sensing 14(15) 3673](https://mdpi.com/2072-4292/14/15/3673).
- PyGMTSAR includes a notebook example where correlation loss serves to identify flooding — [README](https://github.com/AlexeyPechnikov/pygmtsar).

### Inferences

| Task | Hackathon-suitable choice | Why | Avoid in a hackathon |
|---|---|---|---|
| Speckle | Refined Lee (GEE) or a multi-temporal filter on RTC stacks | Available off the shelf | Training a despeckling network; pretrained SAR2SAR is an acceptable stretch goal |
| Change | Log-ratio with Otsu, or CuSum on a VV/VH stack | Few lines of NumPy or xarray | Full Wishart omnibus unless using Canty's code |
| Flood | Otsu threshold with a HAND or permanent-water mask | Mirrors part of the LIST approach | Reproducing the full GFM ensemble |
| Deforestation | CuSum over a forest mask | Published recipes on GRD | RADD-style operational systems needing long calibration |

- Omnibus Wishart is viable if you reuse Canty's published Python and Docker code; it needs dual-pol stacks and care with assumed looks.

### Gaps
- No primary source was retrieved for log-ratio thresholding or the original Quegan filter; both are textbook methods but remain uncited here.
- No 2025-2026 head-to-head of MERLIN, SAR2SAR, Lee and refined Lee on Sentinel-1 was found.
- No operational benchmark comparing CuSum, omnibus and BOCD on a shared reference set was found.
- A 2026 SAR and deep learning deforestation review exists but its contents were not read — [GNEST](https://journal.gnest.org/system/files/2026-07/gnest_08268_accepted%20manuscript.pdf).
- Whether RADD's coverage has been extended recently needs checking; another source mentions temperate and boreal work [snippet] — [TIB](https://av.tib.eu/media/72421).

## How are uncertainty, confidence and quality flags typically represented?

### Takeaway
SAR products rarely deliver a true per-pixel error bar. In practice "uncertainty" means categorical masks, continuous quality proxies such as coherence, and geometry layers, with ensemble likelihood as the closest thing to calibrated confidence in thematic products.

### Cited Findings
- OPERA RTC-S1 static `mask` values: 0 valid, 1 shadow, 2 layover, 3 layover and shadow, 255 invalid. Static bands are `local_incidence_angle`, `incidence_angle`, `number_of_looks`, `rtc_anf_gamma0_to_beta0`, `rtc_anf_gamma0_to_sigma0` and `mask` — [Earth Engine catalog](https://developers.google.com/earth-engine/datasets/catalog/OPERA_RTC_L2_V1_S1_STATIC). A search summary of the same page gave different numbers; the table above is from reading the page directly. Confirm against the [product spec](https://asf.alaska.edu/wp-content/uploads/2023/10/OPERA-RTC-S1-ProductSpec-v1.0.3-D-108758-RevB-2024-03-21-URS324227.pdf).
- OPERA DISP-S1 layers in code: `displacement`, `short_wavelength_displacement`, `recommended_mask`, `connected_component_labels`, `temporal_coherence`, `estimated_phase_quality`, `persistent_scatterer_mask`, `shp_counts`, `water_mask`, `phase_similarity`, `timeseries_inversion_residuals` — [product_info.py](https://github.com/opera-adt/disp-s1/blob/main/src/disp_s1/product_info.py). The layer schema also carries a `keep_bits` field for each dataset — [product_info.py](https://github.com/opera-adt/disp-s1/blob/main/src/disp_s1/product_info.py).
- ASF hides pixels flagged low-quality at any time, based on metrics such as temporal coherence and phase similarity, and shows masked time series points as hollow dots — [ASF DISP FAQ](https://docs.asf.alaska.edu/datasets/disp_faq/). The FAQ does not describe per-pixel uncertainty or error estimates — [ASF DISP FAQ](https://docs.asf.alaska.edu/datasets/disp_faq/).
- OPERA cal/val treats pixels with average coherence of 0.7 or below as temporally decorrelated and removes them, alongside a water mask [snippet, read through a GitHub mirror] — [calval-DISP](https://gh.hhj520.top/OPERA-Cal-Val/calval-DISP).
- OPERA DISP layers separate correction fields (solid earth tides, ionospheric delay) from displacement — [ASF DISP FAQ](https://docs.asf.alaska.edu/datasets/disp_faq/).
- GFM aggregates algorithm uncertainty as a 0-100 ensemble likelihood — [Krullikowski et al.](https://quarxiv.authorea.com/doi/full/10.36227/techrxiv.22688101.v1). It also publishes an exclusion layer marking where no delineation was possible [snippet; page returned 404 on direct fetch] — [GFM output layers](https://extwiki.eodc.eu/GFM/PDD/GFMoutputLayers).
- Exclusion masks are necessary but over-reliance is itself a problem; a TU Wien thesis proposes a HAND-based prior to reduce false negatives [snippet] — [Tupas 2024](https://repositum.tuwien.at/bitstream/20.500.12708/209576/1/Tupas%20Mark%20Edwin%20-%202024%20-%20Improving%20flood%20monitoring%20capabilities%20using...pdf).
- The Canty omnibus test gives p-values, a natural per-pixel significance layer — [Canty et al. 2019](https://www.mdpi.com/2072-4292/12/1/46).
- CEOS ARD NRB per-pixel threshold items are a local incidence angle image, a mask image and an acquisition ID image for composites; scattering area, gamma-to-sigma ratio, ellipsoid incidence angle, noise power and per-pixel DEM are goals **[older, 2022]** — [Rosenqvist LPS22](https://earth.esa.int/living-planet-symposium-2022-presentations/27.05.Friday/Vienna/0830-1010/05_Rosenqvist_LPS22_B1.07.1_CARD4L-SAR.pdf).
- NRB products report gamma-nought, with sigma-nought recoverable through local incidence angle, and cannot be used for polarimetry or interferometry [snippet] — [CSIRO](https://research.csiro.au/cceo/gamma-processing-workflow-for-generating-ceos-ard-nrb-pfs-ver5-5-novasar-1-ard-products).
- The STAC SAR extension provides sensor-level fields such as `sar:looks_equivalent_number`, `sar:looks_range` and `sar:polarizations` — [STAC SAR extension](https://github.com/stac-extensions/sar).
- Xpublish supports categorical styling from CF-style `flag_values`, `flag_meanings` and `flag_colors` — [datacube guide](https://developmentseed.org/datacube-guide/latest/visualization/ecosystem-comparison.html).

### Inferences
- A practical schema for a backend: categorical quality as one uint8 band with documented values and CF `flag_values`/`flag_meanings` attributes, continuous confidence as a separate 0-100 or 0-1 band, geometry layers (LIA, number of looks) as static assets, and a recommended-use mask that applications can override.
- Keep masked pixels and expose them differently rather than deleting them. ASF's hollow-dot approach is a good UI precedent.
- Label coherence and likelihood as "quality proxy" or "model confidence", not as error bars, unless calibrated against reference data.
- In the STAC fields I read, quality lives at asset level rather than in `sar:` properties, so define bit meanings in asset metadata yourself.

### Gaps
- The DISP-S1 Product Specification and ATBD could not be read (the PDF did not extract as text), so exact bit encodings of `recommended_mask` and the formal uncertainty definition are unconfirmed.
- The current CEOS-ARD SAR PFS v1.2 was not read directly; its per-pixel uncertainty requirements are unconfirmed.
- GFM's exact output encodings need verification, since the page returned 404 directly.
- NISAR GCOV/GUNW quality layer conventions were not examined here.

## What is the current best-practice architecture for serving huge raster time series to a web map cheaply?

### Takeaway
The current default is object storage holding COGs or Zarr, a STAC catalogue, a stateless dynamic tiler (TiTiler) and a CDN, with pre-rendering limited to frozen, high-traffic layers. For a dense time series, keep COGs per date for the map path and add a Zarr or virtual store only for pixel time series and analysis queries.

### Cited Findings
- Development Seed's datacube guide says pre-rendered PNG pyramids are "increasingly an anti-pattern" because they lock in colormaps and add a pipeline to maintain, and that "dynamic tilers behind a CDN match the performance" of pre-rendered tiles. It recommends PMTiles only for one-shot visualisations that will never change — [datacube guide overview](https://developmentseed.org/datacube-guide/latest/visualization/overview.html). This is a vendor-authored view from the maintainers of TiTiler.
- TiTiler's docs give a counterpoint: static tiles will always be faster, and a cache in front of a dynamic tiler helps less because the same tile can be requested with different options. They also note the burden of managing many small files [snippet; page returned 404 on direct fetch] — [TiTiler dynamic tiling](https://developmentseed.org/titiler/dynamic_tiling).
- The guide's scale path is "a backend tile/query cache, a CDN, and a browser cache" — [datacube guide overview](https://developmentseed.org/datacube-guide/latest/visualization/overview.html).
- TiTiler is positioned for public slippy maps. Its endpoints are stateless (`?url=`), so "any worker serves any request", with Redis dataset-level caching and official Docker images plus Lambda/ECS CDK examples — [ecosystem comparison](https://developmentseed.org/datacube-guide/latest/visualization/ecosystem-comparison.html).
- Xpublish suits research access on irregular grids and EDR queries, but has a slow first request (Numba JIT warm-up), stateful replicas and no official images — [ecosystem comparison](https://developmentseed.org/datacube-guide/latest/visualization/ecosystem-comparison.html).
- TiTiler now exposes `/zarr/*` through titiler.xarray as a standard endpoint since 2.0 [snippet] — [titiler core API](https://developmentseed.org/datacube-guide/latest/visualization/titiler/apis/titiler-core.html). TiTiler 2.4.0 added an xarray dataset coordinate endpoint — [release](https://github.com/developmentseed/titiler/releases/tag/2.4.0).
- Time-series cost trap: rio-tiler's `XarrayReader.info()` took about 1.6 s per request over 17,228 time steps when no `sel` was supplied, against about 0 ms with a selected step. It was fixed upstream and adopted in titiler-multidim in October 2026 — [titiler-multidim #193](https://github.com/developmentseed/titiler-multidim/issues/193). Benchmarks for that app remain an open task — [#191](https://github.com/developmentseed/titiler-multidim/issues/191).
- Multiscale Zarr was a known gap, since overview group selection had to happen before opening the file — [titiler #1071](https://github.com/developmentseed/titiler/issues/1071), open since January 2025. A January 2026 GeoZarr SWG note says "Titiler is compliant" [snippet] — [SWG notes](https://hackmd.io/@briannapagan/geozarr-spec-swg). These sources conflict; test multiscale behaviour before relying on it.
- GDAL settings have direct cost impact. `GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR` avoids costly LIST requests, and `GDAL_HTTP_MERGE_CONSECUTIVE_RANGES=YES` should always be set — [TiTiler performance tuning](https://github.com/developmentseed/titiler/blob/main/docs/src/advanced/performance_tuning.md).
- GDAL COG defaults are BLOCKSIZE 512, COMPRESS LZW, OVERVIEWS AUTO, TILING_SCHEME CUSTOM and PREDICTOR NO. ZSTD and LERC variants are options. SPARSE_OK defaults to FALSE, with a warning that "most non-GDAL packages cannot read such files" — [GDAL COG driver](https://gdal.org/en/stable/drivers/raster/cog.html).
- The EOPF Sentinel Zarr Explorer is the leading public reference for Zarr-native serving, launched February 2026, using TiTiler-EOPF to compute visualisations on the fly from Zarr in object storage [snippet] — [Development Seed](https://developmentseed.org/blog/2026-02-13-eopf-explorer-launch), [EOX](https://eox.at/2026/02/visualizing-geozarr/).
- Backend-less options exist: Browzarr, GridLook, deck.gl-raster, and zarr-layer for MapLibre/Mapbox render Zarr in the browser. The guide no longer recommends @carbonplan/maps for new work — [datacube guide overview](https://developmentseed.org/datacube-guide/latest/visualization/overview.html).

### Inferences
Suggested low-cost reference architecture for a SAR time series:
1. **Storage:** per-date, per-tile COGs (`COMPRESS=ZSTD` or `LERC_ZSTD`, float predictor for dB or displacement, 512 blocks, overviews) in object storage, in the same region as compute.
2. **Catalogue:** STAC with the SAR extension; a static catalogue is enough for small collections, stac-fastapi once you need search.
3. **Map path:** stateless TiTiler on serverless or small containers, GDAL environment variables tuned, CDN in front with long TTLs. Keep the URL space small by whitelisting a few rescales and colormaps, which directly addresses the cache-hit concern TiTiler raises.
4. **Time slider:** always request one explicit date per tile. Never let a tile request touch the full time dimension, per the rio-tiler lesson.
5. **Point time series:** a separate endpoint backed by a time-chunked Zarr or Icechunk store, because reading one pixel across hundreds of COGs means hundreds of range requests. Chunk the analysis store along time and the map store along space.
6. **Pre-rendering** only for frozen, high-traffic layers such as a mean velocity map, possibly as PMTiles.

Sensible hedges:
- Prefer COG for the first version. Zarr tiling, GeoZarr and virtual GeoTIFF references are all still changing.
- Reserve pygeoapi for cases where OGC API compliance is a requirement.

### Gaps
- No published 2026 cost figures for a TiTiler + CDN deployment, and no measured CDN hit rate for a SAR time series, were found. Any dollar estimate would need modelling from current cloud price lists.
- No independent benchmark of COG versus Zarr tile latency for SAR time series was found. The datacube guide lists separate pages on chunking worst practices that were not read, and it gives no chunk-size figures in the pages reviewed.
- Lazycogs was seen only as a mention in a proposed README change and was not evaluated.
- Outcome of the GeoZarr OAB review and the EOPF Zarr v3 migration remain unconfirmed.
