import os
from urllib.parse import urlsplit

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="Peru Audit Intelligence", page_icon="📑", layout="wide")
st.title("Peru Audit Intelligence")
st.caption("Explora informes públicos de control con evidencia verificable.")
st.info("Proyecto independiente de aprendizaje. Cobertura parcial; no determina responsabilidades.")


def request(method, path, **kwargs):
    try:
        with httpx.Client(timeout=150) as client:
            response = client.request(method, f"{API_URL}/api/v1{path}", **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as error:
        try:
            detail = error.response.json().get("detail", "La API rechazó la solicitud")
        except ValueError:
            detail = "La API rechazó la solicitud"
        st.error(str(detail))
    except httpx.RequestError:
        st.error("No se pudo conectar con la API. Revisa que esté en ejecución.")
    return None


def source_link(url, page=None):
    parsed = urlsplit(url)
    if parsed.scheme == "https" and (
        parsed.hostname == "contraloria.gob.pe"
        or (parsed.hostname or "").endswith(".contraloria.gob.pe")
    ):
        st.link_button("Abrir documento oficial", f"{url}#page={page}" if page else url)


def show_hits(hits):
    if not hits:
        st.info(
            "No se encontraron fragmentos. Prueba otra consulta o revisa el índice y los filtros."
        )
    for index, item in enumerate(hits, 1):
        with st.container(border=True):
            st.subheader(f"{index}. {item['report_number']}")
            st.write(item["title"])
            st.caption(
                f"{item['entity_name']} · Página física {item['page_start']} · "
                f"{item['score_type']}: {item['score']:.3f}"
            )
            st.text(item["text"])
            source_link(item["source_url"], item["page_start"])
            with st.expander("Trazabilidad"):
                st.json(
                    {
                        key: item[key]
                        for key in (
                            "document_id",
                            "chunk_id",
                            "source_hash",
                            "char_start",
                            "char_end",
                            "issue_date",
                            "publication_date",
                            "document_kind",
                        )
                    }
                )


stats = request("GET", "/stats")
if stats is None:
    st.stop()
columns = st.columns(5)
for column, label, key in zip(
    columns,
    ("Documentos registrados", "Con fragmentos", "Páginas", "Fragmentos", "Fragmentos indexados"),
    ("documents", "documents_with_chunks", "pages", "chunks", "indexed_chunks"),
    strict=True,
):
    column.metric(label, stats[key])

with st.sidebar:
    st.header("Exploración")
    view = st.radio("Vista", ["Buscar", "Preguntar", "Informes", "Similares"])
    entity = st.selectbox("Entidad", [None, *stats["entities"]], format_func=lambda v: v or "Todas")
    year = st.selectbox(
        "Año de emisión",
        [None, *stats["issue_years"]],
        format_func=lambda v: str(v) if v else "Todos",
    )
    top_k = st.slider("Cantidad de fragmentos", min_value=1, max_value=10, value=5)
    st.caption("Los resultados corresponden únicamente al corpus cargado.")

filters = {"entity": entity, "year": year}
if stats["documents"] == 0:
    st.warning("Todavía no hay documentos. Carga el manifiesto inicial siguiendo el README.")
elif stats["documents_with_chunks"] == 0:
    st.warning(
        "Hay documentos registrados sin contenido consultable en la búsqueda. "
        "Revisa la calidad y ejecuta audit chunk --document-id ID siguiendo el README."
    )
elif stats["documents_with_chunks"] < stats["documents"]:
    st.info("La búsqueda cubre solo los documentos con fragmentos; revisa los restantes.")

if view == "Buscar":
    st.header("Buscar evidencia")
    st.caption("La búsqueda semántica requiere Ollama y fragmentos previamente indexados.")
    with st.form("search"):
        query = st.text_input("Consulta", placeholder="respaldos digitales")
        mode = st.selectbox(
            "Método",
            ["keyword", "semantic"],
            format_func=lambda value: {
                "keyword": "Palabras clave",
                "semantic": "Semántica (modelo local)",
            }[value],
        )
        submit = st.form_submit_button("Buscar", type="primary")
    if submit and query.strip():
        with st.spinner("Buscando fragmentos…"):
            result = request(
                "POST",
                "/search",
                json={"query": query, "mode": mode, "filters": filters, "top_k": top_k},
            )
        if result is not None:
            show_hits(result["results"])
elif view == "Preguntar":
    st.header("Preguntar sobre los informes")
    if not stats["generation_enabled"]:
        st.warning("La generación está desactivada hasta configurar y evaluar un modelo local.")
    with st.form("ask"):
        question = st.text_area("Pregunta")
        submit = st.form_submit_button("Consultar", disabled=not stats["generation_enabled"])
    if submit and question.strip():
        with st.spinner("Recuperando evidencia y elaborando respuesta…"):
            result = request(
                "POST", "/ask", json={"question": question, "filters": filters, "top_k": top_k}
            )
        if result:
            st.write(result["answer"])
            st.caption(f"Estado: {result['status']}")
            show_hits(result["sources"])
elif view == "Informes":
    st.header("Explorar informes")
    title = st.text_input("Buscar en el título")
    offset = st.number_input("Desplazamiento de informes", min_value=0, step=20)
    result = request(
        "GET",
        "/reports",
        params={
            **{key: value for key, value in filters.items() if value is not None},
            "title": title,
            "offset": offset,
        },
    )
    if result:
        st.caption(f"{result['total']} documentos coinciden")
        rows = result["results"]
        if rows:
            selected_id = st.selectbox(
                "Informe",
                [row["document_id"] for row in rows],
                format_func=lambda value: next(
                    r["report_number"] for r in rows if r["document_id"] == value
                ),
            )
            document = next(row for row in rows if row["document_id"] == selected_id)
            st.subheader(document["title"])
            st.json(document)
            source_link(document["source_url"])
            page_offset = st.number_input("Desplazamiento de páginas", min_value=0, step=20)
            pages = request("GET", f"/reports/{selected_id}/pages", params={"offset": page_offset})
            if pages:
                for page in pages["results"]:
                    with st.expander(f"Página física {page['page_number']}"):
                        st.text(page["text"] or "Sin texto extraíble; requiere OCR.")
else:
    st.header("Fragmentos similares")
    st.caption("Copia el identificador de un fragmento desde la trazabilidad de un resultado.")
    with st.form("similar"):
        chunk_id = st.text_input("Identificador de fragmento")
        submit = st.form_submit_button("Buscar similares")
    if submit and chunk_id.strip():
        result = request(
            "POST", "/similar", json={"chunk_id": chunk_id, "filters": filters, "top_k": top_k}
        )
        if result is not None:
            show_hits(result["results"])
