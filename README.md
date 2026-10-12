# 🌍 Global Air Quality Monitor

End-to-end data pipeline that ingests real-time air quality measurements from the [OpenAQ API](https://openaq.org/), transforms them through a modular dbt layer, and serves an interactive Streamlit dashboard with WHO threshold alerts.

## Architecture

```
OpenAQ API v3 → dlt (Python) → DuckDB → dbt → Streamlit
```

| Layer     | Tool           | Purpose                                  |
|-----------|----------------|------------------------------------------|
| Ingestion | dlt            | Extract from REST API, load into DuckDB  |
| Storage   | DuckDB         | Lightweight columnar analytics database  |
| Transform | dbt            | Staging → Mart models in SQL             |
| Dashboard | Streamlit      | Interactive charts, maps, WHO alerts     |
| Quality   | dbt tests      | not_null, unique, accepted_values checks |
| CI        | GitHub Actions | Lint + dbt compile on every push         |

## Dashboard

The dashboard provides:

- **KPI metrics** — cities monitored, total readings, WHO alert count
- **Top 10 polluted cities** — horizontal bar chart ranked by average pollutant level
- **Pollutant trends** — daily values with 3-day moving average per city
- **Country comparison** — grouped bar chart comparing pollutant levels across countries
- **WHO alerts table** — cities exceeding WHO air quality guidelines
- **Station map** — interactive map of all monitoring stations

## Pollutants Tracked

| Parameter | Name               | WHO 24h Guideline |
|-----------|--------------------|-------------------|
| PM2.5     | Fine particles     | 15 µg/m³          |
| PM10      | Coarse particles   | 45 µg/m³          |
| NO2       | Nitrogen dioxide   | 25 µg/m³          |
| O3        | Ozone              | 100 µg/m³         |
| SO2       | Sulfur dioxide     | 40 µg/m³          |
| CO        | Carbon monoxide    | 4 mg/m³           |

## Quick Start

### Option 1: Docker (recommended)

```bash
cp .env.example .env
# Add your OpenAQ API key to .env
docker-compose up
# Dashboard available at http://localhost:8501
```

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/konstantinostraganos/air-quality-monitor.git
cd air-quality-monitor

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your OpenAQ API key to .env

# Run the pipeline
python pipeline.py

# Run dbt transformations
cd analytics
dbt run
dbt test
cd ..

# Launch dashboard
streamlit run dashboard.py
```

## Configuration

Edit `.env` to customize the pipeline:

```
OPENAQ_API_KEY=your_key_here        # Required: get free key at explore.openaq.org
PIPELINE_COUNTRIES=80,50,22,91,67   # Country IDs: GR, DE, FR, IT, ES
PIPELINE_DAYS_BACK=7                # Number of days to fetch
PIPELINE_PAGE_LIMIT=100             # Results per API page
```

## dbt Models

```
models/
├── staging/
│   ├── stg_locations.sql        # Clean station metadata
│   ├── stg_sensors.sql          # Filter to target pollutants
│   └── stg_measurements.sql     # Remove nulls and negative values
└── marts/
    ├── city_daily_avg.sql       # Daily averages per city/pollutant
    ├── who_alerts.sql           # WHO guideline threshold checks
    └── pollutant_trends.sql     # 3-day moving average trends
```

## Project Structure

```
air-quality-monitor/
├── pipeline.py              # dlt ingestion from OpenAQ API
├── dashboard.py             # Streamlit dashboard
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image
├── docker-compose.yml       # One-command deployment
├── Makefile                 # Development shortcuts
├── .env.example             # Environment template
├── .gitignore               # Git exclusions
├── analytics/               # dbt project
│   ├── dbt_project.yml
│   ├── models/
│   │   ├── staging/
│   │   └── marts/
│   └── tests/
├── tests/                   # Python tests
└── .github/workflows/
    └── ci.yml               # GitHub Actions CI
```

## Tech Stack

- **Python 3.12** — pipeline and dashboard
- **dlt** — data ingestion framework
- **DuckDB** — embedded analytical database
- **dbt** — SQL transformation layer
- **Streamlit** — interactive dashboard framework
- **Plotly** — charts and maps
- **GitHub Actions** — CI/CD
- **Docker** — containerized deployment

## Data Source

[OpenAQ](https://openaq.org/) — a nonprofit providing universal access to air quality data. Data is sourced from government monitoring stations across Europe.

## License

MIT
