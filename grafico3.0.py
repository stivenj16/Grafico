# -*- coding: utf-8 -*-
"""
Created on Sun Oct 12 17:42:47 2025

@author: Stiven Barreto
"""

import numpy as np
import matplotlib.pyplot as plt
import math
import tkinter as tk
from tkinter import messagebox, ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- 1. PARÁMETROS DEL SISTEMA (Datos de Entrada) ---
Temperatura_K = 300
kB = 1.380649e-23
bw_medidor = 1e6


# --- FUNCIÓN PRINCIPAL PARA EJECUTAR LOS CÁLCULOS Y GRAFICAR ---
def ejecutar_simulacion(transmisores, root):
    combinador_perdida_dB = 0.0
    ganancia_amp_dB = 20.0
    perdida_ltx_dB = 7.5
    ganancia_ant_dBi = 24.0

    def uw_to_dbm(P_uw):
        return 10 * np.log10(P_uw / 1000.0)

    def calcular_piso_ruido(T, B):
        kTB_W = kB * T * B
        N_dBm = 10 * np.log10(kTB_W) + 30
        return N_dBm

    def calcular_potencia_combinada(transmisores, perdida_combinador_dB):
        potencia_total_uw = sum(tx['P_tx_uW'] for tx in transmisores if tx['activo'])
        if potencia_total_uw > 0:
            P_combinada_dBm = uw_to_dbm(potencia_total_uw) - perdida_combinador_dB
        else:
            P_combinada_dBm = -999
        return P_combinada_dBm, potencia_total_uw

    # --- Procesamiento general ---
    P_combinada_dBm, P_total_uw = calcular_potencia_combinada(transmisores, combinador_perdida_dB)
    G_total_dB = ganancia_amp_dB - perdida_ltx_dB + ganancia_ant_dBi
    N_Piso_dBm = calcular_piso_ruido(Temperatura_K, bw_medidor)

    activos = [tx for tx in transmisores if tx['activo']]

    if not activos:
        messagebox.showinfo("Aviso", "Debe ingresar al menos un transmisor activo.")
        return

    frecuencias_centrales = [tx['Fc'] for tx in activos]
    anchos_banda = [tx['Bw_tx'] for tx in activos]
    f_min_individuales = [tx['Fc'] - tx['Bw_tx'] / 2 for tx in activos]
    f_max_individuales = [tx['Fc'] + tx['Bw_tx'] / 2 for tx in activos]

    Bw_max = max(anchos_banda)
    sigma_max = Bw_max / 2.5
    rango_sigma = 6 * sigma_max
    f_min_grafico = min(f_min_individuales) - rango_sigma
    f_max_grafico = max(f_max_individuales) + rango_sigma



    def get_espectro_individual(f, Fc, Bw_tx, potencia_dBm, N_Piso_dBm):
        sigma = Bw_tx / 2.5
        potencia_relativa = np.exp(-0.5 * ((f - Fc) / sigma) ** 2)
        log_caida = 10 * np.log10(potencia_relativa + 1e-10)
        espectro_señal = potencia_dBm + log_caida
        espectro_final = np.maximum(espectro_señal, N_Piso_dBm)
        return espectro_final

    def get_espectro_total(f, transmisores, P_combinada_dBm, G_total_dB, N_Piso_dBm):
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

    # --- GRAFICAR ---
    ventana_grafica = tk.Toplevel(root)
    ventana_grafica.title("Gráfica del Espectro de Potencias")
    ventana_grafica.geometry("800x600")
    fig, ax = plt.subplots(figsize=(1, 2))
    f_eje = np.linspace(f_min_grafico, f_max_grafico, 2000)
    espectro_total = get_espectro_total(f_eje, transmisores, P_combinada_dBm, G_total_dB, N_Piso_dBm)

    espectros_individuales = []
    for i, tx in enumerate(activos):
        P_individual_dBm = uw_to_dbm(tx['P_tx_uW']) - combinador_perdida_dB
        P_individual_radiada_dBm = P_individual_dBm + G_total_dB
        espectro_ind = get_espectro_individual(f_eje, tx['Fc'], tx['Bw_tx'], P_individual_radiada_dBm, N_Piso_dBm)
        espectros_individuales.append({
            'nombre': f"Tx{i + 1}",
            'espectro': espectro_ind,
            'Fc': tx['Fc'],
            'P_pico': P_individual_radiada_dBm,
            'f_min': tx['Fc'] - tx['Bw_tx'] / 2,
            'f_max': tx['Fc'] + tx['Bw_tx'] / 2,
            'color': tx['color']
        })

    max_pot_dbm = np.max(espectro_total)
    # 1. Graficar espectro total (línea gruesa negra)
    plt.plot(f_eje / 1e6, espectro_total, 'k', linewidth=3, 
             label='Espectro Total Combinado', alpha=0.8)

    # 2. Graficar espectros individuales y marcar sus características
    for tx_data in espectros_individuales:
        color = tx_data['color']
        
        # Espectro individual (línea delgada)
        plt.plot(f_eje / 1e6, tx_data['espectro'], color=color, linestyle='--', 
                 alpha=0.6, linewidth=1.5, label=f"{tx_data['nombre']} Individual")
        
        # Marcar frecuencia central
        plt.axvline(x=tx_data['Fc']/1e6, color=color, linestyle='-', alpha=0.4)
        
        # Marcar frecuencias mínima y máxima
        plt.axvline(x=tx_data['f_min']/1e6, color=color, linestyle=':', alpha=0.5)
        plt.axvline(x=tx_data['f_max']/1e6, color=color, linestyle=':', alpha=0.5)
        
        # Marcar pico individual
        plt.axhline(y=tx_data['P_pico'], color=color, linestyle='--', alpha=0.5)

    # 3. Línea de piso de ruido
    plt.axhline(y=N_Piso_dBm, color='red', linestyle=':', 
                label=f'Piso de Ruido: {N_Piso_dBm:.2f} dBm', alpha=0.8, linewidth=2)

    # 4. Añadir anotaciones en los ejes para cada transmisor
    for tx_data in espectros_individuales:
        color = tx_data['color']
        
        # Anotación para frecuencia central
        plt.text(tx_data['Fc']/1e6, N_Piso_dBm - 15, f'Fc: {tx_data["Fc"]/1e6:.1f} MHz', 
                ha='center', va='top', color=color, fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))
        
        # Anotación para frecuencias mínima y máxima
        plt.text(tx_data['f_min']/1e6, N_Piso_dBm - 10, f'{tx_data["f_min"]/1e6:.1f} MHz', 
                ha='center', va='top', color=color, fontsize=8,
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))
        
        plt.text(tx_data['f_max']/1e6, N_Piso_dBm - 10, f'{tx_data["f_max"]/1e6:.1f} MHz', 
                ha='center', va='top', color=color, fontsize=8,
                bbox=dict(boxstyle="round,pad=0.1", facecolor="white", alpha=0.7))
        
        # Anotación para pico individual
        plt.text(f_min_grafico/1e6 + 50, tx_data['P_pico'], 
                f'{tx_data["nombre"]}: {tx_data["P_pico"]:.2f} dBm', 
                ha='left', va='center', color=color, fontsize=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

    # 5. Anotación para piso de ruido
    plt.text(f_min_grafico/1e6 + 50, N_Piso_dBm, f'Ruido: {N_Piso_dBm:.2f} dBm', 
             ha='left', va='center', color='red', fontsize=9,
             bbox=dict(boxstyle="round,pad=0.2", facecolor="mistyrose", alpha=0.8))

    # Configuración del gráfico
    plt.xlabel('Frecuencia (MHz)')
    plt.ylabel('Potencia (dBm)')
    plt.title('Espectro de Potencias - Sistema con 3 Transmisores\n'
              'Mostrando Picos Individuales y Límites de Frecuencia')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='upper right')
    plt.xlim(f_min_grafico/1e6, f_max_grafico/1e6)
    plt.ylim(N_Piso_dBm - 20, max_pot_dbm + 5)
    
    
    canvas = FigureCanvasTkAgg(fig, master=ventana_grafica)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)



# --- INTERFAZ CON TKINTER ---
def iniciar_interfaz():
    root = tk.Tk()
    root.title("Simulación de Transmisores")
    root.geometry("520x640")
    root.configure(bg="#eef2f3")

    ttk.Style().configure("TButton", font=("Arial", 11, "bold"), padding=6)
    ttk.Style().configure("TLabel", font=("Arial", 10), background="#eef2f3")

    colores = ['#0078D7', '#28a745', '#ff9800']
    transmisores = []

    # === MENÚ SUPERIOR ===
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    menu_opciones = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Opciones", menu=menu_opciones)

    # Contenido principal
    contenedor_principal = tk.Frame(root, bg="#eef2f3")
    contenedor_principal.pack(fill="both", expand=True)

    tk.Label(contenedor_principal, text="Ingrese los parámetros de los transmisores",
             font=("Arial", 14, "bold"), bg="#eef2f3", fg="#333").pack(pady=15)

    def crear_campos_transmisor(frame, num, color):
        contenedor = tk.LabelFrame(frame, text=f"Transmisor {num}", bg="#fdfdfd",
                                   fg=color, font=("Arial", 11, "bold"),
                                   labelanchor="n", padx=10, pady=10)
        contenedor.pack(padx=10, pady=8, fill="x")

        campos = {}
        for etiqueta, key in [("Potencia (μW)", "P_tx_uW"),
                              ("Frecuencia central (MHz)", "Fc"),
                              ("Ancho de banda (MHz)", "Bw_tx")]:
            fila = tk.Frame(contenedor, bg="#fdfdfd")
            fila.pack(fill="x", pady=3)
            tk.Label(fila, text=etiqueta + ":", bg="#fdfdfd", width=22, anchor="w").pack(side="left")
            entry = ttk.Entry(fila, width=15)
            entry.pack(side="left", padx=5)
            campos[key] = entry

        activo_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(contenedor, text="Activo", variable=activo_var).pack(pady=4)
        campos["activo"] = activo_var
        transmisores.append(campos)

    for i in range(3):
        crear_campos_transmisor(contenedor_principal, i + 1, colores[i])

    # --- Funciones internas ---
    def obtener_datos():
        lista_tx = []
        for i, campos in enumerate(transmisores):
            try:
                if not campos["P_tx_uW"].get().strip() or not campos["Fc"].get().strip() or not campos["Bw_tx"].get().strip():
                    activo = False
                    P_tx, Fc, Bw = 0, 0, 0
                else:
                    P_tx = float(campos["P_tx_uW"].get())
                    Fc = float(campos["Fc"].get()) * 1e6
                    Bw = float(campos["Bw_tx"].get()) * 1e6
                    activo = campos["activo"].get()
                lista_tx.append({
                    "P_tx_uW": P_tx,
                    "Fc": Fc,
                    "Bw_tx": Bw,
                    "activo": activo,
                    "color": colores[i]
                })
            except ValueError:
                messagebox.showerror("Error", "Por favor ingrese valores numéricos válidos.")
                return None
        if not any(tx["activo"] for tx in lista_tx):
            messagebox.showinfo("Aviso", "Debe ingresar al menos un transmisor válido.")
            return None
        return lista_tx

    def mostrar_grafica():
        lista_tx = obtener_datos()
        if lista_tx:
            ejecutar_simulacion(lista_tx, root)

    def mostrar_resultados():
        lista_tx = obtener_datos()
        if not lista_tx:
            return

        # --- Cálculos rápidos ---
        combinador_perdida_dB = 0.0
        ganancia_amp_dB = 20.0
        perdida_ltx_dB = 7.5
        ganancia_ant_dBi = 24.0
        G_total_dB = ganancia_amp_dB - perdida_ltx_dB + ganancia_ant_dBi

        def uw_to_dbm(P_uw):
            return 10 * np.log10(P_uw / 1000.0)

        P_total_uw = sum(tx['P_tx_uW'] for tx in lista_tx if tx['activo'])
        P_combinada_dBm = uw_to_dbm(P_total_uw) - combinador_perdida_dB
        N_Piso_dBm = 10 * np.log10(kB * Temperatura_K * bw_medidor) + 30

        # --- Crear ventana de resultados ---
        ventana = tk.Toplevel(root)
        ventana.title("Resultados del Sistema")
        ventana.geometry("650x500")
        ventana.configure(bg="#fafafa")

        texto = tk.Text(ventana, font=("Consolas", 10), bg="#f0f0f0")
        texto.pack(fill="both", expand=True, padx=10, pady=10)

        texto.insert("end", "=== SISTEMA DE 3 TRANSMISORES ===\n")
        texto.insert("end", "\n--- Configuración de Transmisores ---\n")
        for i, tx in enumerate(lista_tx, 1):
            if tx['activo']:
                P_individual_dBm = uw_to_dbm(tx['P_tx_uW']) - combinador_perdida_dB
                P_pico_individual_dBm = P_individual_dBm + G_total_dB
                f_min = tx['Fc'] - tx['Bw_tx']/2
                f_max = tx['Fc'] + tx['Bw_tx']/2
                texto.insert("end", f"Tx{i}: {tx['P_tx_uW']} μW, Fc: {tx['Fc']/1e6:.0f} MHz, BW: {tx['Bw_tx']/1e6:.0f} MHz\n")
                texto.insert("end", f"     Pico: {P_pico_individual_dBm:.2f} dBm, "
                                    f"Fmin: {f_min/1e6:.1f} MHz, Fmax: {f_max/1e6:.1f} MHz\n")
            else:
                texto.insert("end", f"Tx{i}: INACTIVO\n")

        texto.insert("end", "\n--- Cadena de Transmisión ---\n")
        texto.insert("end", f"Pérdida del Combinador: {combinador_perdida_dB:.1f} dB\n")
        texto.insert("end", f"Ganancia del Amplificador: {ganancia_amp_dB:.1f} dB\n")
        texto.insert("end", f"Pérdida en Línea de Tx: {perdida_ltx_dB:.1f} dB\n")
        texto.insert("end", f"Ganancia de Antena: {ganancia_ant_dBi:.1f} dBi\n")
        texto.insert("end", f"Ganancia Total del Sistema: {G_total_dB:.2f} dB\n")

        texto.insert("end", "\n--- Potencias ---\n")
        texto.insert("end", f"Potencia Total Combinada: {P_total_uw:.1f} μW = {P_combinada_dBm:.2f} dBm\n")
        texto.insert("end", f"Pico de Potencia Radiada Total: {P_combinada_dBm + G_total_dB:.2f} dBm\n")

        texto.insert("end", "\n--- Parámetros de Ruido ---\n")
        texto.insert("end", f"Piso de Ruido Térmico: {N_Piso_dBm:.2f} dBm\n")
        texto.insert("end", "-" * 60 + "\n")

        texto.configure(state="disabled")

    # --- Agregar las opciones al menú ---
    menu_opciones.add_command(label="Ingresar datos", command=lambda: None)
    menu_opciones.add_command(label="Ver resultados", command=mostrar_resultados)

    ttk.Button(contenedor_principal, text="Graficar Espectro", command=mostrar_grafica).pack(pady=20)

    root.mainloop()



# --- EJECUCIÓN ---
if __name__ == "__main__":
    iniciar_interfaz()
