# Intersect Engine Auto Reboot Tool

Automatically reboots the Intersect server at scheduled times with configurable announcements.

## Features

- **Scheduled Reboots**: Configure multiple daily reboot times
- **Pre-Reboot Announcements**: Automatically sends announcements at configurable intervals before reboot
- **Graceful Shutdown**: Sends `exit` command to server for clean shutdown
- **Automatic Restart**: Waits a configurable time after shutdown before restarting
- **Logging**: Comprehensive logging to both file and console

## Configuration

Edit `reboot_config.json` to configure the tool:

```json
{
  "server_path": "C:\\PATH_TO_INTERSECT\\Intersect Server.exe",
  "server_args": [],
  "reboot_schedule": [
    {
      "hour": 4,
      "minute": 0,
      "enabled": true
    },
    {
      "hour": 12,
      "minute": 0,
      "enabled": true
    },
    {
      "hour": 20,
      "minute": 0,
      "enabled": true
    }
  ],
  "announcement_intervals": [
    {
      "minutes_before": 10,
      "message": "The server will reboot in {minutes} minutes"
    },
    {
      "minutes_before": 5,
      "message": "The server will reboot in {minutes} minutes"
    },
    {
      "minutes_before": 2,
      "message": "The server will reboot in {minutes} minutes"
    },
    {
      "minutes_before": 1,
      "message": "The server will reboot in {minutes} minute"
    },
    {
      "seconds_before": 30,
      "message": "The server will reboot in {seconds} seconds"
    },
    {
      "seconds_before": 10,
      "message": "The server will reboot in {seconds} seconds"
    },
    {
      "seconds_before": 2,
      "message": "Rebooting"
    }
  ],
  "restart_delay_seconds": 120,
  "log_file": "reboot_tool.log"
}
```

### Configuration Options

- **server_path**: Path to the server executable (relative or absolute). Use double backslashes (`\\`) for Windows paths.
- **server_args**: Additional command-line arguments to pass to the server (array of strings)
- **reboot_schedule**: Array of reboot times
  - **hour**: Hour of day (0-23)
  - **minute**: Minute of hour (0-59)
  - **enabled**: Whether this reboot time is active (default: true)
- **announcement_intervals**: Array of announcement times before reboot
  - **minutes_before**: Minutes before reboot to send announcement (use `{minutes}` placeholder in message)
  - **seconds_before**: Seconds before reboot to send announcement (use `{seconds}` placeholder in message)
  - **message**: Message to send. Supports `{minutes}` or `{seconds}` placeholders, or plain text
  - You can mix both `minutes_before` and `seconds_before` in the same configuration
- **restart_delay_seconds**: Seconds to wait after server exits before restarting (default: 120)
- **log_file**: Path to log file (default: `reboot_tool.log`)

## Usage

### Basic Usage

```bash
python auto_reboot_tool.py
```

### With Custom Config

```bash
python auto_reboot_tool.py --config my_config.json
```

### Windows

Use the provided batch file:
```batch
run_auto_reboot_tool.bat
```

### Linux/Mac

Use the provided shell script:
```bash
./run_auto_reboot_tool.sh
```

## How It Works

1. The tool starts the server process using `subprocess.Popen`
2. It monitors the current time and calculates the next scheduled reboot
3. At configured intervals before reboot, it sends announcement commands via stdin
4. At reboot time, it sends the `exit` command to gracefully shutdown the server
5. After the server exits, it waits the configured delay time
6. The server is automatically restarted and the cycle repeats

## Commands Sent to Server

The tool sends the following commands to the server's console via stdin:

- `announcement "The server will reboot in X minutes"` - Sent at configured intervals (minutes)
- `announcement "The server will reboot in X seconds"` - Sent at configured intervals (seconds)
- `announcement "Rebooting"` - Sent just before reboot (customizable)
- `exit` - Sent at reboot time to gracefully shutdown the server

All commands are sent to the server's stdin, allowing the tool to control the server process programmatically.

## Logging

Logs are written to both:
- Console (stdout)
- Log file (default: `reboot_tool.log`)

Log entries include timestamps and log levels (INFO, WARNING, ERROR).

## Requirements

- Python 3.6 or higher
- No additional dependencies (uses only standard library)

## Troubleshooting

### Server Not Starting

- **Port Already in Use**: The most common issue is port 5400 (or your configured port) being in use. The tool will automatically detect this and show error messages from server logs.
  - Solution: Stop any existing server instances or change the port in server configuration
- **Path Issues**: Check that `server_path` in config points to the correct executable
  - Use absolute paths with double backslashes on Windows: `C:\\Path\\To\\Server.exe`
  - Verify the server executable has proper permissions
- **Working Directory**: The tool automatically sets the working directory to the server's directory, ensuring config files and resources are found correctly
- **Error Detection**: The tool reads server log files and displays relevant error messages automatically

### Commands Not Being Sent

- Ensure the server process is running and accepting stdin
- Check that the server console is not redirected elsewhere
- Review log file for command sending errors
- The tool primes stdin immediately after starting the server to prevent early exit

### Server Not Exiting

- The tool will wait up to 60 seconds for graceful shutdown
- If the server doesn't exit, it will be terminated forcefully after the timeout
- Check server logs for any issues preventing shutdown
- The tool automatically handles process cleanup and restart

## Notes

- The tool runs continuously until stopped (Ctrl+C)
- Reboot times are calculated daily (if a time has passed today, it schedules for tomorrow)
- The tool automatically restarts the server if it crashes or exits unexpectedly
- All times are in the system's local timezone
- Announcements support both minute and second precision for flexible warning schedules
- The tool handles Windows executable paths with spaces automatically
- Server stdout/stderr are not piped, allowing the server to use its own console window
- The tool includes automatic error detection by reading server log files


