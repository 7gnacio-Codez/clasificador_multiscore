# Clasificador Multi-Categoría por Puntuación 

Un algoritmo determinista diseñado para procesar transcripciones de texto (ej. llamadas de cobranza, atención al cliente) y clasificar múltiples intenciones simultáneamente mediante un sistema de pesos matemáticos.

A diferencia de un clasificador tradicional que se detiene en la primera coincidencia, este motor lee el texto completo, evalúa todas las categorías configuradas de forma independiente, suma los puntajes de las palabras clave encontradas y determina la categoría principal, manteniendo la visibilidad de los temas secundarios.

## Características Principales

*   **Detección Multi-Intención:** Identifica si una llamada contiene tanto una "Promesa de Pago" como un "Reclamo Legal" y puntúa ambas.
*   **Determinista:** No alucina. Si el cliente dice "SERNAC", la alerta legal se dispara con la precisión y el peso exacto configurado.
*   **Trazabilidad y Evidencia:** Extrae qué palabras exactas gatillaron el puntaje y cuántas veces se repitieron.
*   **Reglas:** Las reglas de negocio viven en un archivo `.json` fácil de editar.

## Estructura de Configuración (`cobranzas_config.json`)

El archivo JSON debe tener una estructura jerárquica: `Categoría -> Palabra Clave -> Puntaje`.

```json
{
    "Promesa de Pago (PDP)": {
        "pago el viernes": 50,
        "ya pagué": 100
    },
    "Riesgo Legal / Reclamo": {
        "sernac": 100,
        "cmf": 100
    },
    "Vulnerabilidad Económica": {
        "estoy cesante": 80,
        "no tengo plata": 50
    }
}
```

## Uso desde la Consola (CLI)

Ideal para pruebas rápidas de las reglas de negocio.

**Prueba básica:**
```bash
python classifier_multiscore.py "No tengo plata estoy cesante, pero si consigo trabajo les pago el viernes"
```

**Salida esperada (resumida):**
```json
{
    "categoria_principal": "Vulnerabilidad Económica",
    "scores_por_categoria": {
        "Promesa de Pago (PDP)": 50.0,
        "Riesgo Legal / Reclamo": 0.0,
        "Vulnerabilidad Económica": 130.0
    },
    "evidencia_detallada": { ... }
}
```

## Uso como Módulo

```python
from classifier_multiscore import MultiCategoryScoreClassifier

# 1. Instanciar leyendo las reglas de negocio
clasificador = MultiCategoryScoreClassifier.from_json("config.json")

# 2. Evaluar una transcripción en tiempo real
transcripcion = "Alo, sí, voy a poner un reclamo en la cmf porque son unos sinverguenzas"
resultado = clasificador.evaluate_text(transcripcion)

# 3. Orquestar decisiones basadas en los scores
if resultado["scores_por_categoria"]["Riesgo Legal / Reclamo"] >= 100:
    print("ALERTA: Derivar ticket a equipo Legal de inmediato.")
```

## 🛠️ Métodos Principales

*   `MultiCategoryScoreClassifier.from_json(path)`: Inicializa el motor leyendo el JSON y precompilando las expresiones regulares de manera optimizada.
*   `evaluate_text(text: str)`: Retorna un diccionario con la `categoria_principal`, los `scores_por_categoria` y la `evidencia_detallada`.
*   `process_payload(data: list, text_key: str)`: Procesa listas masivas de diccionarios (ej. lotes de transcripciones de una base de datos) y adjunta el `analisis_multiscore` a cada registro.