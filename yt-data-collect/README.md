# YT Data Collect

A CLI tool for searching YouTube videos and batch-downloading their subtitles as `.srt` files. The results are automatically archived into a ZIP file for easy management.

---

## Project Structure
Based on the current workspace:
```text
yt-data-collect/
├── .venv/               # Virtual environment
├── config.yaml          # Configuration settings
├── README.md            # Documentation
├── requirements.txt     # Python dependencies
└── yt_subtitle_cli.py   # Main script
```

---

## Installation

### 1. Navigate to the project
```bash
cd yt-data-collect
```

### 2. Set Up Virtual Environment
If you haven't created the `.venv` folder yet:
```bash
python -m venv .venv
```

### 3. Activate the Environment
* **Windows:**
    ```bash
    .venv\Scripts\activate
    ```
* **macOS/Linux:**
    ```bash
    source .venv/bin/activate
    ```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Usage

### Option 1: Using the Config File
Edit `config.yaml` with your preferred settings and run:
```bash
python -m yt_subtitle_pipeline.cli --config configs/config.yaml
```

### Option 2: Command Line Overrides
Use the config file but change the search query on the fly:
```bash
python yt_subtitle_pipeline.cli --config configs/config.yaml --query "data science" --limit 10
```

### Option 3: Manual Execution
Run the script with full parameters bypassing the config file:
```bash
python yt_subtitle_cli.py \
    --query "python tutorials" \
    --limit 5 \
    --output subtitles_bundle.zip \
    --language en \
    --log-level INFO
```

---

## Troubleshooting

* **Permissions:** Ensure you have write access to the folder so the script can create the ZIP output.
* **Module Not Found:** Ensure your terminal shows `(.venv)` at the start of the prompt. If not, repeat the **Activate** step.
* **Python Version:** This script requires Python 3.7+. Check yours with `python --version`.

---

## Cleanup
To exit the virtual environment:
```bash
deactivate
```