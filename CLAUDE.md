# gas_network_spain

Análisis inteligente de la red de transporte de gas natural en España mediante grafos, agentes LLM y visualización geoespacial.

## Objetivo del proyecto

Construir un sistema end-to-end que:
1. **Recopila** datos en tiempo real desde ENTSOG, CORES y Eurostat.
2. **Modela** la red como un grafo dirigido (NetworkX) con capacidades, longitudes y operadores reales.
3. **Analiza** flujos máximos, cuellos de botella y centralidad de nodos.
4. **Simula** escenarios de riesgo (corte de Medgaz, reducción de interconexiones con Francia, etc.).
5. **Genera** informes ejecutivos en PDF mediante un pipeline multi-agente (LangGraph + Claude).
6. **Visualiza** la red en mapas interactivos (Folium) y gráficas estáticas (matplotlib).

## Arquitectura

```
gas_network_spain/
├── src/
│   ├── collectors/          # Extracción de datos externos
│   │   ├── entsog_collector.py   # Flujos operacionales ENTSOG
│   │   ├── cores_collector.py    # Almacenamientos y terminales GNL (CORES)
│   │   └── eurostat_collector.py # Estadísticas de oferta/demanda (Eurostat)
│   ├── graph/               # Modelado y análisis del grafo
│   │   ├── network_builder.py    # Construcción del DiGraph NetworkX
│   │   ├── flow_analyzer.py      # Max-flow, cuellos de botella, centralidad
│   │   └── scenario_simulator.py # Simulación de escenarios what-if
│   ├── agents/              # Pipeline multi-agente (LangGraph)
│   │   ├── supervisor.py         # Orquestador del flujo de agentes
│   │   ├── graph_agent.py        # Agente de análisis de red (con tools)
│   │   └── report_agent.py       # Agente de generación de informes
│   ├── viz/                 # Visualización
│   │   ├── map_generator.py      # Mapas interactivos Folium
│   │   └── network_plot.py       # Gráficas estáticas matplotlib
│   └── reports/             # Generación de documentos
│       └── pdf_generator.py      # Markdown → PDF (ReportLab)
├── data/
│   ├── raw/                 # Datos brutos descargados (ignorados en git)
│   └── processed/           # Grafos, mapas, plots, informes generados
├── notebooks/               # Exploración y prototipado (Jupyter)
├── tests/                   # Suite de pruebas unitarias e integración
├── .env.example             # Plantilla de variables de entorno
├── requirements.txt         # Dependencias Python
└── CLAUDE.md                # Este archivo
```

## Fuentes de datos

| Fuente | Datos | Frecuencia |
|--------|-------|------------|
| [ENTSOG Transparency Platform](https://transparency.entsog.eu/) | Flujos físicos, nominaciones, interconexiones | Diaria |
| [CORES](https://www.cores.es/es/estadisticas) | Niveles de almacenamiento, terminales GNL | Mensual |
| [Eurostat](https://ec.europa.eu/eurostat/) | Oferta/demanda gas, comercio exterior | Mensual |
| [GIE AGSI+](https://agsi.gie.eu/) | Almacenamientos europeos en tiempo real | Diaria |

## Infraestructura modelada

- **6 terminales GNL**: Barcelona, Cartagena, Huelva, Sagunto, Bilbao, Mugardos
- **2 interconexiones Francia–España**: Irún (~530 GWh/d), Larrau (~180 GWh/d)
- **1 gasoducto Argelia–España**: Medgaz (~800 GWh/d)
- **1 interconexión Portugal–España**: Badajoz (~110 GWh/d)
- **Almacenamiento subterráneo**: Yela (Guadalajara)
- **Nodos de compresión y distribución**: Madrid, Zaragoza, Sevilla

## Escenarios predefinidos

| Escenario | Descripción |
|-----------|-------------|
| `MEDGAZ_DISRUPTION` | Cierre total del gasoducto Medgaz |
| `FRANCE_BORDER_REDUCTION` | Reducción del 50% en interconexiones FR-ES |
| `NEW_BISCAY_GULF_PIPE` | Nuevo gasoducto Midcat (800 GWh/d) |

## Pipeline de agentes

```
Usuario
  └─▶ Supervisor (LangGraph)
         ├─▶ Graph Agent  ──(tools: get_network_summary, get_bottlenecks,
         │                           get_centrality, run_scenarios)
         └─▶ Report Agent ──(Claude narrative + PDF generation)
```

## Variables de entorno requeridas

Copiar `.env.example` a `.env` y rellenar:

- `ANTHROPIC_API_KEY` — clave de la API de Anthropic (Claude)
- `GIE_API_KEY` — clave de la API de GIE/AGSI+ (opcional)
- `TELEGRAM_BOT_TOKEN` — token de bot de Telegram para alertas (opcional)

## Instalación rápida

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # y rellenar las claves
```

## Uso rápido

```python
# Construir la red
from src.graph.network_builder import build_network
G = build_network()

# Ejecutar pipeline completo
from src.agents.supervisor import run_pipeline
result = run_pipeline()
print(result["report_path"])

# Generar mapa interactivo
from src.viz.map_generator import generate_network_map
generate_network_map(G)
```

## Convenciones de código

- **Logging**: usar `loguru` (`from loguru import logger`), nunca `print()` en producción.
- **Datos brutos**: guardar siempre en `data/raw/` con formato Parquet.
- **Datos procesados**: grafos en `data/processed/` como GraphML.
- **Tests**: cubrir collectors y graph con pytest; mockar las APIs externas.
- **Secrets**: nunca hardcodear claves; usar siempre `python-dotenv` + `.env`.
