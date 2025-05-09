#!/usr/bin/env python3

import subprocess
import time
from colorama import init, Fore, Style
import re
import sys
import threading
from queue import Queue
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
from dotenv import load_dotenv
import ssl
import certifi

# Load environment variables from .env file
load_dotenv()

# Initialize colorama
init()

class LogMonitor:
    def __init__(self):
        self.containers = {
            "bookstore-app": {
                "color": Fore.CYAN,
                "patterns": {
                    'error': r'[error]',
                    'info': r'[info]',
                    'warn': r'[warn]',
                    'debug': r'[debug]'
                }
            }
        }
        self.log_queue = Queue()
        
        # Initialize Slack client
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not slack_token:
            print(f"{Fore.YELLOW}Warning: SLACK_BOT_TOKEN not found in environment or .env file. Slack notifications will be disabled.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please create a .env file with SLACK_BOT_TOKEN and SLACK_CHANNEL variables{Style.RESET_ALL}")
            self.slack_client = None
        else:
            try:
                # Configure SSL context with certifi certificates
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                self.slack_client = WebClient(
                    token=slack_token,
                    ssl=ssl_context
                )
                self.slack_channel = os.getenv("SLACK_CHANNEL", "#monitoring")
                print(f"{Fore.GREEN}Slack integration enabled. Notifications will be sent to {self.slack_channel}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error initializing Slack client: {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Slack notifications will be disabled.{Style.RESET_ALL}")
                self.slack_client = None

    def send_slack_notification(self, container_name, log_line):
        if not self.slack_client:
            return

        try:
            message = f"🚨 *Error detected in {container_name}*\n```{log_line}```"
            self.slack_client.chat_postMessage(
                channel=self.slack_channel,
                text=message,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message
                        }
                    }
                ]
            )

        except SlackApiError as e:
            print(f"{Fore.RED}Error sending Slack notification: {str(e)}{Style.RESET_ALL}")

    def get_color(self, container_name, log_level):
        container_config = self.containers[container_name]
        colors = {
            'error': Fore.RED,
            'info': Fore.GREEN,
            'warn': Fore.YELLOW,
            'warning': Fore.YELLOW,
            'debug': Fore.BLUE
        }
        return colors.get(log_level, container_config['color'])

    def format_log(self, container_name, log_line):
        container_config = self.containers[container_name]
        for level, pattern in container_config['patterns'].items():
            if level in log_line:
                if level == 'error':
                    print(log_line)
                    self.send_slack_notification(container_name, log_line)
                return f"{container_config['color']}[{container_name}] {self.get_color(container_name, level)}{log_line}{Style.RESET_ALL}"

        return f"{container_config['color']}[{container_name}] {log_line}{Style.RESET_ALL}"

    def monitor_container(self, container_name):
        try:
            # Check if container exists
            result = subprocess.run(['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Names}}'], capture_output=True, text=True)
            if container_name not in result.stdout:
                print(f"{Fore.RED}Error: Container '{container_name}' not found{Style.RESET_ALL}")
                return

            print(f"{self.containers[container_name]['color']}Starting log monitor for {container_name}...{Style.RESET_ALL}")

            # Start monitoring logs
            process = subprocess.Popen(
                ['docker', 'logs', '-f', '--timestamps', container_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                log_line = line.strip()
                formatted_log = self.format_log(container_name, log_line)
                self.log_queue.put(formatted_log)

        except subprocess.CalledProcessError as e:
            print(f"{Fore.RED}Docker Error for {container_name}: {str(e)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Unexpected error for {container_name}: {str(e)}{Style.RESET_ALL}")

    def print_logs(self):
        while True:
            try:
                log = self.log_queue.get()
                print(log)
                sys.stdout.flush()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"{Fore.RED}Error printing log: {str(e)}{Style.RESET_ALL}")

    def start_monitoring(self):
        print(f"{Fore.CYAN}Starting log monitoring...{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Press Ctrl+C to stop monitoring{Style.RESET_ALL}\n")

        # Start a thread for each container
        threads = []
        for container_name in self.containers:
            thread = threading.Thread(target=self.monitor_container, args=(container_name,))
            thread.daemon = True
            threads.append(thread)
            thread.start()

        # Start the print thread
        print_thread = threading.Thread(target=self.print_logs)
        print_thread.daemon = True
        print_thread.start()

        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Log monitoring stopped{Style.RESET_ALL}")

def main():
    monitor = LogMonitor()
    monitor.start_monitoring()

if __name__ == "__main__":
    main() 