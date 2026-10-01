#!/usr/bin/env bash
# =============================================================================
# setup_pi.sh — Raspberry Pi Zero W IoT Crypto Environment Setup
# =============================================================================
#
# Target   : Raspberry Pi Zero W (ARMv6, 512 MB RAM, Raspberry Pi OS Lite)
# Python   : 3.11
# Purpose  : Install ECDH + ASCON cryptographic dependencies safely.
#
# DESIGN RATIONALE — Why not "pip install cryptography"?
# -------------------------------------------------------
# The `cryptography` Python package has a Rust build backend.  On the
# Raspberry Pi Zero W (ARMv6 / 512 MB RAM) that compilation step will
# exhaust RAM and hang or crash the device.
#
# Solution: install `python3-cryptography` from the Raspberry Pi OS APT
# repository (pre-compiled ARM binary).  We then create a virtual
# environment with --system-site-packages so the venv inherits the
# system-installed `cryptography` without recompiling it.
#
# Only `ascon` (pure Python, < 20 KB) is installed via pip inside the venv.
#
# Usage
# -----
#   chmod +x setup_pi.sh
#   sudo ./setup_pi.sh
#   source ~/iot-env/bin/activate
#   python test_crypto.py
#
# =============================================================================

set -euo pipefail          # exit on error, undefined vars, pipe failures
IFS=$'\n\t'

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

info()  { echo -e "${GREEN}[INFO]${RESET}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error() { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

# ── Configuration ─────────────────────────────────────────────────────────────
VENV_DIR="${HOME}/iot-env"
PYTHON_BIN="python3"

# ── 0. Preflight checks ───────────────────────────────────────────────────────
info "Checking prerequisites..."

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (sudo ./setup_pi.sh)"
fi

if ! command -v apt-get &>/dev/null; then
    error "apt-get not found. This script targets Raspberry Pi OS (Debian-based)."
fi

${PYTHON_BIN} --version >/dev/null 2>&1 \
    || error "Python 3 not found. Please install python3 first."

info "All prerequisites satisfied."

# ── 1. System package installation (apt) ─────────────────────────────────────
info "Updating APT package lists..."
apt-get update -qq

info "Installing system packages (pre-compiled ARM binaries)..."
apt-get install -y \
    python3-pip \
    python3-venv \
    python3-cryptography   # <-- pre-built ARM binary; avoids Rust compilation

info "System packages installed successfully."

# ── 2. Create virtual environment ─────────────────────────────────────────────
if [[ -d "${VENV_DIR}" ]]; then
    warn "Virtual environment already exists at ${VENV_DIR}. Skipping creation."
else
    info "Creating virtual environment at ${VENV_DIR}..."
    # --system-site-packages: inherit python3-cryptography from the system,
    # avoiding any attempt to recompile it inside the venv.
    ${PYTHON_BIN} -m venv --system-site-packages "${VENV_DIR}"
    info "Virtual environment created."
fi

# ── 3. Upgrade pip inside the venv ───────────────────────────────────────────
info "Upgrading pip inside the virtual environment..."
"${VENV_DIR}/bin/pip" install --quiet --upgrade pip

# ── 4. Install pure-Python packages inside the venv ──────────────────────────
info "Installing 'ascon' (pure Python, safe on constrained hardware)..."
"${VENV_DIR}/bin/pip" install --quiet ascon

# ── 5. Verify installation ────────────────────────────────────────────────────
info "Verifying installed packages..."

"${VENV_DIR}/bin/python" - <<'PYCHECK'
import sys

results = []

try:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    results.append(("cryptography (X25519 + HKDF)", "OK"))
except ImportError as e:
    results.append(("cryptography", f"FAIL — {e}"))

try:
    import ascon
    results.append(("ascon", "OK"))
except ImportError as e:
    results.append(("ascon", f"FAIL — {e}"))

print("\n  Package verification results:")
all_ok = True
for pkg, status in results:
    icon = "✓" if status == "OK" else "✗"
    print(f"    {icon}  {pkg:<40} {status}")
    if status != "OK":
        all_ok = False

if not all_ok:
    sys.exit(1)
PYCHECK

# ── 6. Done ───────────────────────────────────────────────────────────────────
echo ""
info "============================================================"
info "  Setup complete!  To use your IoT crypto environment:"
info ""
info "    source ${VENV_DIR}/bin/activate"
info "    python test_crypto.py"
info "============================================================"
echo ""
