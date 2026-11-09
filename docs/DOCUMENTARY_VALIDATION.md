# Fase documental — 8 de noviembre de 2026

**Resultado parcial: pipeline probado, ampliación a 5–10 informes bloqueada por conectividad.**
No se considera completada la selección del corpus. Se procesó un informe oficial ya descargado;
no hubo nuevas descargas ni se incorporaron informes sin verificar.

## Fuente y selección

La fuente elegida sigue siendo el repositorio público de Contraloría en apps8.contraloria.gob.pe.
Se utilizan informes completos, comprobando portada y metadatos; las fichas resumen, notas de
prensa, planes institucionales y términos de referencia no se cuentan como informes de control.

Informe procesado: 007-2024-OCI/0014-SVC, COFIDE, documentación y respaldo digital de expedientes
de contratación. La portada se revisó visualmente y confirma la fecha 19 de abril de 2024.
La fecha de publicación no se inventa y continúa desconocida.

El candidato del Ministerio de Cultura sobre su plataforma de venta de boletos, encontrado
durante la exploración anterior, no se incorpora: no se pudo completar la revisión/descarga en
esta fase. Su referencia oficial es:
https://apps8.contraloria.gob.pe/SPIC/srvDownload/ViewPDF?CRES_CODIGO=2024CSI576500018&TIPOARCHIVO=ADJUNTO

No se fabricaron los cuatro a nueve informes faltantes ni sus metadatos. Deben seleccionarse
cuando vuelva el acceso a las fuentes oficiales, preferentemente sobre respaldos, accesos,
infraestructura TI, continuidad y seguridad de información.

## Bloqueo externo comprobado

- La búsqueda web devolvió errores de conexión.
- socket.getaddrinfo falla con código 11001 para apps8.contraloria.gob.pe, example.com y pypi.org.
- Resolve-DnsName sobre la fuente oficial agotó el tiempo; curl también falló al resolverla.
- Los adaptadores del equipo aparecen activos; eso no demuestra conectividad a Internet.
- No se cambiaron DNS ni configuración de red del usuario.

El manifiesto `data/manifests/documentary-sample.json` contiene solo el documento verificado.
Su hash esperado y fecha original proceden del registro SQLite anterior y se cotejaron con
los bytes del archivo local. El modo de caché no intenta una descarga nueva ni simula una.

## Resultados reales en PostgreSQL Docker

| Métrica | Resultado |
| --- | ---: |
| Informes registrados | 1 |
| Páginas físicas conservadas | 14 |
| Páginas con algo de texto | 13 |
| Páginas sin texto | 1 |
| Páginas con texto escaso | 1 |
| Páginas distintas con alertas | 2 |
| Páginas con excepción del parser | 0 |
| Chunks creados en esta carga | 0 |
| Embeddings del corpus PostgreSQL | 0 |
| Nuevas descargas durante esta fase | 0 |

SHA-256: `19c4c47fd47d27f8e0853e586dda483b9f211bb4e9102d776ac1bf94a9459210`.
Se conservó la descarga original `2026-11-08T04:06:26.216829+00:00`.
Estado documental: `partial_text`; parser: pypdf 6.21.4.

La base se inicializó con el esquema existente, sin alterarlo ni añadir tablas de calidad.
Los diagnósticos de excepciones se guardan en processing_config; el reporte de calidad se
deriva de documentos y páginas. No se modificó PostgreSQL nativo en 5432 ni se reinició Docker.
La base SQLite previa, incluidos sus chunks iniciales, se dejó intacta; esta carga Docker no
crea chunks. La generación permanece deshabilitada y no hay LLM configurado.

## Revisión visual de las alertas

- Página física 13: 49 caracteres y 7 palabras extraíbles. Contiene un memorando escaneado;
  solo se recupera su encabezado textual, no el cuerpo de la imagen.
- Página física 14: cero caracteres extraíbles. Contiene una captura de pantalla del sistema
  de recepción documental; no está vacía, pero su texto forma parte de una imagen.

Esas páginas requieren OCR o transcripción revisada si se quiere consultar su contenido.
OCR sigue fuera de esta fase. No deben considerarse evidencia de contenido ausente.
El reporte automático no valida fidelidad de tablas, gráficos ni orden de lectura.
El resto del documento conserva texto original y limpio por página, pero presencia de texto
no equivale a una revisión visual exhaustiva de todas sus afirmaciones o tablas.

## Cambios del pipeline

- `documents.py`: conserva numeración y páginas legibles aunque falle la extracción de otra;
  registra la categoría de excepción de la página fallida.
- `ingestion.py`: extracción sin chunks, registro del parser, uso de caché solo con hash y fecha
  originales, rechazo de discrepancias de hash y reintentos limitados de fallos transitorios.
- `schemas.py`: expected_sha256 y cached_downloaded_at opcionales para caché trazable.
- `quality.py`: alertas por página, cobertura, procedencia, versión de reglas y exportación JSON/Markdown.
- `cli.py`: opciones --extract-only, --use-cache y comando quality.
- Tests: ampliados test_documents.py y test_ingestion.py; nuevos test_quality.py y
  test_documentary_postgres.py. Fixtures sintéticas separadas de los documentos oficiales.

No se cambió retrieval, no se ajustó chunking y no se llamó a proveedores de IA.

## Reproducción

Desde la raíz, con PostgreSQL Docker disponible en 127.0.0.1:5433:

```powershell
.\.venv\Scripts\python.exe -m peru_audit.cli init-db
.\.venv\Scripts\python.exe -m peru_audit.cli ingest data/manifests/documentary-sample.json --extract-only --use-cache
.\.venv\Scripts\python.exe -m peru_audit.cli quality --output data/results/documentary-quality.json --markdown docs/EXTRACTION_QUALITY.md
```

Sin el PDF en caché se necesita conectividad para descargarlo; el hash esperado debe coincidir.
Un cambio de contenido oficial requiere revisión del nuevo archivo antes de cambiar ese hash.
El manifiesto ampliado deberá revisarse antes de añadir entradas y marcar reviewed=true.
La ingesta tradicional aún puede crear chunks si se omite --extract-only; esta fase siempre
utiliza la opción explícita. El comando quality es de solo lectura respecto a la base.

El reporte JSON completo queda en data/results/documentary-quality.json (ignorado por Git).
El resumen público generado está en EXTRACTION_QUALITY.md, con URL y hash de origen.
Las imágenes de inspección son temporales bajo tmp/pdf-quality, fuera de Git.

## Pruebas y reejecución

- 38 pruebas locales relevantes aprobadas (extracción, ingesta, calidad y aislamiento de BD).
- 2 pruebas PostgreSQL aprobadas en una base temporal, eliminada al terminar: baseline vectorial
  con vectores sintéticos y nuevo recorrido documental sin chunks. No se ejecutó ningún modelo.
- Repetición real de la ingesta: duplicate, mismo documento y 14 páginas, cero chunks y embeddings.
- Ruff y formato comprobados. No se atribuye una ejecución completa de regresión API a esta fase.
- Los tests PostgreSQL mostraron un aviso de deprecación de Starlette/httpx y otro de caché pytest;
  las pruebas terminaron correctamente. Las pruebas locales se ejecutaron sin el proveedor de caché.

## Pendiente antes de chunking y embeddings

1. Restablecer acceso y verificar al menos otros cuatro informes oficiales, hasta reunir 5–10.
2. Repetir ingesta y calidad con esos PDFs; revisar visualmente todas las páginas alertadas.
3. Definir si se excluyen los anexos escaneados del retrieval o se añade OCR en una fase autorizada.
4. Etiquetar preguntas/evidencias por página y decidir cortes de chunks, tratamiento de tablas,
   exclusiones y parámetros con la muestra ampliada.
5. Solo después seleccionar y probar embeddings; no hay validación semántica en esta fase.
