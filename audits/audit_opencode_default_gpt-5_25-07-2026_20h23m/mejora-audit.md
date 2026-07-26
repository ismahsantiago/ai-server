# Mejora del sistema de auditoría — TASK-0007

Este registro solo clasifica la cobertura normativa de los 25 hallazgos del
run fresco. No modifica `audits/standards/`, `.pm-harness/` ni producto.

## Hallazgos cubiertos por normas existentes

| Hallazgos | Destino normativo | Disposición |
|---|---|---|
| SEC7-002, SEC7-006 | `audits/standards/SECURITY.md:STD-SEC-005` | Aplicar lock hash-verificado y scanner reproducible. |
| SEC7-003 | `SECURITY.md:STD-SEC-001` | Mantener 0600 y probar outputs existentes. |
| SEC7-004, SEC7-007 | `SECURITY.md:STD-SEC-002` y `STD-SEC-006` | Egress y logs son prerequisitos de LAN/least privilege. |
| SEC7-005 | `SECURITY.md:STD-SEC-003` | Validación de path y symlink. |
| LEG7-001 | `audits/standards/LEGAL.md:STD-LEG-001` | Notices y provenance antes de distribución. |
| COD7-001 | `CODE.md:STD-COD-002`; `OPS.md:STD-OPS-005` | ShellCheck del output renderizado dentro de CI. |
| OPS7-001 | `OPS.md:STD-OPS-005`; `GATES.md` Gate 1 | CI reproducible y sin dependencia histórica. |
| OPS7-002 | `OPS.md:STD-OPS-006/007`; `GATES.md` Gate 2 | Cleanup, diagnóstico y recuperación bounded. |
| OPS7-003 | `CODE.md:STD-COD-003`; `OPS.md:STD-OPS-007` | Restore seguro y validación semántica en staging. |
| HARNESS7-001 | `HARNESS.md:STD-ARN-003/004` | Conformance de contrato y materialización. |
| HARNESS7-002 | `HARNESS.md:STD-ARN-001/002/004` | Adaptador y conformance por host soportado. |
| HARNESS7-003 | `HARNESS.md:STD-ARN-003` | Permisos por ruta/comando y confirmación. |
| PERF7-001, PERF7-002 | `PERFORMANCE.md:STD-PERF-002` | Contrato GGUF y factibilidad real del host. |
| PERF7-003 | `PERFORMANCE.md:STD-PERF-005` | Digest, versión, flags y regresión. |
| PERF7-004 | `PERFORMANCE.md:STD-PERF-004` | Estados de readiness y timeout. |
| PERF7-005, PERF7-006 | `PERFORMANCE.md:STD-PERF-003`; `OPS.md:STD-OPS-006` | Benchmark medido y evidencia reproducible. |
| UX7-001 | `CODE.md:STD-COD-004` | Drift-check y fixtures. |
| UX7-002 | `PRODUCT.md:STD-PR-001/002` | Claims y estados planned/blocked veraces. |
| UX7-003 | `DESIGN.md:STD-UX-002`; `OPS.md:STD-OPS-001` | Contrato único de modelo. |
| UX7-004 | `PRODUCT.md:STD-PR-001` | Ejemplos compatibles con `--help`. |

## Hallazgos que requieren mejora de estándar o gate

`SEC7-001` y `OPS7-001` están cubiertos en intención por Gate 1 y la auditoría
periódica, pero requieren una mejora explícita del gate para prohibir rutas de
auditoría históricas y exigir un manifiesto de evidencia del run actual. Se
registran por separado, una vez por ID, como `APR-036` y `APR-037` en
`audits/standards/MEJORA.md`; ambos tienen el destino único `harden gate`.

`HARNESS7-001` requiere que el gate `agents check` valide contenido y no solo
existencia. Su destino único es `APR-038` en
`audits/standards/MEJORA.md`, con refuerzo del gate y pruebas de conformance.

Los demás hallazgos tienen una regla normativa existente y no generan una
segunda entrada de mejora. La ausencia de `pip-audit`, GGUF y runtime vivo se
mantiene como limitación de evidencia, no como vulnerabilidad o PASS.

## Trazabilidad de disposición

Cada ID de esta tabla aparece en `informe_completa.md` y
`checklist_completa.md`. La integración no declara corrección, persistencia ni
comparación; la remediación deberá crear un ledger separado con propietario,
archivo cambiado, prueba y estado.
