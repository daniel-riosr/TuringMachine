import streamlit as st
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Simulador Máquina de Turing", layout="wide")

# --- ESTILOS CSS (Para que la cinta se vea bonita) ---
st.markdown("""
    <style>
    .tape-container {
        display: flex;
        justify_content: center;
        margin: 20px 0;
        overflow-x: auto;
    }
    .tape-cell {
        width: 50px;
        height: 50px;
        border: 2px solid #333;
        display: flex;
        align-items: center;
        justify_content: center;
        font-size: 24px;
        font-family: monospace;
        margin: 2px;
        border-radius: 5px;
        background-color: #f0f2f6;
        color: black;
    }
    .active-head {
        background-color: #ff4b4b !important; /* Rojo Streamlit */
        color: white !important;
        border: 2px solid #ff4b4b;
        box-shadow: 0 0 10px rgba(255, 75, 75, 0.5);
        transform: scale(1.1);
        font-weight: bold;
    }
    .step-log {
        font-family: monospace;
        background-color: #0e1117;
        color: #00ff00;
        padding: 10px;
        border-radius: 5px;
        height: 300px;
        overflow-y: scroll;
        border: 1px solid #333;
    }
    </style>
""", unsafe_allow_html=True)

# --- DEFINICIÓN DE LAS MÁQUINAS DE TURING ---

def get_binary_increment_rules():
    """
    Máquina que suma 1 a un número binario.
    Lógica: Viaja al final, suma 1, maneja el acarreo (carry) hacia la izquierda.
    """
    return {
        # (estado_actual, simbolo_leido): (nuevo_estado, simbolo_escribir, direccion)
        # Ir al final de la cadena (derecha)
        ('q0', '0'): ('q0', '0', 'R'),
        ('q0', '1'): ('q0', '1', 'R'),
        ('q0', 'B'): ('q_add', 'B', 'L'), # B = Blanco/Vacío

        # Estado de suma (q_add)
        ('q_add', '0'): ('q_done', '1', 'S'), # S = Stop/Stay (termina)
        ('q_add', '1'): ('q_add', '0', 'L'),  # Acarreo: 1->0 y sigue a la izq
        ('q_add', 'B'): ('q_done', '1', 'S'), # Overflow: ej 11 + 1 = 100 (escribe 1 al principio)
        
        # Estado final
        ('q_done', '0'): ('q_done', '0', 'S'),
        ('q_done', '1'): ('q_done', '1', 'S'),
    }

def get_anbncn_rules():
    """
    Máquina para L = {a^n b^n c^n}
    Algoritmo: Marca una 'a' con 'X', busca una 'b', marca con 'Y', busca 'c', marca con 'Z'. Repite.
    """
    return {
        # q0: Inicio, busca 'a' para marcar
        ('q0', 'a'): ('q1', 'X', 'R'),
        ('q0', 'Y'): ('q4', 'Y', 'R'), # Si encuentra Y al inicio, ya no hay a's, verificar resto
        ('q0', 'B'): ('q_accept', 'B', 'S'), # Cadena vacía aceptada o fin exitoso

        # q1: Buscar 'b' saltando a's e Y's
        ('q1', 'a'): ('q1', 'a', 'R'),
        ('q1', 'Y'): ('q1', 'Y', 'R'),
        ('q1', 'b'): ('q2', 'Y', 'R'), # Encontró b, marca Y, va a buscar c

        # q2: Buscar 'c' saltando b's y Z's
        ('q2', 'b'): ('q2', 'b', 'R'),
        ('q2', 'Z'): ('q2', 'Z', 'R'),
        ('q2', 'c'): ('q3', 'Z', 'L'), # Encontró c, marca Z, regresa al inicio

        # q3: Regresar al inicio (izquierda) hasta encontrar X
        ('q3', 'a'): ('q3', 'a', 'L'),
        ('q3', 'b'): ('q3', 'b', 'L'),
        ('q3', 'Y'): ('q3', 'Y', 'L'),
        ('q3', 'Z'): ('q3', 'Z', 'L'),
        ('q3', 'X'): ('q0', 'X', 'R'), # Topó con X, paso a la derecha (q0)

        # q4: Verificación final (asegurar que no sobran b's ni c's)
        ('q4', 'Y'): ('q4', 'Y', 'R'),
        ('q4', 'Z'): ('q4', 'Z', 'R'),
        ('q4', 'B'): ('q_accept', 'B', 'S'), # Llegó al final solo viendo marcas -> ACEPTADA
    }

# --- LÓGICA DE LA SIMULACIÓN ---

def initialize_simulation(input_str, machine_type):
    """Inicializa el estado de la sesión."""
    # Agregamos padding de 'B' (blancos) a la cinta
    tape = ['B'] + list(input_str) + ['B'] * 10 
    
    st.session_state.tape = tape
    st.session_state.head = 1 # Empezar después del primer blanco
    st.session_state.state = 'q0'
    st.session_state.history = ["-- Inicio de simulación --"]
    st.session_state.step_count = 0
    st.session_state.finished = False
    st.session_state.result_msg = ""
    
    if machine_type == "Incremento Binario (n+1)":
        st.session_state.rules = get_binary_increment_rules()
        st.session_state.accept_state = 'q_done'
    else:
        st.session_state.rules = get_anbncn_rules()
        st.session_state.accept_state = 'q_accept'

def step():
    """Ejecuta un solo paso de la máquina."""
    if st.session_state.finished:
        return

    tape = st.session_state.tape
    head = st.session_state.head
    state = st.session_state.state
    rules = st.session_state.rules
    
    # Leer símbolo actual
    # Si el cabezal se sale de la lista, extendemos la cinta
    if head >= len(tape):
        tape.append('B')
    if head < 0:
        tape.insert(0, 'B')
        head = 0 # Corregir índice
    
    symbol = tape[head]
    
    # Buscar transición
    key = (state, symbol)
    
    if key in rules:
        new_state, write_symbol, direction = rules[key]
        
        # Registrar log
        step_num = st.session_state.step_count + 1
        log_entry = f"Paso {step_num}: ({state}, {symbol}) → ({new_state}, {write_symbol}, {direction})"
        st.session_state.history.append(log_entry)
        
        # Aplicar cambios
        tape[head] = write_symbol
        st.session_state.state = new_state
        st.session_state.step_count += 1
        
        # Mover cabezal
        if direction == 'R':
            st.session_state.head += 1
        elif direction == 'L':
            st.session_state.head -= 1
        # 'S' es Stay (quedarse quieto), usualmente para terminar
            
        # Verificar parada
        if new_state == st.session_state.accept_state:
            st.session_state.finished = True
            st.session_state.result_msg = ">> CADENA PROCESADA / ACEPTADA"
            st.session_state.history.append(st.session_state.result_msg)
            
            # Limpiar cinta para mostrar resultado limpio (opcional)
            final_string = "".join(tape).replace('B', '')
            st.session_state.history.append(f">> CONTENIDO FINAL CINTA: {final_string}")
            
    else:
        # No hay regla definida -> Rechazo (Crash)
        st.session_state.finished = True
        st.session_state.result_msg = ">> CADENA RECHAZADA (No hay transición definida)"
        st.session_state.history.append(f"Paso {st.session_state.step_count + 1}: ({state}, {symbol}) → ERROR")
        st.session_state.history.append(st.session_state.result_msg)

def run_all():
    """Ejecuta automáticamente hasta terminar o límite de seguridad."""
    limit = 0
    while not st.session_state.finished and limit < 1000:
        step()
        limit += 1

# --- INTERFAZ DE USUARIO (FRONTEND) ---

st.title("🤖 Simulador de Máquina de Turing")
st.markdown("Validador de cadenas y simulador de operaciones paso a paso.")

# Sidebar para controles
with st.sidebar:
    st.header("Configuración")
    machine_option = st.selectbox(
        "Selecciona la Máquina:",
        ["Incremento Binario (n+1)", "Lenguaje a^n b^n c^n"]
    )
    
    input_val = st.text_input("Ingresa la cadena de entrada:", value="1011" if "Binario" in machine_option else "aabbcc")
    
    if st.button("Cargar / Reiniciar Máquina", use_container_width=True):
        initialize_simulation(input_val, machine_option)
        st.success("Máquina cargada y lista.")

# Verificar si la simulación está inicializada
if 'tape' not in st.session_state:
    initialize_simulation(input_val, machine_option)

# --- ÁREA PRINCIPAL ---

# 1. Visualización de la Cinta
st.subheader("📼 Cinta de la Máquina")

# Renderizar cinta con HTML/CSS
tape_html = '<div class="tape-container">'
visible_range_start = max(0, st.session_state.head - 6)
visible_range_end = min(len(st.session_state.tape), st.session_state.head + 7)

for i in range(visible_range_start, visible_range_end):
    char = st.session_state.tape[i]
    # Resaltar la posición del cabezal
    if i == st.session_state.head:
        tape_html += f'<div class="tape-cell active-head">{char}</div>'
    else:
        tape_html += f'<div class="tape-cell">{char}</div>'
tape_html += '</div>'

st.markdown(tape_html, unsafe_allow_html=True)

# Información de Estado
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Estado Actual", st.session_state.state)
with c2:
    st.metric("Posición Cabezal", st.session_state.head)
with c3:
    st.metric("Pasos", st.session_state.step_count)

st.divider()

# 2. Controles de Ejecución
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("👟 Ejecutar Paso a Paso", use_container_width=True, disabled=st.session_state.finished):
        step()
        st.rerun() # Recargar para actualizar visualmente

with col_btn2:
    if st.button("⏩ Ejecutar Todo Automáticamente", use_container_width=True, disabled=st.session_state.finished):
        with st.spinner('Ejecutando máquina...'):
            run_all()
        st.rerun()

# 3. Log de Salida (Consola)
st.subheader("📜 Historial de Ejecución")
log_text = "\n".join(st.session_state.history)

# Usamos un contenedor con estilo para simular una terminal
st.markdown(f"""
<div class="step-log">
<pre>{log_text}</pre>
</div>
""", unsafe_allow_html=True)

if st.session_state.finished:
    if "ACEPTADA" in st.session_state.result_msg or "PROCESADA" in st.session_state.result_msg:
        st.success(st.session_state.result_msg)
    else:
        st.error(st.session_state.result_msg)