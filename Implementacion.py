import tclab 
import numpy as np
import time
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

# ------------------------------------------------------------------------------
# Función para permitir seleccionar el tipo de controlador
def ejecutar_control(tipo_controlador='PID'):
    """
    Ejecuta el control de temperatura con el tipo de controlador seleccionado
    tipo_controlador: 'P', 'PI', o 'PID'
    """
    lab = tclab.TCLab()
    
    # Parámetros de control
    Kc = 62.4  # Ganancia proporcional
    tauI = 18.9295  # Tiempo integral
    tauD = 4.7324  # Tiempo derivativo
    Q_bias = 0.0  # Bias
    ierr = 0.0  # Error integral acumulado
    prev_err = 0.0  # Error anterior (para término derivativo)
    
    # Inicializar listas
    n = 600  # Número de muestras
    T1 = [0.0] * n  # Temperatura en sensor 1
    T2 = [0.0] * n  # Temperatura en sensor 2
    Q1 = [0.0] * n  # Señal de control para calentador 1
    SP1 = [60.0] * n  # Setpoint (temperatura deseada)
    
    # Para almacenar los componentes del controlador
    P_component = [0.0] * n  # Componente proporcional
    I_component = [0.0] * n  # Componente integral
    D_component = [0.0] * n  # Componente derivativo
    
    # Configurar la gráfica en modo interactivo
    plt.ion()
    
    try:
        print(f"Iniciando control {tipo_controlador}...")
        for i in range(n):
            # Leer temperatura actual
            T1[i] = lab.T2
            T2[i] = lab.T1
            
            # Cálculo del error
            err = SP1[i] - T1[i]
            
            # Componente proporcional - siempre se usa
            P_component[i] = Kc * err
            
            # Componente integral - solo para PI y PID
            if tipo_controlador in ['PI', 'PID']:
                ierr += err
                I_component[i] = (Kc / tauI) * ierr
            
            # Componente derivativo - solo para PID
            if tipo_controlador == 'PID':
                deriv = err - prev_err
                D_component[i] = Kc * tauD * deriv
                prev_err = err
            
            # Calcular la acción de control según el tipo de controlador
            if tipo_controlador == 'P':
                Q1[i] = Q_bias + P_component[i]
            elif tipo_controlador == 'PI':
                Q1[i] = Q_bias + P_component[i] + I_component[i]
            else:  # PID
                Q1[i] = Q_bias + P_component[i] + I_component[i] + D_component[i]
            
            # Anti-windup
            if Q1[i] >= 100:
                Q1[i] = 100
                if tipo_controlador in ['PI', 'PID']:
                    ierr -= err  # Corregir el error integral acumulado
            elif Q1[i] <= 0:
                Q1[i] = 0
                if tipo_controlador in ['PI', 'PID']:
                    ierr -= err  # Corregir el error integral acumulado
            
            # Aplicar señal de control
            if i > 10:
                lab.Q1(Q1[i])
            else:
                Q1[i] = 0.0
                lab.Q1(0)
            
            # Gráfica de temperatura
            plt.clf()
            plt.subplot(2, 1, 1)
            plt.plot(T1[:i+1], 'r-o', label='T1')
            plt.plot(T2[:i+1], 'b-o', label='T2')
            plt.plot(SP1[:i+1], 'k--', label='SP')
            plt.ylabel('Temperatura (°C)')
            plt.title(f'Control {tipo_controlador} de Temperatura')
            plt.grid(True)
            plt.legend()
            
            # Gráfica de PWM (Q1)
            plt.subplot(2, 1, 2)
            plt.plot(Q1[:i+1], 'b-', label='Q1 (PWM)')
            
            # También graficar los componentes del controlador
            if tipo_controlador != 'P':
                plt.plot(P_component[:i+1], 'g-', label='P')
                plt.plot(I_component[:i+1], 'y-', label='I')
                if tipo_controlador == 'PID':
                    plt.plot(D_component[:i+1], 'c-', label='D')
            
            plt.ylabel('PWM (%)')
            plt.title('Señal de control Q1')
            plt.xlabel('Tiempo (s)')
            plt.grid(True)
            plt.legend()
            
            plt.tight_layout()
            plt.pause(0.05)  # Actualizar la gráfica
            time.sleep(1)  # Esperar un segundo
        
    except KeyboardInterrupt:
        # En caso de interrupción, apagar y cerrar conexión
        print("\nDetención por usuario. Apagando calentadores y cerrando conexión.")
    
    finally:
        # Asegurar que siempre se apaguen los calentadores y se cierre la conexión
        lab.Q1(0)
        lab.Q2(0)
        lab.close()
        
        # Guardar resultados
        t = np.arange(n)
        
        # Crear DataFrame con los datos
        data = {
            'Tiempo (s)': t,
            'Setpoint (SP)': SP1,
            'Temperatura (T1)': T1,
            'Control PWM (Q1)': Q1,
            'Componente P': P_component
        }
        
        # Añadir componentes según el controlador usado
        if tipo_controlador in ['PI', 'PID']:
            data['Componente I'] = I_component
        if tipo_controlador == 'PID':
            data['Componente D'] = D_component
        
        df = pd.DataFrame(data)
        
        # Generar timestamp para nombrar los archivos
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Guardar datos en CSV
        csv_filename = f'registro_{tipo_controlador}_TempLab_{timestamp}.csv'
        df.to_csv(csv_filename, index=False)
        print(f"Datos guardados en '{csv_filename}'")
        
        # Crear gráfica final para guardar como imagen
        plt.figure(figsize=(12, 8))
        
        # Gráfica de temperatura
        plt.subplot(3, 1, 1)
        plt.plot(t, T1, 'r-', label='T1')
        plt.plot(t, SP1, 'k--', label='SP')
        plt.ylabel('Temperatura (°C)')
        plt.title(f'Control {tipo_controlador} de Temperatura')
        plt.grid(True)
        plt.legend()
        
        # Gráfica de PWM (Q1)
        plt.subplot(3, 1, 2)
        plt.plot(t, Q1, 'b-', label='Q1 (PWM)')
        plt.ylabel('PWM (%)')
        plt.title('Señal de control Q1')
        plt.grid(True)
        plt.legend()
        
        # Gráfica de componentes del controlador
        plt.subplot(3, 1, 3)
        plt.plot(t, P_component, 'g-', label='P')
        if tipo_controlador in ['PI', 'PID']:
            plt.plot(t, I_component, 'y-', label='I')
        if tipo_controlador == 'PID':
            plt.plot(t, D_component, 'c-', label='D')
        plt.ylabel('Componentes')
        plt.xlabel('Tiempo (s)')
        plt.title('Componentes del controlador')
        plt.grid(True)
        plt.legend()
        
        # Guardar imagen
        image_filename = f'grafico_{tipo_controlador}_TempLab_{timestamp}.png'
        plt.tight_layout()
        plt.savefig(image_filename)
        print(f"Gráfica guardada en '{image_filename}'")
        
        plt.ioff()  # Desactivar modo interactivo
        plt.show()  # Mostrar la gráfica final
        
        return df  # Retornar el dataframe con los resultados

# Ejemplo de uso:
if __name__ == "__main__":
    print("Selecciona el tipo de controlador:")
    print("1 - Control Proporcional (P)")
    print("2 - Control Proporcional-Integral (PI)")
    print("3 - Control Proporcional-Integral-Derivativo (PID)")
    
    opcion = input("Ingresa el número de la opción deseada (1, 2 o 3): ")
    
    if opcion == '1':
        ejecutar_control('P')
    elif opcion == '2':
        ejecutar_control('PI')
    elif opcion == '3':
        ejecutar_control('PID')
    else:
        print("Opción no válida. Ejecutando PID por defecto.")
        ejecutar_control('PID')