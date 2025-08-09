#!/bin/bash

# Bash script to install essential web API tools on Ubuntu/Debian systems
#
# USAGE:
#   ./install-webapi-tools.sh                     # Interactive mode - prompts for each tool
#   ./install-webapi-tools.sh -y                  # Auto-yes mode - installs all tools without prompts
#   ./install-webapi-tools.sh --yes               # Same as -y
#   ./install-webapi-tools.sh -f                  # Force mode - reinstalls even if already installed
#   ./install-webapi-tools.sh --force             # Same as -f
#   ./install-webapi-tools.sh -y -f               # Combined: auto-yes + force reinstall
#
# TOOLS INSTALLED:
#   - curl          : Command-line HTTP client (via apt)
#   - jq            : JSON processor (via apt)
#   - httpie        : User-friendly HTTP client (via uv tool/pipx/apt - priority order)
#   - mitmproxy     : HTTP proxy for traffic analysis (via uv tool/pipx/pip - priority order)
#   - yq            : YAML processor (via GitHub releases)
#   - shot-scraper  : Command-line website screenshot tool (via uv tool/pipx/pip - priority order)
#   - playwright    : Browser automation library (via npm) - requires Node.js
#   - puppeteer     : Browser automation library (via npm) - requires Node.js
#
# INSTALLATION PRIORITY:
#   For Python tools (httpie, mitmproxy, shot-scraper):
#   1. uv tool install (if available) - modern Python tool manager
#   2. pipx (if available) - isolated Python environments  
#   3. System package manager (apt/pip) - fallback
#
#   For Node.js-dependent tools (Playwright, Puppeteer):
#   - Requires Node.js to be pre-installed by user
#   - Will prompt user to install Node.js manually if not found
#
#   For uv/pipx availability:
#   - If neither uv nor pipx is available, script offers to install uv via official installer
#
# PREREQUISITES:
#   - Ubuntu/Debian-based Linux system
#   - sudo privileges
#   - Internet connection
#   - bash shell
#   - Node.js (optional - for Playwright/Puppeteer, install manually from https://nodejs.org/)
#   - pipx/uv (optional but recommended for Python tools):
#     * pipx: sudo apt install pipx OR pip install --user pipx
#     * uv: Will be offered for installation if neither uv nor pipx is available
#
# SETUP:
#   chmod +x install-webapi-tools.sh
#
# EXAMPLES:
#   # First time setup (interactive)
#   ./install-webapi-tools.sh
#
#   # Automated CI/CD setup
#   ./install-webapi-tools.sh --yes
#
#   # Fix broken installations
#   ./install-webapi-tools.sh --force
#
#   # Complete automated reinstall
#   ./install-webapi-tools.sh --yes --force
#
# NOTE:
#   - Python tools (mitmproxy, shot-scraper) will be installed to ~/.local/bin/
#   - Node.js must be installed manually by user (see https://nodejs.org/)
#   - If uv is not available, script will offer to install it via official installer
#   - PATH will be updated automatically in ~/.bashrc if needed
#   - You may need to restart terminal or run 'source ~/.bashrc' after installation

set -e  # Exit on any error

# Parse command line arguments
YES_TO_ALL=false
FORCE_INSTALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --yes|-y)
            YES_TO_ALL=true
            shift
            ;;
        --force|-f)
            FORCE_INSTALL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--yes|-y] [--force|-f]"
            echo "  --yes, -y    : Say yes to all prompts"
            echo "  --force, -f  : Force reinstall even if already installed"
            exit 1
            ;;
    esac
done

echo "Installing essential web API tools on Ubuntu/Debian..."

if [ "$YES_TO_ALL" = true ]; then
    echo "Auto-yes mode enabled. All tools will be installed automatically."
fi

if [ "$FORCE_INSTALL" = true ]; then
    echo "Force mode enabled. Existing installations will be overwritten."
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if npm package is installed globally
npm_package_exists() {
    npm list -g "$1" >/dev/null 2>&1
}

# Function to check if a Python package is installed via pipx
pipx_package_exists() {
    pipx list 2>/dev/null | grep -q "$1"
}

# Function to check if a Python package is installed via uv tool
uv_tool_package_exists() {
    uv tool list 2>/dev/null | grep -q "$1"
}

# Function to ask user for confirmation
get_user_confirmation() {
    local tool="$1"
    local is_installed="$2"
    local install_method="${3:-default}"
    
    if [ "$YES_TO_ALL" = true ]; then
        return 0  # true
    fi
    
    if [ "$is_installed" = true ] && [ "$FORCE_INSTALL" != true ]; then
        echo "$tool is already installed. Use --force to reinstall."
        return 1  # false
    fi
    
    local action="install"
    if [ "$is_installed" = true ] && [ "$FORCE_INSTALL" = true ]; then
        action="reinstall"
    fi
    
    local method_text=""
    if [ "$install_method" != "default" ]; then
        method_text=" via $install_method"
    fi
    
    read -p "Do you want to $action $tool$method_text? (y/N): " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0  # true
            ;;
        *)
            return 1  # false
            ;;
    esac
}

# Function to ask user for installation method preference
get_install_method_preference() {
    local tool="$1"
    shift
    local available_methods=("$@")
    
    if [ "$YES_TO_ALL" = true ]; then
        echo "${available_methods[0]}"  # Return first (preferred) method
        return
    fi
    
    echo "Multiple installation methods available for $tool:"
    for i in "${!available_methods[@]}"; do
        echo "  $((i + 1)). ${available_methods[i]}"
    done
    
    while true; do
        read -p "Choose installation method (1-${#available_methods[@]}) or press Enter for default: " response
        if [ -z "$response" ]; then
            echo "${available_methods[0]}"
            return
        fi
        if [[ "$response" =~ ^[0-9]+$ ]] && [ "$response" -ge 1 ] && [ "$response" -le "${#available_methods[@]}" ]; then
            echo "${available_methods[$((response - 1))]}"
            return
        fi
        echo "Invalid choice. Please enter a number between 1 and ${#available_methods[@]}."
    done
}

# Function to install uv via official installer
install_uv_official() {
    echo "Installing uv via official installer..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Source the updated shell environment
    export PATH="$HOME/.cargo/bin:$PATH"
    
    # Add to bashrc if not already there
    if [[ ":$PATH:" != *":$HOME/.cargo/bin:"* ]]; then
        echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
    fi
    
    # Verify installation
    if command_exists "uv"; then
        echo "✓ uv installed successfully"
        return 0
    else
        echo "✗ uv installation failed"
        return 1
    fi
}

# Update package lists
echo "Updating package lists..."
sudo apt update

# Define tools with their commands and supported installation methods
declare -A tool_commands=(
    ["curl"]="curl"
    ["jq"]="jq"
    ["httpie"]="http"
    ["mitmproxy"]="mitmdump"
    ["yq"]="yq"
    ["shot-scraper"]="shot-scraper"
)

declare -A tool_methods=(
    ["curl"]="apt"
    ["jq"]="apt"
    ["httpie"]="uv-tool pipx apt"
    ["mitmproxy"]="uv-tool pipx pip"
    ["yq"]="github"
    ["shot-scraper"]="uv-tool pipx pip"
)

# Check for uv tool and pipx availability
uv_tool_available=false
pipx_available=false

if command_exists "uv"; then
    echo "✓ uv is available (uv tool install)"
    uv_tool_available=true
else
    echo "✗ uv is not available"
fi

if command_exists "pipx"; then
    echo "✓ pipx is available"
    pipx_available=true
else
    echo "✗ pipx is not available"
fi

# If neither uv nor pipx is available, offer to install uv
if [ "$uv_tool_available" = false ] && [ "$pipx_available" = false ]; then
    echo ""
    echo "⚠ Neither uv nor pipx is available for Python package management."
    echo "This will limit installation options for Python tools (httpie, mitmproxy, shot-scraper)."
    echo ""
    if get_user_confirmation "uv (recommended Python tool manager)" false "official installer"; then
        if install_uv_official; then
            uv_tool_available=true
        else
            echo "Failed to install uv. Python tools will use fallback methods."
        fi
    else
        echo "Continuing without uv. Python tools will use system package manager."
    fi
fi

# Install basic tools that are available in apt repositories
echo "Checking and installing tools..."

for package in curl jq httpie mitmproxy yq shot-scraper; do
    command_name="${tool_commands[$package]}"
    supported_methods="${tool_methods[$package]}"
    is_installed=$(command_exists "$command_name")
    
    echo ""
    echo "Checking $package..."
    
    # Build available methods array based on what's installed
    available_methods=()
    for method in $supported_methods; do
        case $method in
            "uv-tool")
                if [ "$uv_tool_available" = true ]; then
                    available_methods+=("uv-tool")
                fi
                ;;
            "pipx")
                if [ "$pipx_available" = true ]; then
                    available_methods+=("pipx")
                fi
                ;;
            *)
                available_methods+=("$method")
                ;;
        esac
    done
    
    if [ ${#available_methods[@]} -eq 0 ]; then
        echo "No installation methods available for $package. Skipping."
        continue
    fi
    
    # Choose installation method
    if [ ${#available_methods[@]} -gt 1 ]; then
        install_method=$(get_install_method_preference "$package" "${available_methods[@]}")
    else
        install_method="${available_methods[0]}"
    fi
    
    if get_user_confirmation "$package" "$is_installed" "$install_method"; then
        echo "Installing $package via $install_method..."
        case $install_method in
            "uv-tool")
                if [ "$FORCE_INSTALL" = true ] && uv_tool_package_exists "$package"; then
                    uv tool uninstall "$package"
                fi
                uv tool install "$package"
                echo "$package installed successfully via uv tool."
                ;;
            "pipx")
                if [ "$FORCE_INSTALL" = true ] && pipx_package_exists "$package"; then
                    pipx uninstall "$package"
                fi
                pipx install "$package"
                echo "$package installed successfully via pipx."
                ;;
            "apt")
                if [ "$FORCE_INSTALL" = true ] && [ "$is_installed" = true ]; then
                    sudo apt install -y --reinstall "$package"
                else
                    sudo apt install -y "$package"
                fi
                echo "$package installed successfully via apt."
                ;;
            "official")
                # This case is no longer used - nodejs is handled separately
                echo "Error: nodejs installation is no longer automatic. Please install manually."
                ;;
            "pip")
                # Special handling for mitmproxy via pip
                sudo apt install -y python3-pip
                if [ "$FORCE_INSTALL" = true ] && [ "$is_installed" = true ]; then
                    pip3 install --user --force-reinstall "$package"
                else
                    pip3 install --user "$package"
                fi
                # Add local pip bin to PATH if not already there
                if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
                    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
                    export PATH="$HOME/.local/bin:$PATH"
                fi
                echo "$package installed successfully via pip."
                ;;
            "github")
                # Special handling for yq via GitHub releases
                if [ "$FORCE_INSTALL" = true ] && [ "$is_installed" = true ]; then
                    sudo rm -f /usr/local/bin/yq
                fi
                YQ_VERSION=$(curl -s "https://api.github.com/repos/mikefarah/yq/releases/latest" | jq -r .tag_name)
                sudo wget -qO /usr/local/bin/yq "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64"
                sudo chmod +x /usr/local/bin/yq
                echo "$package installed successfully via GitHub releases."
                ;;
            *)
                echo "Unknown installation method: $install_method"
                continue
                ;;
        esac
    else
        if [ "$is_installed" = true ]; then
            echo "Skipping $package (already installed)."
        else
            echo "Skipping $package (user declined)."
        fi
    fi
done

# Install Playwright and Puppeteer via npm (requires Node.js)
echo ""
echo "Checking Node.js for browser automation tools..."

if command_exists "node"; then
    echo "✓ Node.js is available"
    
    echo ""
    echo "Checking Playwright..."
    playwright_installed=$(npm_package_exists "playwright")
    
    if get_user_confirmation "Playwright" "$playwright_installed"; then
        echo "Installing Playwright via npm..."
        if [ "$FORCE_INSTALL" = true ] && [ "$playwright_installed" = true ]; then
            sudo npm install -g playwright --force
        else
            sudo npm install -g playwright
        fi
        
        echo "Installing Playwright browsers..."
        npx playwright install
        
        echo "Installing additional dependencies for Playwright..."
        npx playwright install-deps
        
        echo "Playwright installed successfully."
    else
        if [ "$playwright_installed" = true ]; then
            echo "Skipping Playwright (already installed)."
        else
            echo "Skipping Playwright (user declined)."
        fi
    fi
    
    echo ""
    echo "Checking Puppeteer..."
    puppeteer_installed=$(npm_package_exists "puppeteer")
    
    if get_user_confirmation "Puppeteer" "$puppeteer_installed"; then
        echo "Installing Puppeteer via npm..."
        if [ "$FORCE_INSTALL" = true ] && [ "$puppeteer_installed" = true ]; then
            sudo npm install -g puppeteer --force
        else
            sudo npm install -g puppeteer
        fi
        echo "Puppeteer installed successfully."
    else
        if [ "$puppeteer_installed" = true ]; then
            echo "Skipping Puppeteer (already installed)."
        else
            echo "Skipping Puppeteer (user declined)."
        fi
    fi
else
    echo "✗ Node.js is not installed"
    echo ""
    echo "⚠ Node.js is required for browser automation tools (Playwright, Puppeteer)."
    echo "Please install Node.js manually from the official website:"
    echo "  https://nodejs.org/"
    echo ""
    echo "Recommended installation methods:"
    echo "  1. Download and install from https://nodejs.org/en/download/"
    echo "  2. Use Node Version Manager (nvm): https://github.com/nvm-sh/nvm"
    echo "  3. Use package manager with NodeSource repository"
    echo ""
    echo "After installing Node.js, run this script again to install Playwright and Puppeteer."
    echo ""
    echo "Skipping Playwright and Puppeteer installation."
fi

echo ""
echo "Installation complete! Verifying tools..."

# Verify installations
verify_commands=(
    "curl --version"
    "jq --version"
    "http --version"
    "node --version"
    "npm --version"
    "yq --version"
    "mitmdump --version"
    "shot-scraper --version"
)

for cmd in "${verify_commands[@]}"; do
    if eval "$cmd" >/dev/null 2>&1; then
        echo "✓ ${cmd%% *} is working"
    else
        echo "✗ ${cmd%% *} verification failed"
    fi
done

echo ""
echo "All essential web API tools have been installed!"
echo "You may need to restart your terminal or run 'source ~/.bashrc' to refresh your PATH."
echo ""
echo "Installation locations:"
echo "- Python tools: ~/.local/bin/"
echo "- uv tools: ~/.cargo/bin/"
if command_exists "node"; then
    echo "- Node.js tools: $(which node | xargs dirname)"
else
    echo "- Node.js: Not installed (install manually from https://nodejs.org/)"
fi
echo "If you encounter issues, make sure these paths are in your PATH."
