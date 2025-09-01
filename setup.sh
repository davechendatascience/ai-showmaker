#!/bin/bash

# AI-Showmaker Setup Script
# This script helps set up the project environment and troubleshoot common issues

set -e  # Exit on any error

echo "🚀 AI-Showmaker Setup Script"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a virtual environment
check_venv() {
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_success "Virtual environment is active: $VIRTUAL_ENV"
    else
        print_warning "No virtual environment detected"
        read -p "Do you want to create a virtual environment? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Creating virtual environment..."
            python3 -m venv venv
            print_success "Virtual environment created. Please activate it:"
            echo "source venv/bin/activate"
            echo "Then run this script again."
            exit 0
        fi
    fi
}

# Check Python version
check_python() {
    print_status "Checking Python version..."
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_status "Python version: $python_version"
    
    # Extract major and minor version
    major=$(echo $python_version | cut -d'.' -f1)
    minor=$(echo $python_version | cut -d'.' -f2)
    
    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 8 ]); then
        print_error "Python 3.8+ is required. Current version: $python_version"
        exit 1
    fi
    
    print_success "Python version is compatible"
}

# Check pip version
check_pip() {
    print_status "Checking pip version..."
    pip_version=$(pip --version | cut -d' ' -f2)
    print_status "Pip version: $pip_version"
    
    # Upgrade pip if needed
    print_status "Upgrading pip..."
    pip install --upgrade pip
    print_success "Pip upgraded"
}

# Install system dependencies (Linux only)
install_system_deps() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_status "Detected Linux system. Installing system dependencies..."
        
        # Detect package manager
        if command -v apt-get &> /dev/null; then
            print_status "Using apt package manager..."
            sudo apt-get update
            sudo apt-get install -y \
                build-essential \
                python3-dev \
                libxml2-dev \
                libxslt1-dev \
                libffi-dev \
                libssl-dev \
                zlib1g-dev \
                libbz2-dev \
                liblzma-dev
        elif command -v yum &> /dev/null; then
            print_status "Using yum package manager..."
            sudo yum groupinstall -y "Development Tools"
            sudo yum install -y python3-devel libxml2-devel libxslt-devel libffi-devel openssl-devel
        elif command -v dnf &> /dev/null; then
            print_status "Using dnf package manager..."
            sudo dnf groupinstall -y "Development Tools"
            sudo dnf install -y python3-devel libxml2-devel libxslt-devel libffi-devel openssl-devel
        else
            print_warning "Could not detect package manager. Please install system dependencies manually."
        fi
    else
        print_status "Not a Linux system, skipping system dependencies"
    fi
}

# Try different installation methods
install_packages() {
    print_status "Installing Python packages..."
    
    # Method 1: Try with pinned versions
    print_status "Attempting installation with pinned versions..."
    if pip install -r requirements-pinned.txt; then
        print_success "Installation with pinned versions successful!"
        return 0
    fi
    
    # Method 2: Try with original requirements
    print_status "Attempting installation with original requirements..."
    if pip install -r requirements.txt; then
        print_success "Installation with original requirements successful!"
        return 0
    fi
    
    # Method 3: Try minimal requirements
    print_status "Attempting installation with minimal requirements..."
    if pip install -r requirements-minimal.txt; then
        print_success "Installation with minimal requirements successful!"
        return 0
    fi
    
    # Method 4: Install packages individually
    print_status "Attempting individual package installation..."
    packages=(
        "langchain"
        "langchain-openai"
        "llama-index"
        "llama-index-llms-openai"
        "paramiko"
        "beautifulsoup4"
        "lxml"
        "aiohttp"
        "pydantic"
        "structlog"
    )
    
    for package in "${packages[@]}"; do
        print_status "Installing $package..."
        if pip install "$package"; then
            print_success "Installed $package"
        else
            print_error "Failed to install $package"
            return 1
        fi
    done
    
    print_success "All packages installed successfully!"
}

# Verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    python3 -c "
import sys
packages = ['langchain', 'llama_index', 'paramiko', 'bs4', 'lxml', 'aiohttp', 'pydantic', 'structlog']
failed = []
for package in packages:
    try:
        __import__(package)
        print(f'✓ {package}')
    except ImportError as e:
        print(f'✗ {package}: {e}')
        failed.append(package)

if failed:
    print(f'\\nFailed packages: {failed}')
    sys.exit(1)
else:
    print('\\n🎉 All packages installed successfully!')
"
    
    if [ $? -eq 0 ]; then
        print_success "Installation verification passed!"
    else
        print_error "Installation verification failed!"
        return 1
    fi
}

# Main execution
main() {
    print_status "Starting setup process..."
    
    check_venv
    check_python
    check_pip
    install_system_deps
    install_packages
    verify_installation
    
    print_success "Setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Configure your environment variables (see README.md)"
    echo "2. Run: python demo_mcp.py"
    echo "3. Or run: python main.py"
}

# Run main function
main "$@"
