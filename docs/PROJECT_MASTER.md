# Peru Audit Intelligence
## Documento maestro de contexto, alcance y ejecución

**Nombre provisional:** Peru Audit Intelligence
**Tipo:** RAG, búsqueda semántica y analítica documental
**Dominio:** Informes públicos de servicios de control en Perú
**Objetivo de portafolio:** demostrar IA generativa aplicada, embeddings, PostgreSQL + pgvector, FastAPI, Docker, testing, evaluación y desarrollo reproducible en GitHub.

---

# 1. Resumen ejecutivo

**Peru Audit Intelligence** será una aplicación para buscar, explorar y consultar informes públicos de servicios de control de la Contraloría General de la República del Perú usando búsqueda semántica y Retrieval-Augmented Generation (RAG).

El sistema deberá:

1. obtener documentos públicos desde fuentes oficiales;
2. registrar metadatos y trazabilidad;
3. extraer y limpiar texto de PDFs;
4. dividir el contenido en chunks;
5. generar embeddings;
6. almacenarlos en PostgreSQL mediante pgvector;
7. recuperar fragmentos relevantes;
8. generar respuestas basadas en evidencia recuperada;
9. mostrar las fuentes utilizadas;
10. permitir filtros y búsqueda tradicional;
11. exponer las capacidades mediante FastAPI;
12. ofrecer una interfaz web;
13. ser reproducible con Docker;
14. incluir pruebas automatizadas y evaluación del retrieval.

El proyecto **no determinará fraude, corrupción, culpabilidad ni responsabilidad legal**. Solo organizará, recuperará y resumirá información ya publicada oficialmente.

---

# 2. Problema

La revisión manual de numerosos informes de control puede ser lenta. El proyecto buscará facilitar preguntas como:

- ¿Qué situaciones adversas relacionadas con seguridad de información aparecen en determinados informes?
- ¿Qué recomendaciones se repiten?
- ¿Qué informes mencionan deficiencias de contrataciones?
- ¿Qué fragmentos son semánticamente similares?
- ¿Qué documentos corresponden a determinada entidad, región, año o tema?
- ¿En qué páginas se encuentra la evidencia utilizada por el sistema?

---

# 3. Usuarios objetivo

- estudiantes de auditoría;
- estudiantes de ingeniería de sistemas;
- analistas de control;
- analistas de datos;
- investigadores;
- periodistas de datos;
- consultores;
- ciudadanos interesados en documentos públicos.

Es un proyecto de **portafolio y aprendizaje**, no una herramienta oficial de la Contraloría.

---

# 4. Fuente principal

Se utilizarán **informes de servicios de control publicados oficialmente por la Contraloría General de la República del Perú**.

Referencias:

- Buscador de Informes de Servicios de Control:
  `https://appbp.contraloria.gob.pe/BuscadorCGR/Informes/Inicio.html`

- Búsqueda avanzada:
  `https://appbp.contraloria.gob.pe/BuscadorCGR/Informes/Avanzado.html`

- Portal institucional:
  `https://www.gob.pe/contraloria`

- Procedimiento institucional de publicación:
  `https://apps8.contraloria.gob.pe/SPIC/Docs/Manuales/PR-COM-04-v3.pdf`

## Regla de fuente

Solo se utilizarán:

- documentos públicamente accesibles;
- información publicada oficialmente;
- metadatos necesarios para trazabilidad.

No se utilizarán documentos privados, filtraciones, bypass de autenticación ni datos obtenidos mediante mecanismos no autorizados.

---

# 5. Principios legales, éticos y de interpretación

## 5.1 No inferir culpabilidad

El sistema nunca debe convertir una mención o situación adversa en una acusación.

## 5.2 Evidencia antes que generación

Si no existen fragmentos suficientemente relevantes, deberá responder:

> No se encontró evidencia suficiente en los documentos recuperados para responder con confianza.

## 5.3 Trazabilidad

Toda respuesta deberá intentar conservar:

- número de informe;
- título;
- entidad;
- fecha;
- página;
- URL de origen.

## 5.4 Solo versión pública

El proyecto trabajará únicamente con las versiones públicas de los documentos.

---

# 6. Alcance inicial

## MVP recomendado

Trabajar inicialmente con **50 a 200 informes**.

El subconjunto podrá definirse por:

- entidad;
- periodo;
- tipo de servicio;
- región;
- temática.

## Fuera del alcance inicial

- indexar todo el histórico disponible;
- construir un sistema legal;
- determinar responsabilidad;
- identificar culpables;
- predecir corrupción;
- sustituir criterio auditor;
- crawler masivo.

---

# 7. Casos de uso

## CU-01 — Buscar informes
Filtros: entidad, año, región, tipo de control, título y número de informe.

## CU-02 — Preguntar sobre documentos
Ejemplo: “¿Qué problemas relacionados con control de accesos aparecen en los informes seleccionados?”

## CU-03 — Ver fuentes
Mostrar documentos y páginas utilizados.

## CU-04 — Buscar fragmentos similares
Seleccionar un fragmento y recuperar contenido semánticamente parecido.

## CU-05 — Explorar un informe
Mostrar metadata, páginas y fragmentos.

## CU-06 — Comparar
Versión posterior: comparar entidades, periodos o tipos de situación.

---

# 8. Arquitectura

```text
Contraloría
Buscador de informes
        │
        ▼
Descubrimiento / descarga
        │
        ▼
Document Registry
metadata + source URL + hash
        │
        ▼
PDF Extraction
        │
        ▼
Normalización de texto
        │
        ▼
Chunking
        │
        ▼
Embeddings
        │
        ▼
PostgreSQL + pgvector
        │
        ├───────────────┐
        │               │
        ▼               ▼
Filtros SQL       Vector Search
        │               │
        └───────┬───────┘
                ▼
         Hybrid Retrieval
                │
                ▼
           Reranking
           (opcional)
                │
                ▼
          Context Builder
                │
                ▼
               LLM
                │
                ▼
       Response + Sources
                │
        ┌───────┴────────┐
        ▼                ▼
     FastAPI          Web App
```

---

# 9. Componentes

## 9.1 Ingestion
- registrar documentos;
- descargar PDFs;
- guardar metadata;
- verificar archivo;
- calcular hash;
- evitar duplicados;
- registrar errores.

## 9.2 Document processing
- extraer texto por página;
- limpiar;
- detectar páginas sin texto;
- eliminar encabezados repetitivos cuando corresponda;
- crear chunks.

## 9.3 Embeddings
- generar vectores;
- versionar modelo;
- guardar dimensión y configuración;
- permitir regeneración.

## 9.4 Storage
PostgreSQL almacenará documentos, metadata, páginas, chunks, embeddings, ejecuciones y preguntas de evaluación.

## 9.5 Retrieval
Combinará filtros estructurados y búsqueda semántica.

## 9.6 Generation
El LLM recibirá pregunta, contexto recuperado e instrucciones.

## 9.7 API
FastAPI expondrá las funciones.

## 9.8 Frontend
Primera versión: Streamlit.

---

# 10. Stack tecnológico

## Lenguaje
- Python 3.12 o versión estable compatible.

## Backend
- FastAPI
- Pydantic
- Uvicorn

## Base de datos
- PostgreSQL
- pgvector

## Acceso a datos
Opciones:
- SQLAlchemy
- psycopg

## PDFs
Primera opción:
- PyMuPDF

Alternativas:
- pypdf
- pdfplumber

OCR no será obligatorio para el MVP.

## IA
- embeddings
- LLM
- RAG

El proveedor de embeddings y LLM será configurable.

## Interfaz
- Streamlit

## Testing
- pytest

## Infraestructura
- Docker
- Docker Compose

## Desarrollo
- Git
- GitHub
- Codex

## CI
- GitHub Actions

---

# 11. Modelo de datos preliminar

## documents

```text
document_id
report_number
title
entity_name
control_type
publication_date
region
source_url
source_hash
downloaded_at
processing_status
```

## pages

```text
page_id
document_id
page_number
page_text
```

## chunks

```text
chunk_id
document_id
page_start
page_end
chunk_index
chunk_text
token_count
embedding
embedding_model
```

## processing_runs

```text
run_id
started_at
finished_at
documents_processed
documents_failed
pipeline_version
```

## evaluation_questions

```text
question_id
question
expected_document_id
expected_page
category
notes
```

## evaluation_results

```text
evaluation_id
question_id
retrieved_documents
recall_at_k
reciprocal_rank
evaluated_at
```

La estructura podrá cambiar después del profiling.

---

# 12. Metadata mínima

Siempre que la fuente lo permita:

- número de informe;
- título;
- entidad auditada;
- tipo de servicio;
- fecha;
- región;
- órgano auditor;
- URL;
- fecha de descarga;
- hash.

---

# 13. Pipeline documental

```text
discover
    ↓
download
    ↓
validate
    ↓
register
    ↓
extract
    ↓
clean
    ↓
chunk
    ↓
embed
    ↓
index
```

Cada etapa deberá registrar logs, fallar de forma controlada y evitar reprocesamiento innecesario.

---

# 14. Descarga y registro

Antes de guardar un documento:

1. comprobar respuesta HTTP;
2. verificar que sea PDF;
3. calcular SHA-256;
4. comprobar duplicados;
5. guardar URL;
6. guardar timestamp;
7. guardar metadata.

No confiar únicamente en el nombre de archivo.

---

# 15. Extracción PDF

Objetivo: obtener texto por página conservando relación con el documento original.

Los PDFs pueden contener texto, tablas, encabezados, pies, saltos extraños o páginas escaneadas.

El MVP priorizará PDFs con texto extraíble. OCR quedará como ampliación.

---

# 16. Limpieza

Posibles operaciones:

- normalización Unicode;
- espacios repetidos;
- saltos de línea;
- encabezados/pies repetitivos;
- conservación de numeraciones relevantes.

No alterar el contenido semántico.

---

# 17. Chunking

Es una decisión crítica.

## Parámetros iniciales tentativos

```text
chunk_size: 700–1000 tokens
overlap: 100–150 tokens
```

No son definitivos.

Cada chunk conservará:

- document_id;
- página inicial;
- página final;
- índice;
- texto.

El tamaño deberá evaluarse, no elegirse por costumbre.

---

# 18. Embeddings

Proceso:

```text
texto
 ↓
embedding model
 ↓
vector
```

Guardar:

- modelo;
- versión/configuración;
- dimensión;
- fecha.

Si cambia el modelo, deberá poder reconstruirse el índice.

---

# 19. PostgreSQL + pgvector

Se utilizará PostgreSQL con pgvector para combinar:

- metadata estructurada;
- SQL;
- filtros;
- chunks;
- embeddings;
- búsqueda de similitud.

Esto evita introducir una base vectorial separada en el MVP.

---

# 20. Similaridad

Métrica inicial:

- cosine similarity.

Debe verificarse compatibilidad con el modelo de embeddings elegido.

---

# 21. Retrieval

## Baseline

```text
question
 ↓
embedding
 ↓
pgvector
 ↓
Top-K chunks
```

Parámetro inicial:

```text
top_k = 5
```

Debe ser configurable.

---

# 22. Búsqueda híbrida

Versión posterior:

```text
metadata filters
      +
keyword search
      +
vector search
```

Ejemplo:

```text
Entidad = Banco de la Nación
Año >= 2022
```

y después búsqueda semántica sobre el subconjunto.

---

# 23. Reranking

No obligatorio en la primera versión.

Si la evaluación justifica su uso:

```text
Top 20 retrieval
      ↓
reranker
      ↓
Top 5 context
```

---

# 24. RAG

```text
Pregunta
  ↓
Retrieval
  ↓
Chunks relevantes
  ↓
Context Builder
  ↓
LLM
  ↓
Respuesta sustentada
```

---

# 25. Reglas del prompt RAG

1. responder solo con evidencia recuperada;
2. no inventar hechos;
3. indicar insuficiencia de evidencia;
4. distinguir documento de interpretación;
5. no realizar acusaciones;
6. incluir fuentes;
7. mantener neutralidad;
8. expresar incertidumbre.

---

# 26. Formato de respuesta

```text
Respuesta

Se identifican...

Fuentes

1. Informe N.º XXXX
   Página 18

2. Informe N.º YYYY
   Página 42
```

La API devolverá también metadata estructurada.

---

# 27. API

Base:

```text
/api/v1
```

Endpoints preliminares:

```text
GET  /health
GET  /reports
GET  /reports/{report_id}
GET  /reports/{report_id}/pages
POST /search
POST /ask
POST /similar
GET  /stats
```

---

# 28. Ejemplo /search

```json
{
  "query": "control de accesos",
  "top_k": 5,
  "filters": {
    "entity": null,
    "year": null
  }
}
```

Resultado:

```json
{
  "results": [
    {
      "document_id": "...",
      "report_number": "...",
      "page": 18,
      "score": 0.87,
      "text": "..."
    }
  ]
}
```

---

# 29. Ejemplo /ask

```json
{
  "question": "¿Qué problemas relacionados con control de accesos aparecen?",
  "filters": {},
  "top_k": 5
}
```

Resultado:

```json
{
  "answer": "...",
  "sources": [
    {
      "report_number": "...",
      "page": 18,
      "source_url": "..."
    }
  ]
}
```

---

# 30. Similar Findings

Función diferencial.

Entrada:
- chunk_id o texto.

Salida:
- fragmentos similares;
- score;
- documento;
- página;
- entidad.

```text
Fragmento seleccionado
        ↓
Buscar similares
        ↓
Informe A — 0.91
Informe B — 0.87
Informe C — 0.82
```

---

# 31. Interfaz web

Primera versión: Streamlit.

Pantallas:

## Home
- resumen;
- número de informes;
- entidades;
- años.

## Search
- consulta;
- filtros;
- resultados.

## Ask
- pregunta;
- respuesta;
- fuentes;
- fragmentos.

## Report Detail
- metadata;
- páginas;
- chunks.

## Similar Findings
- fragmento;
- resultados similares.

## Evaluation
Opcional para portafolio:
- métricas;
- cobertura;
- estadísticas.

---

# 32. Evaluación

Es obligatoria.

El proyecto no se considerará terminado solo porque “el chatbot responde bien”.

---

# 33. Dataset de evaluación

Crear manualmente entre:

```text
30 y 100 preguntas
```

Cada una con:

- consulta;
- documento esperado;
- página o rango;
- categoría;
- dificultad.

---

# 34. Métricas de retrieval

## Recall@K
¿El resultado relevante apareció entre los primeros K?

## MRR
Mean Reciprocal Rank.

Opcionales:
- Precision@K;
- nDCG.

---

# 35. Evaluación de respuestas

Se podrá evaluar:

- groundedness;
- presencia de fuentes;
- fallback correcto;
- consistencia de citas.

No usar métricas no reproducibles.

---

# 36. Baseline y experimentación

Primero:

```text
Vector search
```

Luego comparar:

```text
Vector
vs.
Hybrid
vs.
Hybrid + reranking
```

Solo agregar complejidad si mejora resultados.

---

# 37. Docker

Arquitectura:

```text
docker compose
│
├── postgres + pgvector
├── backend
└── frontend
```

Comando objetivo:

```bash
docker compose up --build
```

---

# 38. Variables de entorno

```text
DATABASE_URL
EMBEDDING_PROVIDER
EMBEDDING_MODEL
LLM_PROVIDER
LLM_MODEL
API_KEY
```

Nunca subir `.env`.

Sí subir `.env.example`.

---

# 39. Seguridad

- secretos fuera de Git;
- validación de inputs;
- límites de tamaño;
- timeouts;
- no ejecutar contenido de PDFs;
- logs sin credenciales;
- manejo seguro de errores.

---

# 40. Testing

## Unit
- chunking;
- limpieza;
- hashing;
- metadata;
- filtros;
- parsing.

## Integration
- PostgreSQL;
- pgvector;
- endpoints;
- pipeline pequeño.

## Retrieval
- resultados esperados;
- fallback sin evidencia.

Comando:

```bash
pytest
```

---

# 41. CI

GitHub Actions deberá ejecutar:

```text
lint
tests
```

Opcional:

```text
docker build
```

---

# 42. Observabilidad

Logging estructurado:

```text
timestamp
component
document_id
run_id
status
duration
error
```

---

# 43. Estructura de repositorio

```text
peru-audit-intelligence/
│
├── README.md
├── AGENTS.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── docker-compose.yml
│
├── src/
│   ├── ingestion/
│   │   ├── discovery.py
│   │   ├── downloader.py
│   │   └── registry.py
│   ├── documents/
│   │   ├── pdf_parser.py
│   │   ├── cleaner.py
│   │   └── chunker.py
│   ├── embeddings/
│   │   ├── provider.py
│   │   └── indexing.py
│   ├── retrieval/
│   │   ├── vector.py
│   │   ├── keyword.py
│   │   ├── hybrid.py
│   │   └── reranker.py
│   ├── rag/
│   │   ├── prompts.py
│   │   ├── context.py
│   │   └── answer.py
│   ├── database/
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── migrations/
│   ├── api/
│   │   ├── main.py
│   │   ├── schemas.py
│   │   └── routes/
│   ├── evaluation/
│   │   ├── dataset.py
│   │   ├── retrieval.py
│   │   └── metrics.py
│   └── config.py
│
├── app/
│   └── streamlit_app.py
│
├── scripts/
│   ├── ingest.py
│   ├── index.py
│   └── evaluate.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── retrieval/
│
├── data/
│   ├── raw/
│   ├── interim/
│   ├── evaluation/
│   └── sample/
│
├── docs/
│   ├── PROJECT_BRIEF.md
│   ├── ARCHITECTURE.md
│   ├── DATA_SOURCES.md
│   ├── DATA_MODEL.md
│   ├── RAG_DESIGN.md
│   ├── EVALUATION.md
│   ├── SECURITY.md
│   ├── LIMITATIONS.md
│   └── ROADMAP.md
│
└── media/
    ├── architecture.png
    ├── search.png
    ├── ask.png
    └── demo.gif
```

---

# 44. AGENTS.md para Codex

Reglas mínimas:

```text
Read PROJECT_BRIEF.md before implementing major changes.

Do not fabricate data.

Do not infer fraud, corruption or guilt.

Every generated answer must preserve traceability to source documents.

Prefer small, testable modules.

Add or update tests when adding logic.

Do not introduce a dependency unless justified.

Do not change architecture silently.

Evaluation is mandatory for retrieval changes.

Never commit secrets, restricted data or credentials.
```

---

# 45. Roles

## Codex hará principalmente
- scaffolding;
- Python;
- FastAPI;
- PostgreSQL;
- pgvector;
- Docker;
- tests;
- Streamlit;
- refactoring;
- documentación;
- GitHub Actions.

## El propietario debe decidir y entender
- alcance;
- fuentes;
- metadata;
- chunking;
- embeddings;
- retrieval;
- evaluación;
- RAG;
- interpretación;
- limitaciones.

Regla:

> Codex puede escribir gran parte del código; el propietario debe entender el sistema completo.

---

# 46. Trabajo en ChatGPT

- explicación conceptual;
- diseño;
- revisión de arquitectura;
- selección de parámetros;
- interpretación de resultados;
- aprendizaje de RAG y embeddings;
- aprendizaje de FastAPI/Docker;
- preparación para entrevistas;
- redacción para CV.

---

# 47. Fases

## Fase 0 — Diseño
- alcance;
- arquitectura;
- repo;
- AGENTS.md;
- documentación.

## Fase 1 — Fuentes
- validar portal;
- elegir subset;
- muestras;
- metadata.

## Fase 2 — Document Registry
- modelo;
- hash;
- deduplicación;
- trazabilidad.

## Fase 3 — PDF Processing
- extracción;
- páginas;
- limpieza;
- calidad.

## Fase 4 — Chunking
- estrategia;
- pruebas;
- metadata.

## Fase 5 — Embeddings + pgvector
- modelo;
- almacenamiento;
- indexación;
- similarity search.

## Fase 6 — Retrieval baseline
- vector;
- top-k;
- filtros.

## Fase 7 — RAG
- contexto;
- prompt;
- LLM;
- fuentes;
- fallback.

## Fase 8 — FastAPI
- endpoints;
- schemas;
- documentación automática.

## Fase 9 — Streamlit
- búsqueda;
- pregunta;
- fuentes;
- similares.

## Fase 10 — Evaluation
- dataset;
- Recall@K;
- MRR;
- comparación.

## Fase 11 — Hybrid Search
Solo si mejora la evaluación.

## Fase 12 — Docker
- postgres;
- backend;
- frontend.

## Fase 13 — Testing + CI
- pytest;
- GitHub Actions.

## Fase 14 — GitHub Portfolio
- README;
- capturas;
- arquitectura;
- demo;
- release.

---

# 48. Criterios de aceptación por fase

Una fase termina cuando:

1. funciona;
2. tiene pruebas relevantes;
3. documentación actualizada;
4. el propietario puede explicarla;
5. no hay secretos versionados;
6. puede reproducirse.

---

# 49. MVP

Debe incluir:

- conjunto inicial de informes;
- registry;
- extracción por página;
- chunks;
- embeddings;
- pgvector;
- vector search;
- `/search`;
- `/ask`;
- fuentes;
- interfaz básica;
- tests esenciales.

No necesita todavía:

- reranking;
- híbrido avanzado;
- OCR;
- deployment público.

---

# 50. Versión final de portafolio

Debe demostrar:

- pipeline documental;
- PostgreSQL + pgvector;
- RAG;
- FastAPI;
- aplicación web;
- Docker Compose;
- evaluación;
- pytest;
- GitHub Actions;
- documentación;
- arquitectura;
- demo.

---

# 51. Métricas para CV

Solo con resultados reales:

- informes indexados;
- páginas;
- chunks;
- embeddings;
- Recall@5;
- MRR;
- preguntas de evaluación;
- tests;
- tiempo de indexación;
- latencia de búsqueda.

Nunca inventar métricas.

---

# 52. Posible descripción futura para CV

**No usar hasta finalizar y validar.**

> Desarrollé una aplicación RAG para consultar informes públicos de servicios de control, implementando extracción documental, embeddings y búsqueda semántica con PostgreSQL/pgvector.

> Construí una API con FastAPI y una interfaz web que genera respuestas sustentadas en fragmentos recuperados y referencias al documento fuente.

> Containericé la solución con Docker e implementé pruebas automatizadas y evaluación del retrieval mediante un conjunto de consultas de referencia.

---

# 53. Aporte al portafolio

## Peru Public Budget Monitor
```text
ETL
Data Engineering
PostgreSQL
Data Mart
Power BI
Testing
```

## Peru Procurement Risk Intelligence
```text
Data Integration
SQL Analytics
Risk Rules
Web Dashboard
Human Review
```

## Peru Audit Intelligence
```text
Generative AI
RAG
Embeddings
Vector Search
pgvector
FastAPI
Docker
Web App
Evaluation
CI
```

El objetivo es complementar, no repetir.

---

# 54. Riesgos técnicos

## PDFs difíciles
Mitigación: empezar con PDFs digitales; OCR opcional.

## Descarga inestable
Mitigación: separar discovery/download, guardar URLs, limitar volumen.

## Retrieval deficiente
Mitigación: dataset de evaluación, ajustar chunking/top-k, probar híbrido.

## Hallucinations
Mitigación: evidencia, threshold, fallback y fuentes.

## Costos
Mitigación: cache, batch embeddings, limitar contexto y proveedor configurable.

---

# 55. Limitaciones

Documentar:

- cobertura parcial;
- calidad variable de PDFs;
- embeddings imperfectos;
- errores posibles del LLM;
- no sustituye lectura del informe;
- no es análisis legal;
- no determina responsabilidades;
- metadata potencialmente incompleta;
- evaluación manual limitada.

---

# 56. Git

Commits por funcionalidad:

```text
Initialize project architecture
Add document registry
Add PDF extraction pipeline
Add chunking strategy
Add pgvector indexing
Add vector retrieval baseline
Add RAG answer generation
Add FastAPI endpoints
Add Streamlit interface
Add retrieval evaluation
Add Docker environment
Add CI workflow
Prepare portfolio release
```

Evitar un único commit final.

---

# 57. README

Secciones:

1. problema;
2. solución;
3. arquitectura;
4. fuentes;
5. alcance;
6. pipeline;
7. RAG;
8. base;
9. evaluación;
10. interfaz;
11. API;
12. Docker;
13. tests;
14. resultados;
15. limitaciones;
16. ejecución;
17. demo.

---

# 58. Comandos objetivo

```bash
python -m venv .venv
pip install -r requirements.txt
docker compose up --build
python -m scripts.ingest
python -m scripts.index
python -m scripts.evaluate
uvicorn src.api.main:app --reload
streamlit run app/streamlit_app.py
pytest
```

Podrán cambiar durante implementación.

---

# 59. Definition of Done

El proyecto estará listo para CV cuando:

- arquitectura estable;
- ejecución reproducible;
- dataset suficiente;
- retrieval evaluado;
- respuestas con fuentes;
- API funcional;
- app funcional;
- Docker funcional;
- tests pasan;
- CI operativo;
- README completo;
- demo disponible;
- limitaciones documentadas;
- propietario capaz de defender cada componente.

---

# 60. Estado inicial

```text
Diseño conceptual definido.
Implementación aún no iniciada.
```

Siguiente paso:

```text
Fase 0
↓
Crear carpeta local
↓
Crear repo GitHub
↓
Crear AGENTS.md
↓
Crear PROJECT_BRIEF.md
↓
Crear ARCHITECTURE.md
↓
Definir subset inicial de informes
```

---

# 61. Principio final

El proyecto no será evaluado por tener un chatbot que “parezca inteligente”.

Se evaluará por:

```text
Documento oficial
        ↓
Procesamiento reproducible
        ↓
Retrieval evaluado
        ↓
Evidencia verificable
        ↓
Respuesta sustentada
```

Prioridad:

> **retrieval confiable + trazabilidad + evaluación + reproducibilidad**

antes que complejidad innecesaria.
