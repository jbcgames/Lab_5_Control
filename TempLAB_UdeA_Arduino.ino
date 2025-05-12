/*
  Firmware del Laboratorio de Control de Temperatura (TCLab)
  Versión adaptada y comentada en español para estudiantes de
  SISTEMAS DE CONTROL - Universidad de Antioquia

  Hernán Felipe García Arias
  Gracias a  Jeffrey Kantor, Bill Tubbs, John Hedengren, Shawn Summey
  Fecha: Febrero 2025

  Este firmware ofrece una interfaz de alto nivel para el Laboratorio de Control
  de Temperatura. Escucha comandos por el puerto serie (insensibles a mayúsculas).
  Cada comando devuelve una cadena de resultado. Comandos desconocidos ponen el sistema
  en modo reposo y apagan los calentadores.

  Descripción de comandos principales:
    A         Reinicio de software. Devuelve "Start".
    LED v     Establece brillo del LED por v (0-100) durante 10 s. Devuelve el valor real.
    P1 v      Límite de PWM para calentador 1 (0-255). Devuelve P1.
    P2 v      Límite de PWM para calentador 2 (0-255). Devuelve P2.
    Q1 v      Ajusta potencia del calentador 1 (0-100%). Devuelve Q1.
    Q2 v      Ajusta potencia del calentador 2 (0-100%). Devuelve Q2.
    R1        Lee el valor actual del calentador 1 (0-100%).
    R2        Lee el valor actual del calentador 2 (0-100%).
    SCAN      Lee T1, T2, Q1, Q2 en valores separados por líneas.
    T1        Lee temperatura T1 (°C).
    T2        Lee temperatura T2 (°C).
    VER       Devuelve la versión del firmware.
    X         Apaga calentadores y entra en modo reposo. Devuelve "Stop".

  Estado del LED1 en el escudo TC Lab:
    Brillo  Estado
    ------- ----------------------------------
    tenue   operación normal, calentadores apagados
    brillante operación normal, al menos un calentador encendido
    tenue + parpadeo  alarma de alta temperatura, calentadores apagados
    brillante + parpadeo  alarma, calentadores encendidos

  El sistema apaga los calentadores si no recibe comandos durante el tiempo de
  espera, si recibe 'X', o un comando no reconocido.

  Historial de versiones:
    1.0.1  Versión inicial
    1.1.0  Comandos R1 y R2; valores de calefactores en %; modelo LED simplificado
    1.2.0  Añadido comando LED
    1.2.1  Correcciones de reset en close
    1.2.2  Cadena de versión mejorada
    1.2.3  Cambio de baudios a 115200
    1.3.0  Comando SCAN y tipo de placa en versión
    1.4.0  Q1 y Q2 a float
    1.4.1  Serial.flush() al final del loop
    1.4.2  Corrección bug comando X
    1.4.3  Deprecado Arduino < 1.0.0
    1.5.0  Eliminado webusb
    1.6.0  Promedio de 10 lecturas para reducir ruido
    2.0.0  Comunicación binaria; T1B/T2B y Q1B/Q2B 32-bit float; AREF 1.75V
    2.0.1  Actualizaciones de versiones específicas
*/

#include "Arduino.h"

// Detectar tipo de placa Arduino
#if defined(__AVR_ATmega328P__) || defined(__AVR_ATmega168__)
  String boardType = "Arduino Uno";
#elif defined(__AVR_ATmega32U4__) || defined(__AVR_ATmega16U4__)
  String boardType = "Arduino Leonardo/Micro";
#elif defined(__AVR_ATmega1280__) || defined(__AVR_ATmega2560__)
  String boardType = "Arduino Mega";
#else
  String boardType = "Placa desconocida";
#endif

// Habilitar salida de depuración (DEBUG)
const bool DEBUG = false;

// CONSTANTES DE CONFIGURACIÓN
const String vers     = "1.0.1";    // Versión del firmware
const long baud       = 115200;      // Velocidad del puerto serie
const char sp         = ' ';         // Separador de comando y valor
const char nl         = '\n';       // Terminador de línea

// Pines en el escudo TC Lab
const int pinT1       = 0;           // Sensor de temperatura 1 (analog)
const int pinT2       = 2;           // Sensor de temperatura 2 (analog)
const int pinQ1       = 3;           // Salida PWM calentador 1
const int pinQ2       = 5;           // Salida PWM calentador 2
const int pinLED1     = 9;           // LED indicador

// Límites de alarma de temperatura (°C)
const int limT1       = 50;          // Alarma alta T1
const int limT2       = 50;          // Alarma alta T2

// Niveles de brillo para el LED
const int hiLED       =  60;         // Brillo alto
const int loLED       = hiLED/16;    // Brillo bajo

// VARIABLES GLOBALES
char  Buffer[64];       // Buffer para comando recibido
int   buffer_index = 0; // Índice en el buffer
String cmd;             // Comando parseado
float  val;             // Valor numérico del comando
int   ledStatus;        // Estado interno del LED (1..4)
long  ledTimeout = 0;   // Tiempo hasta restaurar LED normal
float LED       = 100;  // Intensidad LED override
float P1        = 200;  // Límite PWM calentador 1 (0..255)
float P2        = 100;  // Límite PWM calentador 2 (0..255)
float Q1        = 0;    // Último valor % aplicado a calentador 1
float Q2        = 0;    // Último valor % aplicado a calentador 2
int   alarmStatus;      // Estado de alarma (0 o 1)
bool  newData    = false; // Flag: llegó nuevo comando
int   n          = 10;   // Número de muestras para promedio de temperatura


// Lee datos del puerto serie hasta encontrar terminador o buffer lleno
void readCommand() {
  while (Serial && Serial.available() > 0 && !newData) {
    int b = Serial.read();
    if (b != '\r' && b != nl && buffer_index < sizeof(Buffer)) {
      Buffer[buffer_index++] = b;
    } else {
      newData = true;
    }
  }
}

// Eco del comando para depuración
void echoCommand() {
  if (newData) {
    Serial.print("Comando recibido: ");
    Serial.write(Buffer, buffer_index);
    Serial.println();
    Serial.flush();
  }
}

// Lee y retorna el promedio de n muestras de temperatura (°C)
inline float readTemperature(int pin) {
  float suma = 0;
  for (int i = 0; i < n; i++) {
    // Conversión para referencia de 3.3 V (usar AREF externa)
    suma += analogRead(pin) * 0.322265625 - 50.0;
  }
  return suma / float(n);
}

// Parsea el comando y separa cmd y val (valor numérico)
void parseCommand() {
  if (!newData) return;
  String r = String(Buffer);
  int idx = r.indexOf(sp);
  cmd = r.substring(0, idx);
  cmd.trim(); cmd.toUpperCase();
  String data = r.substring(idx + 1);
  data.trim();
  val = data.toFloat();
  // Reiniciar buffer para próximo comando
  memset(Buffer, 0, sizeof(Buffer));
  buffer_index = 0;
  newData = false;
}

// Enviar respuesta de texto por serie
void sendResponse(String msg) {
  Serial.println(msg);
}

// Enviar valor flotante con 3 decimales
void sendFloatResponse(float v) {
  Serial.println(String(v, 3));
}

// Enviar valor flotante en formato binario de 32 bits
void sendBinaryResponse(float v) {
  byte *b = (byte*)&v;
  Serial.write(b, 4);
}

// Distribuye la acción según el comando cmd
void dispatchCommand() {
  if (cmd == "A") {
    setHeater1(0);
    setHeater2(0);
    sendResponse("Start");

  } else if (cmd == "LED") {
    ledTimeout = millis() + 10000;
    LED = constrain(val, 0, 100);
    sendResponse(String(LED));

  } else if (cmd == "P1") {
    P1 = constrain(val, 0, 255);
    sendResponse(String(P1));

  } else if (cmd == "P2") {
    P2 = constrain(val, 0, 255);
    sendResponse(String(P2));

  } else if (cmd == "Q1") {
    setHeater1(val);
    sendFloatResponse(Q1);

  } else if (cmd == "Q1B") {
    setHeater1(val);
    sendBinaryResponse(Q1);

  } else if (cmd == "Q2") {
    setHeater2(val);
    sendFloatResponse(Q2);

  } else if (cmd == "Q2B") {
    setHeater2(val);
    sendBinaryResponse(Q2);

  } else if (cmd == "R1") {
    sendFloatResponse(Q1);

  } else if (cmd == "R2") {
    sendFloatResponse(Q2);

  } else if (cmd == "SCAN") {
    sendFloatResponse(readTemperature(pinT1));
    sendFloatResponse(readTemperature(pinT2));
    sendFloatResponse(Q1);
    sendFloatResponse(Q2);

  } else if (cmd == "T1") {
    sendFloatResponse(readTemperature(pinT1));

  } else if (cmd == "T1B") {
    sendBinaryResponse(readTemperature(pinT1));

  } else if (cmd == "T2") {
    sendFloatResponse(readTemperature(pinT2));

  } else if (cmd == "T2B") {
    sendBinaryResponse(readTemperature(pinT2));

  } else if (cmd == "VER") {
    sendResponse("TCLab Firmware " + vers + " " + boardType);

  } else if (cmd == "X") {
    setHeater1(0);
    setHeater2(0);
    sendResponse("Stop");

  } else if (cmd.length() > 0) {
    // Comando desconocido: apagar calentadores
    setHeater1(0);
    setHeater2(0);
    sendResponse(cmd);
  }
  Serial.flush();
  cmd = "";
}

// Verifica si alguna temperatura supera el límite de alarma
void checkAlarm() {
  if (readTemperature(pinT1) > limT1 ||
      readTemperature(pinT2) > limT2) {
    alarmStatus = 1;
  } else {
    alarmStatus = 0;
  }
}

// Actualiza el estado y comportamiento del LED indicador
void updateStatus() {
  // Determinar modo de LED según Q1/Q2 y alarma
  ledStatus = 1;  // solo tenue
  if (Q1 > 0 || Q2 > 0) ledStatus = 2;  // brillante
  if (alarmStatus) ledStatus += 2;        // si alarma, sumar parpadeo

  if (millis() < ledTimeout) {
    // Override manual de LED
    analogWrite(pinLED1, LED);
  } else {
    switch (ledStatus) {
      case 1: // normal, apagado
        analogWrite(pinLED1, loLED);
        break;
      case 2: // normal, encendido
        analogWrite(pinLED1, hiLED);
        break;
      case 3: // alarma, apagado + parpadeo
        analogWrite(pinLED1, (millis() % 2000) > 1000 ? loLED : loLED/4);
        break;
      case 4: // alarma, encendido + parpadeo
        analogWrite(pinLED1, (millis() % 2000) > 1000 ? hiLED : loLED);
        break;
    }
  }
}

// Ajusta la potencia del calentador 1
void setHeater1(float qval) {
  Q1 = constrain(qval, 0.0, 100.0);
  analogWrite(pinQ1, (Q1 * P1) / 100.0);
}

// Ajusta la potencia del calentador 2
void setHeater2(float qval) {
  Q2 = constrain(qval, 0.0, 100.0);
  analogWrite(pinQ2, (Q2 * P2) / 100.0);
}

// Configuración inicial de Arduino
void setup() {
  analogReference(EXTERNAL);  // Usa referencia externa (3.3 V)
  while (!Serial) { /* espera a conectar puerto serie */ }
  Serial.begin(baud);
  Serial.flush();
  setHeater1(0);
  setHeater2(0);
  ledTimeout = millis() + 1000;  // 1 s de override LED al inicio
}

// Bucle principal: lee comando, ejecuta, verifica alarmas y actualiza LED
void loop() {
  readCommand();            
  if (DEBUG) echoCommand();
  parseCommand();          
  dispatchCommand();       
  checkAlarm();            
  updateStatus();          
}
