# -*- coding: utf-8 -*-
"""
Created on Sun Oct 12 17:42:47 2025

@author: Stiven Barreto
"""

import numpy as np
import matplotlib.pyplot as plt
import math
import streamlit as st

# --- 1. PARÁMETROS DEL SISTEMA ---
Temperatura_K = 300
kB = 1.380649e-23
bw_medidor = 1e6
N_Piso_dBm = 10 * np.log10(kB * Temperatura_K * bw_medidor * 1000)

# --- FUNCIONES AUXILIARES ---
def uw_to_dbm(P_uw):
    return 10 * np.log10(P_uw / 1000)

def dbm_to_uw(P_dBm):
    return 10 ** (P_dBm / 10) * 1000

def get_espectro_individual(f, fc, bw, P_pico, N_Piso_dBm):
    espectro = np.full_like(f, N_Piso_dBm)
    fmin = fc - bw / 2
    fmax = fc + bw / 2
    mask = (f >= fmin) & (f <= fmax)
    espectro[mask] = P_pico - 3 * (np.abs(f[mask] - fc) / (bw / 2))
    return espectro

# Configuración general de la cadena
combinador_perdida_dB = 0.0
ganancia_amp_dB = 20.0
perdida_ltx_dB = 7.5
ganancia_ant_dBi = 24.0
G_total_dB = ganancia_amp_dB - perdida_ltx_dB + ganancia_ant_dBi
N_Piso_dBm = calcular_piso_ruido(Temperatura_K, bw_medidor)

# --- CONFIGURACIÓN DE TRANSMISORES ---
st.sidebar.subheader("📡 Transmisores")
lista_tx = []
for i in range(3):
    with st.sidebar.expander(f"Transmisor {i+1}"):
        activo = st.checkbox(f"Activar Tx{i+1}", True, key=f"tx{i}_activo")
        P_tx_uW = st.number_input(f"Potencia (µW)", 0.0, 1e6, 1000.0, key=f"tx{i}_P")
        Fc = st.number_input(f"Frecuencia Central (MHz)", 10.0, 1000.0, 100.0 + 100*i, key=f"tx{i}_Fc") * 1e6
        Bw_tx = st.number_input(f"Ancho de Banda (MHz)", 1.0, 200.0, 20.0, key=f"tx{i}_Bw") * 1e6
        color = ['blue', 'green', 'orange'][i]
        lista_tx.append({"activo": activo, "P_tx_uW": P_tx_uW, "Fc": Fc, "Bw_tx": Bw_tx, "color": color})

# --- BOTÓN DE EJECUCIÓN ---
if st.button("📈 Calcular y Mostrar Resultados"):
    activos = [tx for tx in lista_tx if tx['activo']]
    if not activos:
        st.error("❌ Debes activar al menos un transmisor.")
    else:
        # --- CÁLCULOS ---
        f_min_grafico = min(tx['Fc'] - tx['Bw_tx']/2 for tx in activos) - 5e6
        f_max_grafico = max(tx['Fc'] + tx['Bw_tx']/2 for tx in activos) + 5e6
        f_eje = np.linspace(f_min_grafico, f_max_grafico, 2000)
        espectro_total = np.full_like(f_eje, N_Piso_dBm)

        for tx in activos:
            P_individual_dBm = uw_to_dbm(tx['P_tx_uW']) - combinador_perdida_dB
            P_pico = P_individual_dBm + G_total_dB
            espectro_total = np.maximum(espectro_total, get_espectro_individual(f_eje, tx['Fc'], tx['Bw_tx'], P_pico, N_Piso_dBm))

        # --- GRAFICAR ---
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
            ax.text(tx_data['Fc']/1e6, N_Piso_dBm - 15,
                    f"Fc: {tx_data['Fc']/1e6:.1f} MHz",
                    ha='center', va='top', color=color, fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
            ax.text(tx_data['f_min']/1e6, N_Piso_dBm - 10,
                    f"{tx_data['f_min']/1e6:.1f} MHz",
                    ha='center', va='top', color=color, fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))
            ax.text(tx_data['f_max']/1e6, N_Piso_dBm - 10,
                    f"{tx_data['f_max']/1e6:.1f} MHz",
                    ha='center', va='top', color=color, fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))
            ax.text(f_min_grafico/1e6 + 50, tx_data['P_pico'],
                    f"{tx_data['nombre']}: {tx_data['P_pico']:.2f} dBm",
                    ha='left', va='center', color=color, fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
        
        ax.text(f_min_grafico/1e6 + 50, N_Piso_dBm,
                f"Ruido: {N_Piso_dBm:.2f} dBm",
                ha='left', va='center', color='red', fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="mistyrose", alpha=0.8))
        
        ax.axhline(y=N_Piso_dBm, color='red', linestyle=':', label=f'Piso de Ruido: {N_Piso_dBm:.2f} dBm')
        ax.set_xlabel('Frecuencia (MHz)')
        ax.set_ylabel('Potencia (dBm)')
        ax.set_title('Espectro de Potencias - Sistema de Transmisores')
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.6)
        st.pyplot(fig)

        # --- RESULTADOS TEXTUALES ---
        st.subheader("📋 Resultados del Sistema")
        texto = []
        texto.append("=== SISTEMA DE 3 TRANSMISORES ===")
        texto.append("\n--- Configuración de Transmisores ---")
        for i, tx in enumerate(lista_tx, 1):
            if tx['activo']:
                P_individual_dBm = uw_to_dbm(tx['P_tx_uW']) - combinador_perdida_dB
                P_pico_individual_dBm = P_individual_dBm + G_total_dB
                f_min = tx['Fc'] - tx['Bw_tx']/2
                f_max = tx['Fc'] + tx['Bw_tx']/2
                texto.append(f"Tx{i}: {tx['P_tx_uW']} μW, Fc: {tx['Fc']/1e6:.0f} MHz, BW: {tx['Bw_tx']/1e6:.0f} MHz")
                texto.append(f"     Pico: {P_pico_individual_dBm:.2f} dBm, Fmin: {f_min/1e6:.1f} MHz, Fmax: {f_max/1e6:.1f} MHz")
            else:
                texto.append(f"Tx{i}: INACTIVO")

        texto.append("\n--- Cadena de Transmisión ---")
        texto.append(f"Pérdida del Combinador: {combinador_perdida_dB:.1f} dB")
        texto.append(f"Ganancia del Amplificador: {ganancia_amp_dB:.1f} dB")
        texto.append(f"Pérdida en Línea de Tx: {perdida_ltx_dB:.1f} dB")
        texto.append(f"Ganancia de Antena: {ganancia_ant_dBi:.1f} dBi")
        texto.append(f"Ganancia Total del Sistema: {G_total_dB:.2f} dB")

        P_total_uw = sum(tx['P_tx_uW'] for tx in lista_tx if tx['activo'])
        P_combinada_dBm = uw_to_dbm(P_total_uw) - combinador_perdida_dB

        texto.append("\n--- Potencias ---")
        texto.append(f"Potencia Total Combinada: {P_total_uw:.1f} μW = {P_combinada_dBm:.2f} dBm")
        texto.append(f"Pico de Potencia Radiada Total: {P_combinada_dBm + G_total_dB:.2f} dBm")

        texto.append("\n--- Parámetros de Ruido ---")
        texto.append(f"Piso de Ruido Térmico: {N_Piso_dBm:.2f} dBm")
        texto.append("-" * 60)

        st.text("\n".join(texto))

