import pandas as pd
import streamlit as st
from bisect import bisect_left
from fpdf import FPDF
import datetime
import unicodedata

# Tablas predefinidas como diccionarios para búsquedas rápidas
IMPUESTO_ADQUISICION = [
    (0.12, 123988.81, 314.97, 0.01392),
    (123988.82, 198382.03, 2040.90, 0.02967),
    (198382.04, 297572.76, 4248.16, 0.03876),
    (297572.77, 595145.67, 8092.80, 0.04522),
    (595145.68, 1487864.15, 21549.06, 0.05023),
    (1487864.16, 2975728.34, 66390.32, 0.05487),
    (2975728.35, 5732476.11, 148029.44, 0.05952),
    (5732476.12, float('inf'), 312111.08, 0.06183),
]

DERECHOS_REGISTRO = [
    (0.01, 848550.00, 2411.00),
    (848550.01, 1018260.00, 7233.00),
    (1018260.01, 1187970.00, 12055.00),
    (1187970.01, 1357680.00, 16877.00),
    (1357680.01, float('inf'), 24154.00),
]

HONORARIOS = [
    (0.01, 227607.00, 6632.00, 0),
    (227607.01, 455214.00, 9193.00, 0.01125),
    (455214.01, 910432.00, 13631.00, 0.00975),
    (910432.01, 1820862.00, 21142.00, 0.00825),
    (1820862.01, 3641729.00, 33433.00, 0.00675),
    (3641729.01, 7283459.00, 54482.00, 0.00578),
    (7283459.01, 14566923.00, 85073.00, 0.00420),
    (14566923.01, float('inf'), 0, 0.00327),
]

CONDONACION_HERENCIA = {2326313.00: 0.80, 2736839.00: 0.40}
CONDONACION_ADQUISICION = {448061.00: 0.60, 896120.00: 0.40, 1344180.00: 0.30, 1642105.00: 0.20, 2326313.00: 0.10}

# Funciones optimizadas de cálculo
def normalize_text(text):
    # Elimina acentos y normaliza el texto
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def calcular_impuesto_adquisicion(valor):
    limites = [rango[0] for rango in IMPUESTO_ADQUISICION]
    idx = bisect_left(limites, valor)
    if idx == 0:
        return 0
    lim_inf, _, costo_fijo, factor = IMPUESTO_ADQUISICION[idx - 1]
    return costo_fijo + (valor - lim_inf) * factor

def calcular_derechos_registro(valor):
    limites = [rango[0] for rango in DERECHOS_REGISTRO]
    idx = bisect_left(limites, valor)
    return DERECHOS_REGISTRO[idx - 1][2] if idx > 0 else 0

def calcular_honorarios(valor):
    limites = [rango[0] for rango in HONORARIOS]
    idx = bisect_left(limites, valor)
    if idx == 0:
        return 0
    lim_inf, _, adicion, factor = HONORARIOS[idx - 1]
    return adicion + (valor - lim_inf) * factor

def obtener_condonacion(valor_catastral, tipo_operacion):
    tipo_operacion = normalize_text(tipo_operacion.lower())
    print(f"DEBUG: tipo_operacion normalizado = '{tipo_operacion}'")
    
    if tipo_operacion == "herencia":
        for k, v in sorted(CONDONACION_HERENCIA.items()):
            if valor_catastral <= k:
                return v
        return 0.0
    elif tipo_operacion == "adquisicion":
        for k, v in sorted(CONDONACION_ADQUISICION.items()):
            if valor_catastral <= k:
                return v
        return 0.0
    return 0.0

def calcular_total(valor_operacion, valor_catastral, tipo_operacion):
    condonacion = obtener_condonacion(valor_catastral, tipo_operacion)
    
    # Cálculos comunes (siempre con valor de operación)
    honorarios = calcular_honorarios(valor_operacion)
    iva = honorarios * 0.16
    erogaciones = 16000
    avaluo = (valor_operacion * 0.00195) * 1.16 if condonacion in {0, 0.10, 0.20} else 0
    
    if condonacion > 0:
        # Con condonación: Usamos valor catastral para impuesto y derechos
        impuesto_con = calcular_impuesto_adquisicion(valor_catastral) * (1 - condonacion)
        derechos_con = calcular_derechos_registro(valor_catastral) * (1 - condonacion)
        total_con = impuesto_con + derechos_con + honorarios + iva + erogaciones + avaluo
        detalles = {
            "ISAI Con Condonación": impuesto_con,
            "Derechos de R.P.P. Con Condonación": derechos_con,
            "Honorarios": honorarios,
            "IVA": iva,
            "Erogaciones": erogaciones,
            "Avalúo": avaluo,
            "Condonación Aplicada": f"{condonacion * 100}%",
        }
        resultados = {"Total Con Condonación": total_con}
        
        if condonacion == 0.10:
            # Sin condonación: Usamos valor de operación para impuesto y derechos
            impuesto_sin = calcular_impuesto_adquisicion(valor_operacion)
            derechos_sin = calcular_derechos_registro(valor_operacion)
            total_sin = impuesto_sin + derechos_sin + honorarios + iva + erogaciones + avaluo
            resultados["Total Sin Condonación"] = total_sin
            detalles.update({
                "ISAI Sin Condonación": impuesto_sin,
                "Derechos Sin Condonación": derechos_sin,
            })
        # No se añaden claves con 'No aplica' cuando condonacion != 0.10
    
    else:
        # Sin condonación: Usamos valor de operación para todo
        impuesto = calcular_impuesto_adquisicion(valor_operacion)
        derechos = calcular_derechos_registro(valor_operacion)
        total = impuesto + derechos + honorarios + iva + erogaciones + avaluo
        resultados = {"Total": total}
        detalles = {
            "Impuesto Sobre Adquisicion de Inmuebles": impuesto,
            "Derechos Registro Público": derechos,
            "Honorarios": honorarios,
            "IVA": iva,
            "Erogaciones": erogaciones,
            "Avalúo": avaluo,
            "Condonación Aplicada": "No aplica",
        }
    
    resultados["Detalles"] = detalles
    return resultados, condonacion

def generar_pdf(resultados, usuario, valor_operacion, valor_catastral, condonacion):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Reporte de Gastos Notariales", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Fecha: {datetime.date.today()}", ln=True, align="L")
    if usuario:
        pdf.cell(0, 10, f"Realizado por: {usuario}", ln=True, align="L")
    pdf.ln(10)
    
    # Información adicional sobre los valores utilizados
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Valores Utilizados:", ln=True)
    pdf.set_font("Arial", "", 12)
    if condonacion > 0:
        pdf.cell(0, 10, f"Con condonación: ${valor_catastral:,.2f}", ln=True)
        if condonacion == 0.10:
            pdf.cell(0, 10, f"Sin condonación: ${valor_operacion:,.2f}", ln=True)
    else:
        pdf.cell(0, 10, f"Valor de operación: ${valor_operacion:,.2f}", ln=True)
    pdf.ln(10)
    
    # Tabla de detalles
    pdf.set_font("Arial", "B", 12)
    pdf.cell(100, 10, "Concepto", 1)
    pdf.cell(50, 10, "Valor", 1, ln=True)
    pdf.set_font("Arial", "", 12)
    for key, value in resultados["Detalles"].items():
        pdf.cell(100, 10, key, 1)
        pdf.cell(50, 10, f"${value:,.2f}" if isinstance(value, (int, float)) else value, 1, ln=True)
    
    # Totales
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    for key, value in resultados.items():
        if key != "Detalles":
            pdf.cell(100, 10, key, 1)
            pdf.cell(50, 10, f"${value:,.2f}" if isinstance(value, (int, float)) else value, 1, ln=True)
    
    pdf_file = "reporte_gastos_notariales.pdf"
    pdf.output(pdf_file)
    return pdf_file

# Interfaz de Streamlit
st.title("Calculadora de Impuestos, Derechos, Gastos y Honorarios")
st.write("Proporcione los valores para realizar su Cotización.")
st.write("Todos los derechos reservados. Jaime Alberto Tovar.")

# Campos de entrada con claves únicas
col1, col2 = st.columns(2)
with col1:
    valor_operacion = st.number_input("Valor del inmueble (operación):", min_value=0.0, format="%f", key="valor_operacion")
with col2:
    valor_catastral_input = st.number_input("Valor catastral (Opcional):", min_value=0.0, format="%f", value=None, key="valor_catastral")

# Lógica para el valor catastral
if valor_catastral_input is None:
    valor_catastral = valor_operacion
else:
    valor_catastral = valor_catastral_input

tipo_operacion = st.selectbox("Tipo de operación:", ["adquisicion", "Herencia"], key="tipo_operacion").lower()
usuario = st.text_input("Nombre del usuario (opcional):", key="usuario")

if st.button("Calcular", key="calcular"):
    resultados, condonacion = calcular_total(valor_operacion, valor_catastral, tipo_operacion)
    st.subheader("Resultados")
    st.json(resultados)
    
    # Generar y descargar PDF
    pdf_file = generar_pdf(resultados, usuario, valor_operacion, valor_catastral, condonacion)
    with open(pdf_file, "rb") as f:
        st.download_button("Imprimir (Descargar PDF)", f, file_name="reporte_gastos_notariales.pdf", key="descargar_pdf")
