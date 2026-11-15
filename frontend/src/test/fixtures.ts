import type { Verdict } from '../api/client'

type Overrides = Omit<Partial<Verdict>, 'receipt'> & { receipt?: Partial<Verdict['receipt']> }

/** Veredicto de prueba con la forma de `contracts/verdicts.openapi.json`. */
export function makeVerdict(over: Overrides = {}): Verdict {
  const { receipt, ...rest } = over
  const base: Verdict = {
    id: '20260617_20260629',
    aoi: 'parral',
    series: 'T048A-F015',
    kind: 'consecutive',
    from_date: '2026-06-17',
    to_date: '2026-06-29',
    interval_days: 12,
    state: 'change_probable',
    cause: null,
    cause_label: null,
    summary: {
      detected: 'Entre 2026-06-17 y 2026-06-29 cambió la señal de radar en el 4.1% de la superficie observada.',
      does_not_prove: 'No identifica la causa; la explicación requiere otra fuente o verificación en campo.',
      missing: 'Falta contrastar con una fuente independiente.',
    },
    hypotheses: ['Hipótesis: secado del suelo o agua abierta (baja HH).'],
    evidence: {
      observed_fraction: 0.99,
      changed_fraction: 0.041,
      threshold_hh_db: 3,
      threshold_hv_db: 3,
      mean_change_hh_db: -0.4,
      mean_change_hv_db: -0.2,
      pixel_counts: {},
      signature_counts: {},
      optical: {
        text: 'Escena Sentinel-2 del 2026-06-18 con 3 % de nubes por tesela.',
        before: { status: 'none_in_window', radar_date: '2026-06-17', radar_acquired_at: null, scene: null },
        after: { status: 'none_in_window', radar_date: '2026-06-29', radar_acquired_at: null, scene: null },
      } as Verdict['evidence']['optical'],
      decision_rule: { min_observed_fraction: 0.5, min_changed_fraction: 0.05, calibrated: false },
      scene_shift: null,
      water: { text: 'Sin referencia OPERA DSWx-S1 a ±7 días.' } as Verdict['evidence']['water'],
    },
    layers: { state: '/tiles/state', change_hh: '/tiles/hh', change_hv: '/tiles/hv' },
    receipt: {
      data_kind: 'real',
      maturity: 'PROVISIONAL',
      series: 'T048A-F015',
      track: 48,
      direction: 'A',
      frame: 15,
      mode: '4005',
      polarization: 'DHDH',
      crid: 'P05023',
      granules: ['NISAR_L2_PR_GCOV_023_048_A_015', 'NISAR_L2_PR_GCOV_024_048_A_015'],
      spans_data_gap: false,
      notices: ['Datos PROVISIONAL: se reprocesarán a VALIDATED en 2027.'],
      excluded_passes: [],
      quality: {} as Verdict['receipt']['quality'],
      freshness: {
        reference_date: '2026-11-12',
        published_at_basis: 'cmr_updated',
        before: {
          date: '2026-06-17',
          granule: 'NISAR_L2_PR_GCOV_023_048_A_015',
          acquired_at: '2026-06-17T12:24:34Z',
          published_at: '2026-06-19T04:24:34Z',
          publication_latency_hours: 40,
          latency_status: 'available',
          age_days: 148,
        },
        after: {
          date: '2026-06-29',
          granule: 'NISAR_L2_PR_GCOV_024_048_A_015',
          acquired_at: null,
          published_at: null,
          publication_latency_hours: null,
          latency_status: 'catalog_unavailable',
          age_days: 136,
        },
      },
    },
  }
  return { ...base, ...rest, receipt: { ...base.receipt, ...receipt } }
}
