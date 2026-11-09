# Verificación inicial — 7 de noviembre de 2026

Este documento conserva el historial de comprobaciones. Para el resultado consolidado y los
bloqueos vigentes de la versión documental consulta [RELEASE_STATUS.md](RELEASE_STATUS.md).

## Entorno y comprobaciones

- Windows, Python 3.14.0, entorno virtual local .venv.
- `ruff check .`: correcto; formato comprobado.
- `pytest -q`: 36 pruebas correctas, una omitida por falta de TEST_DATABASE_URL.
- `pip check`: sin incompatibilidades declaradas.
- Hay un aviso de deprecación de Starlette sobre el transporte httpx del cliente de pruebas;
  los contratos API pasan. No afecta a las solicitudes de producción.
- Dependencias resueltas en constraints.txt. Python 3.12/Linux queda sujeto a ejecución de CI.

## Prueba con documento oficial

La ingesta del manifiesto piloto completó la descarga y extracción del informe COFIDE.
Se conservan un documento, 14 páginas y 29 chunks. El estado es `partial_text`: una página
carece de texto extraíble. No hay embeddings reales generados: el contador correcto es cero.

La descarga inicial con el almacén de certificados predeterminado de httpx falló. Se configuró
el contexto TLS del sistema operativo, manteniendo la verificación de certificados habilitada;
la siguiente descarga funcionó. El intento fallido permanece registrado como ConnectError.

## API e interfaz

Comprobaciones HTTP de health, estadísticas y respuesta de Streamlit: correctas.
Prueba con Streamlit AppTest: carga inicial, búsqueda con resultados, detalle de informes,
vista de preguntas deshabilitada y formulario de similares sin excepciones.
El contador se comprobó con datos reales: cero indexados, 29 chunks disponibles para palabras clave.
Esta prueba verifica comportamiento de la interfaz; no es una revisión visual en navegador.

## Evaluación piloto por palabras clave

K=5, tres preguntas respondibles de desarrollo y una sin evidencia:

- Recall@5: 1.0.
- Hit@5: 1.0.
- MRR@5: 0.8333.

Resultado guardado localmente en data/results/pilot-keyword.json, con hash del corpus,
configuración de procesamiento y fecha de ejecución. El conjunto es demasiado pequeño para
afirmar calidad general. La pregunta sin evidencia no entra en estos promedios y todavía
requiere evaluación de abstención con un LLM real.

## Pendiente de verificar

Docker Compose y la integración real PostgreSQL/pgvector no se ejecutaron: Docker no está en PATH.
Ollama y los modelos tampoco están instalados en PATH; las pruebas vectoriales locales usan
embeddings sintéticos, sin valor como evaluación semántica. Generación permanece deshabilitada.
GitHub Actions está escrito pero no se ha ejecutado en un repositorio remoto.

## Actualización — 8 de noviembre de 2026: configuración Docker preparada

Docker 29.9.2 y Compose v5.6.1 están ahora detectados. Se preparó PostgreSQL 18 + pgvector
en host:5433, volumen nuevo dedicado, healthcheck, SQL de extensión y credenciales exclusivas
en .env ignorado por Git. No se conectó ni modificó PostgreSQL nativo en host:5432.

`pytest -q -m 'not postgres'`: 42 correctas, una deseleccionada. Ruff y verificación de formato
correctos. Se comprobó la expansión local de DATABASE_URL y las condiciones estáticas de
puerto, imagen, volumen e inicialización, sin abrir conexiones a bases de datos.

La descarga de imagen, validación de Compose, arranque, conexión, persistencia e integración
Docker quedan pendientes de la aprobación solicitada por el usuario. Ver DOCKER_DATABASE.md.

## Actualización tras aprobación de arranque

Base Docker arrancada y healthy, PostgreSQL 18.6, vector 0.8.7, conexión exclusiva publicada
en 127.0.0.1:5433, base audit_intelligence existente e integración PostgreSQL aprobada.
La persistencia tras recreación sigue pendiente: la revisión automática de permisos agotó
su tiempo y rechazó los comandos posteriores. Ver DOCKER_VALIDATION.md para evidencias,
límites, marcador de prueba y procedimiento restante. No se avanzó a modelos generadores.

## Cierre de persistencia tras nueva aprobación

Recreación completada: contenedor healthy, marcador original conservado y volumen
audit-intelligence_postgres18_data montado en /var/lib/postgresql. Se eliminó únicamente
la base temporal de persistencia y se verificó que no quedaran bases temporales de integración.
Pruebas repetidas: 1 integración PostgreSQL y 7 de aislamiento, todas correctas.
El resultado final y las fechas están en DOCKER_VALIDATION.md. No se activaron embeddings
ni modelos generadores; el PostgreSQL nativo del puerto 5432 quedó fuera de las operaciones.
