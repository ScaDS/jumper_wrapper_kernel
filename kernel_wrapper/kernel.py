"""Main kernel wrapper implementation with jumper_extension support."""

import re
from queue import Queue, Empty
from threading import Thread
from ipykernel.ipkernel import IPythonKernel
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager


class WrapperKernel(IPythonKernel):
    """A Jupyter kernel that can wrap and forward to other kernels with jumper_extension support."""
    
    implementation = 'KernelWrapper'
    implementation_version = '0.4.0'
    
    banner = "Kernel Wrapper - Use %wrap <kernel_name> to wrap another kernel\nJumper extensions are loaded and available."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wrapped_kernel_manager = None
        self.wrapped_kernel_client = None
        self.wrapped_kernel_name = None
        self.wrapped_kernel_spec = None
        self._load_jumper_extension()
    
    def _load_jumper_extension(self):
        """Load jumper_extension as an IPython extension."""
        try:
            # Load the jumper extension using IPython's extension mechanism
            self.shell.extension_manager.load_extension('jumper_extension')
            self.log.info("jumper_extension loaded successfully")
        except Exception as e:
            self.log.error(f"Failed to load jumper_extension: {str(e)}")
            self.log.error("Jumper magics will not be available.")
    
    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        """Execute code or magic commands with jumper_extension support."""
        
        if not silent:
            # Check for %wrap magic command first
            wrap_match = re.match(r'^\s*%wrap\s+(\S+)\s*$', code.strip())
            
            if wrap_match:
                kernel_name = wrap_match.group(1)
                return self._wrap_kernel(kernel_name)
            
            # If we have a wrapped kernel, check if this is a magic command
            if self.wrapped_kernel_manager and self.wrapped_kernel_client:
                # Check if code contains a magic command that should be handled by wrapper
                if self._is_wrapper_magic(code):
                    # Execute in wrapper's IPython shell (handles magics)
                    return super().do_execute(code, silent, store_history, user_expressions, allow_stdin)
                else:
                    # Forward to wrapped kernel
                    return self._forward_to_wrapped_kernel(code, allow_stdin)
            else:
                # No kernel wrapped yet - execute in the wrapper's IPython shell
                # This allows jumper magics to work before wrapping a kernel
                return super().do_execute(code, silent, store_history, user_expressions, allow_stdin)
        
        return {
            'status': 'ok',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }
    
    def _is_wrapper_magic(self, code):
        """Check if code contains a magic command available in the wrapper kernel."""
        code_stripped = code.strip()
        
        # Check for line magic (% or %%)
        line_magic_match = re.match(r'^\s*%{1,2}([a-zA-Z0-9_]+)', code_stripped)
        if not line_magic_match:
            return False
        
        magic_name = line_magic_match.group(1)
        is_cell_magic = code_stripped.startswith('%%')
        
        # Check if this magic is available in the wrapper's IPython shell
        if is_cell_magic:
            # Check for cell magics
            return magic_name in self.shell.magics_manager.magics['cell']
        else:
            # Check for line magics
            return magic_name in self.shell.magics_manager.magics['line']
    
    def _list_available_kernels(self):
        """List all available kernels on the system."""
        ksm = KernelSpecManager()
        specs = ksm.get_all_specs()
        
        result = []
        for name, spec in specs.items():
            if name != 'kernel_wrapper':  # Don't list ourselves
                display_name = spec['spec'].get('display_name', name)
                result.append(f"  - {name}: {display_name}")
        
        return '\n'.join(result) if result else "  (none found)"
    
    def _wrap_kernel(self, kernel_name):
        """Wrap another kernel."""
        # Clean up existing wrapped kernel if any
        if self.wrapped_kernel_manager:
            self._cleanup_wrapped_kernel()
        
        # Check if kernel exists
        ksm = KernelSpecManager()
        try:
            spec = ksm.get_kernel_spec(kernel_name)
        except Exception as e:
            self.send_response(
                self.iopub_socket,
                'stream',
                {
                    'name': 'stderr',
                    'text': (f'Error: Kernel "{kernel_name}" not found.\n'
                           f'Available kernels:\n{self._list_available_kernels()}\n')
                }
            )
            return {
                'status': 'error',
                'execution_count': self.execution_count,
                'ename': 'KernelNotFound',
                'evalue': str(e),
                'traceback': []
            }
        
        # Start the wrapped kernel
        try:
            self.wrapped_kernel_manager = KernelManager(kernel_name=kernel_name)
            self.wrapped_kernel_manager.start_kernel()
            self.wrapped_kernel_client = self.wrapped_kernel_manager.client()
            self.wrapped_kernel_client.start_channels()
            self.wrapped_kernel_client.wait_for_ready(timeout=30)
            self.wrapped_kernel_name = kernel_name
            self.wrapped_kernel_spec = spec
            
            # Update language info for syntax highlighting
            self._update_language_info(spec)
            
            # Initialize jumper extensions in the wrapped kernel if it's a Python kernel
            self._initialize_wrapped_jumper_extensions()
            
            self.send_response(
                self.iopub_socket,
                'stream',
                {
                    'name': 'stdout',
                    'text': (f'Successfully wrapped kernel: {kernel_name} ({spec.display_name})\n'
                           f'Language: {self.language}\n'
                           f'Syntax highlighting updated for {self.language}.\n'
                           f'All subsequent code will be executed in the wrapped kernel.\n'
                           f'Jumper extensions are available in the wrapper kernel.\n')
                }
            )
            
            return {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
            }
            
        except Exception as e:
            self.send_response(
                self.iopub_socket,
                'stream',
                {
                    'name': 'stderr',
                    'text': f'Error starting kernel "{kernel_name}": {str(e)}\n'
                }
            )
            return {
                'status': 'error',
                'execution_count': self.execution_count,
                'ename': 'KernelStartError',
                'evalue': str(e),
                'traceback': []
            }
    
    def _initialize_wrapped_jumper_extensions(self):
        """Initialize jumper extensions in the wrapped kernel if possible."""
        if not self.wrapped_kernel_client:
            return
        
        # Only try to initialize jumper extensions for Python kernels
        if 'python' in self.wrapped_kernel_name.lower():
            init_code = """
try:
    get_ipython().extension_manager.load_extension('jumper_extension')
    print("Jumper extensions initialized in wrapped kernel.")
except Exception as e:
    print(f"Note: Could not load jumper_extension in wrapped kernel: {e}")
"""
            try:
                self.wrapped_kernel_client.execute(init_code, store_history=False, silent=False)
            except Exception as e:
                self.log.warning(f"Failed to initialize jumper extensions in wrapped kernel: {e}")
    
    def _update_language_info(self, spec):
        """Update language info based on wrapped kernel spec for syntax highlighting."""
        # Get language from spec
        language = spec.language if hasattr(spec, 'language') and spec.language else 'text'
        
        # Update the kernel's language attribute
        self.language = language
        
        # Build comprehensive language_info dictionary
        language_info = {
            'name': language,
        }
        
        # Language-specific configurations for syntax highlighting
        lang_configs = {
            'python': {
                'mimetype': 'text/x-python',
                'file_extension': '.py',
                'pygments_lexer': 'ipython3',
                'codemirror_mode': {'name': 'ipython', 'version': 3},
                'nbconvert_exporter': 'python',
            },
            'r': {
                'mimetype': 'text/x-r',
                'file_extension': '.r',
                'pygments_lexer': 'r',
                'codemirror_mode': 'r',
            },
            'julia': {
                'mimetype': 'text/x-julia',
                'file_extension': '.jl',
                'pygments_lexer': 'julia',
                'codemirror_mode': 'julia',
            },
            'javascript': {
                'mimetype': 'application/javascript',
                'file_extension': '.js',
                'pygments_lexer': 'javascript',
                'codemirror_mode': 'javascript',
            },
            'scala': {
                'mimetype': 'text/x-scala',
                'file_extension': '.scala',
                'pygments_lexer': 'scala',
                'codemirror_mode': 'text/x-scala',
            },
            'bash': {
                'mimetype': 'text/x-sh',
                'file_extension': '.sh',
                'pygments_lexer': 'bash',
                'codemirror_mode': 'shell',
            },
        }
        
        # Apply language-specific configuration
        if language.lower() in lang_configs:
            language_info.update(lang_configs[language.lower()])
        else:
            # Generic fallback
            language_info.update({
                'mimetype': f'text/x-{language}',
                'file_extension': f'.{language}',
                'pygments_lexer': language,
                'codemirror_mode': language,
            })
        
        # Update the kernel's language_info
        self.language_info = language_info
        
        self.log.info(f"Updated language info for syntax highlighting: {language}")
    
    def _forward_to_wrapped_kernel(self, code, allow_stdin):
        """Forward code execution to the wrapped kernel."""
        try:
            # Send execution request to wrapped kernel
            msg_id = self.wrapped_kernel_client.execute(code, allow_stdin=allow_stdin)
            
            # Wait for execution to complete and forward all messages
            while True:
                try:
                    # Check for messages from wrapped kernel
                    msg = self.wrapped_kernel_client.get_iopub_msg(timeout=0.1)
                    
                    if msg['parent_header'].get('msg_id') == msg_id:
                        msg_type = msg['header']['msg_type']
                        content = msg['content']
                        
                        # Forward the message to our iopub socket
                        if msg_type in ['stream', 'display_data', 'execute_result', 'error']:
                            self.send_response(self.iopub_socket, msg_type, content)
                        
                        # Check if execution is complete
                        if msg_type == 'status' and content.get('execution_state') == 'idle':
                            break
                            
                except Empty:
                    # Check if kernel is still alive
                    if not self.wrapped_kernel_manager.is_alive():
                        raise Exception("Wrapped kernel died unexpectedly")
                    continue
                except Exception as e:
                    if "Kernel died" in str(e) or not self.wrapped_kernel_manager.is_alive():
                        raise
                    continue
            
            # Get the execution reply
            reply = self.wrapped_kernel_client.get_shell_msg(timeout=1.0)
            reply_content = reply['content']
            
            return {
                'status': reply_content.get('status', 'ok'),
                'execution_count': self.execution_count,
                'payload': reply_content.get('payload', []),
                'user_expressions': reply_content.get('user_expressions', {}),
            }
            
        except Exception as e:
            self.send_response(
                self.iopub_socket,
                'stream',
                {
                    'name': 'stderr',
                    'text': f'Error communicating with wrapped kernel: {str(e)}\n'
                }
            )
            return {
                'status': 'error',
                'execution_count': self.execution_count,
                'ename': 'WrapperError',
                'evalue': str(e),
                'traceback': []
            }
    
    def _cleanup_wrapped_kernel(self):
        """Clean up the wrapped kernel."""
        if self.wrapped_kernel_client:
            try:
                self.wrapped_kernel_client.stop_channels()
            except:
                pass
            self.wrapped_kernel_client = None
        
        if self.wrapped_kernel_manager:
            try:
                self.wrapped_kernel_manager.shutdown_kernel(now=True)
            except:
                pass
            self.wrapped_kernel_manager = None
        
        self.wrapped_kernel_name = None
    
    def do_shutdown(self, restart):
        """Shutdown the kernel and any wrapped kernel."""
        self._cleanup_wrapped_kernel()
        return super().do_shutdown(restart)


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=WrapperKernel)
