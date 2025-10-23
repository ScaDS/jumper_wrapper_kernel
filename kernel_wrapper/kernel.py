"""Main kernel wrapper implementation."""

import json
import re
from queue import Queue, Empty
from threading import Thread
from ipykernel.kernelbase import Kernel
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager


class WrapperKernel(Kernel):
    """A Jupyter kernel that can wrap and forward to other kernels."""
    
    implementation = 'KernelWrapper'
    implementation_version = '0.1.0'
    language = 'text'
    language_version = '0.1'
    language_info = {
        'name': 'text',
        'mimetype': 'text/plain',
        'file_extension': '.txt',
    }
    banner = "Kernel Wrapper - Use %wrap <kernel_name> to wrap another kernel"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wrapped_kernel_manager = None
        self.wrapped_kernel_client = None
        self.wrapped_kernel_name = None
        self.message_queue = Queue()
        self.listener_thread = None
        
    def do_execute(self, code, silent, store_history=True, user_expressions=None,
                   allow_stdin=False):
        """Execute code or magic commands."""
        
        if not silent:
            # Check for %wrap magic command
            wrap_match = re.match(r'^\s*%wrap\s+(\S+)\s*$', code.strip())
            
            if wrap_match:
                kernel_name = wrap_match.group(1)
                return self._wrap_kernel(kernel_name)
            
            # If we have a wrapped kernel, forward the code to it
            if self.wrapped_kernel_manager and self.wrapped_kernel_client:
                return self._forward_to_wrapped_kernel(code, allow_stdin)
            else:
                # No kernel wrapped yet
                self.send_response(
                    self.iopub_socket,
                    'stream',
                    {
                        'name': 'stdout',
                        'text': 'No kernel wrapped yet. Use %wrap <kernel_name> to wrap a kernel.\n'
                               'Available kernels:\n' + self._list_available_kernels()
                    }
                )
        
        return {
            'status': 'ok',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }
    
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
                    'text': f'Error: Kernel "{kernel_name}" not found.\n'
                           f'Available kernels:\n{self._list_available_kernels()}\n'
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
            
            # Update language info based on wrapped kernel
            self._update_language_info(spec)
            
            # Start listener thread for wrapped kernel messages
            self.listener_thread = Thread(target=self._listen_to_wrapped_kernel, daemon=True)
            self.listener_thread.start()
            
            self.send_response(
                self.iopub_socket,
                'stream',
                {
                    'name': 'stdout',
                    'text': f'Successfully wrapped kernel: {kernel_name} ({spec.display_name})\n'
                           f'All subsequent code will be executed in the wrapped kernel.\n'
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
    
    def _update_language_info(self, spec):
        """Update language info based on wrapped kernel spec."""
        if spec.language:
            self.language = spec.language
            self.language_info['name'] = spec.language
            
            # Set common file extensions and mimetypes
            lang_map = {
                'python': {'mimetype': 'text/x-python', 'file_extension': '.py'},
                'r': {'mimetype': 'text/x-r', 'file_extension': '.r'},
                'julia': {'mimetype': 'text/x-julia', 'file_extension': '.jl'},
                'javascript': {'mimetype': 'application/javascript', 'file_extension': '.js'},
            }
            
            if spec.language in lang_map:
                self.language_info.update(lang_map[spec.language])
    
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
    
    def _listen_to_wrapped_kernel(self):
        """Listen for messages from wrapped kernel (for async updates)."""
        # This thread can be used to handle asynchronous messages from the wrapped kernel
        # For now, we handle messages synchronously in _forward_to_wrapped_kernel
        pass
    
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
        return {'status': 'ok', 'restart': restart}


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=WrapperKernel)
