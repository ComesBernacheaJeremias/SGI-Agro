import { ActionIcon, Tooltip } from '@mantine/core';
import { IconHelp } from '@tabler/icons-react';
import { Link, useLocation } from 'react-router-dom';

import { sectionForPath } from '@/modules/manual/content';

/** "?" de la barra: abre el manual en la sección de la pantalla actual. */
export function HelpButton() {
  const section = sectionForPath(useLocation().pathname);
  return (
    <Tooltip label="Ayuda de esta pantalla">
      <ActionIcon
        component={Link}
        to={section ? `/manual?seccion=${section}` : '/manual'}
        variant="subtle"
        color="gray"
        aria-label="Ayuda de esta pantalla"
      >
        <IconHelp size={20} />
      </ActionIcon>
    </Tooltip>
  );
}
