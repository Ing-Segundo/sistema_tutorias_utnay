# Pruebas de Software — Sistema de Tutorías

Este documento resume las dos técnicas de prueba aplicadas al proyecto, tal como se
pide en la lista de cotejo de exposición: **caja negra** y **caja blanca**.

Archivo de pruebas: `test_app.py` (8 pruebas, corridas con `pytest`).
Comando para ejecutarlas: `pytest test_app.py -v`

---

## 1. Pruebas de caja negra

**¿Qué es?** Se prueba el sistema únicamente por su entrada y salida, como lo haría
un usuario real, sin mirar ni usar el código interno. Solo importa: "si mando esto,
¿qué debería devolver el sistema?".

**Cómo se aplicó:** Se usó el cliente de pruebas de Flask (`app.test_client()`) para hacer peticiones HTTP reales contra las rutas del sistema (`/`, `/panel-coordinador`) y verificar el comportamiento esperado desde afuera (redirecciones, cookies de sesión y mensajes flash).

| Caso de prueba | Entrada | Resultado esperado | Resultado obtenido |
|---|---|---|---|
| Login con credenciales correctas | `coordinador` / `clave_coordinador` | Redirige al panel de coordinador | ✅ Pasó |
| Login con credenciales incorrectas | `coordinador` / clave equivocada | Se queda en el login (rechazado) | ✅ Pasó |
| Acceso a panel sin haber iniciado sesión | `GET /panel-coordinador` sin cookie | Redirige al login | ✅ Pasó |
| Un tutor intenta entrar al panel de coordinador | Login como tutor, luego `GET /panel-coordinador` | Acceso bloqueado | ✅ Pasó |

---

## 2. Pruebas de caja blanca

**¿Qué es?** Se diseñan los casos a partir del código interno, buscando ejercitar
caminos y ramas específicas de la lógica (por ejemplo, cada `except` de una función).

**Cómo se aplicó:** El sistema protege sus rutas con el decorador `@requiere_rol` (en `app.py`) que decodifica el token JWT y tiene 4 caminos posibles internamente: token válido, token expirado, token corrupto e inyección de token con rol no permitido. Se construyó un token JWT a mano para cada caso, firmado con la misma `SECRET_KEY` de la aplicación, forzando la ejecución de cada rama del código.

| Caso de prueba | Rama de código ejercitada | Resultado esperado | Resultado obtenido |
|---|---|---|---|
| Token válido y rol correcto | Camino feliz del decorador (`try` exitoso) | Acceso permitido (200 OK) | ✅ Pasó |
| Token expirado (`exp` en el pasado) | `except jwt.ExpiredSignatureError` | Redirige con mensaje "Tu sesión ha expirado" | ✅ Pasó |
| Token con firma inválida / corrupto | `except jwt.InvalidTokenError` | Acceso rechazado, redirige al login | ✅ Pasó |
| Token válido pero de un tutor accediendo a ruta de coordinador | Verificación de `payload["rol"] not in roles_permitidos` | Acceso bloqueado | ✅ Pasó |

---

