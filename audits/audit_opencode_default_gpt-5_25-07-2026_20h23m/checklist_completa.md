# Checklist completa de auditoría — TASK-0007

Snapshot pre-remediación. Ejecutar cada acción en una tarea de remediación
asignada; esta lista no autoriza cambios ni marca hallazgos resueltos.

## Alta prioridad

| ID | Acción ejecutable | Evidencia de cierre requerida |
|---|---|---|
| SEC7-001 | Eliminar de CI la ruta histórica o parametrizar snapshot actual y congelarlo antes de remediar. | Gate de CI reproducible y hash del run. |
| OPS7-001 | Sustituir checksum histórico por manifiesto canónico versionado. | CI limpio sin dependencia de auditoría previa. |
| HARNESS7-001 | Validar marcador, frontmatter, plataforma, modo, skill y tools; escribir materialización atómicamente. | Tests negativos de agente vacío/stale/incorrecto. |
| HARNESS7-002 | Decidir soporte Codex; implementar adaptador y conformance o declararlo fuera de soporte. | Registro de decisión y `agents check`/conformance. |
| PERF7-001 | Añadir contrato GGUF versionado con SHA-256, bytes, origen, revisión, template y RAM. | Schema/checksum tests y rechazo de metadata incompleta. |
| PERF7-002 | Consultar presupuesto real del host/daemon y separar GO generable de host-ready. | Fixtures bajo/en/encima del margen y salida `NO-GO`. |
| PERF7-005 | Ejecutar benchmark real solo con GGUF autorizado; eliminar placeholders de baseline. | JSON con muestras, p50/p95, tokens/s, memoria y provenance. |
| UX7-001 | Migrar controladamente o marcar legacy los workspaces y añadir drift-check. | Diff de fixture/workspace y README con digest. |
| UX7-002 | Convertir instrucciones LAN en planned/blocked y dejar localhost como único ejemplo ejecutable. | Docs check y prueba de rechazo LAN. |

## Prioridad media

| ID | Acción ejecutable | Evidencia de cierre requerida |
|---|---|---|
| SEC7-002 | Crear lock hash-verificado y usar `--require-hashes`. | Instalación y CI con lock/SBOM. |
| SEC7-003 | Reparar modos de `.env` existentes y añadir sweep/restore seguro. | `stat` 0600 y test de backup/restore. |
| SEC7-004 | Definir egress mínimo o red interna y probar operación tras restricción. | Compose parseado y test de red. |
| SEC7-005 | Confinar path al root de modelos y rechazar symlink escape; auditar override. | Tests de path absoluto, symlink y traversal. |
| SEC7-006 | Ejecutar `pip-audit` en toolchain aislada reproducible y retener JSON. | Scanner exit 0 o vulnerabilidades gestionadas. |
| COD7-001 | Renderizar fixture y pasar `bash -n`/ShellCheck, con paths complejos. | ShellCheck exit 0 para output canónico. |
| OPS7-002 | Hacer cleanup bounded/idempotente tras readiness fallido y conservar logs. | Tests de timeout, unhealthy y retry. |
| OPS7-003 | Inspeccionar tar antes de extraer y validar staging completo. | Tests de rutas, symlinks, miembros y manifest. |
| HARNESS7-003 | Materializar permisos por ruta/comando y confirmación destructiva. | Comparación contrato-vs-output y negativos. |
| PERF7-003 | Registrar versión/revisión, digest y esquema de flags; probar compatibilidad. | Manifest y regresión por digest. |
| PERF7-004 | Diferenciar `starting`, `healthy`, `unhealthy` y diagnosticar temprano. | Lifecycle tests y salida no-cero. |
| PERF7-006 | Registrar workload/configuración efectiva y separar smoke de benchmark. | Artefacto auditable con tokens/concurrencia. |
| UX7-003 | Unificar contrato host/container y política de copia en todas las superficies. | Snapshot docs/manifest/Compose consistente. |
| UX7-004 | Documentar helpers reales o implementar CLI `start`. | Comandos extraídos de `--help` ejecutables. |

## Baja/condicional

| ID | Acción ejecutable | Evidencia de cierre requerida |
|---|---|---|
| SEC7-007 | Antes de LAN, implementar logs estructurados, origen, redacción, rotación y retención. | Prueba gateway/backend y runbook. |
| LEG7-001 | Antes de distribuir, crear `THIRD_PARTY_NOTICES` y provenance de runtime, presets y modelos. | Review legal, SBOM, licencias y fuentes oficiales. |

## Prerrequisitos no verificables aún

No ejecutar cierres de runtime, calidad, memoria, tokens/s, compatibilidad GGUF,
LAN o distribución hasta disponer de modelo autorizado y los gates definidos.
