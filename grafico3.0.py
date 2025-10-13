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
N_Piso_dBm = 10 * np.log10(kB * Temperatura_K * bw_medidor) + 30
combinador_perdida_dB = 6
ganancia_amp_dB = 20
perdida_ltx_dB = 2
ganancia_ant_dBi = 10
G_total_dB = ganancia_amp_dB - perdida_ltx_dB + ganancia_ant_dBi

# --- FUNCIONES AUXILIARES ---
def uw_to_dbm(uw):
    return 10 * np.log10(uw) if uw > 0 else -np.inf

def dbm_to_uw(dbm):
    return 10 ** (dbm / 10)

def get_espectro_individual(f, fc, bw, p_pico, n_piso):
    potencia = np.full_like(f, n_piso)
    idx = np.logical_and(f >= (fc - bw/2), f <= (fc + bw/2))
    potencia[idx] = p_pico
    return potencia

# --- INTERFAZ STREAMLIT ---
st.title("📡 Sistema de 3 Transmisores")
st.markdown("Visualización del **espectro combinado**, con anotaciones y parámetros del sistema.")

# --- ENTRADA DE DATOS ---
st.sidebar.header("Configuración de Transmisores")
lista_tx = []
for i in range(3):
    with st.sidebar.expander(f"Transmisor {i+1}"):
        activo = st.checkbox(f"Activar Tx{i+1}", True, key=f"activo_{i}")
        if activo:
            P_tx_uW = st.number_input(f"Potencia Tx{i+1} (μW)", 0.1, 1000.0, 100.0)
            Fc = st.number_input(f"Frecuencia Central Tx{i+1} (MHz)", 10.0, 5000.0, 100.0)
            Bw_tx = st.number_input(f"Ancho de Banda Tx{i+1} (MHz)", 0.1, 100.0, 10.0)
        else:
            P_tx_uW, Fc, Bw_tx = 0, 0, 0
        lista_tx.append({
            "activo": activo,
            "P_tx_uW": P_tx_uW,
            "Fc": Fc * 1e6,
            "Bw_tx": Bw_tx * 1e6,
            "color": ["blue", "green", "orange"][i]
        })

# --- BOTÓN PARA GRAFICAR ---
if st.button("📊 Generar Gráfica y Resultados"):
    activos = [tx for tx in lista_tx if tx['activo']]
    if not activos:
        st.warning("Activa al menos un transmisor para mostrar resultados.")
    else:
        f_min_grafico = min(tx['Fc'] - tx['Bw_tx']/2 for tx in activos) - 1e6
        f_max_grafico = max(tx['Fc'] + tx['Bw_tx']/2 for tx in activos) + 1e6
        f_eje = np.linspace(f_min_grafico, f_max_grafico, 2000)
        espectro_total = np.full_like(f_eje, N_Piso_dBm)

        espectros_individuales = []
        P_total_uw = 0
        for i, tx in enumerate(activos):
            P_individual_dBm = uw_to_dbm(tx['P_tx_uW']) - combinador_perdida_dB
            P_pico = P_individual_dBm + G_total_dB
            espectro_ind = get_espectro_individual(f_eje, tx['Fc'], tx['Bw_tx'], P_pico, N_Piso_dBm)
            espectro_total = np.maximum(espectro_total, espectro_ind)
            P_total_uw += tx['P_tx_uW']
            espectros_individuales.append({
                "nombre": f"Tx{i+1}",
                "color": tx['color'],
                "Fc": tx['Fc'],
                "f_min": tx['Fc'] - tx['Bw_tx']/2,
                "f_max": tx['Fc'] + tx['Bw_tx']/2,
                "P_pico": P_pico
            })

        P_combinada_dBm = uw_to_dbm(P_total_uw) - combinador_perdida_dB

        # --- GRÁFICA ---
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(f_eje / 1e6, espectro_total, 'k', linewidth=3, label='Espectro Total', alpha=0.8)

        for tx in espectros_individuales:
            ax.plot(f_eje / 1e6, get_espectro_individual(f_eje, tx['Fc'], tx['f_max']-tx['f_min'], tx['P_pico'], N_Piso_dBm),
                    linestyle='--', color=tx['color'], alpha=0.7, label=tx['nombre'])
            ax.axvline(tx['Fc']/1e6, color=tx['color'], linestyle='-')
            ax.axvline(tx['f_min']/1e6, color=tx['color'], linestyle=':')
            ax.axvline(tx['f_max']/1e6, color=tx['color'], linestyle=':')

        # --- ANOTACIONES ---
        for tx_data in espectros_individuales:
            color = tx_data['color']
            ax.text(tx_data['Fc']/1e6, N_Piso_dBm - 15, f'Fc: {tx_data["Fc"]/1e6:.1f} MHz',
                    ha='center', va='top', color=color, fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
            ax.text(tx_data['f_min']/1e6, N_Piso_dBm - 10, f'{tx_data["f_min"]/1e6:.1f} MHz',
                    ha='center', va='top', color=color, fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))
            ax.text(tx_data['f_max']/1e6, N_Piso_dBm - 10, f'{tx_data["f_max"]/1e6:.1f} MHz',
                    ha='center', va='top', color=color, fontsize=8,
                    bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))
            ax.text(f_min_grafico/1e6 + 50, tx_data['P_pico'],
                    f'{tx_data["nombre"]}: {tx_data["P_pico"]:.2f} dBm',
                    ha='left', va='center', color=color, fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

        ax.text(f_min_grafico/1e6 + 50, N_Piso_dBm, f'Ruido: {N_Piso_dBm:.2f} dBm',
                ha='left', va='center', color='red', fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="mistyrose", alpha=0.8))

        ax.axhline(y=N_Piso_dBm, color='red', linestyle=':', label=f'Piso de Ruido: {N_Piso_dBm:.2f} dBm')
        ax.set_xlabel('Frecuencia (MHz)')
        ax.set_ylabel('Potencia (dBm)')
        ax.set_title('Espectro de Potencias - Sistema de Transmisores')
        ax.legend()
        ax.grid(True, linestyle=':', alpha=0.6)

        st.pyplot(fig)

        # --- RESULTADOS ---
        st.subheader("📋 Resultados del Sistema")
        texto = "=== SISTEMA DE 3 TRANSMISORES ===\n\n--- Configuración de Transmisores ---\n"
        for i, tx in enumerate(lista_tx, 1):
            if tx['activo']:
                P_individual_dBm = uw_to_dbm(tx['P_tx_uW']) - combinador_perdida_dB
                P_pico_individual_dBm = P_individual_dBm + G_total_dB
                f_min = tx['Fc'] - tx['Bw_tx']/2
                f_max = tx['Fc'] + tx['Bw_tx']/2
                texto += (f"Tx{i}: {tx['P_tx_uW']} μW, Fc: {tx['Fc']/1e6:.0f} MHz, BW: {tx['Bw_tx']/1e6:.0f} MHz\n"
                          f"     Pico: {P_pico_individual_dBm:.2f} dBm, "
                          f"Fmin: {f_min/1e6:.1f} MHz, Fmax: {f_max/1e6:.1f} MHz\n")
            else:
                texto += f"Tx{i}: INACTIVO\n"

        texto += ("\n--- Cadena de Transmisión ---\n"
                  f"Pérdida del Combinador: {combinador_perdida_dB:.1f} dB\n"
                  f"Ganancia del Amplificador: {ganancia_amp_dB:.1f} dB\n"
                  f"Pérdida en Línea de Tx: {perdida_ltx_dB:.1f} dB\n"
                  f"Ganancia de Antena: {ganancia_ant_dBi:.1f} dBi\n"
                  f"Ganancia Total del Sistema: {G_total_dB:.2f} dB\n\n"
                  "--- Potencias ---\n"
                  f"Potencia Total Combinada: {P_total_uw:.1f} μW = {P_combinada_dBm:.2f} dBm\n"
                  f"Pico de Potencia Radiada Total: {P_combinada_dBm + G_total_dB:.2f} dBm\n\n"
                  "--- Parámetros de Ruido ---\n"
                  f"Piso de Ruido Térmico: {N_Piso_dBm:.2f} dBm\n"
                  + "-"*60)

        st.text_area("Resultados detallados", texto, height=400)









