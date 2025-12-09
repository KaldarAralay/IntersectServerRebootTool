"""
Intersect Engine Auto Reboot Tool
Automatically reboots the server at scheduled times with announcements.
"""

import json
import subprocess
import threading
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import sys


class AutoRebootTool:
    """Manages automatic server reboots with scheduled announcements"""
    
    def __init__(self, config_path: str = "reboot_config.json"):
        """Initialize the auto reboot tool with configuration"""
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.server_process: Optional[subprocess.Popen] = None
        self.running = False
        self.reboot_thread: Optional[threading.Thread] = None
        
        # Setup logging
        log_file = self.config.get("log_file", "reboot_tool.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        required_fields = ["server_path", "reboot_schedule", "announcement_intervals", "restart_delay_seconds"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required config field: {field}")
        
        return config
    
    def start_server(self) -> bool:
        """Start the server process"""
        server_path = Path(self.config["server_path"])
        server_args = self.config.get("server_args", [])
        
        if not server_path.exists() and not Path(server_path.name).exists():
            # Try relative to config file
            server_path = self.config_path.parent / server_path
            if not server_path.exists():
                self.logger.error(f"Server executable not found: {self.config['server_path']}")
                return False
        
        try:
            # Get absolute path and working directory
            server_path = server_path.resolve()
            working_dir = server_path.parent
            
            # Use the absolute path
            cmd = [str(server_path)] + server_args
            
            self.logger.info(f"Starting server: {' '.join(cmd)}")
            self.logger.info(f"Working directory: {working_dir}")
            
            # Start process with working directory set to server's directory
            # This is important for .NET apps that need to find their config files
            # Don't pipe stdout/stderr - let server use console directly
            # This prevents the server from detecting it's being run non-interactively
            self.logger.info(f"Starting server in directory: {working_dir}")
            
            # The issue: .NET Console.ReadLine() returns null immediately when stdin is piped
            # This causes the server to exit. We need stdin for commands, so we use a workaround:
            # Start the process and immediately write a newline to stdin to "prime" it
            # This might help prevent the immediate null return
            
            import subprocess as sp
            
            # Quote the executable if it has spaces (Windows)
            if sys.platform == "win32" and ' ' in str(server_path):
                # Use shell=True with quoted path
                cmd_str = f'"{str(server_path)}"'
                if server_args:
                    cmd_str += ' ' + ' '.join(server_args)
                self.server_process = subprocess.Popen(
                    cmd_str,
                    stdin=subprocess.PIPE,
                    stdout=None,
                    stderr=None,
                    text=True,
                    bufsize=1,
                    cwd=str(working_dir),
                    shell=True
                )
            else:
                self.server_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=None,
                    stderr=None,
                    text=True,
                    bufsize=1,
                    cwd=str(working_dir)
                )
            
            # The server's Console.ReadLine() returns null when stdin is piped, causing exit
            # Workaround: Write something to stdin IMMEDIATELY after starting
            # This gives ReadLine() something to read before it returns null
            try:
                if self.server_process.stdin:
                    # Write a comment/empty line immediately to "prime" stdin
                    # The server will ignore empty lines
                    self.server_process.stdin.write('\n')
                    self.server_process.stdin.flush()
                    self.logger.debug("Primed stdin with newline")
            except Exception as e:
                self.logger.warning(f"Could not prime stdin: {e}")
            
            # Give it time to start - but not too long, we want to catch if it exits immediately
            time.sleep(3)
            
            # Check if process is still running
            if self.server_process.poll() is not None:
                return_code = self.server_process.returncode
                self.logger.error(f"Server process exited immediately with code: {return_code}")
                
                # Check server logs for common errors
                log_dir = working_dir / "logs"
                if log_dir.exists():
                    log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
                    if log_files:
                        try:
                            with open(log_files[0], 'r', encoding='utf-8', errors='ignore') as f:
                                # Read last few lines
                                lines = f.readlines()
                                if lines:
                                    last_lines = lines[-10:]
                                    error_found = False
                                    for line in reversed(last_lines):
                                        if 'port' in line.lower() and ('fail' in line.lower() or 'error' in line.lower() or 'listen' in line.lower()):
                                            self.logger.error(f"Server log error: {line.strip()}")
                                            error_found = True
                                            break
                                    if not error_found and 'ERR' in ''.join(last_lines):
                                        # Show any error lines
                                        for line in reversed(last_lines):
                                            if 'ERR' in line:
                                                self.logger.error(f"Server log: {line.strip()}")
                                                break
                        except Exception as e:
                            self.logger.debug(f"Could not read log file: {e}")
                
                self.logger.error("Common issues: Port already in use, missing config files, or database connection problems")
                self.logger.error(f"Check server logs in: {log_dir}")
                
                return False
            
            self.logger.info(f"Server started with PID: {self.server_process.pid}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}", exc_info=True)
            return False
    
    def send_command(self, command: str) -> bool:
        """Send a command to the server's stdin"""
        if not self.server_process or self.server_process.stdin is None:
            self.logger.error("Server process not running or stdin not available")
            return False
        
        try:
            self.logger.info(f"Sending command: {command}")
            self.server_process.stdin.write(command + "\n")
            self.server_process.stdin.flush()
            return True
        except Exception as e:
            self.logger.error(f"Failed to send command '{command}': {e}")
            return False
    
    def wait_for_server_exit(self, timeout: Optional[int] = None) -> bool:
        """Wait for the server process to exit"""
        if not self.server_process:
            return True
        
        try:
            self.server_process.wait(timeout=timeout)
            self.logger.info("Server process exited")
            return True
        except subprocess.TimeoutExpired:
            self.logger.warning("Server did not exit within timeout period")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for server exit: {e}")
            return False
    
    def get_next_reboot_time(self) -> Optional[datetime]:
        """Get the next scheduled reboot time"""
        now = datetime.now()
        reboot_times = []
        
        for schedule in self.config["reboot_schedule"]:
            if not schedule.get("enabled", True):
                continue
            
            hour = schedule["hour"]
            minute = schedule["minute"]
            reboot_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If the time has passed today, schedule for tomorrow
            if reboot_time <= now:
                reboot_time += timedelta(days=1)
            
            reboot_times.append(reboot_time)
        
        if not reboot_times:
            return None
        
        return min(reboot_times)
    
    def schedule_announcements(self, reboot_time: datetime):
        """Schedule and send announcements before reboot"""
        now = datetime.now()
        
        # Sort intervals by time before reboot (convert all to seconds for sorting)
        def get_seconds_before(interval):
            if "seconds_before" in interval:
                return interval["seconds_before"]
            elif "minutes_before" in interval:
                return interval["minutes_before"] * 60
            return 0
        
        announcement_intervals = sorted(
            self.config["announcement_intervals"],
            key=get_seconds_before,
            reverse=True
        )
        
        for interval in announcement_intervals:
            # Calculate time before reboot
            if "seconds_before" in interval:
                seconds_before = interval["seconds_before"]
                announcement_time = reboot_time - timedelta(seconds=seconds_before)
                # Format message with seconds
                if "{seconds}" in interval["message"]:
                    message = interval["message"].format(seconds=seconds_before)
                else:
                    message = interval["message"]
            elif "minutes_before" in interval:
                minutes_before = interval["minutes_before"]
                announcement_time = reboot_time - timedelta(minutes=minutes_before)
                # Format message with minutes
                if "{minutes}" in interval["message"]:
                    message = interval["message"].format(minutes=minutes_before)
                else:
                    message = interval["message"]
            else:
                continue  # Skip invalid intervals
            
            # Only schedule if the announcement time is in the future
            if announcement_time > now:
                wait_seconds = (announcement_time - now).total_seconds()
                
                # Schedule announcement in a separate thread
                threading.Timer(wait_seconds, self.send_command, args=[f'announcement "{message}"']).start()
                self.logger.info(f"Scheduled announcement for {announcement_time}: {message}")
    
    def reboot_cycle(self):
        """Main reboot cycle loop"""
        self.logger.info("Auto reboot tool started")
        
        while self.running:
            try:
                # Start server if not running
                if not self.server_process or self.server_process.poll() is not None:
                    if not self.start_server():
                        self.logger.error("Failed to start server, retrying in 60 seconds...")
                        time.sleep(60)
                        continue
                
                # Get next reboot time
                next_reboot = self.get_next_reboot_time()
                if not next_reboot:
                    self.logger.warning("No reboot schedule configured, sleeping for 1 hour")
                    time.sleep(3600)
                    continue
                
                self.logger.info(f"Next reboot scheduled for: {next_reboot}")
                
                # Schedule announcements
                self.schedule_announcements(next_reboot)
                
                # Wait until reboot time
                now = datetime.now()
                wait_seconds = (next_reboot - now).total_seconds()
                
                if wait_seconds > 0:
                    self.logger.info(f"Waiting {wait_seconds:.0f} seconds until reboot time...")
                    time.sleep(wait_seconds)
                
                # Send exit command
                self.logger.info("Sending exit command to server")
                self.send_command("exit")
                
                # Wait for server to exit (with timeout)
                self.wait_for_server_exit(timeout=60)
                
                # Force kill if still running
                if self.server_process and self.server_process.poll() is None:
                    self.logger.warning("Server did not exit gracefully, terminating...")
                    self.server_process.terminate()
                    time.sleep(5)
                    if self.server_process.poll() is None:
                        self.server_process.kill()
                
                # Wait before restart
                restart_delay = self.config["restart_delay_seconds"]
                self.logger.info(f"Waiting {restart_delay} seconds before restart...")
                time.sleep(restart_delay)
                
                # Clean up process reference
                self.server_process = None
                
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, shutting down...")
                self.stop()
                break
            except Exception as e:
                self.logger.error(f"Error in reboot cycle: {e}", exc_info=True)
                time.sleep(60)  # Wait before retrying
    
    def start(self):
        """Start the auto reboot tool"""
        if self.running:
            self.logger.warning("Tool is already running")
            return
        
        self.running = True
        self.reboot_thread = threading.Thread(target=self.reboot_cycle, daemon=False)
        self.reboot_thread.start()
        self.logger.info("Auto reboot tool thread started")
    
    def stop(self):
        """Stop the auto reboot tool"""
        self.running = False
        
        # Send exit command to server if running
        if self.server_process and self.server_process.poll() is None:
            self.logger.info("Stopping server...")
            self.send_command("exit")
            self.wait_for_server_exit(timeout=30)
            
            if self.server_process and self.server_process.poll() is None:
                self.server_process.terminate()
        
        if self.reboot_thread:
            self.reboot_thread.join(timeout=10)
        
        self.logger.info("Auto reboot tool stopped")
    
    def run(self):
        """Run the tool (blocking)"""
        try:
            self.start()
            if self.reboot_thread:
                self.reboot_thread.join()
        except KeyboardInterrupt:
            self.logger.info("Received interrupt, shutting down...")
            self.stop()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Intersect Engine Auto Reboot Tool")
    parser.add_argument(
        "--config",
        default="reboot_config.json",
        help="Path to configuration file (default: reboot_config.json)"
    )
    
    args = parser.parse_args()
    
    try:
        tool = AutoRebootTool(args.config)
        tool.run()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

