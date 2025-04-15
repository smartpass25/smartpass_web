import serial
import time

ser = serial.Serial('/dev/serial0', 9600, timeout=1)

while True:
    ser.write(b't0.txt="Hola desde Pi"\xff\xff\xff')
    print("Enviado a Nextion")
    time.sleep(3)
