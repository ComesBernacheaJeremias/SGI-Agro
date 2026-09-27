import {
  Accordion,
  Anchor,
  Box,
  Button,
  Container,
  Group,
  List,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { IconArrowLeft, IconBulb, IconSearch } from '@tabler/icons-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useSession } from '@/app/auth/session';

import { searchManual } from './content';

/** Manual de uso: página pública del sistema (/manual), también sin iniciar sesión. */
export function ManualPage() {
  const session = useSession();
  const [query, setQuery] = useState('');
  const sections = searchManual(query);
  const searching = query.trim() !== '';

  return (
    <Box bg="var(--mantine-color-body)" mih="100vh">
      <Container size="sm" py="lg">
        <Group justify="space-between" mb="md">
          <Text fw={700} c="green.8">
            SGI Agro
          </Text>
          <Button
            component={Link}
            to={session.status === 'authenticated' ? '/' : '/login'}
            variant="subtle"
            size="xs"
            leftSection={<IconArrowLeft size={14} />}
          >
            {session.status === 'authenticated' ? 'Volver al sistema' : 'Ir a entrar'}
          </Button>
        </Group>

        <Title order={1} mb={4}>
          ¿Cómo hago…?
        </Title>
        <Text c="dimmed" mb="md">
          Buscá lo que querés hacer o tocá una pregunta.
        </Text>
        <TextInput
          placeholder="Ej.: cargar una venta, cosecha, excel…"
          leftSection={<IconSearch size={16} />}
          value={query}
          onChange={(e) => setQuery(e.currentTarget.value)}
          size="md"
          mb="lg"
        />

        {sections.length === 0 && (
          <Text c="dimmed">No encontramos nada con esas palabras. Probá con otras.</Text>
        )}

        <Stack gap="xl">
          {sections.map((section) => (
            <div key={section.id} id={section.id}>
              <Title order={3} mb="xs">
                {section.title}
              </Title>
              <Accordion
                variant="separated"
                multiple
                // Al buscar se abren los resultados; si no, todo cerrado
                key={searching ? `s-${query}` : 'all'}
                defaultValue={searching ? section.topics.map((t) => t.question) : []}
              >
                {section.topics.map((topic) => (
                  <Accordion.Item key={topic.question} value={topic.question}>
                    <Accordion.Control>
                      <Text fw={500}>{topic.question}</Text>
                    </Accordion.Control>
                    <Accordion.Panel>
                      <List type="ordered" spacing={6}>
                        {topic.steps.map((step) => (
                          <List.Item key={step}>{step}</List.Item>
                        ))}
                      </List>
                      {topic.tip && (
                        <Group gap={6} mt="sm" wrap="nowrap" align="flex-start">
                          <IconBulb size={16} color="var(--mantine-color-yellow-7)" />
                          <Text size="sm" c="dimmed">
                            {topic.tip}
                          </Text>
                        </Group>
                      )}
                    </Accordion.Panel>
                  </Accordion.Item>
                ))}
              </Accordion>
            </div>
          ))}
        </Stack>

        <Text size="sm" c="dimmed" mt="xl">
          Reglas que conviene saber: las fechas son dd/mm/aaaa; nada se borra, se anula; todo cambio
          queda en el historial; un cultivo cerrado ya no cambia (si hay que corregirlo, pedíselo a
          soporte).{' '}
          <Anchor
            component={Link}
            to="/login"
            size="sm"
            hidden={session.status === 'authenticated'}
          >
            Entrar al sistema
          </Anchor>
        </Text>
      </Container>
    </Box>
  );
}
