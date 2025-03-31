import pandas as pd
import streamlit as st
from bisect import bisect_left
from fpdf import FPDF
import datetime
import unicodedata
import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Tuple

# Configuración de logging
logging.basicConfig(filename='uso_beta.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

def log_action(email: str, action: str):
    logging.info(f"Usuario: {email}, Acción: {action}")

# Definición de tablas como clase para mayor eficiencia
@dataclass
class TablaTarifas:
    rangos: List[Tuple[float, float, float, float]]
    limites: List[float] = None

    def __post_init__(self):
        self.limites = [rango[0] for rango in self.rangos]

    def calcular(self, valor: float, usa_factor: bool = True) -> float:
        idx = bisect_left(self.limites, valor)
        if idx == 0:
            return 0
        lim_inf, _, cuota_fija, factor = self.rangos[idx - 1]
        if not usa_factor:
            return cuota_fija
        return round(cuota_fija + (valor - lim_inf) * factor, 2)

@dataclass
class TablaHonorarios(TablaTarifas):
    def calcular(self, valor: float) -> float:
        idx = bisect_left(self.limites, valor)
        if idx == 0:
            return 0
        if idx == len(self.rangos):
            lim_inf = self.rangos[-1][0]
            cuota_fija = self.rangos[-2][2]  # Base acumulada del penúltimo rango
            factor = self.rangos[-1][3]
        else:
            lim_inf, _, cuota_fija, factor = self.rangos[idx - 1]
        honorarios = cuota_fija + (valor - lim_inf) * factor
        return round(honorarios * 1.18, 2)  # Incluye 18%

# Tablas predefinidas
IMPUESTO_ADQUISICION = TablaTarifas([
    (0.12, 123988.81, 314.97, 0.01392),
    (123988.82, 198382.03, 2040.90, 0.02967),
    (198382.04, 297572.76, 4248.16, 0.03876),
    (297572.77, 595145.67, 8092.80, 0.04522),
    (595145.68, 1487864.15, 21549.06, 0.05023),
    (1487864.16, 2975728.34, 66390.32, 0.05487),
    (2975728.35, 5732476.11, 148029.44, 0.05952),
    (5732476.12, 14928323.92, 312111.08, 0.06183),
    (14928323.93, 27529938.63, 880690.36, 0.06251),
    (27529938.64, 55059877.21, 1668417.30, 0.06300),
    (55059877.22, float('inf'), 3402803.44, 0.08679),
])

DERECHOS_REGISTRO = TablaTarifas([
    (0.01, 848550.00, 2411.00, 0),
    (848550.01, 1018260.00, 7233.00, 0),
    (1018260.01, 1187970.00, 12055.00, 0),
    (1187970.01, 1357680.00, 16877.00, 0),
    (1357680.01, float('inf'), 24154.00, 0),
])

HONORARIOS = TablaHonorarios([
    (0.01, 227607.00, 6632.00, 0),
    (227607.01, 455214.00, 9193.00, 0.01125),
    (455214.01, 910432.00, 13631.00, 0.00975),
    (910432.01, 1820862.00, 21142.00, 0.00825),
    (1820862.01, 3641729.00, 33433.00, 0.00675),
    (3641729.01, 7283459.00, 54482.00, 0.00578),
    (7283459.01, 14566923.00, 85073.00, 0.00420),
    (14566923.01, float('inf'), 0, 0.00327),
])

CONDONACION_HERENCIA = {2326313.00: 0.80, 2736839.00: 0.40}
CONDONACION_ADQUISICION = {448061.00: 0.60, 896120.00: 0.40, 1344180.00: 0.30, 1642105.00: 0.20, 2326313.00: 0.10}

# Funciones optimizadas
def normalize_text(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')

def obtener_condonacion(valor: float, tipo_operacion: str) -> float:
    condonaciones = CONDONACION_HERENCIA if normalize_text(tipo_operacion) == "herencia" else CONDONACION_ADQUISICION
    for limite, porcentaje in sorted(condonaciones.items()):
        if valor <= limite:
            return porcentaje
    return 0.0

def calcular_total(valor_operacion: float, valor_catastral: float, tipo_operacion: str) -> Tuple[Dict, float]:
    condonacion = obtener_condonacion(valor_catastral, tipo_operacion)
    honorarios = HONORARIOS.calcular(valor_operacion)
    iva = round(honorarios * 0.16, 2)
    erogaciones = 16000.0
    avaluo = round(valor_operacion * 0.00195 * 1.16, 2) if condonacion in {0, 0.10, 0.20} else 0.0

    detalles = {"Honorarios": honorarios, "IVA": iva, "Erogaciones": erogaciones, "Avalúo": avaluo}
    if condonacion > 0:
        impuesto_con = IMPUESTO_ADQUISICION.calcular(valor_catastral) * (1 - condonacion)
        derechos_con = DERECHOS_REGISTRO.calcular(valor_catastral, usa_factor=False) * (1 - condonacion)
        total_con = impuesto_con + derechos_con + honorarios + iva + erogaciones + avaluo
        detalles.update({
            "ISAI Con Condonación": round(impuesto_con, 2),
            "Derechos de R.P.P. Con Condonación": round(derechos_con, 2),
            "Condonación Aplicada": f"{condonacion * 100}%"
        })
        resultados = {"Total Con Condonación": round(total_con, 2)}
        if condonacion == 0.10:
            impuesto_sin = IMPUESTO_ADQUISICION.calcular(valor_operacion)
            derechos_sin = DERECHOS_REGISTRO.calcular(valor_operacion, usa_factor=False)
            total_sin = impuesto_sin + derechos_sin + honorarios + iva + erogaciones + avaluo
            resultados["Total Sin Condonación"] = round(total_sin, 2)
            detalles.update({"ISAI Sin Condonación": impuesto_sin, "Derechos Sin Condonación": derechos_sin})
    else:
        impuesto = IMPUESTO_ADQUISICION.calcular(valor_operacion)
        derechos = DERECHOS_REGISTRO.calcular(valor_operacion, usa_factor=False)
        total = impuesto + derechos + honorarios + iva + erogaciones + avaluo
        resultados = {"Total": round(total, 2)}
        detalles.update({
            "Impuesto Sobre Adquisicion de Inmuebles": impuesto,
            "Derechos Registro Público": derechos,
            "Condonación Aplicada": "No aplica"
        })

    resultados["Detalles"] = detalles
    return resultados, condonacion

# Funciones de interfaz (sin cambios significativos, solo optimización menor)
def mostrar_pagina_correo():
    st.title("Calculadora Impuestos, Derechos, Erogaciones y Honorarios Beta")
    st.write("Prueba BETA. Ingresa tu correo para continuar. Se recopilan acciones y tiempo de uso para mejorar la experiencia.")
    email = st.text_input("Ingresa tu correo")
    if st.button("Continuar") and email:
        st.session_state["email"] = email
        log_action(email, "Inicio de sesión")
        st.session_state["start_time"] = time.time()
        st.rerun()
    elif st.button("Continuar"):
        st.error("Ingresa un correo válido.")

def mostrar_calculadora():
    st.title("Calculadora de Impuestos, Derechos, Gastos y Honorarios CDMX")
    st.write(f"Bienvenido, {st.session_state['email']}. Proporcione los valores para su cotización.")
    st.write("© Jaime Alberto Tovar.")

    col1, col2 = st.columns(2)
    with col1:
        valor_operacion = st.number_input("Valor del inmueble:", min_value=0.0, format="%f", key="valor_operacion")
    with col2:
        valor_catastral = st.number_input("Valor catastral (opcional):", min_value=0.0, format="%f", key="valor_catastral", value=valor_operacion)

    tipo_operacion = st.selectbox("Tipo de operación:", ["adquisicion", "Herencia"], key="tipo_operacion")
    usuario = st.text_input("Nombre del usuario (opcional):", key="usuario")

    if st.button("Calcular", key="calcular"):
        resultados, condonacion = calcular_total(valor_operacion, valor_catastral, tipo_operacion)
        mostrar_resultados(resultados)
        pdf_file = generar_pdf(resultados, usuario, valor_operacion, valor_catastral, condonacion)
        with open(pdf_file, "rb") as f:
            st.download_button("Descargar PDF", f, file_name="reporte_gastos_notariales.pdf", key="descargar_pdf")
        log_action(st.session_state["email"], f"Cálculo - Operación: {valor_operacion}, Catastral: {valor_catastral}")

    st.subheader("Comentarios")
    comentario = st.text_area("Comentarios o sugerencias:")
    if st.button("Enviar comentario") and comentario:
        log_action(st.session_state["email"], f"Comentario: {comentario}")
        st.success("¡Gracias por tu comentario!")
    elif st.button("Enviar comentario"):
        st.error("Escribe un comentario primero.")

    codigo_secreto = st.text_input("Acceso de Administrador", type="password")
    if codigo_secreto == "Bbvcg Ehzqj":
        try:
            with open('uso_beta.log', 'rb') as file:
                st.download_button(label="Descargar log", data=file, file_name="uso_beta.log", mime="text/plain")
        except FileNotFoundError:
            st.error("Log no disponible.")

    if st.button("Terminar"):
        tiempo_total = time.time() - st.session_state["start_time"]
        log_action(st.session_state["email"], f"Fin - Tiempo: {tiempo_total:.2f} segundos")
        del st.session_state["email"], st.session_state["start_time"]
        st.rerun()

def generar_pdf(resultados, usuario, valor_operacion, valor_catastral, condonacion):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Reporte de Gastos Notariales", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Fecha: {datetime.date.today()}", ln=True, align="L")
    if usuario:
        pdf.cell(0, 10, f"Realizado por: {usuario}", ln=True, align="L")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Valores Utilizados:", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Valor de operación: ${valor_operacion:,.2f}" if condonacion == 0 else f"Con condonación: ${valor_catastral:,.2f}", ln=True)
    if condonacion == 0.10:
        pdf.cell(0, 10, f"Sin condonación: ${valor_operacion:,.2f}", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(100, 10, "Concepto", 1)
    pdf.cell(50, 10, "Valor", 1, ln=True)
    pdf.set_font("Arial", "", 12)
    for key, value in resultados["Detalles"].items():
        pdf.cell(100, 10, key, 1)
        pdf.cell(50, 10, f"${value:,.2f}" if isinstance(value, (int, float)) else value, 1, ln=True)
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    for key, value in resultados.items():
        if key != "Detalles":
            pdf.cell(100, 10, key, 1)
            pdf.cell(50, 10, f"${value:,.2f}", 1, ln=True)
    
    pdf_file = "reporte_gastos_notariales.pdf"
    pdf.output(pdf_file)
    return pdf_file

def mostrar_resultados(resultados):
    df = pd.DataFrame([(k, f"${v:,.2f}" if isinstance(v, (int, float)) else v) for k, v in resultados["Detalles"].items()], 
                      columns=["Concepto", "Valor"])
    st.subheader("Detalles del Cálculo")
    st.table(df)
    
    st.subheader("Totales")
    for key, value in resultados.items():
        if key != "Detalles":
            st.markdown(f"**{key}:** ${value:,.2f}")

if "email" not in st.session_state:
    mostrar_pagina_correo()
else:
    mostrar_calculadora()
