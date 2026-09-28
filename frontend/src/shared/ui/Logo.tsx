import logoOnDark from '@/assets/logo-horizontal-oscuro.svg';
import logoOnLight from '@/assets/logo-horizontal-claro.svg';

type Props = {
  /** Fondo sobre el que va: cambia el color de las parcelas y del texto */
  on: 'dark' | 'light';
  height: number;
};

/** Logo horizontal de SGI Agro (se genera en docs/assets/marca, ver Marca.md). */
export function Logo({ on, height }: Props) {
  return (
    <img
      src={on === 'dark' ? logoOnDark : logoOnLight}
      alt="SGI Agro"
      height={height}
      style={{ display: 'block', width: 'auto' }}
    />
  );
}
