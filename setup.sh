#!/bin/sh
# Exit immediately if a command exits with a non-zero status
set -e

# Install wget and other necessary tools using nix
nix-env -iA nixpkgs.wget nixpkgs.xz nixpkgs.ffmpeg

# Setup completed message
echo "Setup completed."
