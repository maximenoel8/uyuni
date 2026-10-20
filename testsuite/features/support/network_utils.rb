# Copyright (c) 2026 SUSE LLC.
# Licensed under the terms of the MIT license.

require 'net/scp'
require 'net/ssh'
require 'stringio'

# This method is used to execute a command on a remote host using SSH and return the output of the command.
#
# @param [String] command The command to execute on the remote host.
# @param [String] host The hostname or IP address of the remote host.
# @param [Integer] port The port to connect to on the remote host.
# @param [Integer] timeout The timeout to use when connecting to the remote host.
# @param [Integer] buffer_size The buffer size to use when connecting to the remote host.
# @return [Array] An array containing the stdout, stderr, and exit code of the command.
def ssh_command(command, host, port: 22, timeout: DEFAULT_TIMEOUT, buffer_size: 65_536)
  stdout = ''
  stderr = ''
  exit_code = -1
  # Do not wait past the whole-run deadline (see RUN_HARD_LIMIT in env.rb), but always leave a command (e.g. the
  # mgrctl calls of the After hooks) the time to complete. Not defined when loaded from the Rakefile, outside Cucumber
  timeout = [run_time_left, 30].max.clamp(..timeout) if defined?(RUN_HARD_LIMIT) && RUN_HARD_LIMIT.positive?
  begin
    Timeout.timeout(timeout) do # Enforce timeout on the entire SSH operation
      Net::SSH.start(host, nil, port: port, verify_host_key: :never, timeout: timeout, keepalive: true, max_pkt_size: buffer_size, config: true) do |ssh|
        stdout, stderr, exit_code = ssh_exec!(ssh, command, timeout: timeout)
      end
    end
  rescue Timeout::Error
    puts "SSH operation timed out after #{timeout} seconds."
  rescue Net::SSH::ConnectionTimeout, Errno::ECONNREFUSED, Errno::EHOSTUNREACH, Errno::ECONNRESET
    puts "Unable to reach the SSH server at #{host}:#{port}"
  rescue Net::SSH::AuthenticationFailed
    puts "Authentication failed for user #{user} on #{host}"
  end

  [stdout, stderr, exit_code]
end

# This method is used to upload a file on a remote host from the test-runner (aka controller) using SCP and return the output of the command.
#
# @param [String] local_path The path to the file to be uploaded.
# @param [String] remote_path The path to the destination file.
# @param [String] host The hostname or IP address of the remote host.
# @param [Integer] port The port to connect to on the remote host.
# @param [Integer] timeout The timeout to use when connecting to the remote host.
# @param [Integer] buffer_size The buffer size to use when connecting to the remote host.
def scp_upload_command(local_path, remote_path, host, port: 22, timeout: DEFAULT_TIMEOUT, buffer_size: 65_536)
  begin
    Net::SSH.start(host, nil, port: port, verify_host_key: :never, keepalive: true, timeout: timeout, max_pkt_size: buffer_size, config: true) do |ssh|
      ssh.scp.upload! local_path, remote_path
    end
  rescue Net::SSH::ConnectionTimeout, Errno::ECONNREFUSED
    # The connection times out or is refused
  end
end

# This method is used to download a file from a remote host to the test-runner (aka controller) using SCP and return the output of the command.

# @param [String] remote_path The path of the file to be downloaded.
# @param [String] local_path The path to the destination file.
# @param [String] host The hostname or IP address of the remote host.
# @param [Integer] port The port to connect to on the remote host.
# @param [Integer] timeout The timeout to use when connecting to the remote host.
# @param [Integer] buffer_size The buffer size to use when connecting to the remote host.
def scp_download_command(remote_path, local_path, host, port: 22, timeout: DEFAULT_TIMEOUT, buffer_size: 65_536)
  begin
    Net::SSH.start(host, nil, port: port, verify_host_key: :never, keepalive: true, timeout: timeout, max_pkt_size: buffer_size, config: true) do |ssh|
      ssh.scp.download! remote_path, local_path
    end
  rescue Net::SSH::ConnectionTimeout, Errno::ECONNREFUSED
    # The connection times out or is refused
  end
end

# This helper method executes a command on an SSH session and returns the output.
# It's an internal helper used by ssh_command.
#
# @param [Net::SSH::Connection::Session] ssh The SSH session object.
# @param [String] command The command to execute on the remote host.
# @param [Integer] timeout The timeout to use when waiting for the command to complete.
# @return [Array] An array containing the stdout, stderr, and exit code of the command.
def ssh_exec!(ssh, command, timeout: 10)
  stdout = ''
  stderr = ''
  exit_code = -1

  ssh.open_channel do |channel|
    channel.exec(command) do |_ch, success|
      raise SystemCallError, 'FAILED: could not execute command (ssh.channel.exec)' unless success

      channel.on_data do |_ch, data|
        stdout += data
      end

      channel.on_extended_data do |_ch, _type, data|
        stderr += data
      end

      channel.on_request('exit-status') do |_ch, data|
        exit_code = data.read_long
      end
    end

    Timeout.timeout(timeout) do
      channel.wait
    end
  end

  begin
    ssh.loop
  rescue IOError
    puts "The remote node #{ssh.host} has been disconnected."
  rescue Net::SSH::Disconnect
    puts 'The SSH session was unexpectedly terminated.'
  end

  [stdout, stderr, exit_code]
end
