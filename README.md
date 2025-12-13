# Gemini 3 Pro Skill

All-purpose Gemini 3 Pro client with Thinking enabled. Uses browser cookies for authentication - no API key required.

## Features

| Capability | Description |
|------------|-------------|
| Text Queries | Complex reasoning with "Thinking with 3 Pro" mode |
| Video Analysis | Upload MP4 files for summarization, timestamps, insights |
| YouTube Analysis | Analyze videos via URL (uses YouTube extension) |
| Document Analysis | PDF and document Q&A |
| Image Analysis | Describe, OCR, analyze uploaded images |
| Image Generation | Create images from text prompts |
| Image Editing | Modify images with natural language |
| Google Search | Automatic grounding for current information |

## How It Works

```
User Request → webapi CLI → gemini-webapi → Gemini Web (cookies) → Response
```

Authentication uses Chrome browser cookies - no API key needed. Just be logged into gemini.google.com.

## Installation

```bash
cd ~/.claude/skills/gemini
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On macOS, grant Keychain access when prompted on first run.

## Usage

### Text Queries

```bash
# Complex reasoning (Thinking with 3 Pro)
webapi "Explain the implications of quantum computing for cryptography"

# Show thinking process
webapi "Solve step by step: What is 15% of 240?" --show-thoughts
```

### File Analysis

```bash
# Video analysis
webapi "Summarize this video with timestamps" --file meeting.mp4

# Document analysis
webapi "Extract key findings" --file research.pdf

# Image analysis
webapi "What's in this image?" --file photo.png
```

### YouTube Analysis

```bash
webapi "What are the main points discussed?" --youtube "https://youtube.com/watch?v=VIDEO_ID"
```

Requires YouTube extension enabled in gemini.google.com settings.

### Image Generation

```bash
# Generate image
webapi "A cyberpunk cityscape at night" --generate-image city.png

# With aspect ratio
webapi "Mountain landscape" --generate-image landscape.png --aspect 16:9

# Edit existing image
webapi "Make the sky purple" --edit photo.jpg --output edited.png
```

### Current Information (Grounded)

```bash
webapi "What are the latest AI news this week? Search the web."
```

Google Search grounding is automatic when queries need current information.

## CLI Options

| Option | Description |
|--------|-------------|
| `--file, -f FILE` | Input file (MP4, PDF, PNG, JPG, etc.) |
| `--youtube URL` | YouTube video URL |
| `--generate-image FILE` | Generate and save image |
| `--edit IMAGE` | Edit image (with --output) |
| `--output, -o FILE` | Output path for images |
| `--aspect RATIO` | Aspect ratio (16:9, 1:1, 4:3, 3:4) |
| `--show-thoughts` | Display thinking process |
| `--model MODEL` | Model to use (default: gemini-3.0-pro) |
| `--json` | JSON output |
| `--help, -h` | Show help |

## File Structure

```
gemini/
├── SKILL.md           # Claude Code skill definition
├── README.md          # This file
├── requirements.txt   # Python dependencies
├── .venv/             # Virtual environment
├── webapi             # Bash wrapper
└── webapi.py          # Python implementation
```

## Troubleshooting

**"Error initializing client"**
- Log into gemini.google.com in Chrome
- On macOS, allow Keychain access when prompted

**"No images generated"**
- Rephrase prompt, some content is filtered
- Be more explicit about what you want

**"Module not found"**
- Activate venv: `source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`

**"YouTube not working"**
- Enable YouTube extension in gemini.google.com settings

## License

MIT
