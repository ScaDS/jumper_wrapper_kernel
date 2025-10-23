"""Installation script for the kernel wrapper."""

import argparse
import os
import sys
from jupyter_client.kernelspec import KernelSpecManager


def install_kernel(user=True, prefix=None, kernel_name='kernel_wrapper'):
    """Install the kernel wrapper kernel spec."""
    # Get the path to the kernel spec directory
    kernel_spec_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'kernelspec'
    )
    
    # Install the kernel spec
    ksm = KernelSpecManager()
    
    try:
        ksm.install_kernel_spec(
            kernel_spec_dir,
            kernel_name=kernel_name,
            user=user,
            prefix=prefix
        )
        
        print(f"✓ Kernel Wrapper installed successfully as '{kernel_name}'")
        print(f"✓ You can now use it in Jupyter by selecting 'Kernel Wrapper (with jumper)' as your kernel.")
        print("\n📝 Usage:")
        print("  1. Create a new notebook with 'Kernel Wrapper (with jumper)' kernel")
        print("  2. Use %wrap <kernel_name> to wrap any installed kernel")
        print("  3. All jumper_extension magics are available before and after wrapping")
        
    except Exception as e:
        print(f"✗ Error installing kernel spec: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the installation script."""
    parser = argparse.ArgumentParser(description='Install the Kernel Wrapper kernel spec')
    parser.add_argument('--user', action='store_true', help='Install for the current user instead of system-wide')
    parser.add_argument('--prefix', type=str, default=None, help='Install to the given prefix')
    parser.add_argument('--name', type=str, default='kernel_wrapper', help='Name for the kernel spec')
    
    args = parser.parse_args()
    install_kernel(user=args.user, prefix=args.prefix, kernel_name=args.name)


if __name__ == '__main__':
    main()
