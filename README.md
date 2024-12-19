# Sistema de Atención al Cliente con IA y RAG

Este sistema proporciona una plataforma completa para la gestión de comunicaciones con clientes a través de SMS, utilizando IA para generar respuestas automáticas y RAG (Retrieval Augmented Generation) para proporcionar información actualizada y precisa.

## Características Principales

- 🤖 Respuestas automáticas con IA
- 📚 Sistema RAG para información actualizada
- 💬 Gestión de SMS con Telnyx
- 📊 Panel de administración completo
- 📝 Historial de conversaciones
- 📅 Vista de calendario
- 📋 Sistema Kanban

## Requisitos

- Python 3.8+
- SQLite3
- Cuenta de Telnyx
- Cuenta de Vultr Inference
- Dependencias listadas en `requirements.txt`

## Configuración

1. Clonar el repositorio
2. Crear un entorno virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Configurar variables de entorno en `.env`:
   ```env
   TELNYX_API_KEY=tu_api_key
   TELNYX_PUBLIC_KEY=tu_public_key
   VULTR_CLOUD_INFERENCE_API_KEY=tu_api_key
   TELNYX_FROM_NUMBER=tu_numero
   TELNYX_MESSAGING_PROFILE_ID=tu_profile_id
   DB_NAME=crm_pipeline.db
   WEBSITE_URL=tu_url
   PHONE_NUMBER=tu_telefono
   ```

## Estructura de la Base de Datos

El sistema utiliza SQLite con las siguientes tablas principales:

- `clientes`: Información básica de clientes
- `historial_mensajes`: Registro de todas las comunicaciones
- `documentos`: Almacenamiento para el sistema RAG
- `configuracion`: Configuraciones del sistema

## Sistema RAG

### Configuración del Sistema RAG

1. Acceder al panel de administración
2. Hacer clic en "Gestionar Documentos"
3. Agregar documentos con la siguiente información:
   - Título descriptivo
   - Tipo de documento (precio, contacto, promoción, etc.)
   - Contenido detallado

### Tipos de Documentos Soportados

- **Precios**: Listas de precios actualizadas
- **Contacto**: Información de contacto y horarios
- **Promoción**: Ofertas y descuentos vigentes
- **Destino**: Información sobre destinos específicos

### Funcionamiento del RAG

1. Al recibir una consulta:
   - Se genera un embedding del mensaje
   - Se buscan documentos relevantes
   - Se incorpora la información al prompt
   - Se genera una respuesta contextualizada

2. Actualización de información:
   - Los documentos se pueden actualizar en tiempo real
   - Los embeddings se generan automáticamente
   - La información antigua se puede desactivar

## Panel de Administración

### Características Principales

1. **Dashboard**
   - Estadísticas generales
   - Gráficos de actividad
   - Mensajes no leídos

2. **Gestión de Documentos**
   - Agregar/Editar documentos
   - Ver historial de cambios
   - Activar/Desactivar documentos

3. **Configuración de IA**
   - Editar prompt base
   - Ajustar parámetros de búsqueda
   - Ver logs de respuestas

### Vistas Disponibles

- **Kanban**: Gestión visual de casos
- **Calendario**: Vista temporal de interacciones
- **Detalle**: Información específica de cada cliente

## Ejemplos de Documentos RAG

### 1. Ejemplo de Precios

```json
{
    "titulo": "Precios Paquetes Cancún Verano 2024",
    "tipo": "precio",
    "contenido": "Paquetes todo incluido Cancún 2024:\n
    - Básico (3 noches): $599 USD por persona\n
    - Estándar (5 noches): $899 USD por persona\n
    - Premium (7 noches): $1,299 USD por persona\n
    Incluye: Vuelos, hotel, traslados y seguro de viaje.\n
    Válido para viajes entre junio y agosto 2024."
}
```

### 2. Ejemplo de Información de Contacto

```json
{
    "titulo": "Horarios y Contactos Oficina Central",
    "tipo": "contacto",
    "contenido": "Oficina Principal Los Ángeles:\n
    - Dirección: 123 Travel Street, LA 90001\n
    - Teléfono: (818) 244-2184\n
    - WhatsApp: +1 818-244-2184\n
    - Horario: Lunes a Viernes 9am-7pm, Sábados 10am-3pm\n
    - Email: info@paseotravel.com"
}
```

### 3. Ejemplo de Promoción

```json
{
    "titulo": "Promoción Especial Riviera Maya",
    "tipo": "promocion",
    "contenido": "¡Oferta especial Riviera Maya!\n
    - 30% descuento en paquetes de 5+ noches\n
    - Niños menores de 12 años viajan gratis\n
    - Incluye: Acceso a parques Xcaret y Xel-Há\n
    - Reserva antes del 30 de enero 2024\n
    - Válido para viajes hasta diciembre 2024"
}
```

### 4. Ejemplo de Información de Destino

```json
{
    "titulo": "Guía Los Cabos",
    "tipo": "destino",
    "contenido": "Los Cabos, Baja California Sur:\n
    - Mejor temporada: Octubre a Mayo\n
    - Actividades destacadas: Avistamiento de ballenas, golf, pesca deportiva\n
    - Playas principales: Médano, Santa María, Chileno\n
    - Temperatura promedio: 24°C-29°C\n
    - Vuelos directos desde LAX: 2.5 horas\n
    - Documentos necesarios: Pasaporte vigente"
}
```

### Ejemplos de Respuestas del Sistema

1. **Consulta sobre precios Cancún**
   ```
   Usuario: "¿Cuánto cuesta un paquete a Cancún para julio?"
   Sistema: "¡Tenemos excelentes opciones para Cancún! Actualmente hay paquetes desde $599 USD por persona (3 noches) hasta $1,299 USD (7 noches) todo incluido para el verano 2024. ¿Te gustaría más detalles sobre las opciones disponibles?"
   ```

2. **Consulta sobre horarios**
   ```
   Usuario: "¿Hasta qué hora están abiertos?"
   Sistema: "Estamos disponibles de lunes a viernes de 9am a 7pm y los sábados de 10am a 3pm. Puedes contactarnos al (818) 244-2184 o por WhatsApp para atención personalizada."
   ```

3. **Consulta sobre promociones**
   ```
   Usuario: "¿Tienen alguna promoción para Riviera Maya?"
   Sistema: "¡Sí! Tenemos una promoción especial con 30% de descuento en paquetes de 5+ noches en Riviera Maya, y los niños menores de 12 años viajan gratis. Incluye acceso a parques Xcaret y Xel-Há."
   ```

### Mejores Prácticas para Documentos RAG

1. **Formato del Contenido**
   - Usar listas con guiones para mejor legibilidad
   - Incluir precios en formato consistente (USD)
   - Especificar fechas de validez
   - Mantener información concisa pero completa

2. **Actualización de Documentos**
   - Actualizar precios regularmente
   - Marcar promociones expiradas como inactivas
   - Mantener información de contacto al día
   - Verificar fechas de validez

3. **Organización**
   - Usar títulos descriptivos y específicos
   - Categorizar correctamente el tipo de documento
   - Mantener formato consistente
   - Incluir detalles relevantes para búsquedas

4. **Contenido Recomendado por Tipo**

   **Precios:**
   - Valor en USD
   - Qué incluye
   - Fechas de validez
   - Condiciones principales

   **Contacto:**
   - Dirección completa
   - Teléfonos con código de área
   - Horarios detallados
   - Medios de contacto alternativos

   **Promociones:**
   - Descuento o beneficio específico
   - Condiciones
   - Fechas de validez
   - Restricciones

   **Destinos:**
   - Ubicación
   - Mejor temporada
   - Atracciones principales
   - Información práctica

## Mantenimiento

### Respaldos

Se recomienda realizar respaldos regulares de:
- Base de datos SQLite
- Documentos y embeddings
- Configuraciones personalizadas

### Monitoreo

El sistema incluye logging detallado:
- Errores de IA
- Problemas de conexión
- Fallos en búsqueda RAG

## Solución de Problemas

### Problemas Comunes

1. **Error en respuestas IA**
   - Verificar conexión con Vultr
   - Revisar prompt base
   - Comprobar logs de error

2. **Documentos no encontrados**
   - Verificar umbral de similitud
   - Regenerar embeddings
   - Comprobar estado del documento

3. **SMS no enviados**
   - Verificar credenciales Telnyx
   - Comprobar formato de números
   - Revisar logs de envío

## Mejores Prácticas

1. **Gestión de Documentos**
   - Mantener información actualizada
   - Usar títulos descriptivos
   - Organizar por categorías claras

2. **Configuración de IA**
   - Mantener prompt base claro
   - Ajustar umbral según necesidad
   - Revisar respuestas periódicamente

3. **Monitoreo**
   - Revisar logs regularmente
   - Verificar calidad de respuestas
   - Actualizar información obsoleta

## Soporte

Para problemas técnicos o consultas:
- Revisar logs en `/logs/app.log`
- Consultar documentación de APIs
- Contactar soporte técnico

## Licencia

Este proyecto está bajo la licencia MIT. Ver archivo `LICENSE` para más detalles.

####
El sistema RAG está funcionando correctamente ahora con:

Generación de embeddings locales usando sentence-transformers
Almacenamiento de documentos y embeddings en SQLite
Búsqueda semántica con un umbral de similitud de 0.5
Logging detallado para monitorear el proceso
El servidor está corriendo en el puerto 5004 y puedes usar los endpoints:

/agregar-documentos-prueba para agregar más documentos
/test-rag para probar consultas
/limpiar-db para limpiar la base de datos si es necesario


##He agregado:

Un nuevo endpoint /limpiar-mensajes que elimina todos los registros de la tabla historial_mensajes
Un botón rojo "Limpiar Mensajes" en el panel administrativo junto al botón existente de limpiar base de datos
La funcionalidad JavaScript que:
Muestra un diálogo de confirmación antes de limpiar
Hace la petición POST al endpoint
Muestra un mensaje de éxito o error
Recarga la página para mostrar los cambios
El botón está claramente diferenciado del botón de limpiar toda la base de datos:

"Limpiar Base de Datos" es amarillo (warning) porque es más destructivo
"Limpiar Mensajes" es rojo (danger) pero solo afecta a los mensajes
Ahora puedes reiniciar el servidor para que los cambios tomen efecto.

