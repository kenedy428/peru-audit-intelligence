# Versión documental 0.1.0

Estado: MVP documental publicado; validación local y primera ejecución de CI aprobadas.

## Implementado

- Descarga de fuentes oficiales revisadas, hash y deduplicación; texto original por página.
- Extracción sin fragmentos, diagnóstico de calidad y creación posterior con `audit chunk`.
- Búsqueda por palabras, API, interfaz y contadores separados de cobertura e indexación.
- Registro de intentos, idempotencia y rechazo de configuración incompatible sin borrar datos.
- Docker con PostgreSQL aislado en 127.0.0.1:5433; generación deshabilitada.

## Validado en esta entrega

- 61 pruebas locales aprobadas y 2 integraciones PostgreSQL en base temporal independiente.
- Ruff y formato correctos. Dependencias locales sin incompatibilidades declaradas.
- Informe oficial COFIDE: paso de 0 a 29 fragmentos en PostgreSQL, repetición sin duplicados.
- La procedencia y el texto original se conservan; las pruebas verifican offsets y rollback.
- Imagen construida en Python 3.12/Linux con las dependencias fijadas y servicios Docker arrancados.
- API e interfaz comprobadas por HTTP y navegador: búsqueda con resultados, trazabilidad,
  lectura de página física 4 y formulario de generación deshabilitado. Capturas en DEMO.md.
- API real: 1 documento con fragmentos, 14 páginas, 29 fragmentos y cero embeddings.
- Revisión acotada de archivos publicables: sin artefactos prohibidos ni secretos detectados.
- Recorrido CLI en SQLite nueva: extracción desde caché oficial verificada, 29 fragmentos,
  repetición idempotente y búsqueda con resultados en la página física 4.
- Descarga oficial desde Docker con SHA-256 esperado correcta; ingesta duplicada y chunk
  idempotente. `pip check` dentro del contenedor correcto.
- [CI inicial aprobada](https://github.com/kenedy428/peru-audit-intelligence/actions/runs/42550762384):
  Python 3.12/Linux, pruebas locales y PostgreSQL, imagen Docker, arranque completo y smoke HTTP.
  CI usa fixtures sintéticas y una aplicación sin corpus oficial; no mide calidad documental.

## Límites y publicación

Un informe, 14 páginas; páginas 13 y 14 parcialmente/no extraíbles por contener texto en imágenes.
No hay evaluación semántica ni generación con modelos reales. Las cuatro preguntas del piloto
son de desarrollo y no prueban calidad general. Los documentos y resultados locales no se publican.

Repositorio público creado: https://github.com/kenedy428/peru-audit-intelligence.
El commit inicial es f4d9b2f. La etiqueta v0.1.0 se crea únicamente sobre el commit final
con CI aprobada; consultar [las ejecuciones](https://github.com/kenedy428/peru-audit-intelligence/actions).
La conectividad con la semilla oficial se restableció; la ampliación del corpus aún no se realizó.

La validación histórica de base y persistencia se conserva en DOCKER_VALIDATION.md. Los
pendientes antiguos de VALIDATION.md describen su fecha, no sustituyen este estado actual.

## Hitos posteriores

Ampliar a 5–10 informes oficiales revisados; evaluar embeddings reales contra palabras clave;
preparar 30–100 preguntas con separación desarrollo/test; evaluar citas y abstención antes de
habilitar un LLM. Corpus objetivo de 50–200. Migraciones antes de evolucionar el esquema.
