import os
import hmac
import streamlit as st
from google import genai
from google.genai import types

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Instructor Bíblico", page_icon="📖", layout="wide")
st.markdown(
    """<style>div.stButton > button {width: 100%; border-radius: 10px; height: 3em;}</style>""",
    unsafe_allow_html=True
)

# --- API KEY ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    st.error("⚠️ Falta GOOGLE_API_KEY en secrets.")
    st.stop()

# --- ESTADO BASE ---
if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "modo" not in st.session_state:
    st.session_state.modo = "LIBRE"  # AULA | ALUMNO | MAESTRO | REVISION | LIBRE

if "aula_vista" not in st.session_state:
    st.session_state.aula_vista = False

if "submission" not in st.session_state:
    st.session_state.submission = None  # archivo de entrega del alumno

if "attach_file_next" not in st.session_state:
    st.session_state.attach_file_next = False  # adjuntar entrega SOLO en el próximo envío

if "maestro_unlocked" not in st.session_state:
    st.session_state.maestro_unlocked = False

# --- CEREBRO (PROMPT) ---
INSTRUCCIONES_BASE = """
ROL: Eres un Instructor de Seminario de Hermenéutica Expositiva.
INSTRUCCIÓN SUPREMA: NO INVENTES CONTENIDO. Sigue estrictamente las secciones del archivo cargado.

CUANDO EL USUARIO PRESIONE UN BOTÓN, ACTÚA ASÍ:

🟢 MODO AULA (Botón 'Aula')
1. Busca en el archivo actual la sección que dice "### [CONTENIDO_AULA]".
2. Exponlo tal cual está escrito.
3. Al final, haz ÚNICAMENTE la pregunta que aparece en "### [PREGUNTA_AULA]".

🟡 MODO ALUMNO (Botón 'Alumno' - Socrático)
1. Busca la sección "### [GUIA_SOCRATICA]".
2. Usa esas preguntas específicas para guiar al alumno. No le des la respuesta.

🔴 MODO REVISIÓN (Botón 'Revisión')
1. Busca la sección "### [CRITERIO_EVALUACION]".
2. Usa esos puntos para calificar lo que el alumno escribió.

🔵 MODO MAESTRO (Botón 'Maestro')
1. Modela la respuesta correcta basándote en la teoría.
"""

def get_prompt() -> str:
    texto = INSTRUCCIONES_BASE
    texto += "\n\n=== CONTENIDO DE LA LECCIÓN ACTUAL ===\n"

    if os.path.exists("knowledge"):
        archivos_ordenados = sorted(
            [f for f in os.listdir("knowledge") if f.endswith((".md", ".txt"))]
        )
        for f in archivos_ordenados:
            try:
                with open(f"knowledge/{f}", "r", encoding="utf-8") as x:
                    texto += f"\n--- ARCHIVO: {f} ---\n{x.read()}\n"
            except Exception:
                pass

    return texto

# --- CHAT (se crea si no existe) ---
if "chat" not in st.session_state or st.session_state.chat is None:
    st.session_state.chat = st.session_state.client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=get_prompt(),
            temperature=0.2
        )
    )

# --- UTILIDADES ---
def push_internal_command(texto: str):
    st.session_state.messages.append({"role": "user", "content": texto})

def reiniciar():
    st.session_state.chat = None
    st.session_state.messages = []
    st.session_state.modo = "LIBRE"
    st.session_state.aula_vista = False
    st.session_state.submission = None
    st.session_state.attach_file_next = False
    st.session_state.maestro_unlocked = False
    if "uploader" in st.session_state:
        del st.session_state["uploader"]
    if "maestro_pass_input" in st.session_state:
        del st.session_state["maestro_pass_input"]

def desbloquear_maestro():
    if "MAESTRO_PASSWORD" not in st.secrets:
        st.session_state.maestro_unlocked = False
        st.error("⚠️ Falta MAESTRO_PASSWORD en secrets.")
        return

    expected = st.secrets["MAESTRO_PASSWORD"]
    entered = st.session_state.get("maestro_pass_input", "")

    if hmac.compare_digest(entered, expected):
        st.session_state.maestro_unlocked = True
        st.success("✅ Acceso Maestro habilitado")
    else:
        st.session_state.maestro_unlocked = False
        st.error("❌ Contraseña incorrecta")

def bloquear_maestro():
    st.session_state.maestro_unlocked = False
    st.info("🔒 Acceso Maestro bloqueado")

# --- ACCIONES DE BOTONES ---
def activar_aula():
    st.session_state.modo = "AULA"
    st.session_state.aula_vista = True
    st.session_state.attach_file_next = False
    push_internal_command(
        "MODO AULA: Expón la lección actual siguiendo el guion de [CONTENIDO_AULA] y termina con [PREGUNTA_AULA]."
    )

def activar_alumno():
    st.session_state.modo = "ALUMNO"
    st.session_state.attach_file_next = False
    push_internal_command(
        "MODO ALUMNO: Inicia el diálogo socrático usando la [GUIA_SOCRATICA]."
    )

def activar_maestro():
    # BLOQUEO REAL: no mandar nada al modelo si no está desbloqueado
    if not st.session_state.maestro_unlocked:
        st.session_state.messages.append({
            "role": "model",
            "content": "🔒 Modo Maestro bloqueado. Ingresa la contraseña en el panel lateral."
        })
        return

    st.session_state.modo = "MAESTRO"
    st.session_state.attach_file_next = False
    push_internal_command("MODO MAESTRO: Muestra cómo se hace.")

def activar_revision():
    st.session_state.modo = "REVISION"
    st.session_state.attach_file_next = True  # adjuntar SOLO en este envío
    push_internal_command(
        "MODO REVISIÓN: Evalúa mi respuesta usando [CRITERIO_EVALUACION]."
    )

# --- INTERFAZ ---
st.title("📖 Instructor de Interpretación Bíblica")

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3389/3389081.png", width=100)
    st.title("Panel de Control")

    archivo = st.file_uploader(
        "📂 Subir entrega (sermón/trabajo)",
        type=["pdf", "txt", "md"],
        key="uploader"
    )

    if archivo is not None:
        st.session_state.submission = archivo
        st.success(f"✅ Archivo recibido: {archivo.name}")
    else:
        if st.session_state.submission is not None:
            st.info(f"📌 Archivo actual: {st.session_state.submission.name}")
        else:
            st.warning("Sin entrega cargada.")

    st.markdown("---")
    st.subheader("Acceso Maestro")
    st.text_input("Contraseña", type="password", key="maestro_pass_input")
    ca, cb = st.columns(2)
    with ca:
        st.button("Desbloquear", on_click=desbloquear_maestro)
    with cb:
        st.button("Bloquear", on_click=bloquear_maestro)
    st.caption(f"Estado: {'✅ Habilitado' if st.session_state.maestro_unlocked else '🔒 Bloqueado'}")

    st.markdown("---")
    st.button("🗑️ Reiniciar Chat", type="primary", on_click=reiniciar)

# --- BOTONES PRINCIPALES ---
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.button("🎓 Aula", on_click=activar_aula)

with c2:
    st.button("📝 Alumno", on_click=activar_alumno, disabled=not st.session_state.aula_vista)

with c3:
    st.button(
        "🧑‍🏫 Maestro",
        on_click=activar_maestro,
        disabled=(not st.session_state.aula_vista or not st.session_state.maestro_unlocked)
    )

with c4:
    st.button(
        "🔍 Revisión",
        on_click=activar_revision,
        disabled=(not st.session_state.aula_vista or st.session_state.submission is None)
    )

# --- MOSTRAR CHAT (oculta comandos internos "MODO ...") ---
for m in st.session_state.messages:
    if m["role"] == "user" and m["content"].startswith("MODO "):
        continue

    role = "assistant" if m["role"] == "model" else "user"
    with st.chat_message(role):
        st.markdown(m["content"])

# --- INPUT LIBRE ---
if prompt := st.chat_input("Escribe tu respuesta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# --- RESPUESTA DEL MODELO ---
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_text = st.session_state.messages[-1]["content"]

    # BLOQUEO SERVIDOR (anti-atajo): si alguien escribe "MODO MAESTRO" manualmente
    if last_text.startswith("MODO MAESTRO") and not st.session_state.maestro_unlocked:
        st.session_state.messages.pop()  # elimina el comando no autorizado
        with st.chat_message("assistant"):
            st.markdown("🔒 Modo Maestro bloqueado. Requiere contraseña.")
        st.session_state.messages.append({"role": "model", "content": "🔒 Modo Maestro bloqueado. Requiere contraseña."})

    # BLOQUEO SERVIDOR (anti-atajo) para revisión sin archivo
    elif last_text.startswith("MODO REVISIÓN") and st.session_state.submission is None:
        st.session_state.messages.pop()
        with st.chat_message("assistant"):
            st.markdown("🔒 Para usar Revisión debes subir una entrega primero.")
        st.session_state.messages.append({"role": "model", "content": "🔒 Para usar Revisión debes subir una entrega primero."})

    else:
        with st.chat_message("assistant"):
            with st.spinner("..."):
                try:
                    msg_content = [last_text]

                    # Adjuntar entrega SOLO cuando el modo lo requiera (Revisión)
                    if st.session_state.attach_file_next and st.session_state.submission is not None:
                        f = st.session_state.submission
                        msg_content.append(types.Part.from_bytes(data=f.getvalue(), mime_type=f.type))

                    res = st.session_state.chat.send_message(msg_content)
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "model", "content": res.text})

                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    st.session_state.attach_file_next = False
