# re-helper — Real Estate Automation Tools

A collection of CLI tools for real estate automation, from social media listing generation to property inventory management.

---

## Tools

### 1. Listing Generator (`create_listing.py`)

Generates a polished 1080x1080 PNG social media post for real estate properties. Renders at 2x supersampling for crisp edges and supports a property photo or a dark gradient placeholder.

```
┌──────────────────────────────────────────┐
│ [Property Type]          [Agency block]  │
│                                          │
│          (property photo area)           │
│                                          │
├──────────────────────────────────────────┤
│  $Price                                  │
│  Property Title                          │
│  🛏 4  🚿 3  📐 320 m²                  │
│  📍 Location                             │
└──────────────────────────────────────────┘
```

#### Requirements

- Python 3.8+
- [pycairo](https://pycairo.readthedocs.io/) — vector drawing and text
- [Pillow](https://python-pillow.org/) — color emoji compositing
- numpy *(optional, speeds up image conversion)*

##### System fonts

The script expects these fonts installed at the paths below. Update the constants at the top of `create_listing.py` if your paths differ.

| Constant | Default path |
|---|---|
| `FONT_BOLD` | `/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf` |
| `FONT_MEDIUM` | `/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf` |
| `FONT_LIGHT` | `/usr/share/fonts/truetype/google-fonts/Poppins-Light.ttf` |
| `FONT_EMOJI` | `/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf` |

On Ubuntu/Debian:

```bash
sudo apt install fonts-noto-color-emoji
# Poppins via google-fonts package or manual install:
sudo apt install fonts-google-poppins   # if available, otherwise download from fonts.google.com
```

#### Installation

```bash
pip install pycairo pillow numpy
```

#### Usage

##### Via command-line flags

```bash
python create_listing.py \
    --price "$4,500,000 MXN" \
    --title "Casa Moderna en Polanco" \
    --location "Polanco, CDMX" \
    --rooms 4 --baths 3 --area 320 \
    --property-type "Casa en Venta" \
    --agency "Prestige Real Estate" \
    --agent "María López" \
    --phone "+52 55 1234 5678" \
    --photo property.jpg \
    --output listing.png
```

##### Via XML file

```bash
python create_listing.py --xml listing_data.xml --output listing.png
```

**XML structure:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<listing>
    <!-- Property information -->
    <price>$4,500,000 MXN</price>
    <title>Casa Moderna en Polanco</title>
    <location>Polanco, CDMX</location>
    <rooms>4</rooms>
    <baths>3</baths>
    <area>320</area>
    <property_type>Casa en Venta</property_type>

    <!-- Agent / Agency information -->
    <agency>Prestige Real Estate</agency>
    <agent>María López</agent>
    <phone>+52 55 1234 5678</phone>

    <!-- Optional: path to property photo (leave empty for placeholder) -->
    <photo>property.jpg</photo>
</listing>
```

Generate a ready-to-edit template:

```bash
python create_listing.py --sample-xml > my_listing.xml
```

##### All flags

| Flag | Description |
|---|---|
| `--price` | Property price (displayed large, top of bottom bar) |
| `--title` | Property title |
| `--location` | Neighborhood / city shown with pin emoji |
| `--rooms` | Number of bedrooms |
| `--baths` | Number of bathrooms |
| `--area` | Area in m² |
| `--property-type` | Label shown in the top-left pill (e.g. "Casa en Venta") |
| `--agency` | Agency name (top-right block) |
| `--agent` | Agent name (top-right block, shown with 👩🏻‍💼) |
| `--phone` | Agent phone number (top-right block, shown with ☎) |
| `--photo` | Path to a property photo (JPEG/PNG); omit for gradient placeholder |
| `--xml` | Load all fields from an XML file instead of flags |
| `--sample-xml` | Print a sample XML to stdout and exit |
| `--output`, `-o` | Output PNG path (default: `listing.png`) |

#### Customization

All layout and style constants are at the top of `create_listing.py` with inline comments:

| Constant | What it controls |
|---|---|
| `CANVAS` | Output resolution (default 1080) |
| `BOTTOM_BAR_H` | Height of the bottom navy band |
| `MARGIN` | Left/right margin for all text |
| `DEEP_BLUE` / `GOLD` / `LIGHT_GOLD` | Brand colors |
| `FONT_BOLD/MEDIUM/LIGHT/EMOJI` | Font file paths |
| `AGENCY_FONT_SIZES` | Font sizes for agency name, agent, phone |
| `AGENCY_LINE_GAP` | Vertical spacing between agency block lines |
| `AGENCY_PAD` | Internal padding of the agency card |

---

### 2. Property Inventory (`inventory.py`)

Manages a property database: stores listings in CSV and exports formatted multi-sheet XLSX reports grouped by property type, transaction type, and zone.

#### Supported property types

`casa`, `departamento`, `loft`, `penthouse`, `terreno`, `lote`, `bodega`, `local`, `oficina`, `consultorio`

#### Supported transaction types

`venta`, `renta`

#### Installation

`xlsxwriter` is auto-installed on first run. To install manually:

```bash
pip install xlsxwriter
```

#### Usage

```
python inventory.py [--csv FILE] [--xlsx FILE] <command>
```

| Option | Default | Description |
|---|---|---|
| `--csv` | `propiedades.csv` | Path to the CSV data file |
| `--xlsx` | `reporte_inmobiliario.xlsx` | Path for the generated XLSX report |

##### Commands

| Command | Description |
|---|---|
| `agregar` | Add a single property via flags |
| `agregar-lote` | Add multiple properties from a JSON file |
| `reporte` | Generate the XLSX report from the current CSV |
| `resumen` | Print a summary of the CSV to the terminal |
| `ejemplo` | Load 10 sample properties into the CSV |
| `interactivo` | Start an interactive menu |

##### Add a single property

```bash
python inventory.py agregar \
    --id 011 \
    --tipo casa \
    --transaccion venta \
    --precio 4500000 \
    --superficie 200 \
    --construccion 150 \
    --cuartos 3 \
    --banos 2 \
    --cochera 2 \
    --zona Polanco \
    --direccion "Av. Horacio 500" \
    --folder /docs/011
```

Use `--force` to save even when validation warnings are present.

##### Add properties from a JSON file

```bash
python inventory.py agregar-lote --archivo propiedades.json
```

The JSON file must be a list of objects using the field names: `id`, `property_type`, `transaction_type`, `price`, `m2_terrain`, `m2_construction`, `bedrooms`, `baths`, `garage`, `location`, `address`, `file_path`.

```json
[
  {
    "id": "011",
    "property_type": "casa",
    "transaction_type": "venta",
    "price": "4500000",
    "m2_terrain": "200",
    "m2_construction": "150",
    "bedrooms": "3",
    "baths": "2",
    "garage": "2",
    "location": "Polanco",
    "address": "Av. Horacio 500, CDMX",
    "file_path": "/docs/011"
  }
]
```

##### Generate XLSX report

```bash
python inventory.py reporte
# or with custom paths:
python inventory.py --csv datos.csv --xlsx salida.xlsx reporte
```

The report contains four sheets:

| Sheet | Contents |
|---|---|
| Resumen General | All properties with totals and averages |
| Por Tipo Propiedad | Properties grouped by type |
| Por Transacción | Properties grouped by transaction (venta / renta) |
| Por Zona | Properties grouped by zone |

Each sheet includes a summary row with total price, average m², and totals for bedrooms, bathrooms, and garage spaces.

##### Print terminal summary

```bash
python inventory.py resumen
```

##### Load sample data

```bash
python inventory.py ejemplo
```

Loads 10 sample properties (diverse types and zones in CDMX) into the CSV.

##### Interactive mode

```bash
python inventory.py interactivo
```

Launches a numbered menu to add properties, load samples, generate reports, or view a summary — no flags required.
