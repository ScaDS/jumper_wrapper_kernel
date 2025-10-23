# Jupyter Kernel Wrapper with Jumper Extension

A Python-based Jupyter kernel that wraps other Jupyter kernels and provides full access to jumper_extension magic commands.

## Features

- **🎯 Wrap Any Kernel**: Use `%wrap <kernel_name>` to wrap any installed Jupyter kernel
- **✨ Full Jumper Extension Support**: All jumper_extension magics are automatically loaded and available
- **🔄 Seamless Forwarding**: Code execution is transparently forwarded to the wrapped kernel
- **🐍 IPython Extension Loading**: Uses IPython's native extension mechanism (`%load_ext`)
- **🎩 Smart Magic Routing**: Magic commands available in the wrapper are executed locally, others forwarded to wrapped kernel

## Installation

### 1. Install the package

```bash
cd /home/eliasw/CascadeProjects/jupyter-kernel-wrapper
pip install -e .
```

### 2. Install the kernel spec

```bash
python -m kernel_wrapper.install --user
```

Or use the console script:

```bash
install-kernel-wrapper --user
```

## Usage

### Basic Workflow

1. **Start Jupyter**
   ```bash
   jupyter notebook
   # or
   jupyter lab
   ```

2. **Create a new notebook** with "Kernel Wrapper (with jumper)" kernel

3. **Use jumper magics immediately** (before wrapping):
   ```python
   %jumper_status
   %jumper_info
   ```

4. **Wrap a kernel** when you need to execute code:
   ```python
   %wrap python3
   ```

5. **Continue using jumper magics** and execute code normally:
   ```python
   # Jumper magics still work
   %jumper_magic
   
   # Code is executed in the wrapped kernel
   import numpy as np
   print(np.array([1, 2, 3]))
   ```

### Example Session

```python
# Cell 1: Use jumper magics before wrapping
%jumper_status
# Output: Shows jumper extension status

# Cell 2: Wrap a Python kernel
%wrap python3
# Output: Successfully wrapped kernel: python3 (Python 3)
#         All subsequent code will be executed in the wrapped kernel.
#         Jumper extensions are available in the wrapper kernel.

# Cell 3: Execute Python code in wrapped kernel
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
print(df)
# Output: DataFrame is displayed

# Cell 4: Use jumper magics after wrapping
%jumper_info
# Output: Shows jumper extension info

# Cell 5: Switch to a different kernel
%wrap ir
# Output: Successfully wrapped kernel: ir (R)

# Cell 6: Execute R code
x <- c(1, 2, 3, 4, 5)
mean(x)
# Output: [1] 3
```

## How It Works

The kernel wrapper is built on top of `IPythonKernel` and uses IPython's extension loading mechanism:

1. **Initialization**: When the kernel starts, it automatically loads jumper_extension using `shell.extension_manager.load_extension('jumper_extension')`

2. **Magic Commands Available**: All jumper magics are immediately available in the wrapper kernel's IPython shell

3. **Kernel Wrapping**: When you use `%wrap <kernel_name>`, the wrapper:
   - Starts the target kernel as a subprocess
   - Intelligently routes code based on magic command availability
   - Keeps jumper magics available in the wrapper context

4. **Smart Magic Routing**: When a wrapped kernel is active:
   - **Magic commands available in wrapper**: Executed in the wrapper's IPython shell (e.g., jumper magics, %lsmagic, %timeit)
   - **Regular code**: Forwarded to the wrapped kernel
   - **Unknown magics**: Forwarded to the wrapped kernel (may work if supported there)

5. **Dual Context**:
   - **Wrapper kernel**: Handles wrapper-available magics and the `%wrap` command
   - **Wrapped kernel**: Executes regular code and kernel-specific magics

## Architecture

```
┌─────────────────────────────────────┐
│   Jupyter Frontend (Notebook/Lab)  │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│     Kernel Wrapper (IPythonKernel) │
│  - Loads jumper_extension          │
│  - Handles %wrap command           │
│  - Executes jumper magics          │
└─────────────────┬───────────────────┘
                  │
        ┌─────────▼─────────┐
        │  Wrapped Kernel   │
        │  (Python/R/Julia) │
        │  - Executes code  │
        └───────────────────┘
```

## Requirements

- Python 3.7+
- ipykernel >= 6.0.0
- jupyter-client >= 7.0.0
- **jumper-extension >= 0.1.0** (required)

## Available Kernels

To see which kernels you can wrap:

```bash
jupyter kernelspec list
```

Common examples:
- `python3` - Python 3
- `ir` - R
- `julia-1.x` - Julia
- `javascript` - JavaScript (Node.js)

## Advanced Features

### Automatic Jumper Extension in Wrapped Kernels

For Python kernels, the wrapper automatically attempts to load jumper_extension in the wrapped kernel as well. This means jumper magics can work in both contexts.

### Error Handling

If jumper_extension cannot be loaded, the kernel will log a warning but continue to function. The `%wrap` command will still work, but jumper magics will not be available.

## Troubleshooting

### "jumper_extension not found" error

Make sure jumper_extension is installed:
```bash
pip install jumper-extension
```

### Kernel not responding after wrap

Try restarting the notebook or wrapping a different kernel.

### Magic commands not working

Verify that jumper_extension is properly installed and the kernel was started correctly. Check the kernel logs for any error messages.

## Development

To contribute or modify the kernel:

```bash
git clone <repository>
cd jupyter-kernel-wrapper
pip install -e .
python -m kernel_wrapper.install --user
```

## Uninstallation

```bash
# Remove the kernel spec
jupyter kernelspec uninstall kernel_wrapper

# Uninstall the package
pip uninstall jupyter-kernel-wrapper
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.
