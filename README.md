# filesystem-sim

Simulador de **Sistemas de Archivos** que implementa y compara tres estrategias de asignación:
- Asignación Contigua
- Asignación Enlazada 
- Asignación Indexada

## Características

### Interfaces
- **CLI Interactiva**: Menú con 5 opciones principales
  - Listar estrategias disponibles
  - Listar escenarios de prueba
  - Ejecutar simulación única
  - Ejecutar barrido (todas las estrategias)
  - Salir

- **UI Gráfica** (opcional):
  - Visualización en tiempo real del bitmap del disco
  - Resultados detallados con métricas por estrategia
  - Modo "demo" para visualización lenta

### Métricas Implementadas
- Tiempo promedio de acceso (ms)
- Uso de espacio (%)
- Fragmentación externa/interna (%)
- Throughput (ops/seg)
- Estimación de seeks
- Tiempo total de simulación
- CPU usage
- Fairness index

### Escenarios Predefinidos
- **mix-small-large**: Mezcla de archivos pequeños y grandes (60% seq / 40% rand)
- **seq-vs-rand**: Comparativa acceso secuencial vs aleatorio
- **frag-intensive**: Creación/borrado intensivo para fragmentación

## Requisitos

### Mínimos
- Python 3.10+

### Opcionales (UI)
- `customtkinter`
- `pandas` 
- `matplotlib`

## Uso

### CLI Interactiva
```bash
python -m src.fsim
```

### UI Gráfica
```bash
python -m src.fsim.ui.app
```

## Estructura de Archivos
```
src/fsim/
  ├── core/           # Abstracciones base (Block, Disk, FilesystemBase)
  ├── fs_strategies/  # Implementaciones de las 3 estrategias
  ├── sim/           # Motor de simulación y métricas
  ├── cli/           # Interfaz de línea de comandos
  └── ui/            # Interfaz gráfica (opcional)
```

## Salida de Resultados
Los resultados se guardan en el directorio `results/` en formato JSON o CSV, incluyendo:
- Métricas detalladas por estrategia
- Estado final del bitmap
- Tiempos de operación
- Estadísticas de fragmentación

## Documentación
El diseño y resultados experimentales se documentan en `docs/acl_paper/`.

## Notas de Implementación
- Todas las estrategias están completamente implementadas y funcionales
- El sistema incluye detección de corrupción y validaciones
- Soporte para instrumentación y eventos para métricas detalladas
