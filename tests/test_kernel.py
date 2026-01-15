"""Tests for JumperWrapperKernel."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


def _create_kernel_with_mock_shell(mock_shell):
    """Helper to create kernel instance bypassing traitlet validation.

    Returns a context manager that patches shell property and yields kernel.
    Use with 'with' statement to ensure proper cleanup.
    """
    from jumper_wrapper_kernel.kernel import JumperWrapperKernel

    class KernelContext:
        def __init__(self):
            self.kernel = None
            self._patcher = None

        def __enter__(self):
            with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
                self.kernel = JumperWrapperKernel()
            self._patcher = patch.object(
                type(self.kernel), 'shell',
                new_callable=PropertyMock,
                return_value=mock_shell
            )
            self._patcher.start()
            return self.kernel

        def __exit__(self, *args):
            self._patcher.stop()

    return KernelContext()


class TestRegisterWrapperMagics:
    """Tests for _register_wrapper_magics method."""

    def test_captures_new_magics_as_wrapper_commands(self, mock_shell):
        """Should capture difference in magics as wrapper commands."""
        # Track call count to return different values
        call_count = [0]
        magics_before = {'time', 'timeit'}
        magics_after = {'time', 'timeit', 'list_kernels', 'wrap_kernel'}

        def mock_get_all_magics():
            call_count[0] += 1
            if call_count[0] == 1:
                return magics_before.copy()
            return magics_after.copy()

        with _create_kernel_with_mock_shell(mock_shell) as kernel:
            kernel._wrapper_magic_commands = set()
            kernel._get_all_magics = mock_get_all_magics

            # Patch JumperWrapperMagics to avoid traitlet validation
            with patch('jumper_wrapper_kernel.kernel.JumperWrapperMagics'):
                kernel._register_wrapper_magics()

            # Verify wrapper magics captured correctly
            assert kernel._wrapper_magic_commands == {'list_kernels', 'wrap_kernel'}


class TestGetLocalMagics:
    """Tests for _get_local_magics method."""

    def test_returns_union_of_jumper_and_wrapper_magics(
        self, jumper_magics, wrapper_magics
    ):
        """Should return union of jumper and wrapper magic commands."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._jumper_magic_commands = jumper_magics
            kernel._wrapper_magic_commands = wrapper_magics

        result = kernel._get_local_magics()

        assert result == jumper_magics | wrapper_magics


class TestListKernels:
    """Tests for _list_kernels method."""

    def test_lists_available_kernels(
        self, mock_kernel_spec_manager, mock_kernel_specs, mock_iopub_socket
    ):
        """Should list all available kernels."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._kernel_spec_manager = mock_kernel_spec_manager
            kernel._wrapped_kernel_name = None
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1

        result = kernel._list_kernels()

        assert result['status'] == 'ok'
        kernel.send_response.assert_called_once()

        # Verify output contains kernel names
        call_args = kernel.send_response.call_args
        output_text = call_args[0][2]['text']
        assert 'python3' in output_text
        assert 'ir' in output_text
        assert 'julia-1.9' in output_text

    def test_shows_currently_wrapped_kernel(
        self, mock_kernel_spec_manager, mock_iopub_socket
    ):
        """Should show currently wrapped kernel if any."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._kernel_spec_manager = mock_kernel_spec_manager
            kernel._wrapped_kernel_name = 'python3'
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1

        kernel._list_kernels()

        call_args = kernel.send_response.call_args
        output_text = call_args[0][2]['text']
        assert 'Currently wrapped kernel: python3' in output_text


class TestWrapKernel:
    """Tests for _wrap_kernel method."""

    def test_wrap_kernel_no_name_returns_error(self, mock_iopub_socket):
        """Should return error when no kernel name provided."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1

        result = kernel._wrap_kernel('')

        assert result['status'] == 'error'
        assert result['ename'] == 'ValueError'

    def test_wrap_kernel_not_found_returns_error(
        self, mock_kernel_spec_manager, mock_iopub_socket
    ):
        """Should return error when kernel not found."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._kernel_spec_manager = mock_kernel_spec_manager
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1

        result = kernel._wrap_kernel('nonexistent_kernel')

        assert result['status'] == 'error'
        assert 'not found' in result['evalue']

    @patch('jumper_wrapper_kernel.kernel.KernelManager')
    def test_wrap_kernel_success(
        self,
        mock_km_class,
        mock_kernel_spec_manager,
        mock_kernel_manager,
        mock_kernel_client,
        mock_iopub_socket,
    ):
        """Should successfully wrap an existing kernel."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        mock_km_class.return_value = mock_kernel_manager

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._kernel_spec_manager = mock_kernel_spec_manager
            kernel._kernel_manager = None
            kernel._kernel_client = None
            kernel._wrapped_kernel_name = None
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1
            kernel.language = 'python'
            kernel.language_info = {}

        result = kernel._wrap_kernel('python3')

        assert result['status'] == 'ok'
        assert kernel._wrapped_kernel_name == 'python3'
        mock_kernel_manager.start_kernel.assert_called_once()
        mock_kernel_client.start_channels.assert_called_once()

    @patch('jumper_wrapper_kernel.kernel.KernelManager')
    def test_wrap_kernel_shuts_down_existing(
        self,
        mock_km_class,
        mock_kernel_spec_manager,
        mock_kernel_manager,
        mock_kernel_client,
        mock_iopub_socket,
    ):
        """Should shutdown existing wrapped kernel before wrapping new one."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        mock_km_class.return_value = mock_kernel_manager

        old_manager = MagicMock()
        old_client = MagicMock()

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._kernel_spec_manager = mock_kernel_spec_manager
            kernel._kernel_manager = old_manager
            kernel._kernel_client = old_client
            kernel._wrapped_kernel_name = 'ir'
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1
            kernel.language = 'R'
            kernel.language_info = {}

        kernel._wrap_kernel('python3')

        old_client.stop_channels.assert_called_once()
        old_manager.shutdown_kernel.assert_called_once_with(now=True)

    @patch('jumper_wrapper_kernel.kernel.KernelManager')
    def test_wrap_kernel_handles_startup_failure(
        self, mock_km_class, mock_kernel_spec_manager, mock_iopub_socket
    ):
        """Should handle kernel startup failure gracefully."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        mock_km = MagicMock()
        mock_km.start_kernel.side_effect = RuntimeError('Kernel failed to start')
        mock_km_class.return_value = mock_km

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._kernel_spec_manager = mock_kernel_spec_manager
            kernel._kernel_manager = None
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1

        result = kernel._wrap_kernel('python3')

        assert result['status'] == 'error'
        assert result['ename'] == 'RuntimeError'


class TestShutdownWrappedKernel:
    """Tests for _shutdown_wrapped_kernel method."""

    def test_shuts_down_client_and_manager(self):
        """Should stop client channels and shutdown manager."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        mock_client = MagicMock()
        mock_manager = MagicMock()

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._kernel_client = mock_client
            kernel._kernel_manager = mock_manager
            kernel._wrapped_kernel_name = 'python3'

        kernel._shutdown_wrapped_kernel()

        mock_client.stop_channels.assert_called_once()
        mock_manager.shutdown_kernel.assert_called_once_with(now=True)
        assert kernel._kernel_client is None
        assert kernel._kernel_manager is None
        assert kernel._wrapped_kernel_name is None

    def test_handles_no_wrapped_kernel(self):
        """Should handle case when no kernel is wrapped."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._kernel_client = None
            kernel._kernel_manager = None
            kernel._wrapped_kernel_name = None

        # Should not raise
        kernel._shutdown_wrapped_kernel()


class TestIsLocalMagic:
    """Tests for _is_local_magic method."""

    def test_recognizes_local_magic(self):
        """Should recognize local magic commands."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._jumper_magic_commands = {'perfmonitor_start', 'perfmonitor_stop'}
            kernel._wrapper_magic_commands = {'list_kernels', 'wrap_kernel'}

        assert kernel._is_local_magic('%list_kernels') is True
        assert kernel._is_local_magic('%wrap_kernel python3') is True
        assert kernel._is_local_magic('%perfmonitor_start') is True

    def test_rejects_non_local_magic(self):
        """Should reject non-local magic commands."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._jumper_magic_commands = {'perfmonitor_start'}
            kernel._wrapper_magic_commands = {'list_kernels'}

        assert kernel._is_local_magic('%time x = 1') is False
        assert kernel._is_local_magic('print("hello")') is False

    def test_handles_comments_and_empty_lines(self):
        """Should handle cells with comments and empty lines."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._jumper_magic_commands = {'perfmonitor_start'}
            kernel._wrapper_magic_commands = {'list_kernels'}

        code = """
            # This is a comment
            %list_kernels
            # Another comment
        """
        assert kernel._is_local_magic(code) is True


class TestDoExecute:
    """Tests for do_execute method."""

    def test_executes_local_magic_locally(self):
        """Should execute local magic commands locally."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._jumper_magic_commands = set()
            kernel._wrapper_magic_commands = {'list_kernels'}
            kernel._execute_local_magic = MagicMock(return_value={'status': 'ok'})
            kernel._forward_to_wrapped_kernel = MagicMock()

        result = kernel.do_execute('%list_kernels', silent=False)

        kernel._execute_local_magic.assert_called_once_with('%list_kernels')
        kernel._forward_to_wrapped_kernel.assert_not_called()
        assert result['status'] == 'ok'

    def test_forwards_regular_code_to_wrapped_kernel(self):
        """Should forward regular code to wrapped kernel."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._jumper_magic_commands = set()
            kernel._wrapper_magic_commands = {'list_kernels'}
            kernel._execute_local_magic = MagicMock()
            kernel._forward_to_wrapped_kernel = MagicMock(return_value={'status': 'ok'})

        result = kernel.do_execute('print("hello")', silent=False)

        kernel._forward_to_wrapped_kernel.assert_called_once()
        kernel._execute_local_magic.assert_not_called()

    def test_passes_correct_arguments_to_forward(self):
        """Should pass all arguments when forwarding."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._jumper_magic_commands = set()
            kernel._wrapper_magic_commands = set()
            kernel._forward_to_wrapped_kernel = MagicMock(return_value={'status': 'ok'})

        kernel.do_execute(
            'code',
            silent=True,
            store_history=False,
            user_expressions={'a': 'b'},
            allow_stdin=True,
        )

        kernel._forward_to_wrapped_kernel.assert_called_once_with(
            'code', True, False, {'a': 'b'}, True
        )


class TestForwardToWrappedKernel:
    """Tests for _forward_to_wrapped_kernel method."""

    def test_returns_error_when_no_kernel_wrapped(self, mock_iopub_socket):
        """Should return error when no kernel is wrapped."""
        from jumper_wrapper_kernel.kernel import JumperWrapperKernel

        with patch.object(JumperWrapperKernel, '__init__', lambda x: None):
            kernel = JumperWrapperKernel()
            kernel._kernel_client = None
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1

        result = kernel._forward_to_wrapped_kernel('code', False, True, {}, False)

        assert result['status'] == 'error'
        assert result['ename'] == 'RuntimeError'
        assert 'No kernel is currently wrapped' in result['traceback'][0]


class TestExecuteLocalMagic:
    """Tests for _execute_local_magic method."""

    def test_successful_execution(self, mock_shell, mock_iopub_socket):
        """Should execute magic and return ok status."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = None
        mock_shell.run_cell.return_value = mock_result

        with _create_kernel_with_mock_shell(mock_shell) as kernel:
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1

            result = kernel._execute_local_magic('%list_kernels')

            assert result['status'] == 'ok'
            mock_shell.run_cell.assert_called_once_with('%list_kernels')

    def test_sends_result_to_stdout(self, mock_shell, mock_iopub_socket):
        """Should send result to stdout if present."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.result = 'magic output'
        mock_shell.run_cell.return_value = mock_result

        with _create_kernel_with_mock_shell(mock_shell) as kernel:
            kernel.iopub_socket = mock_iopub_socket
            kernel.send_response = MagicMock()
            kernel.execution_count = 1

            kernel._execute_local_magic('%some_magic')

            kernel.send_response.assert_called_once()
            call_args = kernel.send_response.call_args
            assert call_args[0][1] == 'stream'
            assert 'magic output' in call_args[0][2]['text']

    def test_handles_execution_error(self, mock_shell, mock_iopub_socket):
        """Should handle execution errors gracefully."""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_in_exec = ValueError('test error')
        mock_result.error_before_exec = None
        mock_shell.run_cell.return_value = mock_result

        with _create_kernel_with_mock_shell(mock_shell) as kernel:
            kernel.iopub_socket = mock_iopub_socket
            kernel.execution_count = 1

            result = kernel._execute_local_magic('%bad_magic')

            assert result['status'] == 'error'
            assert result['ename'] == 'ValueError'
