"""Shared pytest fixtures for kernel tests."""

import os

# Suppress jupyter_client DeprecationWarning about platformdirs migration
os.environ["JUPYTER_PLATFORM_DIRS"] = "1"

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_kernel_specs():
    """Sample kernel specs for testing."""
    return {
        'python3': {
            'spec': {
                'display_name': 'Python 3',
                'language': 'python',
                'file_extension': '.py',
            },
            'resource_dir': '/usr/share/jupyter/kernels/python3',
        },
        'ir': {
            'spec': {
                'display_name': 'R',
                'language': 'R',
                'file_extension': '.r',
            },
            'resource_dir': '/usr/share/jupyter/kernels/ir',
        },
        'julia-1.9': {
            'spec': {
                'display_name': 'Julia 1.9',
                'language': 'julia',
                'file_extension': '.jl',
            },
            'resource_dir': '/usr/share/jupyter/kernels/julia-1.9',
        },
    }


@pytest.fixture
def mock_kernel_spec_manager(mock_kernel_specs):
    """Mock KernelSpecManager."""
    manager = MagicMock()
    manager.get_all_specs.return_value = mock_kernel_specs
    return manager


@pytest.fixture
def mock_kernel_client():
    """Mock kernel client for wrapped kernel."""
    client = MagicMock()
    client.wait_for_ready.return_value = None
    client.execute.return_value = 'msg-id-123'
    client.complete.return_value = 'complete-msg-id'
    client.inspect.return_value = 'inspect-msg-id'
    return client


@pytest.fixture
def mock_kernel_manager(mock_kernel_client):
    """Mock KernelManager."""
    manager = MagicMock()
    manager.client.return_value = mock_kernel_client
    return manager


@pytest.fixture
def mock_shell():
    """Mock IPython shell with magics manager."""
    shell = MagicMock()

    # Setup magics manager
    shell.magics_manager.magics = {
        'line': {'time': MagicMock(), 'timeit': MagicMock()},
        'cell': {'time': MagicMock()},
    }
    shell.magics_manager.lsmagic.return_value = {
        'line': ['time', 'timeit'],
        'cell': ['time'],
    }

    # Mock run_line_magic (for loading extensions)
    shell.run_line_magic.return_value = None

    # Mock events
    shell.events = MagicMock()
    shell.events.trigger = MagicMock()

    return shell


@pytest.fixture
def mock_iopub_socket():
    """Mock iopub socket for send_response."""
    return MagicMock()


@pytest.fixture
def jumper_magics():
    """Set of jumper-extension magic commands."""
    return {'jumper_start', 'jumper_stop', 'jumper_status'}


@pytest.fixture
def wrapper_magics():
    """Set of wrapper magic commands."""
    return {'list_kernels', 'wrap_kernel'}


@pytest.fixture
def local_magics(jumper_magics, wrapper_magics):
    """Combined set of local magic commands."""
    return jumper_magics | wrapper_magics
