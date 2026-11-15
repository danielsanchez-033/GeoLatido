# GeoLatido

**Listening to the Earth's surface heartbeat with NISAR radar.**
GeoLatido turns NASA–ISRO NISAR radar data into clear, auditable answers about how the land surface changes:
**what changed, what was not detected, and what cannot be known** — anywhere in the world.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
![NASA Space Apps Challenge 2026](https://img.shields.io/badge/NASA%20Space%20Apps-2026-0b3d91)
![Data: NISAR L-band](https://img.shields.io/badge/data-NISAR%20L--band-6b4fbb)
![Languages: ES | EN](https://img.shields.io/badge/UI-Espa%C3%B1ol%20%7C%20English-informational)

> 🇲🇽 **Resumen en español.** GeoLatido nació en Hidalgo del Parral, Chihuahua, por la curiosidad de entender el pulso
> de la Tierra. Convierte el radar NISAR (NASA–ISRO) en veredictos que cualquiera puede leer: qué cambió, qué no se
> detectó y qué no se puede saber, con cada cifra respaldada por sus datos. **Guía de uso e instalación:
> [docs/GUIA.md](docs/GUIA.md).**

---

## Contents

- [The challenge](#the-challenge)
- [Our solution](#our-solution)
- [Key findings](#key-findings)
- [Features](#features)
- [Study area](#study-area)
- [How to run it](#how-to-run-it)
- [Architecture](#architecture)
- [Data and credits](#data-and-credits)
- [Team](#team)
- [Use of AI](#use-of-ai)
- [License](#license)

## The challenge

NASA Space Apps Challenge 2026 — **NISAR (NASA–ISRO Synthetic Aperture Radar)**: build an interactive application that
tracks and visualizes changes on the Earth's surface over time with NISAR data, makes radar accessible to a broad
audience, and turns complex observations into actionable information.

A point-by-point checklist of every challenge requirement and where GeoLatido covers it is in
[docs/REQUISITOS.md](docs/REQUISITOS.md).

## Our solution

Radar images are hard to read: bright and dark pixels mean roughness, moisture and structure, not colour. GeoLatido
compares NISAR acquisitions of the same orbit and gives every pair of dates a **verdict in three states**:

| State | Meaning |
|---|---|
| **Probable change** | The radar signal changed more than its own noise over enough of the observed area. |
| **No detectable change** | The radar saw the area and found nothing above the threshold. It does not prove nothing changed. |
| **Not observable** | The radar could not measure (no pass, missing data, terrain layover/shadow) — and it says why. |

Every verdict comes with its receipt (granules, thresholds, noise, scene-wide shifts), plain-language hypotheses about
the cause, and what it does **not** prove. No threshold is presented as calibrated when it is not.

## Key findings

Full report with figures, hypotheses, polarization analysis and future applications:
**[docs/HALLAZGOS.md](docs/HALLAZGOS.md)**.

- **Hidalgo del Parral (real NISAR data, 18 dates, Jun–Oct 2026):** 2 of 16 consecutive pairs show probable change
  (16–28 Aug, 5.2 %; 28 Aug–9 Sep, 9.6 %), in the middle of the monsoon season. The 1 July 2026 flash flood was **not
  observable**: no satellite pass happened while water was on the streets.
- **Polarizations:** in 16 of 16 pairs the whole scene brightened or darkened in the same direction in HH and HV, always
  more in HH (1.18 dB vs 0.74 dB on average): HH responds more to soil moisture, HV is steadier and helps isolate local
  change.
- **Subsidence (NISAR GUNW interferograms):** in eastern Mexico City, 24 % of the area sinks at least 83 mm/yr faster
  than the rest, reaching ~186 mm/yr near Nezahualcóyotl and the airport, while Ciudad Universitaria is stable — in line
  with published subsidence. The phase sign was verified against this known case before use.
- **L-band vs C-band:** NISAR saw more water than OPERA DSWx-S1 (Sentinel-1); reported as a disagreement between
  methods, not as an error.

## Features

- **Interactive change map** — verdict state layer, HH and HV change in dB, 1 km cells, per-pixel time series, 3D globe.
- **Comparator** — swipe between optical Sentinel-2 *before/after*, HH change, HV change or subsidence on each side.
- **Anywhere on Earth** — search any city: GeoLatido finds the NISAR series with HH and HV and processes its latest four
  dates **online, in memory, without storing granules** (~2–3 min for a 0.3° area). A **Regenerate** button refreshes
  them with the newest acquisitions.
- **Subsidence** — NISAR GUNW unwrapped phase, ionosphere-corrected and stacked, in mm/yr relative to the area.
- **Vegetation and forest** — HV-dominant signatures read as vegetation growth or loss (harvest, logging, fire).
- **Time series** — pass timeline, change-evolution chart, 12-day pairs and full-window comparisons, multi-year trend
  analysis in the *Research* tab.
- **Stories with evidence** — each area gets a playable story on the map with cited events (USGS, GDACS, Copernicus EMS,
  NASA EONET, NASA Global Landslide Catalog, NOAA IBTrACS).
- **For everyone** — Spanish and English, WCAG 2 AA checked with axe-core, plain-language findings, a *Radar & science*
  explainer (what SAR measures, polarizations, hypotheses, future applications). No account needed to see anything.

## Study area

**Hidalgo del Parral, Chihuahua, Mexico** — the team's home town: a semi-arid mining city with summer monsoon rains,
tailings, rain-fed farming and urban streams that overflow. Two full NISAR series cover it (T048 ascending and T171
descending). The architecture works for any place: the same app processes any city worldwide on demand.

## How to run it

Requirements: [Docker](https://www.docker.com/) with Compose.

```bash
git clone https://github.com/danielsanchez-033/GeoLatido.git
cd GeoLatido
docker compose up --build
```

- App: <http://localhost:3000>
- API: <http://localhost:8080> (`/api/verdicts/docs`, `/api/catalog/docs`, `/api/research/docs`)

A fresh clone runs with **synthetic data** (clearly labelled in the UI) so it works offline. To read **real NISAR data**,
create a free [NASA Earthdata](https://urs.earthdata.nasa.gov/) token, copy `.env.example` to `.env` and set
`EARTHDATA_TOKEN`. Step-by-step instructions, including processing Parral's full series, are in
**[docs/GUIA.md](docs/GUIA.md)**. Deployment notes: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Architecture

Independent services that talk over HTTP and published contracts ([contracts/](contracts/)):

| Service | Role |
|---|---|
| `catalog` | NISAR passes and series from NASA CMR, timelines, optical and OPERA references |
| `ingest` | Reads only the area of interest from NISAR GCOV granules over HTTPS |
| `processor` | Change detection (HH/HV), quality control, terrain masks, subsidence from GUNW, Cloud-Optimized GeoTIFFs |
| `online` | On-demand processing of any searched place, in memory |
| `verdicts` | Turns artifacts into verdicts, events, search and exports |
| `research` | From a question to a story with evidence and cited events |
| `auth` | Optional accounts to publish and rate community stories |
| `tiles` + `gateway` | TiTiler map tiles and the nginx API gateway |
| `frontend` | React + MapLibre GL web app |

More: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SAR_PROCESSING.md](docs/SAR_PROCESSING.md),
[docs/API.md](docs/API.md), specifications in [specs/](specs/README.md).

## Data and credits

| Data | Provider | Use |
|---|---|---|
| NISAR L2 GCOV (HH, HV) and L2 GUNW | NASA/JPL and ISRO; distributed by ASF DAAC (NASA Earthdata) | Change verdicts, subsidence |
| OPERA DSWx-S1 | NASA/JPL OPERA; PO.DAAC | Water cross-check (C-band) |
| Copernicus Sentinel-2 L2A | ESA / European Commission, via Element 84 Earth Search | Optical before/after |
| Sentinel-2 cloudless 2016 | EOX IT Services (CC BY 4.0) | Base map |
| OpenStreetMap / Nominatim | OpenStreetMap contributors (ODbL) | Streets and place search |
| Copernicus DEM GLO-30 | ESA / Airbus, via AWS Open Data | Terrain, layover and shadow |
| USGS ComCat, GDACS, Copernicus EMS, NASA EONET, NASA GLC, NOAA IBTrACS, INEGI | Various | Event context |

Full credits in [NOTICE](NOTICE) and [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md). What data the app collects:
[docs/PRIVACIDAD.md](docs/PRIVACIDAD.md).

## Team

**GeoLatido** — Hidalgo del Parral, Chihuahua, Mexico.

- Daniel Peña
- Alan Flores
- Elvin Sanchez
- Juan Daniel Sanchez
- Homero Haros

How we work (spec-driven development, roles and conventions): [AGENTS.md](AGENTS.md),
[CONTRIBUTING.md](CONTRIBUTING.md), decisions and verified facts in [MEMORY.md](MEMORY.md).

## Use of AI

Parts of the code, documentation and analysis were written with the help of AI coding assistants (Claude Code). Every
figure reported comes from the project's own pipeline and real data, and was checked by the team.

## License

Copyright 2026 GeoLatido contributors. Released under the [Apache License 2.0](LICENSE). Data keep the licence of their
source; credits in [NOTICE](NOTICE) must be preserved when redistributing.
