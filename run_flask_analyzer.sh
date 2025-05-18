#!/bin/bash
# Flask API Analyzer Script
# This script extracts Flask routes and then analyzes them with Gemini API

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  echo "Loading environment variables from .env file"
  export $(grep -v '^#' .env | xargs)
fi

# Set default values for paths and configuration
FLASK_PROJECT_DIR="./flask_project"
OUTPUT_DIR="./output"
FLASK_ROUTES_JSON="$OUTPUT_DIR/flask_routes.json"
REQUEST_SCHEMAS_JSON="$OUTPUT_DIR/request_schemas.json"
GEMINI_MODEL="gemini-2.0-flash"
# Use API key from environment variable if set
GEMINI_API_KEY=${GEMINI_API_KEY:-}

# ANSI color codes for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display script usage
show_usage() {
  echo -e "${BLUE}Usage:${NC}"
  echo -e "  $0 [options]"
  echo -e "\n${BLUE}Options:${NC}"
  echo -e "  -d, --directory DIR    Path to Flask project directory (default: ./flask_project)"
  echo -e "  -o, --output DIR       Output directory (default: ./output)"
  echo -e "  -k, --api-key KEY      Gemini API key (required unless set as env variable or in .env file)"
  echo -e "  -m, --model MODEL      Gemini model to use (default: gemini-2.0-flash)"
  echo -e "  -h, --help             Show this help message"
  echo -e "\n${YELLOW}Note:${NC} You can also set GEMINI_API_KEY in .env file or as an environment variable"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
  -d | --directory)
    FLASK_PROJECT_DIR="$2"
    shift 2
    ;;
  -o | --output)
    OUTPUT_DIR="$2"
    FLASK_ROUTES_JSON="$OUTPUT_DIR/flask_routes.json"
    REQUEST_SCHEMAS_JSON="$OUTPUT_DIR/request_schemas.json"
    shift 2
    ;;
  -k | --api-key)
    GEMINI_API_KEY="$2"
    shift 2
    ;;
  -m | --model)
    GEMINI_MODEL="$2"
    shift 2
    ;;
  -h | --help)
    show_usage
    exit 0
    ;;
  *)
    echo -e "${YELLOW}Warning:${NC} Unknown option $1"
    show_usage
    exit 1
    ;;
  esac
done

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Check for required arguments
if [ -z "$GEMINI_API_KEY" ]; then
  echo -e "${YELLOW}Error:${NC} Gemini API key is required."
  echo -e "Please provide it using one of these methods:"
  echo -e "  1. Use the -k/--api-key command line option"
  echo -e "  2. Set the GEMINI_API_KEY environment variable"
  echo -e "  3. Add GEMINI_API_KEY=your_key to a .env file in this directory"
  show_usage
  exit 1
fi

if [ -z "$FLASK_PROJECT_DIR" ]; then
  echo -e "${YELLOW}Error:${NC} Flask project directory is required."
  show_usage
  exit 1
fi

# Check if Python scripts exist
if [ ! -f "flask_code_extractor.py" ]; then
  echo -e "${YELLOW}Error:${NC} flask_code_extractor.py not found in current directory"
  exit 1
fi

if [ ! -f "gemini_flask_analyser.py" ]; then
  echo -e "${YELLOW}Error:${NC} gemini_flask_analyser.py not found in current directory"
  exit 1
fi

# Run the Flask route extractor
echo -e "${GREEN}Step 1:${NC} Extracting Flask routes from $FLASK_PROJECT_DIR"
python3 flask_code_extractor.py "$FLASK_PROJECT_DIR"

# Check if the routes extraction was successful
if [ ! -f "flask_routes.json" ]; then
  echo -e "${YELLOW}Error:${NC} Flask routes extraction failed. Check your Flask project directory."
  exit 1
fi

# Move the generated file to output directory if different from current directory
if [ "$(pwd)/flask_routes.json" != "$FLASK_ROUTES_JSON" ]; then
  mv flask_routes.json "$FLASK_ROUTES_JSON"
fi

# Run the Gemini analyzer
echo -e "${GREEN}Step 2:${NC} Analyzing endpoints with Gemini API"
python3 gemini_flask_analyser.py "$FLASK_ROUTES_JSON" "$REQUEST_SCHEMAS_JSON" "$GEMINI_API_KEY" "$GEMINI_MODEL"

# Check if analysis was successful
if [ -f "$REQUEST_SCHEMAS_JSON" ]; then
  echo -e "${GREEN}Success!${NC} Flask API analysis complete."
  echo -e "Routes extracted: $FLASK_ROUTES_JSON"
  echo -e "Request schemas: $REQUEST_SCHEMAS_JSON"
else
  echo -e "${YELLOW}Warning:${NC} Gemini analysis may have failed. Check the log messages above."
fi

echo -e "\n${BLUE}Process completed.${NC}"
