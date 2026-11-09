# Cambios

## 0.1.0 — 8 de noviembre de 2026

Primera versión documental para ejecución local y portafolio.

- Ingesta de informes públicos oficiales con manifiesto revisado, SHA-256 y deduplicación.
- Texto original por página física, limpieza conservadora, calidad y fragmentos con offsets.
- `audit chunk --document-id ID` conecta extracción y búsqueda sin nuevas descargas.
- Búsqueda por palabras, filtros, API FastAPI e interfaz Streamlit con trazabilidad.
- PostgreSQL/pgvector en Docker aislado del servidor nativo; SQLite para desarrollo.
- Pruebas sintéticas, integración PostgreSQL y CI con construcción y arranque Docker.
- Demostración real de un informe COFIDE: 14 páginas y 29 fragmentos.

Semántica y RAG tienen adaptadores implementados pero no validación con modelos reales.
Generación deshabilitada por defecto. Sin OCR: las páginas 13 y 14 del piloto tienen cobertura
textual incompleta. Sin autenticación ni despliegue público de la aplicación.
