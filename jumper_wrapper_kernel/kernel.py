"""
Jumper Wrapper Kernel - Main kernel implementation.

This kernel wraps other Jupyter kernels and forwards execution to them,
while keeping jumper-extension magic commands local.
"""

import sys
from ipykernel.ipkernel import IPythonKernel
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core.interactiveshell import ExecutionInfo, ExecutionResult

from .utilities import is_local_magic_cell


# Check for jumper-extension dependency
import importlib.util
JUMPER_EXTENSION_AVAILABLE = importlib.util.find_spec("jumper_extension") is not None

if not JUMPER_EXTENSION_AVAILABLE:
    raise ImportError(
        "jumper-extension is required but not installed. "
        "Please install it with: pip install jumper-extension"
    )


@magics_class
class JumperWrapperMagics(Magics):
    """Magic commands for the Jumper Wrapper Kernel."""
    
    def __init__(self, shell, kernel):
        super().__init__(shell)
        self._kernel = kernel
    
    @line_magic
    def list_kernels(self, line):
        """List all available Jupyter kernels."""
        return self._kernel._list_kernels()
    
    @line_magic
    def wrap_kernel(self, line):
        """Wrap an existing Jupyter kernel."""
        return self._kernel._wrap_kernel(line.strip())


class JumperWrapperKernel(IPythonKernel):
    """A Jupyter kernel that wraps other kernels."""
    
    implementation = 'jumper_wrapper_kernel'
    implementation_version = '0.1.0'
    language = 'python'
    language_version = sys.version.split()[0]
    language_info = {
        'name': 'python',
        'mimetype': 'text/x-python',
        'file_extension': '.py',
        'codemirror_mode': {
            'name': 'ipython',
            'version': 3,
        },
        'pygments_lexer': 'ipython3',
    }
    banner = "Jumper Wrapper Kernel - Wrap any Jupyter kernel with jumper-extension support"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Wrapped kernel state
        self._wrapped_kernel_name = None
        self._kernel_manager = None
        self._kernel_client = None
        self._kernel_spec_manager = KernelSpecManager()
        
        # Set of magic commands registered (populated after loading extensions)
        self._jumper_magic_commands = set()
        self._wrapper_magic_commands = set()
        self._load_jumper_extension()
        self._register_wrapper_magics()
    
    def _load_jumper_extension(self):
        """Load jumper-extension and capture its registered magic commands."""
        # Get magics before loading extension
        magics_before = self._get_all_magics()
        
        # Load jumper extension using the kernel's shell
        self.shell.run_line_magic('load_ext', 'jumper_extension')
        
        # Get magics after loading extension
        magics_after = self._get_all_magics()
        
        # The difference is the magics registered by jumper-extension
        self._jumper_magic_commands = magics_after - magics_before
    
    def _register_wrapper_magics(self):
        """Register wrapper magic commands and capture their names."""
        # Get magics before registering
        magics_before = self._get_all_magics()
        
        # Register our magic class
        wrapper_magics = JumperWrapperMagics(self.shell, self)
        self.shell.register_magics(wrapper_magics)
        
        # Get magics after registering
        magics_after = self._get_all_magics()
        
        # The difference is our wrapper magics
        self._wrapper_magic_commands = magics_after - magics_before
    
    def _get_all_magics(self):
        """Get all currently registered magic command names."""
        magics = set()
        magic_manager = self.shell.magics_manager
        
        # Get line magics
        for name in magic_manager.magics.get('line', {}).keys():
            magics.add(name)
        
        # Get cell magics
        for name in magic_manager.magics.get('cell', {}).keys():
            magics.add(name)
        
        return magics
    
    def _get_available_kernels(self):
        """Get a list of available kernel specs."""
        return self._kernel_spec_manager.get_all_specs()
    
    def _get_local_magics(self):
        """Get combined set of local magic commands."""
        return self._jumper_magic_commands | self._wrapper_magic_commands
    
    def _list_kernels(self):
        """List all available Jupyter kernels."""
        kernels = self._get_available_kernels()
        
        output = "Available Jupyter Kernels:\n"
        output += "-" * 50 + "\n"
        
        for name, spec in kernels.items():
            display_name = spec.get('spec', {}).get('display_name', name)
            language = spec.get('spec', {}).get('language', 'unknown')
            output += f"  {name}: {display_name} ({language})\n"
        
        if self._wrapped_kernel_name:
            output += "\n" + "-" * 50 + "\n"
            output += f"Currently wrapped kernel: {self._wrapped_kernel_name}\n"
        
        self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': output})
        
        return {
            'status': 'ok',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }
    
    def _wrap_kernel(self, kernel_name):
        """Wrap the specified kernel."""
        if not kernel_name:
            error_msg = "Usage: %wrap_kernel <kernel_name>\nUse %list_kernels to see available kernels."
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': error_msg})
            return {
                'status': 'error',
                'ename': 'ValueError',
                'evalue': 'No kernel name specified',
                'traceback': [error_msg],
                'execution_count': self.execution_count,
            }
        
        # Check if kernel exists
        available_kernels = self._get_available_kernels()
        if kernel_name not in available_kernels:
            error_msg = f"Kernel '{kernel_name}' not found. Use %list_kernels to see available kernels."
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': error_msg})
            return {
                'status': 'error',
                'ename': 'ValueError',
                'evalue': f'Kernel not found: {kernel_name}',
                'traceback': [error_msg],
                'execution_count': self.execution_count,
            }
        
        # Shutdown existing wrapped kernel if any
        if self._kernel_manager is not None:
            self._shutdown_wrapped_kernel()
        
        # Start the new kernel
        try:
            self._kernel_manager = KernelManager(kernel_name=kernel_name)
            self._kernel_manager.start_kernel()
            self._kernel_client = self._kernel_manager.client()
            self._kernel_client.start_channels()
            self._kernel_client.wait_for_ready(timeout=60)
            self._wrapped_kernel_name = kernel_name
            
            # Update language info from wrapped kernel
            kernel_spec = available_kernels[kernel_name].get('spec', {})
            self.language = kernel_spec.get('language', 'python')
            self.language_info = {
                'name': self.language,
                'mimetype': f'text/x-{self.language}',
                'file_extension': kernel_spec.get('file_extension', '.txt'),
            }
            
            success_msg = f"Successfully wrapped kernel: {kernel_name}\n"
            self.send_response(self.iopub_socket, 'stream', {'name': 'stdout', 'text': success_msg})
            
            return {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
            }
        except Exception as e:
            error_msg = f"Failed to start kernel '{kernel_name}': {str(e)}"
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': error_msg})
            return {
                'status': 'error',
                'ename': type(e).__name__,
                'evalue': str(e),
                'traceback': [error_msg],
                'execution_count': self.execution_count,
            }
    
    def _shutdown_wrapped_kernel(self):
        """Shutdown the currently wrapped kernel."""
        if self._kernel_client is not None:
            self._kernel_client.stop_channels()
            self._kernel_client = None
        
        if self._kernel_manager is not None:
            self._kernel_manager.shutdown_kernel(now=True)
            self._kernel_manager = None
        
        self._wrapped_kernel_name = None
    
    def _trigger_pre_run_cell(self, code, silent, store_history):
        """Trigger pre_run_cell event for jumper-extension hooks."""
        info = ExecutionInfo(
            raw_cell=code,
            store_history=store_history,
            silent=silent,
            shell_futures=True,
            cell_id=None
        )
        self.shell.events.trigger('pre_run_cell', info)
        return info
    
    def _trigger_post_run_cell(self, info, success=True, result_value=None, error=None):
        """Trigger post_run_cell event for jumper-extension hooks."""
        exec_result = ExecutionResult(info)
        exec_result.result = result_value
        if error:
            exec_result.error_in_exec = error
        self.shell.events.trigger('post_run_cell', exec_result)
        return exec_result
    
    def _forward_to_wrapped_kernel(self, code, silent, store_history, user_expressions, allow_stdin):
        """Forward code execution to the wrapped kernel."""
        if self._kernel_client is None:
            error_msg = "No kernel is currently wrapped. Use %wrap_kernel <kernel_name> to wrap a kernel."
            self.send_response(self.iopub_socket, 'stream', {'name': 'stderr', 'text': error_msg})
            return {
                'status': 'error',
                'ename': 'RuntimeError',
                'evalue': 'No wrapped kernel',
                'traceback': [error_msg],
                'execution_count': self.execution_count,
            }
        
        # Trigger pre_run_cell event for jumper-extension
        exec_info = self._trigger_pre_run_cell(code, silent, store_history)
        
        # Execute on wrapped kernel
        msg_id = self._kernel_client.execute(
            code,
            silent=silent,
            store_history=store_history,
            user_expressions=user_expressions,
            allow_stdin=allow_stdin,
        )
        
        # Process messages from the wrapped kernel
        execution_error = None
        while True:
            try:
                msg = self._kernel_client.get_iopub_msg(timeout=30)
                msg_type = msg['header']['msg_type']
                content = msg['content']
                
                if msg_type == 'status':
                    if content.get('execution_state') == 'idle':
                        break
                elif msg_type == 'error':
                    execution_error = Exception(content.get('evalue', 'Unknown error'))
                    self.send_response(self.iopub_socket, msg_type, content)
                elif msg_type in ('stream', 'display_data', 'execute_result'):
                    self.send_response(self.iopub_socket, msg_type, content)
                    
            except Exception:
                break
        
        # Get the reply
        try:
            reply = self._kernel_client.get_shell_msg(timeout=30)
            result = reply['content']
        except Exception as e:
            execution_error = e
            result = {
                'status': 'error',
                'ename': type(e).__name__,
                'evalue': str(e),
                'traceback': [str(e)],
                'execution_count': self.execution_count,
            }
        
        # Trigger post_run_cell event for jumper-extension
        self._trigger_post_run_cell(
            exec_info,
            success=(result.get('status') == 'ok'),
            error=execution_error
        )
        
        return result
    
    def _execute_local_magic(self, code):
        """Execute a magic command locally using IPython."""
        try:
            result = self.shell.run_cell(code)
            
            if result.success:
                if result.result is not None:
                    self.send_response(self.iopub_socket, 'stream', 
                                      {'name': 'stdout', 'text': str(result.result) + '\n'})
                return {
                    'status': 'ok',
                    'execution_count': self.execution_count,
                    'payload': [],
                    'user_expressions': {},
                }
            else:
                error_info = result.error_in_exec or result.error_before_exec
                if error_info:
                    return {
                        'status': 'error',
                        'ename': type(error_info).__name__,
                        'evalue': str(error_info),
                        'traceback': [str(error_info)],
                        'execution_count': self.execution_count,
                    }
                return {
                    'status': 'error',
                    'ename': 'Error',
                    'evalue': 'Unknown error',
                    'traceback': [],
                    'execution_count': self.execution_count,
                }
        except Exception as e:
            return {
                'status': 'error',
                'ename': type(e).__name__,
                'evalue': str(e),
                'traceback': [str(e)],
                'execution_count': self.execution_count,
            }
    
    def _is_local_magic(self, code):
        """Check if code is a magic command that should be executed locally."""
        return is_local_magic_cell(code, self._get_local_magics())
    
    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):
        """Execute code - either locally or forwarded to wrapped kernel."""
        user_expressions = user_expressions or {}
        
        # Check for local magic commands (wrapper + jumper) - execute locally
        if self._is_local_magic(code):
            return self._execute_local_magic(code)
        
        # Forward everything else to the wrapped kernel
        return self._forward_to_wrapped_kernel(code, silent, store_history, user_expressions, allow_stdin)
    
    def do_shutdown(self, restart):
        """Shutdown the kernel."""
        self._shutdown_wrapped_kernel()
        return {'status': 'ok', 'restart': restart}
    
    def do_complete(self, code, cursor_pos):
        """Handle code completion - forward to wrapped kernel if available."""
        if self._kernel_client is not None:
            msg_id = self._kernel_client.complete(code, cursor_pos)
            try:
                reply = self._kernel_client.get_shell_msg(timeout=10)
                return reply['content']
            except Exception:
                pass
        
        return {
            'status': 'ok',
            'matches': [],
            'cursor_start': cursor_pos,
            'cursor_end': cursor_pos,
            'metadata': {},
        }
    
    def do_inspect(self, code, cursor_pos, detail_level=0):
        """Handle object inspection - forward to wrapped kernel if available."""
        if self._kernel_client is not None:
            msg_id = self._kernel_client.inspect(code, cursor_pos, detail_level)
            try:
                reply = self._kernel_client.get_shell_msg(timeout=10)
                return reply['content']
            except Exception:
                pass
        
        return {
            'status': 'ok',
            'found': False,
            'data': {},
            'metadata': {},
        }


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=JumperWrapperKernel)
