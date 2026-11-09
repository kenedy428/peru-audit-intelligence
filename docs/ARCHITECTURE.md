# Arquitectura y decisiones de la primera entrega

```text
Manifiesto oficial revisado -> descarga limitada -> SHA-256 -> registro
  -> extracción original por página -> limpieza -> chunks con offsets
  -> Ollama embeddings -> PostgreSQL/pgvector -> recuperación filtrada
  -> contexto con evidencias -> Ollama chat opcional -> respuesta y fuentes

Streamlit -> FastAPI /api/v1 -> servicios -> SQLAlchemy -> almacenamiento
CLI --------------------------^                         ^
```

## Almacenamiento

PostgreSQL + pgvector es el destino principal de Docker Compose. SQLite permite desarrollar y
usar la búsqueda por palabras sin Docker. En SQLite la similitud se calcula exactamente en Python;
en PostgreSQL se utiliza distancia coseno de pgvector. No hay índice aproximado aún: para el corpus
pequeño preferimos una referencia exacta. SQLite no sustituye las pruebas de PostgreSQL.

La configuración Docker usa PostgreSQL 18 con pgvector 0.8.7, base `audit_intelligence`,
puerto host 5433 y puerto interno 5432. El PostgreSQL 18 nativo del usuario en host:5432
queda fuera del proyecto: no se conecta, configura, detiene ni modifica.
Credenciales exclusivas en `.env` (ignorado por Git y Docker build); `.env.example` contiene
solo una plantilla. El volumen `audit-intelligence_postgres18_data` monta `/var/lib/postgresql`,
la ruta correspondiente a PostgreSQL 18. Se conserva al detener o recrear el contenedor.
Un SQL de primer arranque activa `vector`; el healthcheck espera disponibilidad TCP.
`scripts.check_postgres` rechaza destinos distintos de loopback:5433/audit_intelligence y
ejecuta integración en una base temporal independiente. CI utiliza el mismo Compose.

`documents` conserva metadatos declarados, hash único, fecha de descarga, estado y parámetros del
pipeline. Emisión y publicación son fechas diferentes; el filtro anual usa emisión. `pages`
conserva texto original y limpio. `chunks` conserva página física (base 1), offsets de caracteres
en el texto limpio, cantidad de palabras y embedding versionado. `processing_runs` registra cada
intento, duplicados y categorías de fallo; una extracción fallida no deja documentos parciales.

La deduplicación es por bytes. Una URL con un PDF modificado crea otro documento. Dos URLs con
los mismos bytes no generan otro documento; ambos intentos quedan en processing_runs. El documento
conserva como fuente canónica la primera URL. No se identifican equivalencias semánticas de PDFs.

El esquema inicial se crea mediante `audit init-db`. Es idempotente, no es un sistema de migraciones.
Antes de cambiar un esquema con datos persistidos se deberá incorporar Alembic y una migración.

## Procesamiento

Se utiliza pypdf por su extracción por página y su instalación ligera, en lugar de PyMuPDF
propuesto inicialmente. No elimina firmas, encabezados o pies de forma heurística. La limpieza
solo normaliza Unicode, espacios y caracteres NUL. Tablas y gráficos pueden perder estructura.

Los chunks no cruzan páginas: 180 palabras con 30 de solapamiento. Son palabras, no tokens del
modelo. Esta decisión provisional favorece citas exactas y permite empezar sin tokenizer específico.
Ollama rechaza entradas que exceden su contexto (`truncate=false`), nunca se truncan en silencio.
No hay re-chunking automático: para ensayos de otras configuraciones usar una base de datos separada.

`audit chunk --document-id ID` crea fragmentos desde páginas persistidas cuando no existen.
Conserva texto original, procedencia y estado de extracción; actualiza la configuración y
pipeline_version a page-words-v2. Registra chunk_completed, chunk_unchanged o chunk_failed
en processing_runs. Repeticiones compatibles son idempotentes; configuraciones incompatibles
se rechazan sin reemplazar fragmentos. La escritura es atómica y PostgreSQL bloquea la fila del
documento durante la operación. No descarga PDFs ni llama a modelos ni requiere migraciones.

PDF sin texto: `needs_ocr`; parcialmente extraíble: `partial_text`; totalmente extraíble: `ready`.
`has_text` indica existencia de texto, no garantiza calidad. OCR no implementado.

La fase documental usa `ingest --extract-only`: registra páginas sin crear chunks. Cada página
que falla conserva su posición física y un error tipado en processing_config.extraction_errors;
se mantienen las páginas legibles. No se añade ninguna columna ni cambia el esquema de la BD.
`quality` genera JSON/Markdown con no_text, sparse_text, suspicious_encoding, fragmented_text y
extraction_error. Umbrales y versión de reglas quedan en el reporte; son alertas, no una nota
de fidelidad. Texto original y limpio se conservan por separado.

La caché es optativa (`--use-cache`), requiere un SHA-256 esperado y fecha original de descarga
en el manifiesto, y vuelve a verificar los bytes. No se vuelve a fechar el PDF como recién
descargado. Un hash distinto aborta la ingesta. Las descargas nuevas tienen reintentos acotados
de fallos transitorios; no se elude autenticación ni se implementa un crawler.

## Modelos y recuperación

Ollama es el único proveedor implementado. No se instala ni descarga un modelo automáticamente.
El embedding inicial configurable es `embeddinggemma`, dimensión 768. El fingerprint incluye
nombre, digest reportado por Ollama, dimensión y normalización. Una consulta solo usa chunks
con el mismo fingerprint; `audit index` reconstruye los incompatibles por lotes reanudables.
Evitar actualizar modelos durante indexación; actualmente se retiene un embedding por chunk.

`keyword` puntúa cobertura de términos normalizados, sin stemming ni ranking BM25. `semantic`
usa similitud coseno. Los scores no son probabilidades y no se comparan entre métodos.
Filtros se aplican antes del ranking. `similar` excluye el chunk de origen.

La generación requiere habilitación explícita y LLM_MODEL. Solo recibe fragmentos por encima
de un umbral provisional, instrucciones de neutralidad y salida JSON con identificadores de
evidencia. Se rechazan citas inexistentes o sin correspondencia estructural. Esto no demuestra
que cada afirmación esté respaldada: requiere revisión de groundedness y calibración.

## Interfaces

- GET `/api/v1/health`, `/reports`, `/reports/{document_id}`, `/reports/{document_id}/pages`, `/stats`.
- POST `/api/v1/search`: query, mode, top_k y filters.
- POST `/api/v1/ask`: question, top_k y filters; status, answer, sources y reason.
- POST `/api/v1/similar`: chunk_id, top_k y filters.
- Filtros: entity, year (emisión), region, control_type, document_ids. Coincidencia exacta.
- Listado de informes: también título parcial, número exacto y paginación offset/limit.
- Fuentes: document_id, chunk_id, hash, URL, página física, offsets y score_type.
- `/stats` añade documents_with_chunks; indexed_chunks sigue contando fragmentos con embeddings.
- 422 para entradas inválidas, 404 para identificadores ausentes, 503 para BD/modelos no disponibles.

No se expone ingesta ni descarga arbitraria desde la API. Uso local sin autenticación.
Compose publica puertos solo en loopback. No desplegar públicamente esta configuración.
