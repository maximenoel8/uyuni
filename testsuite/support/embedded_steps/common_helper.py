from support.remote_nodes_env import get_target


def run_command_on_host(cmd: str, host: str):
    """Run a command on a host, asserting success."""
    node = get_target(host)
    return node.run(cmd)


def run_command_on_host_no_check(cmd: str, host: str):
    """Run a command on a host without checking exit code."""
    node = get_target(host)
    return node.run(cmd, check_errors=False)


def check_command_on_host(cmd: str, host: str) -> bool:
    """Return True if command exits 0 on host, False otherwise."""
    node = get_target(host)
    _out, code = node.run(cmd, check_errors=False)
    return code == 0
