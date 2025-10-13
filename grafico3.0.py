# -*- coding: utf-8 -*-
"""
Created on Sun Oct 12 17:42:47 2025

@author: Stiven Barreto
"""

import numpy as np
import matplotlib.pyplot as plt
import math
import streamlit as st

# --- PARÁMETROS DEL SISTEMA ---
Temperatura_K = 300
kB = 1.380649e-23
bw_medidor = 1e6

# --- FUNCIONES AUXILIARES ---
def uw_to_dbm(P_uw):
    return 10 * np.log10(P_uw / 1000.0)

def calcular_piso_ruido(T, B):
    kTB_W = kB * T * B
    N_dBm = 10 * np.log10(kTB_W) + 30
    return N_dBm

def get_espectro_individual(f, Fc, Bw_tx, potencia_dBm, N_Piso_dBm):
    sigma = Bw_tx / 2.5
    potencia_relativa = np.exp(-0.5 * ((f - Fc) / sigma) ** 2)
    log_caida = 10 * np.log10(potencia_relativa + 1e-10)
    espectro_señal = potencia_dBm + log_caida
    espectro_final = np.maximum(espectro_señal, N_Piso_dBm)
    return espectro_final

def get_espectro_total(f, transmisores, combinador_perdida_dB, G_total_dB, N_Piso_dBm):
    espectro_total = np.full_like(f, N_Piso_dBm)
    for tx in transmisores:
        if tx['activo']:
            P_individual_dBm = uw_to_dbm(tx['P_tx_uW']) - combinador_perdida_dB
            P_individual_radiada_dBm = P_individual_dBm + G_total_dB
            espectro_individual = get_espectro_individual(
                f, tx['Fc'], tx['Bw_tx'], P_individual_radiada_dBm, N_Piso_dBm
            )
            potencia_lineal_total = 10 ** (espectro_total / 10) + 10 ** (espectro_individual / 10)
            espectro_total = 10 * np.log10(potencia_lineal_total + 1e-10)
    return espectro_total

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Simulación de Transmisores", layout="wide")
st.title("📡 Simulación de Espectro - Sistema de 3 Transmisores")

colores = ['#0078D7', '#28a745', '#ff9800']

# Configuración general de la cadena
combinador_perdida_dB = 0.0
ganancia_amp_dB = 20.0
perdida_ltx_dB = 7.5
ganancia_ant_dBi = 24.0
G_total_dB = ganancia_amp_dB - perdida_ltx_dB + ganancia_ant_dBi
N_Piso_dBm = calcular_piso_ruido(Temperatura_K, bw_medidor)

# --- ENTRADA DE DATOS ---
st.sidebar.header("📊 Parámetros de Transmisores")
transmisores = []

for i in range(3):
    st.sidebar.subheader(f"Transmisor {i+1}")
    activo = st.sidebar.checkbox(f"Activar Tx{i+1}", value=True)
    P_tx = st.sidebar.number_input(f"Potencia Tx{i+1} (μW)", min_value=0.0, value=1000.0, step=100.0)
    Fc = st.sidebar.number_input(f"Fc Tx{i+1} (MHz)", min_value=1.0, value=2400.0 + i*10, step=1.0)
    Bw = st.sidebar.number_input(f"BW Tx{i+1} (MHz)", min_value=1.0, value=20.0, step=1.0)

    transmisores.append({
        "P_tx_uW": P_tx,
        "Fc": Fc * 1e6,
        "Bw_tx": Bw * 1e6,
        "activo": activo,
        "color": colores[i]
    })

# --- VALIDACIÓN ---
activos = [tx for tx in transmisores if tx["activo"] and tx["P_tx_uW"] > 0]
if not activos:
    st.warning("⚠️ Debe ingresar al menos un transmisor activo con potencia mayor a 0 μW.")
    st.stop()

# --- CÁLCULOS ---
frecuencias_centrales = [tx['Fc'] for tx in activos]
anchos_banda = [tx['Bw_tx'] for tx in activos]
f_min_individuales = [tx['Fc'] - tx['Bw_tx'] / 2 for tx in activos]
f_max_individuales = [tx['Fc'] + tx['Bw_tx'] / 2 for tx in activos]

Bw_max = max(anchos_banda)
sigma_max = Bw_max / 2.5
rango_sigma = 6 * sigma_max
f_min_grafico = min(f_min_individuales) - rango_sigma
f_max_grafico = max(f_max_individuales) + rango_sigma

f_eje = np.linspace(f_min_grafico, f_max_grafico, 2000)
espectro_total = get_espectro_total(f_eje, transmisores, combinador_perdida_dB, G_total_dB, N_Piso_dBm)

# --- GRÁFICA ---
fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(f_eje / 1e6, espectro_total, 'k', linewidth=3, label='Espectro Total', alpha=0.8)

espectros_individuales = []
for i, tx in enumerate(activos):
    P_individual_dBm = uw_to_dbm(tx['P_tx_uW']) - combinador_perdida_dB
    P_pico = P_individual_dBm + G_total_dB
    espectro_ind = get_espectro_individual(f_eje, tx['Fc'], tx['Bw_tx'], P_pico, N_Piso_dBm)
    espectros_individuales.append({
        "nombre": f"Tx{i+1}",
        "color": tx['color'],
        "Fc": tx['Fc'],
        "f_min": tx['Fc'] - tx['Bw_tx']/2,
        "f_max": tx['Fc'] + tx['Bw_tx']/2,
        "P_pico": P_pico
    })

    ax.plot(f_eje / 1e6, espectro_ind, linestyle='--', color=tx['color'], alpha=0.7, label=f"Tx{i+1}")
    ax.axvline(tx['Fc']/1e6, color=tx['color'], linestyle='-')
    ax.axvline((tx['Fc'] - tx['Bw_tx']/2)/1e6, color=tx['color'], linestyle=':')
    ax.axvline((tx['Fc'] + tx['Bw_tx']/2)/1e6, color=tx['color'], linestyle=':')

# --- ANOTACIONES ---
for tx_data in espectros_individuales:
    color = tx_data['color']
    # Anotación para frecuencia central
    ax.text(tx_data['Fc']/1e6, N_Piso_dBm - 15,
            f"Fc: {tx_data['Fc']/1e6:.1f} MHz",
            ha='center', va='top', color=color, fontsize=9,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
    
    # Anotación para frecuencias mínima y máxima
    ax.text(tx_data['f_min']/1e6, N_Piso_dBm - 10,
            f"{tx_data['f_min']/1e6:.1f} MHz",
            ha='center', va='top', color=color, fontsize=8,
            bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))
    
    ax.text(tx_data['f_max']/1e6, N_Piso_dBm - 10,
            f"{tx_data['f_max']/1e6:.1f} MHz",
            ha='center', va='top', color=color, fontsize=8,
            bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))
    
    # Anotación para pico individual
    ax.text(f_min_grafico/1e6 + 50, tx_data['P_pico'],
            f"{tx_data['nombre']}: {tx_data['P_pico']:.2f} dBm",
            ha='left', va='center', color=color, fontsize=9,
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

# Anotación para piso de ruido
ax.text(f_min_grafico/1e6 + 50, N_Piso_dBm,
        f"Ruido: {N_Piso_dBm:.2f} dBm",
        ha='left', va='center', color='red', fontsize=9,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="mistyrose", alpha=0.8))

# --- FORMATO FINAL ---
ax.axhline(y=N_Piso_dBm, color='red', linestyle=':', label=f'Piso de Ruido: {N_Piso_dBm:.2f} dBm')
ax.set_xlabel('Frecuencia (MHz)')
ax.set_ylabel('Potencia (dBm)')
ax.set_title('Espectro de Potencias - Sistema de Transmisores')
ax.legend()
ax.grid(True, linestyle=':', alpha=0.6)

st.pyplot(fig)

# --- RESULTADOS NUMÉRICOS ---
P_total_uw = sum(tx['P_tx_uW'] for tx in activos)
P_combinada_dBm = uw_to_dbm(P_total_uw) - combinador_perdida_dB

st.subheader("📈 Resultados del Sistema")
st.write(f"**Potencia Total Combinada:** {P_total_uw:.2f} μW = {P_combinada_dBm:.2f} dBm")
st.write(f"**Ganancia Total:** {G_total_dB:.2f} dB")
st.write(f"**Pico Total Radiado:** {P_combinada_dBm + G_total_dB:.2f} dBm")
st.write(f"**Piso de Ruido:** {N_Piso_dBm:.2f} dBm")

st.markdown("---")
st.subheader("📡 Detalles por Transmisor")
for i, tx_data in enumerate(espectros_individuales):
    st.markdown(f"**{tx_data['nombre']}** | Fc: `{tx_data['Fc']/1e6:.2f} MHz` | BW: `{(tx_data['f_max']-tx_data['f_min'])/1e6:.2f} MHz` | Pico: `{tx_data['P_pico']:.2f} dBm`")

















