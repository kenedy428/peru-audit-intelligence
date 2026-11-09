# Verificación Docker — 8 de noviembre de 2026

Estado final: base operativa y persistencia del volumen comprobada tras recrear el contenedor.
Las ocho condiciones se verificaron con el alcance descrito abajo. Esta validación termina
la fase de infraestructura; no se inició trabajo con embeddings ni modelos generadores.

| Condición | Resultado y evidencia |
| --- | --- |
| Contenedor healthy | `docker compose up -d --wait --wait-timeout 120 postgres` finalizó con exit 0 y `Container audit-intelligence-postgres-1 Healthy`. |
| Puerto exclusivo en host | `netstat -ano -p TCP` muestra LISTENING solo en `127.0.0.1:5433` para el puerto 5433, sin 0.0.0.0 ni IPv6. Conexión SQL real por esa dirección. |
| Base exclusiva | `SELECT current_database()` devolvió `audit_intelligence`. |
| Extensión activa | Servidor `18.6 (Debian 18.6-1.pgdg13+2)`; consulta pg_extension devolvió `vector`, versión `0.8.7`; operación coseno sobre vectores idénticos devolvió cero. |
| Script e integración | Después de recrear, `python -m scripts.check_postgres --integration` terminó con exit 0: 1 prueba PostgreSQL aprobada, 43 deseleccionadas. Las 7 pruebas de aislamiento también pasaron. Las bases temporales de integración fueron eliminadas. |
| PostgreSQL local intacto | Sin conexiones SQL a host:5432 ni cambios de archivos/configuración del PostgreSQL nativo. Su servicio `postgresql-x64-18` seguía Running y su proceso de servicio conservó PID 5356 antes y después de las operaciones ejecutadas. Solo se leyó metainformación del sistema operativo. |
| Persistencia | Recreación completada; el marcador original y su payload coincidieron exactamente. El nuevo contenedor usa `audit-intelligence_postgres18_data` montado en `/var/lib/postgresql`. Se eliminó únicamente la base temporal de la prueba y el registro local del marcador. |
| Secretos en Git | `.env` ignorado y fuera del índice. Escaneo repetido tras la validación: cero coincidencias de la contraseña real en archivos publicables. No se imprimieron DSN ni credenciales. No se usó la contraseña del PostgreSQL nativo. |

El puerto interno de PostgreSQL sigue siendo 5432 dentro de la red Docker; la exclusividad
anterior se refiere a su publicación en el host. No se probaron credenciales ni conexiones
contra el PostgreSQL nativo para demostrar aislamiento.

## Persistencia: ejecución final con nueva aprobación

Los primeros intentos agotaron el plazo de revisión automática de permisos y no se ejecutaron.
Al retomar la tarea se comprobó que el marcador original seguía intacto, pero el arranque del
servidor era anterior a su creación. El usuario volvió a aprobar explícitamente la recreación.
Después de esa aprobación se ejecutó con exit 0:

```powershell
docker compose up -d --no-deps --force-recreate --wait --wait-timeout 120 postgres
```

Evidencia de la comprobación final (UTC):

- Registro original del marcador: `2026-11-08T22:17:39.425439+00:00`.
- Creación del contenedor actual: `2026-11-08T22:40:50.844202165Z`, posterior al marcador.
- Nuevo arranque PostgreSQL: `2026-11-08T22:40:53.248817+00:00`.
- Contenedor: `1314a0c6be41b845a6ff7270220b7e563cfe6be9bf0ece411e03011aa94e7ef3`.
- Inspección Docker: `healthy`, binding exclusivo `127.0.0.1:5433`, volumen nombrado
  `audit-intelligence_postgres18_data` en `/var/lib/postgresql`.
- Único servicio del proyecto en ejecución: `postgres`.

Se consultaron el marcador y el payload originales por `127.0.0.1:5433`; ambos coincidieron
exactamente tras la recreación. Antes de limpiar se verificó el nombre exacto de la base
temporal y que solo contenía la tabla `public.persistence_probe` con la fila sintética esperada.
Se eliminó esa base exclusivamente y se comprobó su ausencia. También se eliminó
`data/results/docker-probe.json`, que contenía el marcador ya consumido.

No quedan bases temporales de persistencia ni integración. `audit_intelligence` y el volumen
se conservaron. No se usó `down -v` ni se borraron tablas o filas del corpus del proyecto.
El recibo sin contraseñas se conserva localmente en
`data/results/docker-persistence-original.json`, ignorado por Git.

La ejecución final utilizó el marcador original y comandos separados de recreación,
comprobación SQL y limpieza. No se atribuye esta ejecución al script
`scripts/check_postgres_persistence.py`, que crea otra prueba desde cero y no se ejecutó
de principio a fin.

## Alcance y comprobaciones adicionales

No se arrancaron los servicios init/backend/frontend ni modelos de IA. La generación sigue
deshabilitada y LLM_MODEL vacío. El corpus SQLite no se migró ni modificó en esta fase.
La base del proyecto tiene la extensión; el esquema de aplicación no se inicializó aquí.

En la ejecución anterior, la regresión global adicional se interrumpió al quedar esperando el arranque de
Starlette TestClient en Windows/Python 3.14; no se declara como aprobada en esta ejecución.
En la validación final se repitieron únicamente las pruebas pertinentes: 1 integración
PostgreSQL y 7 de aislamiento, todas aprobadas. Hay un aviso de deprecación de
Starlette relacionado con httpx en el cliente de pruebas, independiente de la conexión Docker.
