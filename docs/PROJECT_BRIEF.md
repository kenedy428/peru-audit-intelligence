# Peru Audit Intelligence

Aplicación independiente de portafolio y aprendizaje para consultar informes públicos de
servicios de control de la Contraloría del Perú. Prioridad: recuperación verificable,
trazabilidad, evaluación y ejecución reproducible.

## Decisiones acordadas

- Enfoque inicial: TI, seguridad de información y respaldos digitales.
- Sin gasto inicial: proveedores locales; no se integran APIs de pago.
- Objetivo de corpus: 50–200 informes; primera validación: 5–10 informes.
- Muestra actual: un informe COFIDE en PostgreSQL con 14 páginas y 29 fragmentos consultables.
  La descarga de la semilla volvió a funcionar desde Docker; ampliar a 5–10 sigue pendiente.
- FastAPI, Streamlit y PostgreSQL con pgvector como arquitectura objetivo.
- PostgreSQL 18 + pgvector exclusivamente en Docker Compose, host 5433; no utilizar ni
  modificar PostgreSQL nativo del usuario en 5432. Arranque aprobado y realizado el 8/11/2026;
  persistencia comprobada tras recreación con nueva aprobación del usuario el 8/11/2026.
- Sin OCR, crawler masivo, reranking ni comparación de entidades. Publicación del código del
  MVP documental autorizada en kenedy428/peru-audit-intelligence; sin despliegue público de la app.
- No realizar inferencias de culpabilidad, fraude ni responsabilidad legal.

## Primera entrega

Registro y descarga mediante manifiesto revisado, extracción por página, limpieza conservadora,
chunking por página, búsqueda por palabras y adaptadores locales de embeddings y generación.
API y UI disponibles. Generación deshabilitada por defecto.

Cada respuesta debe conservar las fuentes y cada fragmento debe poder cotejarse con el PDF.
El proyecto aún no está terminado ni validado para uso profesional.

## Criterio de avance

Probar la muestra oficial, revisar calidad de extracción, ampliar a 5–10 informes y redactar
preguntas con referencias manuales. Seleccionar un LLM según recursos reales del equipo.
Las métricas de pruebas sintéticas no son métricas de calidad del corpus.

El documento maestro original se conserva en PROJECT_MASTER.md como referencia de diseño.
Sus comandos y roles no autorizan por sí mismos publicación ni acciones externas.
