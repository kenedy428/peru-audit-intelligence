# Fuentes y registro de revisión

Buscador principal: https://appbp.contraloria.gob.pe/BuscadorCGR/Informes/Inicio.html

El buscador y la búsqueda avanzada agotaron el tiempo de espera en la revisión inicial.
No se implementa un crawler. Se registran URLs oficiales explícitas con `reviewed=true`.

## Semilla COFIDE

- Número: 007-2024-OCI/0014-SVC.
- Materia: documentación y respaldo digital de expedientes de contratación.
- Informe completo: https://apps8.contraloria.gob.pe/SPIC/srvDownload/ViewPDF?CRES_CODIGO=2024CSI001400007&TIPOARCHIVO=ADJUNTO
- Ficha resumen: https://apps8.contraloria.gob.pe/SPIC/srvDownload/ViewPDF?CRES_CODIGO=2024CSI001400007&TIPOARCHIVO=RE
- El informe completo tiene 14 páginas físicas según la lectura del recurso oficial.
- La portada indica 19 de abril de 2024; la ficha indica emisión 22 de abril de 2024.
  Se conserva 19 de abril como fecha del documento completo. Publicación queda desconocida.
- Solo el informe completo figura en el manifiesto; la ficha no se duplica como informe.
- `reviewed` indica revisión de origen/metadatos, no aprobación de contenido ni auditoría legal.

No se suben los PDFs a Git. La ingesta conserva el archivo por hash y calcula SHA-256 al descargarlo.
La URL debe continuar siendo pública; no se sortean autenticación, CAPTCHA ni restricciones.
Las redirecciones también se validan como URLs HTTPS de Contraloría.

## Fase documental: estado real

El PDF semilla se volvió a procesar desde la descarga oficial previa con hash verificado,
conservando su fecha original, y se registró en PostgreSQL sin chunks ni embeddings.
Las páginas físicas 13 y 14 contienen imágenes con texto: la primera solo aporta el encabezado
como texto extraíble y la segunda no aporta texto. Se revisaron visualmente las páginas 1, 13 y 14.

La ampliación sigue pendiente: la fuente y otros dominios no resuelven por DNS en el entorno
durante esta fase (error 11001). No se incorporaron informes sin verificar ni se inventó un corpus.
Ver DOCUMENTARY_VALIDATION.md y EXTRACTION_QUALITY.md para resultados y limitaciones.

## Ampliación pendiente

Añadir 4–9 informes oficiales vinculados con TI y seguridad. Revisar número, portada, entidad,
tipo de servicio, fecha, calidad del texto y páginas antes de marcar cada entrada como revisada.
No usar planes institucionales, términos de referencia ni notas de prensa como informes de control.
