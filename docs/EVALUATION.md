# Evaluación

## Piloto

`data/evaluation/pilot.json` contiene tres preguntas de desarrollo con referencias por número
de informe y página física, más una pregunta diseñada sin evidencia. Las primeras referencias
se prepararon leyendo el informe oficial; deben cotejarse tras cada cambio de extracción.
Una sola referencia por pregunta puede no cubrir todas las páginas relevantes del documento.

```powershell
audit evaluate data/evaluation/pilot.json --mode keyword --top-k 5
audit evaluate data/evaluation/pilot.json --mode semantic --top-k 5
```

La salida JSON conserva método, K, fingerprint semántico, snapshot del corpus, fecha y resultados.
Guardar salidas fuera de Git en data/results junto a configuración, fecha y snapshot del corpus.
La primera ejecución real está registrada en VALIDATION.md; es una prueba de desarrollo limitada.

## Métricas

- Recall@K: referencias únicas relevantes recuperadas / referencias únicas esperadas.
- Hit@K: al menos una referencia relevante entre K chunks.
- MRR@K: promedio del inverso del rango del primer chunk relevante; cero si no hay ninguno.

Una referencia es (número de informe, página física). Dos chunks de la misma página no cuentan
dos veces en Recall. Preguntas sin respuesta se excluyen de Recall/MRR: recuperar resultados
no determina si el sistema debe contestar. El CLI advierte que requieren evaluación separada.

## Antes de habilitar generación para una demo

Ampliar a 30–100 preguntas revisadas manualmente, incluyendo paráfrasis, filtros, múltiples
evidencias y consultas sin respuesta. Separar desarrollo de test antes de ajustar parámetros.
Revisar que cada afirmación tenga respaldo en su cita, que no convierta menciones en acusaciones,
que respete filtros y que se abstenga en casos sin evidencia. Medir latencia y costo local.

El umbral coseno 0.6 es provisional, no una confianza calibrada. La validación estructural de
citas no reemplaza la revisión factual. No se declara una meta numérica sin medir la muestra.
Comparar vector con keyword; añadir híbrido/reranking solo con mejora comprobada.

## Pruebas automatizadas

Fixtures sintéticas aisladas del corpus oficial verifican extracción, offsets, deduplicación,
fallos atómicos, validación de fuentes, filtros, versionado de embeddings, contratos API,
citas inválidas y fórmulas de métricas. El proveedor sintético nunca representa calidad semántica.
El test marcado postgres ejecuta distancia coseno real con pgvector en CI; se omite localmente
sin TEST_DATABASE_URL. Esa variable debe señalar una base desechable dedicada a pruebas.
