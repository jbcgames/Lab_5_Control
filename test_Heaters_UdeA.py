"""
Prueba de escalón con registro de datos en Python
Adaptado y documentado para el Laboratorio de Control de Temperatura (TempLabUdeA)
Universidad de Antioquia - Sistemas de Control
"""

import tclab
import numpy as np
import time
import matplotlib.pyplot as plt

# ------------------------------------------------------------------------------
# Conexión con el dispositivo Arduino + TCLab
# ------------------------------------------------------------------------------
lab = tclab.TCLab()

# ------------------------------------------------------------------------------
# Función para guardar datos en un archivo de texto
# ------------------------------------------------------------------------------
def save_txt(t, u1, u2, y1, y2, sp1, sp2, filename='data.txt'):
    """
    Guarda los arrays como columnas en un archivo CSV con cabecera.
    - t: vector de tiempos (s)
    - u1, u2: señales de control de calentadores (%)
    - y1, y2: temperaturas medidas (°C)
    - sp1, sp2: puntos de consigna (°C)
    """
    # Apilar verticalmente y transponer
    data = np.vstack((t, u1, u2, y1, y2, sp1, sp2)).T
    encabezado = ('Tiempo (s), Cal1 (%), Cal2 (%), '
                  'Temp1 (°C), Temp2 (°C), Set1 (°C), Set2 (°C)')
    np.savetxt(filename, data, delimiter=',', header=encabezado, comments='')

# ------------------------------------------------------------------------------
# Mostrar versión de firmware y encender LED al 100% de brillo
# ------------------------------------------------------------------------------
print("Firmware:", lab.version)
print("Encendiendo LED al 100%")
lab.LED(100)

# ------------------------------------------------------------------------------
# Parámetros de la prueba
# ------------------------------------------------------------------------------
duracion_min = 10.0             # Tiempo de corrida en minutos
ciclos = int(60 * duracion_min) # Número de iteraciones de 1 segundo
t_array = np.zeros(ciclos)      # Vector de tiempos

# Definir punto de consigna constante
Tset1 = np.ones(ciclos) * 23.0  # (°C)
Tset2 = np.ones(ciclos) * 23.0  # (°C)

# Inicializar vectores de temperatura con lectura inicial
T1 = np.ones(ciclos) * lab.T1
T2 = np.ones(ciclos) * lab.T2

# Definir perfil de control: escalón en Q1 al 80% a partir del segundo 10
Q1 = np.zeros(ciclos)
Q2 = np.zeros(ciclos)
Q1[10:] = 80.0  # Escalón en cal1

# Mostrar encabezado en consola
print("Iniciando bucle principal. Ctrl-C para detener.")
print(f"{'t(s)':>6s} {'Q1(%)':>6s} {'Q2(%)':>6s} {'T1(°C)':>7s} {'T2(°C)':>7s}")
print(f"{t_array[0]:6.1f} {Q1[0]:6.2f} {Q2[0]:6.2f} {T1[0]:7.2f} {T2[0]:7.2f}")

# ------------------------------------------------------------------------------
# Preparar gráfico
# ------------------------------------------------------------------------------
plt.figure(figsize=(10, 7))
plt.ion()  # modo interactivo
plt.show()

# ------------------------------------------------------------------------------
# Bucle principal de adquisición y control
# ------------------------------------------------------------------------------
t_inicio = time.time()
t_ant = t_inicio

try:
    for i in range(1, ciclos):
        # Regular frecuencia de muestreo ~1 s
        dt = time.time() - t_ant
        t_sleep = max(0.0, 1.0 - dt)
        time.sleep(t_sleep)
        
        # Actualizar tiempo
        t_actual = time.time()
        t_array[i] = t_actual - t_inicio
        t_ant = t_actual
        
        # Leer temperaturas (°K)
        T1[i] = lab.T1
        T2[i] = lab.T2
        
        # AQUI: lógica de controlador o estimador (si aplica)
        
        # Enviar señales de control a los calentadores
        lab.Q1(Q1[i])
        lab.Q2(Q2[i])
        
        # Imprimir datos en consola
        print(f"{t_array[i]:6.1f} {Q1[i]:6.2f} {Q2[i]:6.2f} {T1[i]:7.2f} {T2[i]:7.2f}")
        
        # Actualizar gráfico en tiempo real
        plt.clf()
        ax1 = plt.subplot(2,1,1)
        ax1.grid(True)
        ax1.plot(t_array[:i], T1[:i], 'r-o', label='T1')
        ax1.plot(t_array[:i], T2[:i], 'b-x', label='T2')
        plt.ylabel('Temperatura (°C)')
        plt.legend(loc='best')
        
        ax2 = plt.subplot(2,1,2)
        ax2.grid(True)
        ax2.plot(t_array[:i], Q1[:i], 'r-', label='Q1')
        ax2.plot(t_array[:i], Q2[:i], 'b--', label='Q2')
        plt.ylabel('Calentadores (%)')
        plt.xlabel('Tiempo (s)')
        plt.legend(loc='best')
        
        plt.pause(0.05)
    
    # Al terminar el bucle, apagar calentadores
    lab.Q1(0)
    lab.Q2(0)
    
    # Guardar datos y figura
    save_txt(t_array, Q1, Q2, T1, T2, Tset1, Tset2, filename='data.txt')
    plt.savefig('resultado_prueba.png')
    
except KeyboardInterrupt:
    # En caso de interrupción, apagar y cerrar conexión
    print("\nDetención por usuario. Apagando calentadores y cerrando conexión.")
    lab.Q1(0)
    lab.Q2(0)
    lab.close()
    save_txt(t_array[:i], Q1[:i], Q2[:i], T1[:i], T2[:i], Tset1[:i], Tset2[:i], filename='data.txt')
    plt.savefig('resultado_prueba.png')
    
except Exception as e:
    # En caso de error, asegurar cierre y guardar datos
    print(f"\nError inesperado: {e}")
    lab.Q1(0)
    lab.Q2(0)
    lab.close()
    save_txt(t_array[:i], Q1[:i], Q2[:i], T1[:i], T2[:i], Tset1[:i], Tset2[:i], filename='data.txt')
    plt.savefig('resultado_prueba.png')
    raise
