import tclab
import numpy as np
import time
import matplotlib.pyplot as plt

# Parámetros de control
Kc = 1 / 0.9
tauI = 175.0
tauD = 5.0
Q_bias = 0.0
n = 600  # Duración en segundos

# Inicialización de variables
ierr = 0.0
prev_err = 0.0

# Conexión con el dispositivo
lab = tclab.TCLab()

# Definir vectores
SP1 = np.ones(n) * 23.0  # Setpoint constante
Q1 = np.zeros(n)
T1 = np.zeros(n)

print("Firmware:", lab.version)

for i in range(n):
    # Leer temperatura actual
    T1[i] = lab.T1

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
        Q1[i] = 100
        ierr -= err
    elif Q1[i] <= 0:
        Q1[i] = 0
        ierr -= err

    # Aplicar control al calentador
    lab.Q1(Q1[i])
    time.sleep(1)

# Apagar calentadores al finalizar
lab.Q1(0)
lab.close()

print("Controlador finalizado y conexión cerrada.")