"""Installation script for the kernel wrapper."""

import argparse
import json
import os
import sys
from pathlib import Path
from jupyter_client.kernelspec import KernelSpecManager


def main():
    """Install the kernel wrapper kernel spec."""
    parser = argparse.ArgumentParser(
        description='Install the Kernel Wrapper kernel spec'
    )
    parser.add_argument(
        '--user',
        action='store_true',
        help='Install for the current user instead of system-wide'
    )
    parser.add_argument(
        '--prefix',
        type=str,
        default=None,
        help='Install to the given prefix'
    )
    parser.add_argument(
        '--name',
        type=str,
        default='kernel_wrapper',
        help='Name for the kernel spec (default: kernel_wrapper)'
    )
    
    args = parser.parse_args()
    
    # Get the kernel spec directory
    kernel_spec_dir = Path(__file__).parent / 'kernelspec'
    
    # Install the kernel spec
    ksm = KernelSpecManager()
    
    try:
        ksm.install_kernel_spec(
            str(kernel_spec_dir),
            kernel_name=args.name,
            user=args.user,
            prefix=args.prefix
        )
        
        print(f"Kernel Wrapper installed successfully as '{args.name}'")
        print(f"You can now use it in Jupyter by selecting '{args.name}' as your kernel.")
        
    except Exception as e:
        print(f"Error installing kernel spec: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
