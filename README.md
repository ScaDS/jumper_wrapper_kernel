# Jupyter Kernel Wrapper

A Python-based Jupyter kernel that can wrap and forward execution to any other Jupyter kernel available on your system.

## Features

- **Magic Command**: Use `%wrap <kernel_name>` to wrap any installed Jupyter kernel
- **Transparent Forwarding**: Once wrapped, all code execution is forwarded to the underlying kernel
- **Dynamic Language Support**: Automatically adapts to the wrapped kernel's language
- **Easy Installation**: Simple pip installation and kernel registration

## Installation

### 1. Install the package

```bash
cd /home/eliasw/CascadeProjects/jupyter-kernel-wrapper
pip install -e .
```

### 2. Install the kernel spec

```bash
# Install for current user
python -m kernel_wrapper.install --user

# Or install system-wide (may require sudo)
python -m kernel_wrapper.install
```

Alternatively, you can use the console script:

```bash
install-kernel-wrapper --user
```

## Usage

### 1. Start Jupyter

Launch Jupyter Notebook or JupyterLab:

```bash
jupyter notebook
# or
jupyter lab
```

### 2. Create a new notebook with "Kernel Wrapper"

Select "Kernel Wrapper" from the kernel list when creating a new notebook.

### 3. Use the %wrap magic command

In the first cell, wrap any available kernel:

```
%wrap python3
```

This will wrap the Python 3 kernel. You can replace `python3` with any kernel name available on your system.

### 4. Execute code normally

After wrapping a kernel, all subsequent cells will execute in the wrapped kernel:

```python
# This will execute in the wrapped Python kernel
print("Hello from the wrapped kernel!")
x = 42
print(f"x = {x}")
```

## Available Kernels

To see which kernels are available on your system, run:

```bash
jupyter kernelspec list
```

Common kernel names include:
- `python3` - Python 3
- `ir` - R
- `julia-1.x` - Julia
- `javascript` - JavaScript (Node.js)

## Example Workflow

```
Cell 1:
%wrap python3

Output: Successfully wrapped kernel: python3 (Python 3)
        All subsequent code will be executed in the wrapped kernel.

Cell 2:
import numpy as np
print(np.array([1, 2, 3]))

Output: [1 2 3]

Cell 3:
%wrap ir

Output: Successfully wrapped kernel: ir (R)
        All subsequent code will be executed in the wrapped kernel.

Cell 4:
x <- c(1, 2, 3)
print(x)

Output: [1] 1 2 3
```

## How It Works

The Kernel Wrapper creates a lightweight proxy kernel that:

1. Intercepts all code execution requests
2. Detects the `%wrap` magic command
3. Starts the specified kernel as a subprocess
4. Forwards all subsequent code to the wrapped kernel
5. Relays all output, errors, and display data back to Jupyter

This allows you to switch between different language kernels within a single notebook session.

## Architecture

```
Jupyter Frontend (Notebook/Lab)
        ↓
Kernel Wrapper (this kernel)
        ↓
Wrapped Kernel (Python, R, Julia, etc.)
```

## Uninstallation

To remove the kernel:

```bash
jupyter kernelspec uninstall kernel_wrapper
```

To uninstall the package:

```bash
pip uninstall jupyter-kernel-wrapper
```

## Requirements

- Python 3.7+
- ipykernel >= 6.0.0
- jupyter-client >= 7.0.0

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Troubleshooting

### Kernel not found error

If you get a "Kernel not found" error when using `%wrap`, make sure the kernel you're trying to wrap is installed:

```bash
jupyter kernelspec list
```

### Wrapped kernel not responding

If the wrapped kernel stops responding, you can wrap a different kernel or restart the notebook.

### Installation issues

If you encounter permission errors during installation, try:

```bash
pip install --user -e .
python -m kernel_wrapper.install --user
```
