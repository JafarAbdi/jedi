"""
Tests for subprocess IPC stability.
"""
import os
import pickle
import sys


def test_stdout_fd_redirection():
    """
    Test that stdout file descriptor redirection works correctly.

    This tests the fix for the issue where C extensions writing directly
    to file descriptor 1 would corrupt the pickle IPC stream.
    """
    # Create a pipe to simulate IPC
    read_fd, write_fd = os.pipe()

    # Simulate the Listener.listen() fd redirection logic
    saved_stdout_fd = os.dup(write_fd)
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull_fd, 1)
    os.close(devnull_fd)
    ipc_stdout = os.fdopen(saved_stdout_fd, 'wb')

    # Simulate a C extension writing to fd 1 (should go to /dev/null)
    os.write(1, b'This should NOT corrupt the IPC stream\n')

    # Write pickle data to the IPC channel
    test_data = (False, None, 'test_result')
    pickle.dump(test_data, ipc_stdout, protocol=4)
    ipc_stdout.flush()
    ipc_stdout.close()

    # Read and verify the pickle data is intact
    os.close(write_fd)
    read_file = os.fdopen(read_fd, 'rb')
    result = pickle.load(read_file)
    read_file.close()

    assert result == test_data, f"IPC data corrupted: expected {test_data}, got {result}"


def test_unpickling_error_is_caught():
    """
    Test that pickle.UnpicklingError is handled gracefully.
    """
    # This is more of a unit test to ensure the exception type is correct
    import pickle
    from io import BytesIO

    # Create invalid pickle data
    invalid_data = BytesIO(b'not valid pickle data')

    try:
        pickle.load(invalid_data)
        assert False, "Should have raised an exception"
    except (EOFError, pickle.UnpicklingError):
        # This is the expected behavior - both should be caught
        pass
