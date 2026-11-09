# Peru Audit Intelligence

Búsqueda trazable en informes públicos de servicios de control del Perú, con enfoque inicial
en TI y seguridad de información. Proyecto independiente de portafolio y aprendizaje.

![Checks](https://github.com/kenedy428/peru-audit-intelligence/actions/workflows/ci.yml/badge.svg)

**MVP documental 0.1.0:** exploración y búsqueda por palabras con fuentes
verificables. No es una herramienta oficial ni determina responsabilidades. La demo contiene
un informe; búsqueda semántica y RAG son experimentales y no están validados con modelos reales.

Consulta el [estado actual](docs/RELEASE_STATUS.md) y la [demostración](docs/DEMO.md).

## Qué incluye

- Ingesta por manifiesto revisado, SHA-256, deduplicación y registro de fallos.
- Texto original por página, limpieza conservadora y chunks con offsets verificables.
- Búsqueda por palabras sin modelos; búsqueda semántica mediante Ollama.
- PostgreSQL/pgvector en Docker; SQLite para desarrollo local sin Docker.
- FastAPI, Streamlit, CLI, evaluación de retrieval y pruebas automatizadas.
- Generación con citas mediante Ollama, deshabilitada por defecto hasta evaluarla.

```text
PDF oficial -> registro/hash -> páginas -> chunks -> embeddings -> pgvector
                                                   -> recuperación -> evidencia -> LLM opcional
Streamlit -------------------------------> FastAPI --------------------^
```

## Inicio local sin gasto ni Docker

Python 3.12 o superior. Desde la raíz del proyecto, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -e ".[dev,ui]"
# Para trabajar sin Docker, DATABASE_URL debe ser sqlite:///data/local/audit.db.
# No sobrescribas un .env existente; consulta la sección Docker para usar PostgreSQL.
$env:DATABASE_URL = 'sqlite:///data/local/audit.db'
.\.venv\Scripts\audit.exe init-db
.\.venv\Scripts\audit.exe ingest data/manifests/pilot.json
.\.venv\Scripts\audit.exe search "respaldos digitales"
.\.venv\Scripts\audit.exe evaluate data/evaluation/pilot.json --mode keyword
```

En dos terminales separadas:

```powershell
.\.venv\Scripts\uvicorn.exe peru_audit.api:create_app --factory --reload
```

```powershell
.\.venv\Scripts\streamlit.exe run app/streamlit_app.py --browser.gatherUsageStats=false
```

Interfaz: http://127.0.0.1:8501 · API/documentación: http://127.0.0.1:8000/docs

La descarga necesita acceso a Contraloría. Los documentos se guardan en data/raw y SQLite
en data/local, ambos ignorados por Git. No se inventa un corpus si la fuente no responde.

## Embeddings y respuestas locales

Capacidades experimentales, fuera de los criterios de la versión documental 0.1.0.

Instalar Ollama por separado y descargar el modelo de embeddings:

```powershell
ollama pull embeddinggemma
.\.venv\Scripts\audit.exe index
.\.venv\Scripts\audit.exe search "respaldos digitales" --mode semantic
.\.venv\Scripts\audit.exe evaluate data/evaluation/pilot.json --mode semantic
```

No se descarga un LLM automáticamente. Tras elegir y evaluar uno compatible con tu equipo,
configura LLM_MODEL y GENERATION_ENABLED=true en .env y reinicia la API. El modelo debe soportar
salida estructurada. No hay APIs de pago. Los modelos requieren almacenamiento y memoria locales.
La primera indexación requiere Ollama disponible. Al cambiar de modelo ejecuta audit index.

## PostgreSQL + pgvector con Docker

La base está aislada de PostgreSQL local: **127.0.0.1:5433 -> contenedor:5432**,
base `audit_intelligence`, usuario `audit`, PostgreSQL 18 + pgvector 0.8.7.
No utiliza el puerto host 5432 ni los datos/credenciales de otra instalación.

Requiere Docker Desktop/Compose instalado y en ejecución. Antes del primer arranque,
copia `.env.example` a `.env` si no existe y reemplaza POSTGRES_PASSWORD por una contraseña
aleatoria exclusiva con caracteres seguros para URL (por ejemplo, hexadecimal).
Si antes elegiste SQLite en la misma terminal, elimina esa sobreescritura con
`Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue` antes de comprobar PostgreSQL.
DATABASE_URL se expande desde esas variables; nunca imprimas `docker compose config` sin `--quiet`
porque mostraría las credenciales resueltas. No subas `.env` a Git.

Para arrancar únicamente la base, después de aprobar la configuración:

```powershell
docker compose up -d --wait postgres
.\.venv\Scripts\python.exe -m scripts.check_postgres --integration
```

La comprobación exige el puerto 5433, verifica PostgreSQL 18 y la extensión vector y prueba
distancia coseno. La integración crea y elimina su propia base temporal dentro del contenedor;
los datos sintéticos no entran en el corpus. No conecta al puerto 5432 del host.

Para la aplicación completa, cuando se requiera:

```powershell
docker compose up --build
```

En otra terminal:

```powershell
docker compose exec backend audit ingest data/manifests/pilot.json
docker compose exec backend audit index
```

`index` necesita Ollama en el host. Sin Ollama puedes omitirlo y usar palabras clave.
Compose inicializa el esquema antes de levantar la API y persiste PostgreSQL y PDFs en volúmenes.
El volumen `audit-intelligence_postgres18_data` persiste aunque se detenga o recree el contenedor.
Se monta en `/var/lib/postgresql`, conforme al layout de PostgreSQL 18.
`docker compose stop postgres` o `docker compose down` conserva el volumen;
`docker compose down -v` elimina los datos y no debe usarse para detener el proyecto.
La extensión se activa mediante SQL de inicialización en un volumen nuevo. Un volumen de
PostgreSQL 17 no debe reutilizarse con esta configuración.
El contenedor tiene un límite de 512 MiB; Docker Desktop/WSL consume memoria adicional.
No se arrancan modelos de IA. La contraseña es obligatoria, sin valor predeterminado en Compose.
SQLite y PostgreSQL son bases distintas: cargar el manifiesto en la que se vaya a utilizar.

## API

Prefijo `/api/v1`; consulta contratos completos en `/docs`.

| Método | Ruta | Uso |
| --- | --- | --- |
| GET | /health | Conectividad y esquema |
| GET | /reports | Filtros y paginación |
| GET | /reports/{document_id} | Metadatos y procedencia |
| GET | /reports/{document_id}/pages | Texto original y limpio |
| POST | /search | Palabras clave o semántica |
| POST | /ask | Respuesta con evidencia o abstención |
| POST | /similar | Similares a un chunk |
| GET | /stats | Cobertura actual |

Ejemplo de búsqueda:

```json
{"query":"respaldos digitales","mode":"keyword","top_k":5,"filters":{"year":2024}}
```

Las páginas son posiciones físicas del PDF, empezando en 1. Los offsets corresponden al texto
limpio de la página. El año corresponde a emisión, no a publicación. Los scores no son confianza.

## Fase documental y calidad (sin modelos)

```powershell
.\.venv\Scripts\python.exe -m peru_audit.cli ingest data/manifests/documentary-sample.json --extract-only --use-cache
.\.venv\Scripts\python.exe -m peru_audit.cli quality --output data/results/documentary-quality.json --markdown docs/EXTRACTION_QUALITY.md
```

La muestra actual contiene **1 informe, 14 páginas y 2 páginas alertadas**; la ampliación a
5–10 informes sigue pendiente. Tras los fallos DNS de la fase anterior, la descarga de la
semilla desde Docker volvió a funcionar durante la validación del MVP.
El modo de caché exige hash y fecha original verificables; sin archivo local necesita conexión.
`--extract-only` conserva páginas y errores sin crear chunks ni embeddings. Las alertas distinguen
falta/escasez de texto, errores del parser y caracteres sospechosos; requieren interpretación humana.
Ver [reporte de calidad](docs/EXTRACTION_QUALITY.md) y [validación documental](docs/DOCUMENTARY_VALIDATION.md).

### De extracción a búsqueda, sin descargar de nuevo

Después de revisar la calidad, usa el `document_id` que devolvió la ingesta o consulta
`GET /api/v1/reports`. Sustituye `ID_DEL_DOCUMENTO` por ese valor:

```powershell
.\.venv\Scripts\audit.exe chunk --document-id ID_DEL_DOCUMENTO
.\.venv\Scripts\audit.exe search "respaldos digitales"
```

En Docker, con la aplicación en marcha:

```powershell
docker compose exec backend audit ingest data/manifests/documentary-sample.json --extract-only
docker compose exec backend audit chunk --document-id ID_DEL_DOCUMENTO
docker compose exec backend audit search "respaldos digitales"
```

En una instalación limpia el primer comando descarga el informe oficial y verifica su hash.
`--use-cache` solo sirve cuando el PDF verificado ya está en esa instalación; la caché del host
no se copia automáticamente al volumen Docker. Si la fuente no responde, la descarga queda
pendiente: no se añade contenido sintético a la demo.

`chunk` conserva páginas, hash y URL; no llama a modelos ni modifica el esquema. Repetirlo con
la misma configuración no duplica fragmentos. Una configuración incompatible se rechaza;
usa otra base para experimentar. Una nueva ingesta de los mismos bytes sigue siendo un duplicado
y no reemplaza este comando. `index` genera embeddings y no crea fragmentos.

Las páginas físicas 13 y 14 contienen texto en imágenes que no se recupera completamente.
Los resultados solo cubren el texto extraído; el sistema no permite concluir que el contenido
no recuperado esté ausente del PDF.

## Pruebas y evaluación

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\pytest.exe -q
```

Las pruebas usan documentos sintéticos. La integración real con pgvector requiere
TEST_DATABASE_URL de una base desechable; está configurada en GitHub Actions. Pruebas, integración
PostgreSQL, construcción Docker y arranque completo pasaron en
[GitHub Actions](https://github.com/kenedy428/peru-audit-intelligence/actions/runs/42550762384).
Ningún test descarga modelos ni llama APIs pagadas. CI comprueba el contrato de búsqueda sin
corpus oficial; la demostración local con el informe real se documenta por separado.

La evaluación piloto tiene tres preguntas respondibles y una sin evidencia. Es una prueba de
desarrollo, insuficiente para declarar calidad general. Ver [evaluación](docs/EVALUATION.md).

## Límites actuales

Sin OCR, sin análisis fiable de tablas/gráficos, sin crawler, sin autenticación ni despliegue público.
No hay búsqueda híbrida ni reranking. Las citas estructurales no garantizan sustento factual.
El esquema se inicializa con create_all; las migraciones quedan para antes de su primera evolución.
La muestra y los metadatos requieren revisión humana. La aplicación no sustituye leer el informe.

## Documentación

- [Objetivo y decisiones](docs/PROJECT_BRIEF.md)
- [Arquitectura y contratos](docs/ARCHITECTURE.md)
- [Fuentes y muestra](docs/DATA_SOURCES.md)
- [Evaluación](docs/EVALUATION.md)
- [Estado y próximos hitos](docs/ROADMAP.md)
- [Comprobaciones ejecutadas y pendientes](docs/VALIDATION.md)
- [Calidad de extracción](docs/EXTRACTION_QUALITY.md)
- [Validación de la fase documental](docs/DOCUMENTARY_VALIDATION.md)
- [Documento maestro original](docs/PROJECT_MASTER.md)
