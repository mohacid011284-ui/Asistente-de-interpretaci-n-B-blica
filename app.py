import os
import re
import hmac
import base64
import streamlit as st
from openai import OpenAI

# ----------------------------
# CONFIG
# ----------------------------
st.set_page_config(page_title="Instructor Bíblico AI (GPT)", page_icon="📖", layout="wide")

st.markdown("""
<style>
div.stButton > button {
  width: 100%;
  border-radius: 8px;
  height: 3.5em;
  font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------
# SECRETS
# ----------------------------
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("⚠️ Falta OPENAI_API_KEY en secrets.")
    st.stop()

# Password Maestro (obligatoria si quieres Maestro)
MAESTRO_PASSWORD = st.secrets.get("MAESTRO_PASSWORD", None)

# Modelo: si quieres PDF como input_file, usa uno con capacidades de visión.
# La guía menciona gpt-4o / gpt-4o-mini / o1 como ejemplos compatibles con PDFs. :contentReference[oaicite:3]{index=3}
MODEL_NAME = "gpt-4o-mini"

# ----------------------------
# PROMPT BASE
# ----------------------------
SYSTEM_INSTRUCTION_BASE = """
Eres un GPT personalizado que funciona como INSTRUCTOR DE INTERPRETACIÓN BÍBLICA.
Tu autoridad normativa es el texto bíblico.
PRINCIPIO RECTOR: “Permanecer en la línea: decir exactamente lo que el texto dice, ni más ni menos.”

MARCO HERMENÉUTICO OBLIGATORIO (En orden):
1. Texto bíblico | 2. Audiencia original | 3. Tipo de texto | 4. Rasgos literarios | 5. Estructura
6. Énfasis | 7. Contexto | 8. Línea melódica | 9. Argumento | 10. Reflexión teológica
11. Persuasión | 12. Arreglo | 13. Aplicación.

MODOS DE OPERACIÓN:
- MODO AULA: Enseña lección por lección. No permitas avanzar sin validar el paso anterior.
- MODO ALUMNO: Guía con preguntas socráticas. Nunca des respuestas completas.
- MODO MAESTRO: Modela interpretaciones completas y perfectas. (SOLO SI SE SOLICITA EXPLÍCITAMENTE).
- MODO REVISIÓN: Evalúa trabajos subidos. Sé estricto con el marco hermenéutico.

IMPORTANTE: Si el usuario intenta saltarse pasos en Modo Alumno, bloquéalo y regrésalo al paso correspondiente.
"""

def get_system_instruction() -> str:
    """Opcional: si usas carpeta knowledge/ con lecciones (.md/.txt), se inyectan aquí."""
    texto = SYSTEM_INSTRUCTION_BASE
    texto += "\n\n=== CONTENIDO DE LECCIONES (knowledge/) ===\n"
    if os.path.exists("knowledge"):
        files = sorted([f for f in os.listdir("knowledge") if f.endswith((".md", ".txt"))])
        for f in files:
            try:
                with open(os.path.join("knowledge", f), "r", encoding="utf-8") as fh:
                    texto += f"\n--- ARCHIVO: {f} ---\n{fh.read()}\n"
            except Exception:
                pass
    return texto

# ----------------------------
# STATE
# ----------------------------
if "client" not in st.session_state:
    st.session_state.client = OpenAI(api_key=OPENAI_API_KEY)

if "messages" not in st.session_state:
    # Guardamos solo para UI. No se re-envía todo al modelo.
    st.session_state.messages = []

if "prev_response_id" not in st.session_state:
    st.session_state.prev_response_id = None  # para multi-turn con Responses API :contentReference[oaicite:4]{index=4}

if "maestro_unlocked" not in st.session_state:
    st.session_state.maestro_unlocked = False

if "submission" not in st.session_state:
    st.session_state.submission = None

if "attach_file_next" not in st.session_state:
    st.session_state.attach_file_next = False

if "aula_iniciada" not in st.session_state:
    st.session_state.aula_iniciada = False

# ----------------------------
# SECURITY HELPERS
# ----------------------------
def is_maestro_request(texto: str) -> bool:
    if not texto:
        return False
    patron = r"(modo\s*maestro|act[uú]a\s+como\s+maestro|actua\s+como\s+maestro|respuesta\s+modelo|soluci[oó]n\s+modelo)"
    return re.search(patron, texto, flags=re.IGNORECASE) is not None

def is_revision_request(texto: str) -> bool:
    if not texto:
        return False
    return re.search(r"\bmodo\s*revisi[oó]n\b", texto, flags=re.IGNORECASE) is not None

def verificar_password():
    if not MAESTRO_PASSWORD:
        st.session_state.maestro_unlocked = False
        st.error("⚠️ Falta MAESTRO_PASSWORD en secrets (no se puede desbloquear Maestro).")
        return
    intento = st.session_state.get("pass_input", "")
    if hmac.compare_digest(intento, MAESTRO_PASSWORD):
        st.session_state.maestro_unlocked = True
        st.success("✅ Modo Maestro Desbloqueado")
    else:
        st.session_state.maestro_unlocked = False
        st.error("❌ Contraseña incorrecta")

def bloquear_maestro():
    st.session_state.maestro_unlocked = False
    st.info("🔒 Modo Maestro Bloqueado")

def reiniciar_chat():
    st.session_state.messages = []
    st.session_state.prev_response_id = None
    st.session_state.aula_iniciada = False
    st.session_state.attach_file_next = False
    st.session_state.maestro_unlocked = False
    if "pass_input" in st.session_state:
        st.session_state["pass_input"] = ""

# ----------------------------
# OPENAI SEND (Responses API)
# ----------------------------
def enviar_a_gpt(texto: str, adjuntar_archivo: bool = False):
    # Candado anti-atajo: Maestro por texto sin unlock
    if is_maestro_request(texto) and not st.session_state.maestro_unlocked:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "🔒 Modo Maestro bloqueado. Desbloquéalo con contraseña en el panel lateral."
        })
        return

    # Candado anti-atajo: Revisión por texto sin archivo
    if is_revision_request(texto) and st.session_state.submission is None:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "🔒 Para usar Revisión debes subir una entrega primero."
        })
        return

    content_parts = [{"type": "input_text", "text": texto}]

    if adjuntar_archivo and st.session_state.submission is not None:
        f = st.session_state.submission
        data = f.getvalue()

        # PDFs: se recomienda enviarlos como input_file (base64 o file_id). :contentReference[oaicite:5]{index=5}
        if f.type == "application/pdf" or f.name.lower().endswith(".pdf"):
            b64 = base64.b64encode(data).decode("utf-8")
            content_parts.append({
                "type": "input_file",
                "filename": f.name,
                "file_data": f"data:application/pdf;base64,{b64}",
            })
        else:
            # txt/md: lo pegamos como texto para evitar uploads
            try:
                text = data.decode("utf-8", errors="replace")
            except Exception:
                text = "(No se pudo decodificar el archivo como texto.)"
            content_parts.append({
                "type": "input_text",
                "text": f"\n\n=== ARCHIVO ADJUNTO: {f.name} ===\n{text}\n"
            })

    input_payload = [{
        "role": "user",
        "content": content_parts
    }]

    try:
        resp = st.session_state.client.responses.create(
            model=MODEL_NAME,
            instructions=get_system_instruction(),  # system/developer message :contentReference[oaicite:6]{index=6}
            input=input_payload,
            previous_response_id=st.session_state.prev_response_id,  # multi-turn :contentReference[oaicite:7]{index=7}
            temperature=0.3
        )
        st.session_state.prev_response_id = resp.id
        st.session_state.messages.append({"role": "assistant", "content": resp.output_text})
    except Exception as e:
        st.error(f"Error al llamar a OpenAI: {e}")

# ----------------------------
# BUTTON ACTIONS
# ----------------------------
def trigger_aula():
    st.session_state.aula_iniciada = True
    msg = "COMANDO INTERNO: Inicia el MODO AULA. Avanza paso a paso según la lección y valida cada paso antes de continuar."
    st.session_state.messages.append({"role": "user", "content": msg, "hidden": True})
    enviar_a_gpt(msg)

def trigger_alumno():
    msg = "COMANDO INTERNO: Cambia a MODO ALUMNO. Hazme una pregunta socrática sobre el paso actual."
    st.session_state.messages.append({"role": "user", "content": msg, "hidden": True})
    enviar_a_gpt(msg)

def trigger_maestro():
    # Candado por función (aunque el botón esté deshabilitado)
    if not st.session_state.maestro_unlocked:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "🔒 Modo Maestro bloqueado. Desbloquéalo con contraseña en el panel lateral."
        })
        return
    msg = "COMANDO INTERNO: Cambia a MODO MAESTRO. Modela el paso actual perfectamente y explica tus decisiones hermenéuticas."
    st.session_state.messages.append({"role": "user", "content": msg, "hidden": True})
    enviar_a_gpt(msg)

def trigger_revision():
    if st.session_state.submission is None:
        st.session_state.messages.append({"role": "assistant", "content": "🔒 Sube una entrega antes de usar Revisión."})
        return
    st.session_state.attach_file_next = True
    msg = "COMANDO INTERNO: Cambia a MODO REVISIÓN. Evalúa estrictamente la tarea adjunta con el marco hermenéutico."
    st.session_state.messages.append({"role": "user", "content": msg, "hidden": True})
    enviar_a_gpt(msg, adjuntar_archivo=True)
    st.session_state.attach_file_next = False

# ----------------------------
# UI
# ----------------------------
with st.sidebar:
    st.image("https://cfmpaideia.com/wp-content/uploads/2023/05/logo-paideia-blanco.png", width=200)
    st.header("Panel de Control")

    uploaded_file = st.file_uploader("📂 Subir Tarea (PDF/TXT/MD)", type=["pdf", "txt", "md"])
    if uploaded_file:
        st.session_state.submission = uploaded_file
        st.success("Archivo cargado y listo para revisión.")
    else:
        st.session_state.submission = None

    st.markdown("---")

    st.subheader("🔐 Acceso Maestro")
    if not st.session_state.maestro_unlocked:
        st.text_input("Contraseña", type="password", key="pass_input")
        st.button("Desbloquear", on_click=verificar_password)
    else:
        st.success("Modo Maestro: ACTIVO")
        st.button("Bloquear de nuevo", on_click=bloquear_maestro)

    st.markdown("---")
    st.button("🗑️ Reiniciar Clase", on_click=reiniciar_chat)

st.title("Aula de Hermenéutica Expositiva (GPT)")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.button("🏫 MODO AULA", on_click=trigger_aula, help="Iniciar la clase paso a paso")

with col2:
    st.button("🤔 MODO ALUMNO", on_click=trigger_alumno, disabled=not st.session_state.aula_iniciada, help="Ayuda socrática")

with col3:
    st.button("👨‍🏫 MODO MAESTRO", on_click=trigger_maestro, disabled=not st.session_state.maestro_unlocked)

with col4:
    st.button("📝 MODO REVISIÓN", on_click=trigger_revision, disabled=(st.session_state.submission is None))

st.markdown("---")

# CHAT HISTORY
for m in st.session_state.messages:
    if m.get("hidden"):
        continue
    role = m["role"]
    avatar = "🧑‍💻" if role == "user" else "📖"
    with st.chat_message("user" if role == "user" else "assistant", avatar=avatar):
        st.markdown(m["content"])

# USER INPUT
if prompt := st.chat_input("Escribe tu análisis o pregunta..."):
    # Bloqueo directo si intentan activar Maestro por texto
    if is_maestro_request(prompt) and not st.session_state.maestro_unlocked:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "⛔ ACCESO DENEGADO: No puedes activar funciones de Maestro sin contraseña. Usa el panel lateral."
        })
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner("El instructor está analizando..."):
        enviar_a_gpt(prompt)
        st.rerun()
