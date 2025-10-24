# filesystem-sim

Simulador de **Sistemas de Archivos** que implementa y compara tres estrategias de asignación:
- **Asignación Contigua**: Bloques contiguos en disco para acceso secuencial óptimo
- **Asignación Enlazada**: Bloques enlazados con punteros para flexibilidad
- **Asignación Indexada**: Bloques indexados para acceso aleatorio eficiente

## Características

### Interfaces
- **CLI Interactiva**: Interfaz en línea de comandos con:
  - Listado y selección de estrategias
  - Configuración de escenarios de prueba
  - Ejecución de simulaciones individuales y comparativas
  - Visualización de resultados y métricas

- **UI Gráfica** (Implementada con customtkinter):
  - Visualización interactiva del estado del disco
  - Monitoreo en tiempo real de operaciones
  - Análisis gráfico de métricas y resultados
  - Vista detallada de la fragmentación

### Métricas Implementadas
- **Rendimiento**:
  - Tiempo promedio de acceso (ms)
  - Throughput (operaciones/seg)
  - Estimación de seeks y movimientos de cabeza
  - Tiempo total de operación

- **Utilización**:
  - Uso efectivo del espacio (%)
  - Fragmentación interna y externa (%)
  - Overhead por metadatos
  - Índice de equidad (fairness)

- **Recursos**:
  - Uso de CPU (%)
  - Memoria utilizada
  - Hit/Miss ratio
  - Tiempo de CPU total

### Escenarios Predefinidos
- **mix-small-large**:
  - Mezcla realista de archivos (200 pequeños, 30 grandes)
  - Patrón 60% secuencial / 40% aleatorio
  - 10% tasa de borrado
  - 1000 operaciones

- **seq-vs-rand**:
  - Enfoque en patrones de acceso
  - 90% accesos secuenciales vs aleatorios
  - 150 archivos pequeños, 20 grandes
  - 5% tasa de borrado

- **frag-intensive**:
  - Prueba de fragmentación intensiva
  - 40% tasa de borrado
  - 250 archivos pequeños, 10 grandes
  - 1500 operaciones

## Requisitos e Instalación

### Requisitos Base
- Python 3.10 o superior
- pip (gestor de paquetes de Python)

### Dependencias Principales
```bash
pip install -r requirements.txt
```

### Dependencias Opcionales (UI)
```bash
pip install customtkinter pandas matplotlib
```

## Uso

### CLI Interactiva
```bash
# Ejecutar simulación interactiva
python -m src.fsim

# Ejecutar escenario específico
python -m src.fsim --scenario seq-vs-rand

# Comparar todas las estrategias
python -m src.fsim --compare-all
```

### UI Gráfica
```bash
# Iniciar interfaz gráfica
python -m src.fsim.ui.app
```

## Estructura del Proyecto
```
src/fsim/
  ├── core/              # Núcleo del sistema
  │   ├── block.py      # Gestión de bloques
  │   ├── disk.py       # Simulación de disco
  │   └── filesystem_base.py  # Clase base abstracta
  │
  ├── fs_strategies/    # Implementaciones
  │   ├── contiguous.py  # Asignación contigua
  │   ├── linked.py      # Asignación enlazada
  │   └── indexed.py     # Asignación indexada
  │
  ├── sim/              # Motor de simulación
  │   ├── metrics.py     # Cálculo de métricas
  │   ├── runner.py      # Ejecución de pruebas
  │   └── workload_generators.py  # Generadores
  │
  ├── cli/              # Interfaz de comandos
  └── ui/               # Interfaz gráfica
      ├── app.py        # Aplicación principal
      ├── disk_view.py  # Vista del disco
      └── charts_view.py # Gráficas y métricas
```

## Resultados y Análisis
Los resultados se almacenan en formato JSON en el directorio `results/`:

```json
{
  "estrategia": {
    "avg_access_time_ms": 0.088,
    "space_usage_pct": 47.05,
    "fragmentation_internal_pct": 0.0,
    "fragmentation_external_pct": 6.53,
    "throughput_ops_per_sec": 451.66,
    ...
  }
}
```

### Métricas Disponibles
- Métricas detalladas por estrategia
- Análisis temporal de operaciones
- Estadísticas de fragmentación
- Perfiles de rendimiento

## Detalles de Implementación

### Características Avanzadas
- Detección y manejo de corrupción de datos
- Validación de operaciones y límites
- Eventos instrumentados para métricas
- Soporte para patrones de acceso personalizados

### Optimizaciones
- Gestión eficiente de espacio libre
- Caché de metadatos
- Operaciones batch para mejor rendimiento
- Detección de fragmentación en tiempo real
