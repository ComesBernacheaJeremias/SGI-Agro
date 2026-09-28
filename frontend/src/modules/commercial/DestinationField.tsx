import { Select } from '@mantine/core';

import { assetsResource } from '@/modules/assets/api';
import { useActiveList } from '@/modules/masterdata/api';
import { farmsResource, plotsResource, useCycles } from '@/modules/production/api';

import type { Destination } from './destination';

/** Valor del desplegable: el destino más específico ("cycle:<id>", "plot:<id>", "farm:<id>"). */
function placeKey(d: Destination): string | null {
  if (d.crop_cycle_id) return `cycle:${d.crop_cycle_id}`;
  if (d.plot_id) return `plot:${d.plot_id}`;
  if (d.farm_id) return `farm:${d.farm_id}`;
  return null;
}

function fromPlaceKey(key: string | null, assetId: string | null | undefined): Destination {
  const [kind, id] = key ? key.split(':') : [null, null];
  return {
    crop_cycle_id: kind === 'cycle' ? id : null,
    plot_id: kind === 'plot' ? id : null,
    farm_id: kind === 'farm' ? id : null,
    asset_id: assetId ?? null,
  };
}

type Props = {
  value: Destination;
  onChange: (value: Destination) => void;
  disabled?: boolean;
};

/**
 * A qué se imputa un gasto: ciclo, lote o establecimiento (el backend completa hacia arriba)
 * y, opcional, un activo. Vacío = gasto de estructura.
 */
export function DestinationField({ value, onChange, disabled }: Props) {
  const { data: cycles } = useCycles({ status: 'active', page_size: 200 });
  const { data: plots = [] } = useActiveList(plotsResource);
  const { data: farms = [] } = useActiveList(farmsResource);
  const { data: assets = [] } = useActiveList(assetsResource);

  const current = placeKey(value);
  const cycleItems = (cycles?.items ?? []).map((c) => ({
    value: `cycle:${c.id}`,
    label: c.name,
  }));
  // Un ciclo finalizado no aparece en la lista, pero si ya estaba cargado se muestra igual
  if (value.crop_cycle_id && !cycleItems.some((i) => i.value === current)) {
    cycleItems.push({ value: current as string, label: 'Cultivo finalizado' });
  }
  const data = [
    { group: 'Cultivos en curso', items: cycleItems },
    {
      group: 'Lotes',
      items: plots.map((p) => ({ value: `plot:${p.id}`, label: `${p.farm.name} · ${p.name}` })),
    },
    {
      group: 'Establecimientos',
      items: farms.map((f) => ({ value: `farm:${f.id}`, label: f.name })),
    },
  ];

  return (
    <>
      <Select
        label="Destino"
        placeholder="Estructura (sin destino)"
        data={data}
        value={current}
        onChange={(key) => onChange(fromPlaceKey(key, value.asset_id))}
        searchable
        clearable
        disabled={disabled}
        style={{ flex: '1 1 200px' }}
      />
      <Select
        label="Activo"
        placeholder="—"
        data={assets.map((a) => ({ value: a.id, label: a.name }))}
        value={value.asset_id ?? null}
        onChange={(asset_id) => onChange({ ...value, asset_id })}
        searchable
        clearable
        disabled={disabled}
        style={{ flex: '1 1 140px' }}
      />
    </>
  );
}
