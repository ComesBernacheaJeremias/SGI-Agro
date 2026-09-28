import {
  Alert,
  Badge,
  Button,
  FileInput,
  Group,
  Loader,
  Paper,
  Stack,
  Table,
  Tabs,
  Text,
} from '@mantine/core';
import { useQueryClient } from '@tanstack/react-query';
import { IconCheck, IconFileSpreadsheet } from '@tabler/icons-react';
import { useState } from 'react';

import { confirmAction, notifyError, notifySuccess } from '@/shared/ui/feedback';
import { PageHeader } from '@/shared/ui/PageHeader';

import {
  confirmImport,
  downloadTemplate,
  type ImportInfo,
  type ImportResult,
  previewImport,
  useImports,
} from './api';

/** Una importación: plantilla → subir → revisar (vista previa) → importar (todo o nada). */
function ImportPanel({ info }: { info: ImportInfo }) {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState<'preview' | 'confirm' | 'template' | null>(null);

  async function run(action: 'preview' | 'confirm' | 'template', fn: () => Promise<void>) {
    setBusy(action);
    try {
      await fn();
    } catch (err) {
      notifyError(err);
    } finally {
      setBusy(null);
    }
  }

  const preview = () =>
    run('preview', async () => {
      if (file) setResult(await previewImport(info.key, file));
    });

  const confirm = () =>
    run('confirm', async () => {
      if (!file || !result) return;
      const ok = await confirmAction({
        message: `Se van a importar ${result.valid} filas de "${info.title}".`,
        confirmLabel: 'Importar',
      });
      if (!ok) return;
      const done = await confirmImport(info.key, file);
      setResult(done);
      if (done.committed) {
        notifySuccess(`Importación terminada: ${done.valid} filas.`);
        setFile(null);
        await queryClient.invalidateQueries();
      }
    });

  const ready = result !== null && result.errors.length === 0 && !result.committed;

  return (
    <Stack>
      <Text c="dimmed">{info.description}</Text>
      <Paper withBorder p="sm">
        <Text fw={600} size="sm" mb="xs">
          1. Descargá la plantilla y completala (una fila por registro)
        </Text>
        <Table verticalSpacing={2} fz="sm" mb="sm">
          <Table.Tbody>
            {info.columns.map((c) => (
              <Table.Tr key={c.key}>
                <Table.Td w={200}>
                  {c.label}
                  {c.required && (
                    <Text span c="red">
                      {' '}
                      *
                    </Text>
                  )}
                </Table.Td>
                <Table.Td c="dimmed">
                  {c.help}
                  {c.example && ` Ej.: ${c.example}`}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        <Button
          loading={busy === 'template'}
          onClick={() => run('template', () => downloadTemplate(info.key))}
        >
          Descargar plantilla
        </Button>
      </Paper>

      <Paper withBorder p="sm">
        <Text fw={600} size="sm" mb="xs">
          2. Subí el archivo y revisalo (todavía no se guarda nada)
        </Text>
        <Group align="flex-end">
          <FileInput
            placeholder="Elegí el Excel (.xlsx)"
            accept=".xlsx"
            leftSection={<IconFileSpreadsheet size={16} />}
            value={file}
            onChange={(f) => {
              setFile(f);
              setResult(null);
            }}
            clearable
            w={320}
          />
          <Button variant="default" disabled={!file} loading={busy === 'preview'} onClick={preview}>
            Revisar
          </Button>
        </Group>
      </Paper>

      {result && (
        <Paper withBorder p="sm">
          <Text fw={600} size="sm" mb="xs">
            3. Resultado
          </Text>
          {result.committed ? (
            <Alert color="green" icon={<IconCheck size={16} />}>
              Se importaron {result.valid} filas.
            </Alert>
          ) : result.errors.length === 0 ? (
            <Alert color="green">
              Las {result.total} filas están bien. Tocá “Importar” para guardarlas.
            </Alert>
          ) : (
            <Alert color="yellow">
              {result.valid} de {result.total} filas están bien; corregí las {result.errors.length}{' '}
              con error en el Excel y volvé a revisar. No se importa nada hasta que estén todas
              bien.
            </Alert>
          )}
          {result.errors.length > 0 && (
            <Table mt="sm" verticalSpacing={4} fz="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th w={80}>Fila</Table.Th>
                  <Table.Th>Error</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {result.errors.map((e, i) => (
                  <Table.Tr key={`${e.row}-${i}`}>
                    <Table.Td>
                      <Badge variant="light" color="red">
                        {e.row}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{e.message}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
          {ready && (
            <Button mt="sm" loading={busy === 'confirm'} onClick={confirm}>
              Importar {result.valid} filas
            </Button>
          )}
        </Paper>
      )}
    </Stack>
  );
}

/** Importar datos desde Excel (carga inicial). Solo aparecen las que el usuario puede hacer. */
export function ImportsPage() {
  const { data: imports, isLoading } = useImports();
  return (
    <>
      <PageHeader
        title="Importar datos"
        subtitle="Orden sugerido: productos y clientes/proveedores primero; después stock inicial y saldos."
      />
      {isLoading && <Loader />}
      {imports?.length === 0 && <Text c="dimmed">No tenés importaciones disponibles.</Text>}
      {imports?.[0] && (
        <Tabs defaultValue={imports[0].key} keepMounted={false}>
          <Tabs.List mb="md">
            {imports.map((i) => (
              <Tabs.Tab key={i.key} value={i.key}>
                {i.title}
              </Tabs.Tab>
            ))}
          </Tabs.List>
          {imports.map((i) => (
            <Tabs.Panel key={i.key} value={i.key}>
              <ImportPanel info={i} />
            </Tabs.Panel>
          ))}
        </Tabs>
      )}
    </>
  );
}
