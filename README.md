# Sheet Cutting Optimization App

A Tkinter-based desktop application for optimizing sheet cutting, visualizing results, and exporting to Google Sheets.

## Features
- Add, edit, and manage parts for cutting
- Packing optimization using multiple algorithms
- Visualize cutting plans interactively
- Export results to a single Google Sheet (with tab per export)

## Structure
- `main.py` — Entry point
- `ui/app_ui.py` — Main Tkinter UI
- `models/part.py` — Data models (Part, Placement, Sheet)
- `packing/engine.py` — Packing and optimization logic
- `visualization/visualizer.py` — Visualization system
- `export/google_sheets.py` — Google Sheets export logic
- `config.py` — Constants and configuration

## Setup
1. Install dependencies:
   ```
pip install -r requirements.txt
   ```
2. Set up your Google service account and place the JSON key in the project directory.
3. (Optional) Set the `GOOGLE_SHEET_ID` environment variable to use an existing Google Sheet.

## Usage
Run the app:
```
python main.py
```

## Contributing
Pull requests and suggestions are welcome!

## License
MIT
