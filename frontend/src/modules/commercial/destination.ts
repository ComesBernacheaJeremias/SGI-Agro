/** Destino de un gasto (ciclo, lote, establecimiento y/o activo). Vacío = estructura. */
export type Destination = {
  farm_id: string | null;
  plot_id: string | null;
  crop_cycle_id: string | null;
  asset_id: string | null;
};

export const emptyDestination = (): Destination => ({
  farm_id: null,
  plot_id: null,
  crop_cycle_id: null,
  asset_id: null,
});

type Named = { id: string; name: string } | null;
type DestinationOut = { farm: Named; plot: Named; crop_cycle: Named; asset: Named };

/** Destino guardado (con nombres) → valores del formulario. */
export const destinationValues = (d: DestinationOut): Destination => ({
  farm_id: d.farm?.id ?? null,
  plot_id: d.plot?.id ?? null,
  crop_cycle_id: d.crop_cycle?.id ?? null,
  asset_id: d.asset?.id ?? null,
});

/** Texto del destino de un gasto ya guardado. */
export function destinationText(d: DestinationOut): string {
  const place = d.crop_cycle?.name ?? d.plot?.name ?? d.farm?.name ?? 'Estructura';
  return d.asset ? `${place} · ${d.asset.name}` : place;
}
