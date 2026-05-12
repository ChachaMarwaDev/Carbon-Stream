### 1. Core Emission Metrics (What is being measured)

Relying on CO₂ alone creates blind spots since different sectors emit different greenhouse gases. A complete national comparison requires:

- **CO₂ (excluding LULUCF)** – baseline for fossil fuel and industrial emissions
- **CH₄ (Methane)** – key for agriculture and natural gas sectors
- **N₂O (Nitrous Oxide)** – reflects fertilizer and agricultural intensity
- **F-gases** – tied to industrial processes (where available)
- **Total GHG (CO₂-equivalent)** – unified metric for cross-country comparison

**Data Sources:** Global Carbon Project, World Bank

---

### 2. Climate & Weather Drivers (What influences emissions and variability)

Using Copernicus ERA5 reanalysis data, the following variables explain carbon behavior:

**High Priority (Core Drivers):**

- 2m Temperature – affects respiration, energy demand, growing seasons
- Total Precipitation – controls soil moisture and productivity
- Surface Solar Radiation – drives photosynthesis and solar energy
- Surface Pressure – needed for accurate CO₂ calculations

**Medium Priority (Transport & Dynamics):**

- Dew Point / Humidity – influences plant stress and evapotranspiration
- 10m Wind Speed – determines CO₂ dispersion
- Sensible & Latent Heat Flux – affect atmospheric mixing

**Advanced:**

- Boundary Layer Height – explains concentration spikes and trapping effects

---

### 3. Ground Truth & Validation (Ensuring accuracy)

Models and emission inventories can be biased, so validation is essential:

- **Atmospheric CO₂ validation:**  
    Use NOAA CarbonTracker and station data (e.g., Mauna Loa Observatory)
- **Air quality proxy:**  
    PM2.5 data (from the World Bank) correlates with fossil fuel emissions
- **Satellite validation:**  
    Use NASA / JAXA missions (GOSAT, OCO-2) for independent CO₂ observations

---

### 4. Final Data Checklist

A robust pipeline should include:

- **GHG Inventory:** CO₂, CH₄, N₂O, Total GHG
- **Meteorological Data:** Temperature, Precipitation, Solar Radiation, Wind, Pressure, Dew Point
- **Land–Atmosphere Exchange:** Heat fluxes
- **Validation Layer:** NOAA CO₂ data & CarbonTracker
- **Air Quality Indicator:** PM2.5
- **Satellite Data:** CO₂ column observations