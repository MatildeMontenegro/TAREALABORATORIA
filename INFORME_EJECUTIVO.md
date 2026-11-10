# Informe ejecutivo · Gestión de pedidos para ArtesaníasPlus

**Tipo de proyecto:** caso práctico (datos ficticios)
**Stack:** Python (Flask), MySQL, HTML/CSS/JavaScript, openpyxl
**Repositorio:** `artesanias-plus-pedidos`

---

## 1. Resumen

Una micro-pyme de artesanías registra sus pedidos en planillas dispersas. Eso dificulta saber qué pedidos están pagados, cuáles siguen pendientes de envío y cuáles requieren revisión. El proyecto entrega una aplicación web que:

- centraliza los pedidos en una base de datos MySQL;
- clasifica cada pedido automáticamente en **Completo**, **En proceso** o **Por verificar**;
- permite cargar pedidos desde un formulario o desde un archivo Excel, sin necesidad de conocer formatos técnicos;
- mantiene un historial de cambios que nunca se borra;
- funciona en celular y computador desde cualquier navegador de la red interna.

## 2. Problema

| Situación actual | Riesgo |
|---|---|
| Pedidos en planillas o notas separadas | Se pierden pedidos o se duplican |
| No hay una vista general del estado | Envíos olvidados y cobros pendientes |
| No hay registro de cambios | Imposible saber quién cambió qué y cuándo |
| Datos cargados a mano por distintas personas | Errores de tipeo y estados contradictorios |

## 3. Solución propuesta

Una aplicación web de tres capas:

1. **Interfaz:** un dashboard con indicadores, una lista de pedidos, un formulario y la carga de Excel.
2. **Lógica (Flask):** valida los datos, aplica las reglas de clasificación, guarda los cambios y registra el historial.
3. **Datos (MySQL):** dos tablas, `pedidos` (estado actual) e `historial` (todos los movimientos).

### Flujo de datos

```
Excel o formulario  →  validación (normalizar)  →  transacción MySQL  →  historial  →  dashboard
```

Cada carga se procesa en una sola transacción: si una fila falla, el sistema informa el número de fila y el motivo. Las filas válidas se guardan y las erróneas se listan para corregir.

## 4. Reglas de negocio

| Categoría | Condición |
|---|---|
| **Completo** | Pagado y entregado, con número de guía |
| **En proceso** | Existe una acción pendiente (enviar, cobrar o contactar) |
| **Por verificar** | Falta un dato obligatorio, el envío está entregado sin guía, o hay contradicción (enviado sin pagar) |

Las reglas están en `app.py`, función `clasificar`, y se cubren con pruebas en `tests/test_reglas.py`.

## 5. Pasos de implementación

1. **Modelado de datos.** Se definieron dos tablas en `schema.sql`. Los estados usan `ENUM` para impedir valores inválidos. El historial solo admite inserciones.
2. **Reglas de negocio.** Se tradujeron los criterios de clasificación a una función pura (`clasificar`), sin acceso a base de datos, para poder probarla de forma aislada.
3. **Validación de entradas.** La función `normalizar` acepta mayúsculas, minúsculas y acentos en los estados, convierte montos y fechas, y rechaza datos incompletos con un mensaje claro.
4. **Persistencia transaccional.** La función `guardar` inserta o actualiza pedidos bloqueando la fila (`SELECT ... FOR UPDATE`), registra el historial con los campos que cambiaron y confirma todo en una sola transacción.
5. **API REST.** Seis rutas (ver README). Las rutas de envío y de carga reutilizan `normalizar` y `guardar`, así que la regla se aplica igual desde cualquier canal.
6. **Carga desde Excel.** Se lee la primera hoja con openpyxl. Los encabezados se reconocen con o sin acentos y se ignoran las filas vacías. La plantilla descargable incluye una hoja de instrucciones.
7. **Interfaz.** Un único archivo HTML con diseño responsive. Se adapta a pantallas pequeñas y consume la API con `fetch`. Los textos se escapan antes de mostrarse para evitar inyección de HTML.
8. **Pruebas.** Pruebas unitarias de las reglas de clasificación y validación.
9. **Documentación.** README con instalación paso a paso, tabla de la API y limitaciones conocidas.

## 6. Decisiones técnicas

| Decisión | Motivo |
|---|---|
| Flask | Ligero, fácil de desplegar en un servidor interno |
| MySQL | Motor conocido, transaccional y disponible en la mayoría de hostings |
| Reglas en Python, no en SQL | Son fáciles de probar y de cambiar sin tocar la base de datos |
| Historial de solo inserción | Trazabilidad: ningún cambio borra información anterior |
| Excel como canal de carga | Es la herramienta que ya usa el negocio; no requiere capacitación técnica |
| Sin frameworks de frontend | Un solo archivo HTML; menos piezas que mantener |

## 7. Resultados

- **Entregable:** aplicación completa con código, esquema, plantilla, pruebas y documentación.
- **Indicadores disponibles:** pedidos registrados, monto total, distribución por categoría.
- **Trazabilidad:** cada alta y cambio queda con fecha, detalle y origen (formulario, Excel o web).

### Verificación realizada

- Sintaxis de Python verificada en el entorno de desarrollo.
- Pruebas unitarias escritas para las reglas de clasificación y validación.

### Verificación pendiente

- **Ejecución de las pruebas** con `pytest` en un entorno con las dependencias instaladas.
- **Prueba de integración** contra una base MySQL real: alta, actualización, cambio de estado y carga de Excel.
- **Prueba de usuario** con un archivo Excel real de la plantilla.

Estas verificaciones deben completarse antes de un despliegue productivo.

## 8. Riesgos y limitaciones

| Riesgo | Mitigación propuesta |
|---|---|
| Sin inicio de sesión | Publicar solo en red interna o detrás de autenticación del servidor web |
| Sin respaldos automáticos | Respaldo diario de MySQL (`mysqldump`) |
| Montos con separador de miles | Documentado; se puede agregar validación más estricta |
| Concurrencia alta | Bajo el volumen de una micro-pyme no es un problema; el bloqueo por fila evita pérdidas |
| Reglas de negocio cambiantes | Están aisladas en una función; cambiarlas no afecta el resto del sistema |

## 9. Próximos pasos

1. Agregar inicio de sesión con roles (administrador y operador).
2. Exportar el dashboard y el historial a PDF o Excel.
3. Enviar aviso por correo cuando un pedido queda "Por verificar".
4. Registrar el usuario que hizo cada cambio, en lugar del origen.
5. Automatizar pruebas de integración con una base MySQL temporal.

## 10. Conclusión

El proyecto resuelve el problema central de la micro-pyme: tener una sola fuente de verdad sobre sus pedidos, con reglas claras y trazabilidad. Su diseño separa las reglas de negocio, la validación y la persistencia, lo que facilita mantenerlo y ampliarlo. Antes de un despliegue real, falta completar las pruebas de integración y agregar control de acceso.
