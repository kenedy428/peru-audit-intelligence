# Calidad de extracción documental

Generado: 2026-11-08T23:03:37.707461+00:00 · Reglas: page-quality-v1

Informes: **1** · Páginas: **14** · Con texto: **13** · Con alertas: **2**.

Las alertas son heurísticas para revisión humana. No son una puntuación de fidelidad.
Todas las páginas son posiciones físicas del PDF, empezando en 1.

| Informe | Páginas | Sin texto | Texto escaso | Error de extracción |
| --- | ---: | ---: | ---: | ---: |
| 007-2024-OCI/0014-SVC | 14 | 1 | 1 | 0 |

## Procedencia y páginas para revisión

### 007-2024-OCI/0014-SVC

Proceso de documentación y respaldo de los expedientes de contratación en soporte digital

Fuente: https://apps8.contraloria.gob.pe/SPIC/srvDownload/ViewPDF?CRES_CODIGO=2024CSI001400007&TIPOARCHIVO=ADJUNTO

SHA-256: `19c4c47fd47d27f8e0853e586dda483b9f211bb4e9102d776ac1bf94a9459210`

Descarga: 2026-11-08T04:06:26.216829+00:00 · Estado: partial_text

- Página 13: sparse_text; 49 caracteres, 7 palabras.
- Página 14: no_text; 0 caracteres, 0 palabras.

## Interpretación de alertas

- `no_text`: sin texto; revisar si es página vacía, imagen o fallo del parser.
- `sparse_text`: menos de 80 caracteres o 15 palabras; no implica un error.
- `extraction_error`: falló esa página; las páginas legibles se conservaron.
- `suspicious_encoding`: caracteres sospechosos o glifos sin mapear.
- `fragmented_text`: abundan palabras de una letra; revisar lectura y orden.

No se evalúan automáticamente tablas, gráficos, semántica ni orden de lectura.
