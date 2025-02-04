import pandas as pd
import streamlit as st

# Funciones para el cálculo de impuestos, honorarios, derechos de registro, erogaciones y jornadas

def calcular_impuesto_adquisicion(valor):
    tabla = [
        {"limite_inferior": 0.12, "limite_superior": 123988.81, "costo_fijo": 314.97, "factor": 0.01392},
        {"limite_inferior": 123988.82, "limite_superior": 198382.03, "costo_fijo": 2040.90, "factor": 0.02967},
        {"limite_inferior": 198382.04, "limite_superior": 297572.76, "costo_fijo": 4248.16, "factor": 0.03876},
        {"limite_inferior": 297572.77, "limite_superior": 595145.67, "costo_fijo": 8092.80, "factor": 0.04522},
        {"limite_inferior": 595145.68, "limite_superior": 1487864.15, "costo_fijo": 21549.06, "factor": 0.05023},
        {"limite_inferior": 1487864.16, "limite_superior": 2975728.34, "costo_fijo": 66390.32, "factor": 0.05487},
        {"limite_inferior": 2975728.35, "limite_superior": 5732476.11, "costo_fijo": 148029.44, "factor": 0.05952},
        {"limite_inferior": 5732476.12, "limite_superior": float('inf'), "costo_fijo": 312111.08, "factor": 0.06183}
    ]

    for rango in tabla:
        if rango["limite_inferior"] <= valor <= rango["limite_superior"]:
            return rango["costo_fijo"] + ((valor - rango["limite_inferior"]) * rango["factor"])
    return 0

def calcular_derechos_registro(valor):
    tabla = [
        {"limite_inferior": 0.01, "limite_superior": 848550.00, "total": 2411.00},
        {"limite_inferior": 848550.01, "limite_superior": 1018260.00, "total": 7233.00},
        {"limite_inferior": 1018260.01, "limite_superior": 1187970.00, "total": 12055.00},
        {"limite_inferior": 1187970.01, "limite_superior": 1357680.00, "total": 16877.00},
        {"limite_inferior": 1357680.01, "limite_superior": float('inf'), "total": 24154.00}
    ]

    for rango in tabla:
        if rango["limite_inferior"] <= valor <= rango["limite_superior"]:
            return rango["total"]
    return 0

def calcular_honorarios(valor):
    tabla = [
        {"limite_inferior": 0.01, "limite_superior": 227607.00, "adicion": 6632.00, "factor": 0},
        {"limite_inferior": 227607.01, "limite_superior": 455214.00, "adicion": 9193.00, "factor": 0.01125},
        {"limite_inferior": 455214.01, "limite_superior": 910432.00, "adicion": 13631.00, "factor": 0.00975},
        {"limite_inferior": 910432.01, "limite_superior": 1820862.00, "adicion": 21142.00, "factor": 0.00825},
        {"limite_inferior": 1820862.01, "limite_superior": 3641729.00, "adicion": 33433.00, "factor": 0.00675},
        {"limite_inferior": 3641729.01, "limite_superior": 7283459.00, "adicion": 54482.00, "factor": 0.00578},
        {"limite_inferior": 7283459.01, "limite_superior": 14566923.00, "adicion": 85073.00, "factor": 0.00420},
        {"limite_inferior": 14566923.01, "limite_superior": float('inf'), "adicion": 0, "factor": 0.00327}
    ]

    for rango in tabla:
        if rango["limite_inferior"] <= valor <= rango["limite_superior"]:
            return rango["adicion"] + ((valor - rango["limite_inferior"]) * rango["factor"])
    return 0

def calcular_avaluo(valor, condonacion):
    if condonacion in [0.10, 0.20] or condonacion == 0:
        return (valor * 1.95 / 1000) * 1.16
    return 0

def calcular_iva(honorarios):
    return honorarios * 0.16

def calcular_erogaciones():
    return 16000

def obtener_condonacion(valor_catastral, tipo_operacion):
    if tipo_operacion == "herencia":
        if valor_catastral <= 2326313.00:
            return 0.80
        elif 2326313.01 <= valor_catastral <= 2736839.00:
            return 0.40
    elif tipo_operacion == "adquisicion":
        if valor_catastral <= 448061.00:
            return 0.60
        elif 448061.01 <= valor_catastral <= 896120.00:
            return 0.40
        elif 896120.01 <= valor_catastral <= 1344180.00:
            return 0.30
        elif 1344180.01 <= valor_catastral <= 1642105.00:
            return 0.20
        elif 1642105.01 <= valor_catastral <= 2326313.00:
            return 0.10
    return 0.0

def calcular_total_general(valor, valor_catastral, tipo_operacion):
    condonacion = obtener_condonacion(valor_catastral, tipo_operacion)
    valor_para_calculo = valor_catastral if condonacion > 0 else valor

    # Cálculo sin condonación
    impuesto_sin_condonacion = calcular_impuesto_adquisicion(valor_para_calculo)
    derechos_sin_condonacion = calcular_derechos_registro(valor_para_calculo)
    honorarios_sin_condonacion = calcular_honorarios(valor_para_calculo)
    iva_sin_condonacion = calcular_iva(honorarios_sin_condonacion)
    erogaciones = calcular_erogaciones()
    avaluo_sin_condonacion = calcular_avaluo(valor_para_calculo, 0)

    total_sin_condonacion = impuesto_sin_condonacion + derechos_sin_condonacion + honorarios_sin_condonacion + iva_sin_condonacion + erogaciones + avaluo_sin_condonacion

    # Cálculo con condonación
    impuesto_con_condonacion = impuesto_sin_condonacion * (1 - condonacion)
    derechos_con_condonacion = derechos_sin_condonacion * (1 - condonacion)
    avaluo_con_condonacion = calcular_avaluo(valor_para_calculo, condonacion)

    total_con_condonacion = impuesto_con_condonacion + derechos_con_condonacion + honorarios_sin_condonacion + iva_sin_condonacion + erogaciones + avaluo_con_condonacion

    return {
        "Total Sin Condonación": total_sin_condonacion,
        "Total Con Condonación": total_con_condonacion if condonacion == 0.10 else "No aplica para este porcentaje",
        "Condonación Aplicada": f"{condonacion * 100}%" if condonacion > 0 else "No aplica",
        "Detalles": {
            "Impuesto Sin Condonación": impuesto_sin_condonacion,
            "Derechos Sin Condonación": derechos_sin_condonacion,
            "Avalúo Sin Condonación": avaluo_sin_condonacion,
            "Impuesto Con Condonación": impuesto_con_condonacion,
            "Derechos Con Condonación": derechos_con_condonacion,
            "Avalúo Con Condonación": avaluo_con_condonacion
        }
    }

# Interfaz de usuario con Streamlit
st.title("Calculadora de Gastos Notariales")

valor = st.number_input("Ingrese el valor del inmueble:", min_value=0.0, format="%f")
valor_catastral = st.number_input("Ingrese el valor catastral:", min_value=0.0, format="%f")
tipo_operacion = st.selectbox("Seleccione el tipo de operación:", ["adquisicion", "herencia"])

if st.button("Calcular"):
    resultados = calcular_total_general(valor, valor_catastral, tipo_operacion)

    st.subheader("Resultados")
    for key, value in resultados.items():
        if key != "Detalles":
            st.write(f"{key}: ${value:,.2f}" if isinstance(value, (int, float)) else f"{key}: {value}")

    st.subheader("Detalles del Cálculo")
    for key, value in resultados["Detalles"].items():
        st.write(f"{key}: ${value:,.2f}")
