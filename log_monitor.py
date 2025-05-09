#!/usr/bin/env python3

import docker
import time
from datetime import datetime
from colorama import init, Fore, Style
import re
import sys

# Initialize colorama
init()

class LogMonitor:
    def __init__(self):
        self.client = docker.from_env()
        self.container_name = "bookstore-app"
        self.log_patterns = {
            'error': r'\[error\]',
            'info': r'\[info\]',
            'warn': r'\[warn\]',
            'debug': r'\[debug\]'
        }

    def get_color(self, log_level):
        colors = {
            'error': Fore.RED,
            'info': Fore.GREEN,
            'warn': Fore.YELLOW,
            'debug': Fore.BLUE
        }
        return colors.get(log_level, Fore.WHITE)

    def format_log(self, log_line):
        # Try to parse the log line
        for level, pattern in self.log_patterns.items():
            if re.search(pattern, log_line, re.IGNORECASE):
                return f"{self.get_color(level)}{log_line}{Style.RESET_ALL}"
        return log_line

    def monitor_logs(self):
        try:
            # Get the container
            container = self.client.containers.get(self.container_name)
            
            print(f"{Fore.CYAN}Starting log monitor for {self.container_name}...{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Press Ctrl+C to stop monitoring{Style.RESET_ALL}\n")

            # Stream the logs
            for log in container.logs(stream=True, follow=True, timestamps=True):
                try:
                    # Decode the log line
                    log_line = log.decode('utf-8').strip()
                    
                    # Format and print the log
                    formatted_log = self.format_log(log_line)
                    print(formatted_log)
                    
                    # Flush stdout to ensure real-time output
                    sys.stdout.flush()
                except UnicodeDecodeError:
                    continue

        except docker.errors.NotFound:
            print(f"{Fore.RED}Error: Container '{self.container_name}' not found{Style.RESET_ALL}")
        except docker.errors.APIError as e:
            print(f"{Fore.RED}Docker API Error: {str(e)}{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Log monitoring stopped{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Unexpected error: {str(e)}{Style.RESET_ALL}")

def main():
    monitor = LogMonitor()
    monitor.monitor_logs()

if __name__ == "__main__":
    main() 