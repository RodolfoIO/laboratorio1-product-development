# Decisiones técnicas y de producto

## Horizonte y frecuencia

Se eligió publicación semanal con horizonte de 7 días porque coincide con la necesidad de pedidos de la operación y mantiene el flujo demostrable en Airflow. La fecha de corte es parte de la clave de cada artefacto; un backfill crea o reemplaza únicamente el resultado de ese corte.

## Disponibilidad temporal

Las ventas y transacciones se consideran disponibles un día después de su fecha observada. Los feriados se consideran disponibles con siete días de anticipación. El petróleo se usa únicamente hasta su última fecha disponible. Las ventas futuras nunca entran en features de una predicción.

El modelo se entrena con rezagos y ventanas desplazadas; las ventanas usan `shift(1)` antes de calcular medias. El pronóstico de varios días es recursivo: después de cada día se agrega únicamente la predicción p50, no la venta real futura.

## Bandeja y correcciones

La carpeta original de Kaggle es una fuente externa de solo lectura. La bandeja genera un manifest lógico por fuente y fecha con fecha de disponibilidad y hash SHA-256. Una corrección produce un hash diferente y permite reprocesar los cortes afectados sin editar la entrega original.

## Validación

Se detiene la ingesta cuando faltan columnas, hay fechas inválidas, claves duplicadas, archivos vacíos o valores negativos donde no están permitidos. Un pronóstico todavía sin ventas reales se marca como pendiente y no como error de Airflow.

## Modelos

El baseline es un rezago de siete días con fallback a la media de los últimos 28 días. El candidato es un modelo global `HistGradientBoostingRegressor` entrenado con pérdidas cuantílicas p10, p50 y p90. Un modelo global reduce la cantidad de artefactos y permite aprender patrones compartidos entre tiendas y familias.

Se usan las mismas fechas de validación para ambos modelos. El modelo candidato solo se promociona cuando reduce al menos 5% la pérdida económica y no empeora el WAPE más de 2%. Si no cumple, se conserva el baseline.

## Pedido y costos

El dataset no contiene inventario disponible ni tiempo de reposición. Por eso el producto publica un requerimiento bruto de demanda para cada tienda-familia, no una orden neta.

El cuantil crítico se deriva de los costos:

```text
cuantil = costo_de_quiebre / (costo_de_quiebre + costo_de_merma)
```

La configuración está en `configs/business.yaml`. Los pronósticos publican p10, p50 y p90; si el cuantil crítico queda entre ellos, se interpola linealmente. Cambiar costos modifica el pedido sin modificar el programa.

## DVC y reproducibilidad

Git conserva código, configuración, DAGs, pruebas y archivos `.dvc`. DVC conserva datos, features, modelos, pronósticos y reportes. El remoto se configura fuera del código para que el equipo docente pueda ejecutar `dvc pull` sin que existan credenciales en el repositorio.

## Airflow

Los DAGs solo llaman módulos Python. Cada resultado se escribe en una ruta determinista por fecha de corte y se vuelve a generar de forma idempotente. `catchup=True` permite backfill; una corrección cambia el hash del snapshot y reabre las etapas downstream.

