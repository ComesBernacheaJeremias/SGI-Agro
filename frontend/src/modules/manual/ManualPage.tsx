import {
  Accordion,
  Alert,
  Anchor,
  Button,
  Container,
  CopyButton,
  Group,
  List,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconBulb, IconSearch } from '@tabler/icons-react';
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { ACTIONS, actionUrl } from '@/app/actions';
import { useSession } from '@/app/auth/session';
import { Logo } from '@/shared/ui/Logo';

import { MANUAL, type ManualTopic, searchManual } from './content';
import classes from './ManualPage.module.css';

const ACCORDION_CLASSES = { item: classes.item, label: classes.label, control: classes.control };

/** Dirección del sistema (la misma desde la que se abrió el manual) con botón para copiarla. */
function SystemAddress() {
  const address = window.location.origin;
  return (
    <Group gap="xs" my="xs" wrap="nowrap">
      <span className={classes.address}>{address}</span>
      <CopyButton value={address}>
        {({ copied, copy }) => (
          <Button size="xs" variant="default" onClick={copy}>
            {copied ? 'Copiada' : 'Copiar'}
          </Button>
        )}
      </CopyButton>
    </Group>
  );
}

function TopicBody({ topic }: { topic: ManualTopic }) {
  // Un solo paso, o pasos que no son una secuencia: sin numerar
  const single = topic.steps.length === 1;
  return (
    <Stack gap="sm">
      {single ? (
        <Text>{topic.steps[0]}</Text>
      ) : (
        <List type={topic.unordered ? 'unordered' : 'ordered'} spacing={6}>
          {topic.steps.map((step) => (
            <List.Item key={step}>{step}</List.Item>
          ))}
        </List>
      )}
      {topic.showAddress && <SystemAddress />}
      {topic.bullets && (
        <List spacing={4} withPadding>
          {topic.bullets.map((b) => (
            <List.Item key={b}>{b}</List.Item>
          ))}
        </List>
      )}
      {topic.warning && (
        <Alert color="yellow" variant="light" p="xs">
          <Text size="sm">{topic.warning}</Text>
        </Alert>
      )}
      {topic.tip && (
        <Group gap={6} wrap="nowrap" align="flex-start">
          <IconBulb size={16} color="var(--mantine-color-dimmed)" style={{ flexShrink: 0 }} />
          <Text size="sm" c="dimmed">
            {topic.tip}
          </Text>
        </Group>
      )}
      {topic.action && (
        <Button
          component={Link}
          to={actionUrl(topic.action)}
          variant="light"
          size="xs"
          w="fit-content"
        >
          {ACTIONS[topic.action].button}
        </Button>
      )}
    </Stack>
  );
}

/**
 * Manual de uso: página pública del sistema (/manual), también sin iniciar sesión.
 * `?seccion=campo` muestra solo esa sección (el "?" de la barra lleva a la de cada pantalla).
 */
export function ManualPage() {
  const session = useSession();
  const loggedIn = session.status === 'authenticated';
  const [params, setParams] = useSearchParams();
  const scoped = MANUAL.find((s) => s.id === params.get('seccion'));
  const [query, setQuery] = useState('');
  const sections = searchManual(query, scoped ? [scoped] : MANUAL);
  const searching = query.trim() !== '';

  return (
    <div className={classes.page}>
      <Container size="sm" py="lg">
        <Group justify="space-between" mb="lg">
          <Logo on="light" height={28} />
          <Button component={Link} to={loggedIn ? '/' : '/login'} variant="default" size="xs">
            {loggedIn ? 'Volver al sistema' : 'Entrar'}
          </Button>
        </Group>

        <Title order={1} mb={4}>
          ¿Cómo hago…?
        </Title>
        <Text c="dimmed" mb="md">
          Buscá lo que querés hacer, con tus palabras, o elegí un tema.
        </Text>
        <TextInput
          placeholder="Ej.: fumigación, remito, gasoil, cosecha…"
          leftSection={<IconSearch size={16} />}
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
          size="md"
          mb="lg"
        />

        {scoped && (
          <Text size="sm" mb="md">
            Mostrando: {scoped.title}.{' '}
            <Anchor component="button" size="sm" onClick={() => setParams({}, { replace: true })}>
              Ver todo el manual
            </Anchor>
          </Text>
        )}

        {sections.length === 0 && (
          <Text c="dimmed">No encontramos nada con esas palabras. Probá con otras.</Text>
        )}

        <Stack gap="xl">
          {sections.map((section) => (
            <div key={section.id} id={section.id}>
              <Title order={3} mb="xs" className={classes.sectionTitle}>
                {section.title}
              </Title>
              <Accordion
                multiple
                chevronPosition="right"
                classNames={ACCORDION_CLASSES}
                // Al buscar se abren los resultados; si no, todo cerrado
                key={searching ? `s-${query}` : 'all'}
                defaultValue={searching ? section.topics.map((t) => t.title) : []}
              >
                {section.topics.map((topic) => (
                  <Accordion.Item key={topic.title} value={topic.title}>
                    <Accordion.Control>{topic.title}</Accordion.Control>
                    <Accordion.Panel>
                      <TopicBody topic={topic} />
                    </Accordion.Panel>
                  </Accordion.Item>
                ))}
              </Accordion>
            </div>
          ))}
        </Stack>

        <Text size="sm" c="dimmed" mt="xl">
          Conviene saber: las fechas son dd/mm/aaaa; nada se borra, se anula; todo cambio queda en
          el historial; un cultivo finalizado ya no cambia (si hay que corregirlo, pedíselo a
          soporte).
        </Text>
      </Container>
    </div>
  );
}
