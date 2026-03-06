#!/usr/bin/env bash
# =============================================================================
#  BILLING & INVENTORY SOFTWARE — ONE-COMMAND INSTALLER
#  Usage:  bash <(curl -fsSL https://raw.githubusercontent.com/djkalirdp/billing/main/install.sh)
# =============================================================================

set -e   # Stop on any error

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 0 — CLONE REPO (download all source files)
# ─────────────────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/djkalirdp/billing.git"
REPO_RAW="https://raw.githubusercontent.com/djkalirdp/billing/main"
INSTALL_TARGET="billing-app"

# Check git available
if command -v git &>/dev/null; then
    if [[ -d "$INSTALL_TARGET/.git" ]]; then
        echo "  → Repo already cloned — pulling latest..."
        cd "$INSTALL_TARGET"
        git pull --quiet
        cd ..
    elif [[ -d "$INSTALL_TARGET" ]]; then
        echo "  → billing-app folder exists (no git) — skipping clone"
    else
        echo "  → Cloning repo from GitHub..."
        git clone "$REPO_URL" "$INSTALL_TARGET"
        echo "  ✔  Repo cloned"
    fi
    cd "$INSTALL_TARGET"
else
    # git not available — download each file via curl
    echo "  → git not found — downloading files via curl..."
    mkdir -p "$INSTALL_TARGET"
    cd "$INSTALL_TARGET"

    FILES=(
        "app.py"
        "database_manager.py"
        "pdf_generator.py"
        "reports_generator.py"
    )

    for f in "${FILES[@]}"; do
        echo "    downloading $f..."
        curl -fsSL "$REPO_RAW/$f" -o "$f" || echo "    WARNING: $f not downloaded"
    done

    # Download all templates
    TEMPLATES=(
        "templates/base.html"
        "templates/dashboard.html"
        "templates/billing.html"
        "templates/invoices.html"
        "templates/invoice_detail.html"
        "templates/products.html"
        "templates/product_form.html"
        "templates/product_rate_list.html"
        "templates/product_variations.html"
        "templates/buyers.html"
        "templates/buyer_form.html"
        "templates/buyer_ledger.html"
        "templates/vendors.html"
        "templates/vendor_form.html"
        "templates/purchases.html"
        "templates/purchase_form.html"
        "templates/proforma_list.html"
        "templates/proforma_form.html"
        "templates/proforma_detail.html"
        "templates/batches.html"
        "templates/batch_history.html"
        "templates/reports.html"
        "templates/settings.html"
        "templates/users.html"
        "templates/login.html"
        "templates/404.html"
        "templates/500.html"
        "templates/mobile/base_mobile.html"
        "templates/mobile/dashboard.html"
        "templates/mobile/billing.html"
        "templates/mobile/invoices.html"
        "templates/mobile/invoice_detail.html"
        "templates/mobile/products.html"
        "templates/mobile/product_form.html"
        "templates/mobile/product_variations.html"
        "templates/mobile/buyers.html"
        "templates/mobile/buyer_form.html"
        "templates/mobile/buyer_ledger.html"
        "templates/mobile/vendors.html"
        "templates/mobile/vendor_form.html"
        "templates/mobile/purchases.html"
        "templates/mobile/reports.html"
        "templates/mobile/settings.html"
        "templates/mobile/users.html"
        "templates/mobile/batches.html"
        "templates/mobile/login.html"
        "templates/mobile/404.html"
        "templates/mobile/500.html"
    )

    mkdir -p templates/mobile

    for tpl in "${TEMPLATES[@]}"; do
        echo "    downloading $tpl..."
        curl -fsSL "$REPO_RAW/$tpl" -o "$tpl" 2>/dev/null || echo "    WARNING: $tpl not downloaded"
    done

    echo "  ✔  Files downloaded"
fi

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'  # No Colour

# ── Banner ───────────────────────────────────────────────────────────────────
clear
echo ""
echo -e "${BLUE}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}${BOLD}║        BILLING & INVENTORY SOFTWARE — INSTALLER              ║${NC}"
echo -e "${BLUE}${BOLD}║        Flask + SQLite + ReportLab + GST Reports              ║${NC}"
echo -e "${BLUE}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Helper functions ─────────────────────────────────────────────────────────
ok()   { echo -e "  ${GREEN}✔${NC}  $1"; }
info() { echo -e "  ${CYAN}→${NC}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
fail() { echo -e "  ${RED}✘  ERROR: $1${NC}"; exit 1; }
step() { echo -e "\n${BOLD}${BLUE}▶  $1${NC}"; }

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1 — DETECT OS
# ─────────────────────────────────────────────────────────────────────────────
step "Detecting operating system..."

OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if   command -v apt-get &>/dev/null; then PKG="apt";
    elif command -v dnf     &>/dev/null; then PKG="dnf";
    elif command -v yum     &>/dev/null; then PKG="yum";
    elif command -v pacman  &>/dev/null; then PKG="pacman";
    else PKG="unknown"; fi
    ok "Linux detected (package manager: $PKG)"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
    ok "macOS detected"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
    warn "Windows detected — use WSL (Windows Subsystem for Linux) or Git Bash"
    warn "If you are in Git Bash or WSL, this script will work."
else
    warn "Unknown OS ($OSTYPE) — proceeding anyway..."
fi

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 — CHECK PYTHON
# ─────────────────────────────────────────────────────────────────────────────
step "Checking Python..."

PYTHON=""
for cmd in python3 python3.12 python3.11 python3.10 python3.9 python3.8 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [[ "$MAJOR" -ge 3 && "$MINOR" -ge 8 ]]; then
            PYTHON="$cmd"
            ok "Found $cmd (version $VER)"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo ""
    echo -e "${RED}  Python 3.8+ not found. Please install it first:${NC}"
    echo ""
    if [[ "$OS" == "linux" && "$PKG" == "apt" ]]; then
        echo "    sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
    elif [[ "$OS" == "linux" && "$PKG" == "dnf" ]]; then
        echo "    sudo dnf install -y python3 python3-pip"
    elif [[ "$OS" == "mac" ]]; then
        echo "    brew install python3"
        echo "    (Install Homebrew first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\")"
    else
        echo "    Download from: https://www.python.org/downloads/"
    fi
    echo ""
    exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3 — INSTALL SYSTEM DEPENDENCIES (fonts, pip)
# ─────────────────────────────────────────────────────────────────────────────
step "Installing system dependencies..."

if [[ "$OS" == "linux" && "$PKG" == "apt" ]]; then
    # Update package list silently
    info "Updating apt package list..."
    sudo apt-get update -qq 2>/dev/null || warn "apt update failed — continuing..."
    # Python pip + venv
    info "Installing python3-pip and python3-venv..."
    sudo apt-get install -y -qq python3-pip python3-venv 2>/dev/null || \
        warn "Could not install via apt — will try pip directly"
    # DejaVu fonts for ₹ symbol in PDFs
    info "Installing DejaVu fonts (for ₹ symbol in PDFs)..."
    sudo apt-get install -y -qq fonts-dejavu-core 2>/dev/null && ok "DejaVu fonts installed" || \
        warn "DejaVu fonts not installed via apt — will download manually"
    # curl for font download fallback
    sudo apt-get install -y -qq curl 2>/dev/null || true
    ok "System packages done"

elif [[ "$OS" == "linux" && "$PKG" == "dnf" ]]; then
    info "Installing dependencies via dnf..."
    sudo dnf install -y python3-pip python3-virtualenv dejavu-sans-fonts curl 2>/dev/null || \
        warn "Some packages failed — continuing"
    ok "System packages done"

elif [[ "$OS" == "linux" && "$PKG" == "pacman" ]]; then
    info "Installing dependencies via pacman..."
    sudo pacman -Sy --noconfirm python-pip python-virtualenv ttf-dejavu curl 2>/dev/null || \
        warn "Some packages failed — continuing"
    ok "System packages done"

elif [[ "$OS" == "mac" ]]; then
    if command -v brew &>/dev/null; then
        info "Homebrew found — installing python3 if needed..."
        brew install python3 2>/dev/null || true
        ok "Homebrew packages done"
    else
        warn "Homebrew not found — skipping system package install"
        info "To install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    fi
else
    warn "Skipping system package install (unknown OS or Windows)"
    info "Make sure Python 3.8+ and pip are installed manually"
fi

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 4 — ENSURE ALL SUBDIRECTORIES EXIST
# ─────────────────────────────────────────────────────────────────────────────
step "Setting up project directories..."

# We are already inside billing-app/ from Step 0
mkdir -p data backups invoices reports static/uploads templates/mobile
ok "Project directories ready"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 5 — SET UP PYTHON VIRTUAL ENVIRONMENT
# ─────────────────────────────────────────────────────────────────────────────
step "Creating Python virtual environment..."

if [[ -d "venv" ]]; then
    warn "Virtual environment already exists — reusing it"
else
    $PYTHON -m venv venv 2>/dev/null || {
        warn "venv module not found — trying virtualenv..."
        pip3 install virtualenv 2>/dev/null || pip install virtualenv
        $PYTHON -m virtualenv venv
    }
    ok "Virtual environment created"
fi

# Activate venv
if [[ "$OS" == "windows" ]]; then
    VENV_PY="venv/Scripts/python"
    VENV_PIP="venv/Scripts/pip"
else
    VENV_PY="venv/bin/python"
    VENV_PIP="venv/bin/pip"
fi

# Upgrade pip silently
info "Upgrading pip..."
"$VENV_PIP" install --upgrade pip --quiet
ok "pip upgraded"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 6 — INSTALL PYTHON PACKAGES
# ─────────────────────────────────────────────────────────────────────────────
step "Installing Python packages..."
echo ""

PACKAGES=(
    "flask"
    "werkzeug"
    "reportlab"
    "openpyxl"
    "num2words"
    "qrcode[pil]"
    "Pillow"
)

for pkg in "${PACKAGES[@]}"; do
    printf "  ${CYAN}→${NC}  Installing %-20s" "$pkg..."
    if "$VENV_PIP" install "$pkg" --quiet 2>/dev/null; then
        echo -e " ${GREEN}✔${NC}"
    else
        echo -e " ${YELLOW}⚠ warning (non-fatal)${NC}"
    fi
done

ok "All Python packages installed"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 7 — DOWNLOAD DEJAVUSANS FONTS (for ₹ symbol in PDFs)
# ─────────────────────────────────────────────────────────────────────────────
step "Setting up fonts for ₹ symbol in PDFs..."

FONT_COPIED=false

# Try system font paths first (Linux after apt install)
SYSTEM_FONT_DIRS=(
    "/usr/share/fonts/truetype/dejavu"
    "/usr/share/fonts/dejavu"
    "/usr/share/fonts/TTF"
    "/Library/Fonts"
    "/System/Library/Fonts"
)
for dir in "${SYSTEM_FONT_DIRS[@]}"; do
    if [[ -f "$dir/DejaVuSans.ttf" ]]; then
        cp "$dir/DejaVuSans.ttf"      . 2>/dev/null && \
        cp "$dir/DejaVuSans-Bold.ttf" . 2>/dev/null && \
        ok "Copied DejaVuSans fonts from $dir" && \
        FONT_COPIED=true && break
    fi
done

# Download from GitHub if not found locally
if [[ "$FONT_COPIED" == false ]]; then
    if command -v curl &>/dev/null; then
        info "Downloading DejaVuSans.ttf from GitHub..."
        BASE_URL="https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf"
        curl -fsSL "$BASE_URL/DejaVuSans.ttf"      -o DejaVuSans.ttf      2>/dev/null && \
        curl -fsSL "$BASE_URL/DejaVuSans-Bold.ttf" -o DejaVuSans-Bold.ttf 2>/dev/null && \
        ok "DejaVuSans fonts downloaded" || \
        warn "Font download failed — PDFs will use Rs. instead of ₹"
    elif command -v wget &>/dev/null; then
        info "Downloading DejaVuSans.ttf via wget..."
        BASE_URL="https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf"
        wget -q "$BASE_URL/DejaVuSans.ttf"      -O DejaVuSans.ttf      2>/dev/null && \
        wget -q "$BASE_URL/DejaVuSans-Bold.ttf" -O DejaVuSans-Bold.ttf 2>/dev/null && \
        ok "DejaVuSans fonts downloaded" || \
        warn "Font download failed — PDFs will use Rs. instead of ₹"
    else
        warn "curl/wget not available — skipping font download"
        warn "PDFs will use 'Rs.' instead of '₹' symbol"
        warn "To fix later: copy DejaVuSans.ttf and DejaVuSans-Bold.ttf into the billing-app/ folder"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 8 — WRITE requirements.txt
# ─────────────────────────────────────────────────────────────────────────────
step "Writing requirements.txt..."

cat > requirements.txt << 'REQEOF'
flask>=2.3.0
werkzeug>=2.3.0
reportlab>=4.0.0
openpyxl>=3.1.0
num2words>=0.5.12
qrcode[pil]>=7.4.0
Pillow>=10.0.0
REQEOF

ok "requirements.txt created"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 9 — WRITE start.sh (one-command launcher)
# ─────────────────────────────────────────────────────────────────────────────
step "Creating start.sh launcher..."

cat > start.sh << 'STARTEOF'
#!/usr/bin/env bash
# =============================================================
#  BILLING SOFTWARE — LAUNCHER
#  Run this script to start the app: bash start.sh
# =============================================================
cd "$(dirname "$0")"

# Activate virtual environment
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
elif [[ -f "venv/Scripts/activate" ]]; then
    source venv/Scripts/activate
fi

echo ""
echo "  ┌─────────────────────────────────────────────────────┐"
echo "  │  BILLING & INVENTORY SOFTWARE — Starting...         │"
echo "  │  Open in browser: http://localhost:5000             │"
echo "  │  Default login  : admin / admin123                  │"
echo "  │  Press Ctrl+C to stop                               │"
echo "  └─────────────────────────────────────────────────────┘"
echo ""

python app.py
STARTEOF

chmod +x start.sh
ok "start.sh created"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 10 — VERIFY INSTALLATION
# ─────────────────────────────────────────────────────────────────────────────
step "Verifying installation..."

# Test all imports
"$VENV_PY" - << 'PYTEST'
import sys
results = {}

def test(name, import_str):
    try:
        exec(import_str)
        results[name] = True
    except Exception as e:
        results[name] = str(e)

test("Flask",      "import flask")
test("ReportLab",  "from reportlab.platypus import SimpleDocTemplate")
test("openpyxl",   "import openpyxl")
test("num2words",  "from num2words import num2words")
test("Werkzeug",   "from werkzeug.security import generate_password_hash")
test("QR Code",    "import qrcode")
test("Pillow",     "from PIL import Image")

all_ok = True
for pkg, res in results.items():
    if res is True:
        print(f"  \033[32m✔\033[0m  {pkg}")
    else:
        print(f"  \033[33m⚠\033[0m  {pkg} — {res}")
        if pkg not in ("QR Code", "Pillow"):
            all_ok = False

if not all_ok:
    print("\n  \033[31mSome required packages failed.\033[0m")
    print("  Run: pip install flask reportlab openpyxl num2words werkzeug")
    sys.exit(1)
else:
    print("\n  \033[32mAll packages OK!\033[0m")
PYTEST

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 11 — GET LOCAL IP FOR MOBILE ACCESS
# ─────────────────────────────────────────────────────────────────────────────
step "Getting local network IP..."

LOCAL_IP=""
if command -v hostname &>/dev/null; then
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}') || true
fi
if [[ -z "$LOCAL_IP" ]] && command -v ip &>/dev/null; then
    LOCAL_IP=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+') || true
fi
if [[ -z "$LOCAL_IP" ]] && command -v ifconfig &>/dev/null; then
    LOCAL_IP=$(ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | head -1) || true
fi

# ─────────────────────────────────────────────────────────────────────────────
#  DONE — PRINT SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║          INSTALLATION COMPLETE!                              ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}To START the app:${NC}"
echo -e "  ${CYAN}  bash start.sh${NC}"
echo ""
echo -e "  ${BOLD}Then open in browser:${NC}"
echo -e "  ${CYAN}  http://localhost:5000${NC}"
if [[ -n "$LOCAL_IP" ]]; then
    echo ""
    echo -e "  ${BOLD}Mobile access (same Wi-Fi):${NC}"
    echo -e "  ${CYAN}  http://${LOCAL_IP}:5000${NC}"
fi
echo ""
echo -e "  ${BOLD}Default Login:${NC}"
echo -e "  ${CYAN}  Username : admin${NC}"
echo -e "  ${CYAN}  Password : admin123${NC}"
echo -e "  ${YELLOW}  ⚠  Change password after first login!${NC}"
echo ""
echo -e "  ${BOLD}Files:${NC}"
echo -e "  ${CYAN}  data/billing_app.db${NC}  ← Your database (keep this safe!)"
echo -e "  ${CYAN}  settings.json${NC}         ← Company settings"
echo -e "  ${CYAN}  backups/${NC}              ← Auto daily backups"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
#  ASK TO START NOW
# ─────────────────────────────────────────────────────────────────────────────
echo -e "  ${BOLD}Start the app now?${NC}"
read -p "  (y/N): " START_NOW

if [[ "$START_NOW" == "y" || "$START_NOW" == "Y" ]]; then
    echo ""
    echo -e "  ${GREEN}Starting billing app...${NC}"
    echo -e "  ${CYAN}Open: http://localhost:5000${NC}"
    echo -e "  ${CYAN}Press Ctrl+C to stop${NC}"
    echo ""

    # Activate venv and start
    if [[ -f "venv/bin/activate" ]]; then
        source venv/bin/activate
    elif [[ -f "venv/Scripts/activate" ]]; then
        source venv/Scripts/activate
    fi
    python app.py
fi
