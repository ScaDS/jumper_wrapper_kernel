---
title: API Overview
---

# API Overview

The Jumper Wrapper Kernel exposes a modular API organized into three main components:

- **Kernel** - The main `JumperWrapperKernel` class that implements the Jupyter kernel protocol and manages kernel wrapping
- **Installation** - Functions for installing and uninstalling the kernel specification
- **Utilities** - Helper functions for magic command detection and cell routing

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Jupyter Frontend                      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              JumperWrapperKernel                         │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │ JumperWrapper   │  │ jumper-extension             │  │
│  │ Magics          │  │ (loaded locally)             │  │
│  │ - %list_kernels │  │ - %perfmonitor_start         │  │
│  │ - %wrap_kernel  │  │ - %perfmonitor_stop          │  │
│  └─────────────────┘  │ - etc.                       │  │
│                       └──────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Wrapped Kernel                      │   │
│  │   (Python, R, Julia, etc.)                       │   │
│  │   - Receives forwarded code                      │   │
│  │   - Returns execution results                    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Message Flow

1. Cell code arrives at `do_execute()`
2. `_is_local_magic()` checks if code contains only local magic commands
3. Local magics are executed via `_execute_local_magic()`
4. Other code is forwarded via `_forward_to_wrapped_kernel()`
5. Pre/post cell events are triggered for jumper-extension hooks

## Module Reference

For detailed API documentation, see:

- [Kernel](kernel.md) - Main kernel class and magic commands
- [Installation](install.md) - Kernel installation functions
- [Utilities](utilities.md) - Magic detection helpers
