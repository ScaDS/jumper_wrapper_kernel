# Jumper Wrapper Kernel

A Jupyter kernel that wraps other kernels while providing jumper-extension performance monitoring capabilities.

## Features

- **Wrap any Jupyter kernel**: Use `%wrap_kernel` to wrap any installed Jupyter kernel (Python, R, Julia, etc.)
- **Performance monitoring**: All jumper-extension magic commands are handled locally, allowing you to monitor performance of any wrapped kernel
- **Seamless forwarding**: All non-magic code is forwarded to the wrapped kernel transparently

## Requirements

- Python >= 3.8
- ipykernel >= 6.0
- jupyter_client >= 7.0
- **jumper-extension >= 0.3.0** (required dependency)

## Installation

```bash
# Install the package
pip install jumper_wrapper_kernel

# Install the kernel spec
python -m jumper_wrapper_kernel.install install

# Or install to sys.prefix (for virtualenv/conda)
python -m jumper_wrapper_kernel.install install --sys-prefix
```

### Development Installation

```bash
git clone https://github.com/ScaDS/jumper_wrapper_kernel.git
cd jumper_wrapper_kernel
pip install -e .
python -m jumper_wrapper_kernel.install install
```

## Usage

1. Start Jupyter Notebook or JupyterLab
2. Select "Jumper Wrapper Kernel" as your kernel
3. Use the magic commands:

### Available Magic Commands

#### `%list_kernels`
List all available Jupyter kernels that can be wrapped.

```python
%list_kernels
```

Output:
```
Available Jupyter Kernels:
--------------------------------------------------
  python3: Python 3 (ipykernel) (python)
  ir: R (r)
  julia-1.9: Julia 1.9 (julia)
--------------------------------------------------
```

#### `%wrap_kernel <kernel_name>`
Wrap an existing Jupyter kernel. All subsequent code will be forwarded to this kernel.

```python
%wrap_kernel python3
```

Output:
```
Successfully wrapped kernel: python3
```

#### `%remove_kernel <kernel_name>`
Remove a wrapper-created kernel spec. If the kernel is currently wrapped, it will be shut down first.

```python
%remove_kernel my_wrapped_kernel
```

Output:
```
Removed kernel spec: my_wrapped_kernel
```

### Jumper Extension Commands

All jumper-extension magic commands are available and executed locally:

- `%perfmonitor_start [interval]` - Start performance monitoring
- `%perfmonitor_stop` - Stop performance monitoring
- `%perfmonitor_perfreport` - View performance report
- `%perfmonitor_plot` - Plot performance data
- `%cell_history` - View cell execution history
- And more...

See the [jumper-extension documentation](https://pypi.org/project/jumper-extension/) for full details.

## Example Workflow

```python
# List available kernels
%list_kernels

# Wrap a Python kernel
%wrap_kernel python3

# Start performance monitoring (handled locally)
%perfmonitor_start

# Execute code on the wrapped kernel
import numpy as np
x = np.random.rand(1000, 1000)
y = np.dot(x, x.T)

# View performance report (handled locally)
%perfmonitor_perfreport
```

## How It Works

The Jumper Wrapper Kernel acts as a proxy:

1. **Magic commands** from jumper-extension are intercepted and executed locally in the wrapper kernel's IPython environment
2. **All other code** is forwarded to the wrapped kernel for execution
3. **Output** from the wrapped kernel is streamed back to the notebook

This allows you to monitor performance of any Jupyter kernel, regardless of its language.

## Uninstallation

```bash
# Uninstall the kernel spec
python -m jumper_wrapper_kernel.install uninstall

# Uninstall the package
pip uninstall jumper_wrapper_kernel
```

## License

MIT License

## Citation

If you use this kernel in your research, please cite the jumper-extension paper:

```
Werner, E., Rygin, A., Gocht-Zech, A., Döbel, S., & Lieber, M. (2024, November). 
JUmPER: Performance Data Monitoring, Instrumentation and Visualization for Jupyter Notebooks. 
In SC24-W: Workshops of the International Conference for High Performance Computing, 
Networking, Storage and Analysis (pp. 2003-2011). IEEE. 
https://www.doi.org/10.1109/SCW63240.2024.00250
```
