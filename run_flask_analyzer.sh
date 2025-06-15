#!/bin/bash
# Flask API Analyzer Script
# This script extracts Flask routes, parses functions, and then analyzes them with Gemini API

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
FUNCTIONS_JSON="$OUTPUT_DIR/sample_functions.json"
GEMINI_MODEL="gemini-2.0-flash"
# Use API key from environment variable if set
GEMINI_API_KEY=${GEMINI_API_KEY:-}

# ANSI color codes for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
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
  echo -e "  --skip-functions       Skip function parsing step"
  echo -e "  --functions-only       Only run function parsing (skip Flask routes and Gemini analysis)"
  echo -e "  -h, --help             Show this help message"
  echo -e "\n${YELLOW}Note:${NC} You can also set GEMINI_API_KEY in .env file or as an environment variable"
  echo -e "\n${BLUE}Process Overview:${NC}"
  echo -e "  1. Extract Flask routes from the project"
  echo -e "  2. Parse and extract function information from Python files"
  echo -e "  3. Analyze endpoints with Gemini API"
}

# Initialize flags
SKIP_FUNCTIONS=false
FUNCTIONS_ONLY=false

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
    FUNCTIONS_JSON="$OUTPUT_DIR/sample_functions.json"
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
  --skip-functions)
    SKIP_FUNCTIONS=true
    shift
    ;;
  --functions-only)
    FUNCTIONS_ONLY=true
    shift
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

# Check for required arguments (only if not running functions-only mode)
if [ "$FUNCTIONS_ONLY" = false ]; then
  if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}Error:${NC} Gemini API key is required."
    echo -e "Please provide it using one of these methods:"
    echo -e "  1. Use the -k/--api-key command line option"
    echo -e "  2. Set the GEMINI_API_KEY environment variable"
    echo -e "  3. Add GEMINI_API_KEY=your_key to a .env file in this directory"
    show_usage
    exit 1
  fi
fi

if [ -z "$FLASK_PROJECT_DIR" ]; then
  echo -e "${RED}Error:${NC} Flask project directory is required."
  show_usage
  exit 1
fi

# Check if Flask project directory exists
if [ ! -d "$FLASK_PROJECT_DIR" ]; then
  echo -e "${RED}Error:${NC} Flask project directory '$FLASK_PROJECT_DIR' does not exist."
  exit 1
fi

# Check if Python scripts exist (only check the ones we need)
if [ "$FUNCTIONS_ONLY" = false ]; then
  if [ ! -f "flask_code_extractor.py" ]; then
    echo -e "${RED}Error:${NC} flask_code_extractor.py not found in current directory"
    exit 1
  fi

  if [ ! -f "gemini_flask_analyser.py" ]; then
    echo -e "${RED}Error:${NC} gemini_flask_analyser.py not found in current directory"
    exit 1
  fi
fi

if [ "$SKIP_FUNCTIONS" = false ]; then
  if [ ! -f "function_extractor.py" ]; then
    echo -e "${RED}Error:${NC} function_extractor.py not found in current directory"
    exit 1
  fi
fi

# Function to run Flask route extraction
run_flask_extraction() {
  echo -e "${GREEN}Step 1:${NC} Extracting Flask routes from $FLASK_PROJECT_DIR"
  python3 flask_code_extractor.py "$FLASK_PROJECT_DIR"

  # Check if the routes extraction was successful
  if [ ! -f "flask_routes.json" ]; then
    echo -e "${RED}Error:${NC} Flask routes extraction failed. Check your Flask project directory."
    exit 1
  fi

  # Move the generated file to output directory if different from current directory
  if [ "$(pwd)/flask_routes.json" != "$FLASK_ROUTES_JSON" ]; then
    mv flask_routes.json "$FLASK_ROUTES_JSON"
  fi
  
  echo -e "${GREEN}✓${NC} Flask routes extracted successfully"
}

# Function to run function parsing
run_function_parsing() {
  echo -e "${GREEN}Step 2:${NC} Parsing functions from $FLASK_PROJECT_DIR"
  
  # Run the function parser with custom output path
  python3 function_extractor.py "$FLASK_PROJECT_DIR" -o "$FUNCTIONS_JSON" -s
  
  # Check if function parsing was successful
  if [ -f "$FUNCTIONS_JSON" ]; then
    echo -e "${GREEN}✓${NC} Function parsing completed successfully"
  else
    echo -e "${YELLOW}Warning:${NC} Function parsing may have failed, but continuing with analysis..."
  fi
}

# Function to run Gemini analysis
run_gemini_analysis() {
  local step_num=$1
  echo -e "${GREEN}Step $step_num:${NC} Analyzing endpoints with Gemini API"
  python3 gemini_flask_analyser.py "$FLASK_ROUTES_JSON" "$REQUEST_SCHEMAS_JSON" "$GEMINI_API_KEY" "$GEMINI_MODEL"

  # Check if analysis was successful
  if [ -f "$REQUEST_SCHEMAS_JSON" ]; then
    echo -e "${GREEN}✓${NC} Gemini analysis completed successfully"
  else
    echo -e "${YELLOW}Warning:${NC} Gemini analysis may have failed. Check the log messages above."
  fi
}

# Main execution logic
if [ "$FUNCTIONS_ONLY" = true ]; then
  # Only run function parsing
  echo -e "${BLUE}Running function parsing only...${NC}"
  run_function_parsing
else
  # Run full pipeline or skip functions based on flag
  run_flask_extraction
  
  if [ "$SKIP_FUNCTIONS" = false ]; then
    run_function_parsing
    run_gemini_analysis 3
  else
    echo -e "${YELLOW}Skipping function parsing step${NC}"
    run_gemini_analysis 2
  fi
fi

# Display results summary
echo -e "\n${BLUE}=== Process Summary ===${NC}"

if [ "$FUNCTIONS_ONLY" = false ]; then
  if [ -f "$FLASK_ROUTES_JSON" ]; then
    echo -e "${GREEN}✓${NC} Routes extracted: $FLASK_ROUTES_JSON"
  else
    echo -e "${RED}✗${NC} Routes extraction failed"
  fi
fi

if [ "$SKIP_FUNCTIONS" = false ]; then
    echo -e "${GREEN}✓${NC} Functions parsed: $FUNCTIONS_JSON"
fi

if [ "$FUNCTIONS_ONLY" = false ]; then
  if [ -f "$REQUEST_SCHEMAS_JSON" ]; then
    echo -e "${GREEN}✓${NC} Request schemas: $REQUEST_SCHEMAS_JSON"
  else
    echo -e "${RED}✗${NC} Gemini analysis failed"
  fi
fi

# Final status
if [ "$FUNCTIONS_ONLY" = true ]; then
  if [ -f "$FUNCTIONS_JSON" ]; then
    echo -e "\n${GREEN}Success!${NC} Function parsing complete."
  else
    echo -e "\n${RED}Failed!${NC} Function parsing unsuccessful."
    exit 1
  fi
else
  if [ -f "$FLASK_ROUTES_JSON" ] && ([ "$SKIP_FUNCTIONS" = true ] || [ -f "$FUNCTIONS_JSON" ]) && [ -f "$REQUEST_SCHEMAS_JSON" ]; then
    echo -e "\n${GREEN}Success!${NC} Flask API analysis complete."
  else
    echo -e "\n${YELLOW}Partial Success!${NC} Some steps may have failed. Check the summary above."
  fi
fi

echo -e "\n${BLUE}Process completed.${NC}"