# Step 1: Create a project folder
mkdir yt-subtitle-cli
cd yt-subtitle-cli

# Step 2: Create the Python file
# Save the provided code into a file named:
# yt_subtitle_cli.py

# Step 3: Create requirements.txt file
# Add the following lines inside requirements.txt:

yt-dlp>=2024.8.6
youtube-transcript-api>=0.6.2

# Step 4: (Recommended) Create a virtual environment
python -m venv venv

# Step 5: Activate the virtual environment

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Step 6: Install dependencies
pip install -r requirements.txt

# Step 7: Run the application

python yt_subtitle_cli.py --query "python tutorial" --limit 5 --output output.zip

# Step 8: Example with more options

python yt_subtitle_cli.py \
    --query "machine learning" \
    --limit 10 \
    --output subtitles.zip \
    --upload-days 365 \
    --max-workers 4 \
    --language en \
    --log-level INFO

# Step 9: Output
# After execution:
# - A ZIP file (e.g., subtitles.zip) will be created
# - It will contain .srt subtitle files for each video

# Step 10: If command not found issues occur

# Check Python version
python --version

# If multiple Python versions exist, try:
python3 yt_subtitle_cli.py --query "AI" --limit 3 --output test.zip

# Step 11: Deactivate virtual environment (optional)
deactivate