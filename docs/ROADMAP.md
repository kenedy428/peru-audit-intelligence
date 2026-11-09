# Estado y próximos hitos

Prioridad actual: cerrar y publicar la versión documental 0.1.0. Estado vigente y comprobaciones
en [RELEASE_STATUS.md](RELEASE_STATUS.md); semántica y RAG quedan como hitos posteriores.

## Primera base implementada

- Paquete Python, configuración, CLI y esquema inicial.
- Manifiesto oficial inicial; descarga limitada, hashes y registro de ejecuciones.
- Extracción por página, texto original/limpio, chunks y estados sin OCR.
- Búsqueda por palabras; búsqueda vectorial y generación mediante Ollama configurables.
- FastAPI y Streamlit; Docker Compose y workflow de CI.
- Evaluación por páginas y pruebas con fixtures sintéticas.

## Próximos hitos

1. Ampliar de 1 a 5–10 informes oficiales revisados. La descarga de la semilla COFIDE volvió
   a funcionar y su recorrido extracción, calidad, fragmentación y búsqueda está probado.
2. Revisar las páginas alertadas y decidir exclusiones/OCR antes de avanzar a chunking.
   Docker/PostgreSQL ya están validados; Ollama y los embeddings reales siguen pendientes.
3. Medir recursos y seleccionar un LLM local; evaluar grounding y abstención antes de habilitarlo.
4. Ampliar corpus a 50–200 informes y evaluación a 30–100 preguntas; separar test de desarrollo.
5. Ajustar chunking y K; comparar con búsqueda híbrida solo si los resultados lo requieren.
6. Incorporar migraciones antes de evolucionar el esquema con datos persistidos.
7. Mantener la demo y CI publicadas; el repositorio remoto y las capturas del MVP ya existen.

No se considera terminado el MVP semántico mientras PostgreSQL, modelos reales y evaluación
documental no estén comprobados. CI documental ya pasó en GitHub; no valida modelos reales.
