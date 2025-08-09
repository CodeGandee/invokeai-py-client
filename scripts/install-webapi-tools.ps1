# PowerShell script to install essential web API tools
# Can run with or without Administrator privileges
#
# ADMIN vs NON-ADMIN BEHAVIOR:
#   - Administrator: Full access to all installation methods (uv tool, pipx, Chocolatey)
#   - Non-Admin: Only uv tool/pipx installations (Chocolatey requires admin rights)
#
# USAGE:
#   .\install-webapi-tools.ps1                    # Interactive mode - prompts for each tool
#   .\install-webapi-tools.ps1 -y                 # Auto-yes mode - installs all tools without prompts
#   .\install-webapi-tools.ps1 --yes              # Same as -y
#   .\install-webapi-tools.ps1 -f                 # Force mode - reinstalls even if already installed
#   .\install-webapi-tools.ps1 --force            # Same as -f
#   .\install-webapi-tools.ps1 -y -f              # Combined: auto-yes + force reinstall
#
# TOOLS INSTALLED:
#   - curl          : Command-line HTTP client (via Chocolatey)
#   - jq            : JSON processor (via Chocolatey)
#   - httpie        : User-friendly HTTP client (via uv tool/pipx/Chocolatey - priority order)
#   - mitmproxy     : HTTP proxy for traffic analysis (via uv tool/pipx/Chocolatey - priority order)
#   - yq            : YAML processor (via Chocolatey)
#   - shot-scraper  : Command-line website screenshot tool (via uv tool/pipx/Chocolatey - priority order)
#   - playwright    : Browser automation library (via npm) - requires Node.js
#   - puppeteer     : Browser automation library (via npm) - requires Node.js
#
# INSTALLATION PRIORITY:
#   For Python tools (httpie, mitmproxy, shot-scraper):
#   1. uv tool install (if available) - modern Python tool manager
#   2. pipx (if available) - isolated Python environments
#   3. Chocolatey (fallback) - system package manager (requires admin)
#
#   For Node.js-dependent tools (Playwright, Puppeteer):
#   - Requires Node.js to be pre-installed by user
#   - Will prompt user to install Node.js manually if not found
#
#   For uv/pipx availability:
#   - If neither uv nor pipx is available, script offers to install uv via official installer
#
# PREREQUISITES:
#   - Windows PowerShell 5.1+ or PowerShell 7+
#   - Administrator privileges (optional - enables Chocolatey)
#   - Internet connection
#   - Node.js (optional - for Playwright/Puppeteer, install manually from https://nodejs.org/)
#   - Chocolatey will be installed automatically if running as admin
#   - pipx/uv (optional but recommended for Python tools):
#     * pipx: pip install --user pipx
#     * uv: Will be offered for installation if neither uv nor pipx is available
#
# EXAMPLES:
#   # First time setup (interactive)
#   .\install-webapi-tools.ps1
#
#   # Automated CI/CD setup
#   .\install-webapi-tools.ps1 --yes
#
#   # Fix broken installations
#   .\install-webapi-tools.ps1 --force
#
#   # Complete automated reinstall
#   .\install-webapi-tools.ps1 --yes --force

param(
    [switch]$SkipCheck,
    [Alias("y")]
    [switch]$Yes,
    [Alias("f")]
    [switch]$Force
)

Write-Host "Installing essential web API tools..." -ForegroundColor Green

if ($Yes) {
    Write-Host "Auto-yes mode enabled. All tools will be installed automatically." -ForegroundColor Yellow
}

if ($Force) {
    Write-Host "Force mode enabled. Existing installations will be overwritten." -ForegroundColor Yellow
}

# Function to check if running as Administrator
function Test-IsAdmin {
    try {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = [Security.Principal.WindowsPrincipal] $identity
        return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    catch {
        return $false
    }
}

$isAdmin = Test-IsAdmin
if ($isAdmin) {
    Write-Host "✓ Running with Administrator privileges" -ForegroundColor Green
} else {
    Write-Host "⚠ Running without Administrator privileges" -ForegroundColor Yellow
    Write-Host "  Chocolatey installations will be skipped." -ForegroundColor Yellow
    Write-Host "  Only uv tool/pipx installations will be available." -ForegroundColor Yellow
    Write-Host "  To use Chocolatey, please run this script as Administrator." -ForegroundColor Cyan
}

# Function to check if a command exists
function Test-CommandExist {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to check if a Python package is installed via pipx
function Test-PipxPackageExist {
    param($Package)
    try {
        $result = pipx list 2>$null | Select-String $Package
        return $null -ne $result
    }
    catch {
        return $false
    }
}

# Function to check if a Python package is installed via uv tool
function Test-UvToolPackageExist {
    param($Package)
    try {
        $result = uv tool list 2>$null | Select-String $Package
        return $null -ne $result
    }
    catch {
        return $false
    }
}

# Function to ask user for confirmation
function Get-UserConfirmation {
    param($Tool, $IsInstalled)

    if ($Yes) {
        return $true
    }

    if ($IsInstalled -and -not $Force) {
        Write-Host "$Tool is already installed. Use --force to reinstall." -ForegroundColor Green
        return $false
    }

    $action = if ($IsInstalled -and $Force) { "reinstall" } else { "install" }
    $response = Read-Host "Do you want to $action $Tool? (y/N)"
    return $response -match '^[Yy]'
}

# Function to ask user for installation method preference
function Get-InstallMethodPreference {
    param($Tool, $AvailableMethods)

    if ($Yes) {
        return $AvailableMethods[0]  # Return first (preferred) method
    }

    Write-Host "Multiple installation methods available for ${Tool}:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $AvailableMethods.Length; $i++) {
        Write-Host "  $($i + 1). $($AvailableMethods[$i])" -ForegroundColor Yellow
    }

    do {
        $response = Read-Host "Choose installation method (1-$($AvailableMethods.Length)) or press Enter for default"
        if ([string]::IsNullOrEmpty($response)) {
            return $AvailableMethods[0]
        }
        $choice = [int]$response - 1
    } while ($choice -lt 0 -or $choice -ge $AvailableMethods.Length)

    return $AvailableMethods[$choice]
}

# Function to install uv via official installer
function Install-UvOfficial {
    Write-Host "Installing uv via official installer..." -ForegroundColor Yellow
    try {
        # Download and run the official uv installer
        $uvInstaller = (Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing).Content
        Invoke-Expression $uvInstaller
        
        # Refresh PATH for current session
        $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [Environment]::GetEnvironmentVariable("PATH", "Machine")
        
        # Verify installation
        if (Test-CommandExist "uv") {
            Write-Host "✓ uv installed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ uv installation failed" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "✗ uv installation failed: $_" -ForegroundColor Red
        return $false
    }
}

# Check if Chocolatey is installed
$chocoAvailable = $false
if ($isAdmin -and -not $SkipCheck -and -not (Get-Command choco -ErrorAction SilentlyContinue)) {
    if ($Yes -or (Get-UserConfirmation -Tool "Chocolatey" -IsInstalled $false)) {
        Write-Host "Chocolatey is not installed. Installing Chocolatey first..." -ForegroundColor Yellow
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        # Official Chocolatey installation method - Invoke-Expression is required here
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        Write-Host "Chocolatey installed successfully." -ForegroundColor Green
        $chocoAvailable = $true
    } else {
        Write-Host "Chocolatey installation declined." -ForegroundColor Yellow
    }
} elseif ($isAdmin -and (Get-Command choco -ErrorAction SilentlyContinue)) {
    $chocoAvailable = $true
    Write-Host "✓ Chocolatey is available" -ForegroundColor Green
} elseif (-not $isAdmin) {
    Write-Host "✗ Chocolatey requires Administrator privileges" -ForegroundColor Yellow
}

# Define tools with their commands for checking and supported installation methods
$tools = @(
    @{ Package = "curl"; Command = "curl"; Methods = @("choco") },
    @{ Package = "jq"; Command = "jq"; Methods = @("choco") },
    @{ Package = "httpie"; Command = "http"; Methods = @("uv-tool", "pipx", "choco") },
    @{ Package = "mitmproxy"; Command = "mitmdump"; Methods = @("uv-tool", "pipx", "choco") },
    @{ Package = "yq"; Command = "yq"; Methods = @("choco") },
    @{ Package = "shot-scraper"; Command = "shot-scraper"; Methods = @("uv-tool", "pipx", "choco") }
)

# Check for uv tool and pipx availability
$uvToolAvailable = Test-CommandExist "uv"
$pipxAvailable = Test-CommandExist "pipx"

if ($uvToolAvailable) {
    Write-Host "✓ uv is available (uv tool install)" -ForegroundColor Green
} else {
    Write-Host "✗ uv is not available" -ForegroundColor Yellow
}

if ($pipxAvailable) {
    Write-Host "✓ pipx is available" -ForegroundColor Green
} else {
    Write-Host "✗ pipx is not available" -ForegroundColor Yellow
}

# If neither uv nor pipx is available, offer to install uv
if (-not $uvToolAvailable -and -not $pipxAvailable) {
    Write-Host "" -ForegroundColor Yellow
    Write-Host "⚠ Neither uv nor pipx is available for Python package management." -ForegroundColor Yellow
    Write-Host "This will limit installation options for Python tools (httpie, mitmproxy, shot-scraper)." -ForegroundColor Yellow
    Write-Host ""
    if (Get-UserConfirmation -Tool "uv (recommended Python tool manager)" -IsInstalled $false) {
        if (Install-UvOfficial) {
            $uvToolAvailable = $true
        } else {
            Write-Host "Failed to install uv. Python tools will use fallback methods." -ForegroundColor Yellow
        }
    } else {
        Write-Host "Continuing without uv. Python tools will use system package manager." -ForegroundColor Yellow
    }
}

Write-Host "Checking and installing tools..." -ForegroundColor Cyan

foreach ($tool in $tools) {
    $package = $tool.Package
    $command = $tool.Command
    $supportedMethods = $tool.Methods
    $isInstalled = Test-CommandExist $command

    Write-Host "`nChecking $package..." -ForegroundColor Yellow

    # Filter available methods based on what's installed and admin rights
    $availableMethods = @()
    foreach ($method in $supportedMethods) {
        switch ($method) {
            "uv-tool" { if ($uvToolAvailable) { $availableMethods += $method } }
            "pipx" { if ($pipxAvailable) { $availableMethods += $method } }
            "choco" { if ($chocoAvailable) { $availableMethods += $method } }
            default { $availableMethods += $method }
        }
    }

    if ($availableMethods.Length -eq 0) {
        Write-Host "No installation methods available for $package." -ForegroundColor Red
        if (-not $isAdmin -and ($supportedMethods -contains "choco")) {
            Write-Host "  Tip: Run as Administrator to enable Chocolatey installation." -ForegroundColor Cyan
        }
        if (-not $pipxAvailable -and -not $uvToolAvailable -and ($supportedMethods -contains "uv-tool" -or $supportedMethods -contains "pipx")) {
            Write-Host "  Tip: Install uv or pipx for Python package management." -ForegroundColor Cyan
        }
        continue
    }

    # Choose installation method
    $installMethod = if ($availableMethods.Length -gt 1) {
        Get-InstallMethodPreference $package $availableMethods
    } else {
        $availableMethods[0]
    }

    if (Get-UserConfirmation -Tool $package -IsInstalled $isInstalled) {
        Write-Host "Installing $package via $installMethod..." -ForegroundColor Yellow
        try {
            switch ($installMethod) {
                "uv-tool" {
                    if ($Force -and (Test-UvToolPackageExist $package)) {
                        uv tool uninstall $package
                    }
                    uv tool install $package
                }
                "pipx" {
                    if ($Force -and (Test-PipxPackageExist $package)) {
                        pipx uninstall $package
                    }
                    pipx install $package
                }
                "choco" {
                    if ($Force -and $isInstalled) {
                        choco install $package -y --force
                    } else {
                        choco install $package -y
                    }
                }
                default {
                    Write-Host "Unknown installation method: $installMethod" -ForegroundColor Red
                    continue
                }
            }
            Write-Host "$package installed successfully via $installMethod." -ForegroundColor Green
        }
        catch {
            Write-Host "Failed to install $package via $installMethod. Error: $_" -ForegroundColor Red
        }
    } else {
        if ($isInstalled) {
            Write-Host "Skipping $package (already installed)." -ForegroundColor Green
        } else {
            Write-Host "Skipping $package (user declined)." -ForegroundColor Yellow
        }
    }
}

# Install Playwright and Puppeteer via npm (requires Node.js)
Write-Host "`nChecking Node.js for browser automation tools..." -ForegroundColor Cyan

$nodeInstalled = Test-CommandExist "node"
if ($nodeInstalled) {
    Write-Host "✓ Node.js is available" -ForegroundColor Green
    
    $playwrightInstalled = Test-CommandExist "playwright"
    $puppeteerInstalled = $null -ne (npm list -g puppeteer 2>$null)

    if (Get-UserConfirmation -Tool "Playwright" -IsInstalled $playwrightInstalled) {
        Write-Host "Installing Playwright via npm..." -ForegroundColor Yellow
        try {
            if ($Force -and $playwrightInstalled) {
                npm install -g playwright --force
            } else {
                npm install -g playwright
            }
            npx playwright install
            Write-Host "Playwright installed successfully." -ForegroundColor Green
        }
        catch {
            Write-Host "Failed to install Playwright. Error: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "Skipping Playwright." -ForegroundColor Yellow
    }

    if (Get-UserConfirmation -Tool "Puppeteer" -IsInstalled $puppeteerInstalled) {
        Write-Host "Installing Puppeteer via npm..." -ForegroundColor Yellow
        try {
            if ($Force -and $puppeteerInstalled) {
                npm install -g puppeteer --force
            } else {
                npm install -g puppeteer
            }
            Write-Host "Puppeteer installed successfully." -ForegroundColor Green
        }
        catch {
            Write-Host "Failed to install Puppeteer. Error: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "Skipping Puppeteer." -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ Node.js is not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "⚠ Node.js is required for browser automation tools (Playwright, Puppeteer)." -ForegroundColor Yellow
    Write-Host "Please install Node.js manually from the official website:" -ForegroundColor Yellow
    Write-Host "  https://nodejs.org/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Recommended installation methods:" -ForegroundColor Yellow
    Write-Host "  1. Download and install from https://nodejs.org/en/download/" -ForegroundColor Cyan
    Write-Host "  2. Use Chocolatey (requires admin): choco install nodejs" -ForegroundColor Cyan
    Write-Host "  3. Use Scoop: scoop install nodejs" -ForegroundColor Cyan
    Write-Host "  4. Use winget: winget install OpenJS.NodeJS" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "After installing Node.js, run this script again to install Playwright and Puppeteer." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Skipping Playwright and Puppeteer installation." -ForegroundColor Yellow
}

Write-Host "`nInstallation complete! Verifying tools..." -ForegroundColor Green

# Verify installations
$verifyCommands = @(
    "curl --version",
    "jq --version",
    "http --version",
    "node --version",
    "npm --version",
    "mitmdump --version",
    "yq --version",
    "shot-scraper --version"
)

foreach ($cmd in $verifyCommands) {
    try {
        $cmdParts = $cmd.Split()
        $null = & $cmdParts[0] $cmdParts[1..($cmdParts.Length-1)] 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ $($cmdParts[0]) is working" -ForegroundColor Green
        } else {
            Write-Host "✗ $($cmdParts[0]) verification failed" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "✗ $($cmd.Split()[0]) verification failed: $_" -ForegroundColor Red
    }
}

Write-Host "`nAll essential web API tools have been processed!" -ForegroundColor Green
if (-not $isAdmin) {
    Write-Host "Note: Some tools may require Administrator privileges for installation." -ForegroundColor Yellow
    Write-Host "Consider running this script as Administrator for full functionality." -ForegroundColor Cyan
}
if (-not $nodeInstalled) {
    Write-Host "Note: Node.js is not installed. Install it manually to enable Playwright and Puppeteer." -ForegroundColor Yellow
    Write-Host "Download from: https://nodejs.org/" -ForegroundColor Cyan
}
Write-Host "You may need to restart your terminal or refresh your PATH environment variable." -ForegroundColor Yellow
