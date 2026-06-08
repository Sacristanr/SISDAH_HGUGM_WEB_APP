# SISDAH Web — Despliegue en equipo fijo

## Orden de pasos (una sola vez)

### 1. Instalar XAMPP
- Descargar: https://www.apachefriends.org
- Instalar en `C:\xampp`
- Abrir **XAMPP Control Panel**
- En la fila **MySQL** → pulsar **Start**
- Configurar arranque automático: en la fila MySQL → clic en el cuadrado de la izquierda (se marca en rojo = arranca con Windows)

### 2. Crear la base de datos
- Con MySQL arrancado, abrir: http://localhost/phpmyadmin
- Clic en **Nueva** (panel izquierdo)
- Nombre: `sisdah` · Cotejamiento: `utf8mb4_unicode_ci`
- Pulsar **Crear**

### 3. Copiar la carpeta del proyecto
Copiar toda la carpeta `PROYECTO HGUGM` al equipo (pendrive, red, etc.)
Ruta recomendada: `C:\SISDAH\`

### 4. Ejecutar instalación
```
Clic derecho en web\INSTALAR.bat → Ejecutar como administrador
```
Esto instala las dependencias Python.

### 5. Cambiar a MySQL
```
Clic derecho en web\CAMBIAR_A_MYSQL.bat → Ejecutar como administrador
```
Introduce la contraseña de root de MySQL si la tiene (normalmente vacía en XAMPP).

### 6. Instalar como servicio Windows (arranque automático)
```
Clic derecho en web\INSTALAR_SERVICIO.bat → Ejecutar como administrador
```
Descarga NSSM e instala el servidor Flask como servicio que arranca con Windows.

---

## Verificar que funciona

Abrir navegador → `http://localhost:5000`

Debe aparecer la pantalla de login de SISDAH.

---

## Acceso desde otros equipos de la red

La URL para otros equipos es `http://[IP-del-servidor]:5000`

Para saber la IP del servidor:
```
Abrir cmd → ipconfig → buscar "Dirección IPv4"
Ejemplo: 192.168.1.45 → los demás acceden en http://192.168.1.45:5000
```

Para que funcione hay que abrir el puerto 5000 en el Firewall de Windows:
```
web\ABRIR_FIREWALL.bat → Ejecutar como administrador
```

---

## Gestión del servicio

| Acción | Comando |
|---|---|
| Ver estado | `sc query SISDAH_Web` |
| Iniciar | `sc start SISDAH_Web` |
| Detener | `sc stop SISDAH_Web` |
| Ver logs | `web\logs\sisdah_out.log` |

---

## Credenciales de acceso

| Tipo | Credencial |
|---|---|
| Técnico | Solo DNI (sin contraseña) |
| Admin emergencia | DNI: `54421076V` · Contraseña: ver `CREDENCIALES_SISDAH.txt` |

---

## Estructura de archivos

```
web\
├── INSTALAR.bat          ← Paso 4: instalar dependencias
├── CAMBIAR_A_MYSQL.bat   ← Paso 5: configurar MySQL
├── INSTALAR_SERVICIO.bat ← Paso 6: servicio Windows
├── INICIAR_SERVIDOR.bat  ← Arrancar manualmente (sin servicio)
├── .env                  ← Configuración BD y clave secreta
├── logs\                 ← Logs del servidor
└── sisdah_dev.db         ← BD SQLite (solo desarrollo, en prod usar MySQL)
```
