# Base Docker: arrancada y persistencia validada

## Archivos

- docker-compose.yml: servicio postgres con PostgreSQL 18 + pgvector, salud y volumen persistente.
- docker/postgres/init/01-vector.sql: CREATE EXTENSION IF NOT EXISTS vector en la base del proyecto.
- .env.example: plantilla pública; .env: credenciales locales exclusivas, sin versionar.
- scripts/check_postgres.py: conexión, versión, vector y prueba coseno; integración en base temporal.
- .github/workflows/ci.yml: mismas imagen, configuración y pruebas en un runner aislado.

## Valores concretos

| Parámetro | Valor |
| --- | --- |
| Proyecto Compose | audit-intelligence |
| Imagen | pgvector/pgvector:0.8.7-pg18-trixie |
| Host | 127.0.0.1:5433 |
| Contenedor | postgres:5432 |
| Base | audit_intelligence |
| Usuario | audit |
| Contraseña | Aleatoria, exclusiva, conservada solo en .env |
| Volumen | audit-intelligence_postgres18_data |
| Punto de montaje PG18 | /var/lib/postgresql |
| Límite de memoria del contenedor | 512 MiB (sin incluir Docker Desktop/WSL) |

## Procedimiento de validación

1. Validar Compose sin imprimir secretos (`docker compose config --quiet`).
2. Descargar imagen y arrancar solo postgres (`docker compose up -d --wait postgres`).
3. Verificar salud, versión 18, conexión por 5433, extensión vector y distancia coseno.
4. Ejecutar `python -m scripts.check_postgres --integration` con el entorno virtual.
5. Comprobar persistencia con un marcador sintético en una base temporal del contenedor,
   recreando únicamente el servicio postgres sin eliminar volúmenes; eliminar luego esa base.
6. Registrar resultados reales y limitaciones. No se migra el corpus SQLite en este paso.

No modificar el PostgreSQL nativo, ni usar su contraseña, archivos o puerto host 5432.
No ejecutar `down -v`; los scripts de inicialización se ejecutan solo con un volumen nuevo.
Cambiar .env después del primer arranque no cambia automáticamente la contraseña guardada en la BD.

## Estado de revisión

Docker CLI y Compose detectados el 8 de noviembre de 2026. Ninguna imagen descargada ni
contenedor creado por esta tarea antes de la aprobación. La CLI emitió una advertencia de
acceso a su config.json bajo este entorno: la disponibilidad del daemon y acceso al registro
quedan pendientes de verificar después de la aprobación, sin modificar la configuración del usuario.

Actualización tras aprobación: Docker Desktop se inició, Compose validó y arrancó únicamente
postgres, que alcanzó healthy. PostgreSQL 18.6 y vector 0.8.7 comprobados mediante conexión
real en 127.0.0.1:5433; integración aprobada. La recreación y lectura de metadatos Docker
posteriores fueron rechazadas por timeout de la revisión automática de permisos, sin ejecutarse.
Actualización final: con una nueva aprobación del usuario se recreó el contenedor y se verificó
que el marcador original permanecía en el volumen. Se eliminó su base temporal y se repitió
la integración correctamente. Evidencias y resultado final en DOCKER_VALIDATION.md.

Referencias: https://hub.docker.com/r/pgvector/pgvector y
https://hub.docker.com/_/postgres (cambio de volumen/PGDATA desde PostgreSQL 18).
