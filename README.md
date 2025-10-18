# filesystem-sim

Simulador de **Sistemas de Archivos** (contigua, enlazada, indexada) con:
- **CLI** ejecutable: `python -m fsim …`
- **UI** opcional en `customtkinter` (no requerida para correr).
- **Resultados** en `results/` (CSV/JSON) para el paper ACL en `docs/acl_paper/`.

## Requisitos mínimos
- Python 3.10+
- (Opcional) `customtkinter` para la UI
- (Opcional) `pandas` y `matplotlib` si deseas tablas/gráficos desde UI

## Ejecutar por consola
```bash
# Mostrar estrategias y escenarios
python -m fsim list-strategies
python -m fsim list-scenarios

# Ejecutar un escenario predefinido con asignación contigua
python -m fsim run --strategy contiguous --scenario mix-small-large --out results/mix_contigua.csv

# Barrido de parámetros (ejemplo)
python -m fsim sweep --strategy all --scenario frag-intensive --vary block-size=1024,2048,4096 --repeats 3 --out results/sweep.json
```

> Nota: Las estrategias están en **stubs** y levantan `NotImplementedError` hasta que cada Dev implemente su parte.
