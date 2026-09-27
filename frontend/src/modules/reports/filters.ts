/** Filtros de reportes que se eligen de un maestro: parámetro de la API y recurso a listar. */
import { assetsResource } from '@/modules/assets/api';
import { cashAccountsResource, expenseCategoriesResource } from '@/modules/commercial/api';
import { partiesResource, warehousesResource } from '@/modules/masterdata/api';
import { cropsResource, farmsResource } from '@/modules/production/api';

import type { ReportFilter } from './api';

export type FilterResource = {
  key: string;
  list: (p: object) => Promise<{ items: { id: string; name: string }[] }>;
};

export const FILTER_RESOURCES: Partial<
  Record<ReportFilter['kind'], { param: string; resource: FilterResource }>
> = {
  farm: { param: 'farm_id', resource: farmsResource },
  crop: { param: 'crop_id', resource: cropsResource },
  expense_category: { param: 'expense_category_id', resource: expenseCategoriesResource },
  party: { param: 'party_id', resource: partiesResource },
  asset: { param: 'asset_id', resource: assetsResource },
  warehouse: { param: 'warehouse_id', resource: warehousesResource },
  cash_account: { param: 'cash_account_id', resource: cashAccountsResource },
};
