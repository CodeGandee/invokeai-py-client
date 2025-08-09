# Utility Scripts

This directory contains utility scripts for setting up and managing the development environment.

## Installation Scripts

### `install-webapi-tools.ps1`
PowerShell script to install essential web API tools on Windows:
- curl
- jq
- httpie
- nodejs
- mitmproxy
- yq
- playwright
- puppeteer

**Features:**
- Interactive prompts for each tool
- Checks for existing installations
- Command-line options for automation
- **Smart admin detection**: Works with or without Administrator privileges
- **Intelligent installation routing**: Uses pipx/uvx when available, Chocolatey when admin

**Admin vs Non-Admin Behavior:**
- **Administrator**: Full access to all installation methods (pipx → uvx → Chocolatey)
- **Non-Admin**: Only pipx/uvx installations (Chocolatey requires admin rights)

**Usage:**
```powershell
# Interactive mode (works with or without admin)
.\install-webapi-tools.ps1

# Auto-yes mode (install all tools without prompts)
.\install-webapi-tools.ps1 --yes
.\install-webapi-tools.ps1 -y

# Force mode (reinstall even if already installed)
.\install-webapi-tools.ps1 --force
.\install-webapi-tools.ps1 -f

# Combined options
.\install-webapi-tools.ps1 --yes --force
```

### `install-webapi-tools.sh`
Bash script to install essential web API tools on Ubuntu/Debian systems:
- curl (via apt)
- jq (via apt)
- httpie (via apt)
- nodejs (via NodeSource repository)
- mitmproxy (via pip)
- yq (via GitHub releases)
- playwright (via npm)
- puppeteer (via npm)

**Features:**
- Interactive prompts for each tool
- Checks for existing installations
- Command-line options for automation

**Usage:**
```bash
# Interactive mode
chmod +x install-webapi-tools.sh
./install-webapi-tools.sh

# Auto-yes mode (install all tools without prompts)
./install-webapi-tools.sh --yes
./install-webapi-tools.sh -y

# Force mode (reinstall even if already installed)
./install-webapi-tools.sh --force
./install-webapi-tools.sh -f

# Combined options
./install-webapi-tools.sh --yes --force
```

## Prerequisites

### Windows (PowerShell script)
- Windows PowerShell 5.1 or PowerShell 7+
- Administrator privileges (optional - enables Chocolatey installations)
- Internet connection
- pipx/uvx recommended for Python tools (can install without admin rights)

### Linux (Bash script)
- Ubuntu/Debian-based system
- sudo privileges
- Internet connection
- bash shell