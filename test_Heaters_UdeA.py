"""
Prueba de escalón con registro de datos en Python
Adaptado y documentado para el Laboratorio de Control de Temperatura (TempLabUdeA)
Universidad de Antioquia - Sistemas de Control
"""

import tclab 
import numpy as np
import time
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime


# ------------------------------------------------------------------------------
lab = tclab.TCLab()
# Parámetros de control
Kc = 62.4
tauI = 18.9295
tauD = 4.7324
Q_bias = 0.0
ierr = 0.0
prev_err = 0.0

# Inicializar listas (suponiendo que n ya está definido)
n=600
T1 = [0.0] * n
T2 = [0.0] * n
Q1 = [0.0] * n
SP1 = [60.0] * n  # Por ejemplo, setpoint constante de 50

plt.ion()  # Activar modo interactivo
try:
    for i in range(n):
    # Leer temperatura actual
        T1[i] = lab.T2
        T2[i] = lab.T1

        # Cálculo del error
        err = SP1[i] - T1[i]

        # Término integral
        ierr += err

        # Término derivativo
        deriv = err - prev_err
        prev_err = err

        # Acción de control PID
        Q1[i] = Q_bias + Kc * err + (Kc / tauI) * ierr + Kc * tauD * deriv

        # Anti-windup
        if Q1[i] >= 100:
            print(Q1[i])
            Q1[i] = 100
            ierr -= err
        elif Q1[i] <= 0:
            Q1[i] = 0
            ierr -= err

        # Aplicar señal de control
        if (i>10):
            lab.Q1(Q1[i])
        if (i<10):
            Q1=[0.0] * n
        # Gráfica de temperatura
        plt.clf()
        plt.subplot(2, 1, 1)
        plt.plot(T1[:i+1], 'r-o', label='T1')
        plt.plot(T2[:i+1], 'b-o', label='T2')
        plt.ylabel('Temperatura (°C)')
        plt.title('Temperatura')
        plt.grid(True)
        plt.legend()

        # Gráfica de PWM (Q1)
        plt.subplot(2, 1, 2)
        plt.plot(Q1[:i+1], 'b-', label='Q1 (PWM)')
        plt.ylabel('PWM (%)')
        plt.title('Señal de control Q1')
        plt.xlabel('Tiempo (s)')
        plt.grid(True)
        plt.legend()

        plt.pause(0.05)  # Pequeña pausa para actualizar la gráfica
        time.sleep(1)
except KeyboardInterrupt:
    # En caso de interrupción, apagar y cerrar conexión
    print("\nDetención por usuario. Apagando calentadores y cerrando conexión.")
    lab.Q1(0)
    lab.Q2(0)
    lab.close()
    plt.savefig('resultado_prueba.png')
    
plt.show()
t = np.arange(n)

# Crear DataFrame
df = pd.DataFrame({
    'Tiempo (s)': t,
    'Setpoint (SP)': SP1,
    'Temperatura (T)': T1,
    'Control PWM (Q)': Q1
})

# Generar timestamp para los archivos
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Guardar datos en CSV
csv_filename = f'registro_PID_TempLab_{timestamp}.csv'
df.to_csv(csv_filename, index=False)
print(f"Datos guardados en '{csv_filename}'")

# Volver a graficar la última figura para guardarla como imagen
plt.figure(figsize=(10,6))

# Temperatura
plt.subplot(2, 1, 1)
plt.plot(t, T1, 'r-o', label='T1')
plt.plot(t, SP1, 'k--', label='SP')
plt.ylabel('Temperatura (°C)')
plt.title('Temperatura T1 vs Setpoint')
plt.grid(True)
plt.legend()

# PWM
plt.subplot(2, 1, 2)
plt.plot(t, Q1, 'b-', label='Q1 (PWM)')
plt.ylabel('PWM (%)')
plt.xlabel('Tiempo (s)')
plt.title('Señal de control Q1')
plt.grid(True)
plt.legend()

# Guardar imagen
image_filename = f'grafico_PID_TempLab_{timestamp}.png'
plt.tight_layout()
plt.savefig(image_filename)
print(f"Gráfica guardada en '{image_filename}'")

plt.show()
