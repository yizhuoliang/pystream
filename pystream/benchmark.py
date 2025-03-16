"""
STREAM benchmark Python wrapper.

This module provides a Python interface for running the STREAM memory 
bandwidth benchmark as a separate process, allowing for generating
controlled memory bandwidth pressure.
"""

import os
import subprocess
import signal
import time
import enum
import threading
import atexit
import psutil
import logging
import sys
from typing import Optional, Dict, List, Union, Tuple

logger = logging.getLogger(__name__)

class StreamOperation(enum.Enum):
    """STREAM benchmark operation types."""
    COPY = "copy"
    SCALE = "scale"
    ADD = "add"
    TRIAD = "triad"

class StreamBenchmark:
    """
    Python wrapper for the STREAM memory bandwidth benchmark.
    
    This class allows running the STREAM benchmark as a separate process
    to generate memory bandwidth pressure, which can be useful for testing
    the behavior of other code under memory contention.
    """
    
    def __init__(self, 
                 executable_path: Optional[str] = None,
                 threads: int = 4,
                 array_size: int = 100000000,
                 operation: StreamOperation = StreamOperation.TRIAD,
                 scalar: float = 3.0):
        """
        Initialize the STREAM benchmark wrapper.
        
        Args:
            executable_path: Path to the STREAM executable. If None, uses the one
                             included with this package.
            threads: Number of threads to use for the benchmark.
            array_size: Size of the arrays used in the benchmark.
            operation: The STREAM operation to perform.
            scalar: Scalar value for operations that require it.
        """
        self.process = None
        self.stop_event = threading.Event()
        self.monitor_thread = None
        
        # Find the executable
        if executable_path is None:
            package_dir = os.path.dirname(os.path.abspath(__file__))
            self.executable = os.path.join(package_dir, "c_src", "stream")
            
            # If not found in the installed package, try to build it
            if not os.path.isfile(self.executable):
                self._build_executable()
        else:
            self.executable = executable_path
            
        # Ensure the executable exists and is executable
        if not os.path.isfile(self.executable):
            raise FileNotFoundError(f"STREAM executable not found at {self.executable}")
        if not os.access(self.executable, os.X_OK):
            os.chmod(self.executable, 0o755)  # Make executable
            
        # Store configuration
        self.threads = threads
        self.array_size = array_size
        self.operation = operation
        self.scalar = scalar
        self.runtime_seconds = None  # For runtime mode
        self.use_hrperf = False
        self.silent_mode = True      # Default to silent mode for background use
        
        # Register cleanup handler
        atexit.register(self.stop)
    
    def _build_executable(self):
        """Attempt to build the STREAM executable if it's not found."""
        try:
            # Get the source directory
            source_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "c_src")
            
            if not os.path.isdir(source_dir):
                logger.error(f"Source directory not found at {source_dir}")
                return
                
            # Store current directory
            cwd = os.getcwd()
            
            try:
                # Change to source directory
                os.chdir(source_dir)
                
                # Check if source files exist
                if not os.path.isfile("stream.c"):
                    logger.error("stream.c not found in source directory")
                    return
                
                # Attempt to build
                logger.info("Attempting to build STREAM executable...")
                subprocess.check_call(["make", "clean"])
                subprocess.check_call(["make"])
                
                logger.info("STREAM executable built successfully")
                
            finally:
                # Always return to original directory
                os.chdir(cwd)
                
        except Exception as e:
            logger.error(f"Failed to build STREAM executable: {e}")
            
    def set_runtime(self, seconds: float):
        """
        Set the benchmark to run for a specific duration.
        
        Args:
            seconds: Duration to run in seconds.
        """
        self.runtime_seconds = seconds
    
    def enable_hrperf(self, enable: bool = True):
        """
        Enable or disable hrperf measurements.
        
        Args:
            enable: Whether to enable hrperf.
        """
        self.use_hrperf = enable
    
    def set_silent_mode(self, silent: bool = True):
        """
        Enable or disable silent mode.
        
        Args:
            silent: Whether to run in silent mode.
        """
        self.silent_mode = silent
    
    def build_command(self) -> List[str]:
        """
        Build the command to run the STREAM benchmark.
        
        Returns:
            List of command arguments.
        """
        cmd = [
            self.executable,
            "-n", str(self.threads),
            "-s", str(self.array_size),
            "-o", self.operation.value,
            "-c", str(self.scalar)
        ]
        
        if self.runtime_seconds is not None:
            cmd.extend(["-r", str(self.runtime_seconds)])
        else:
            # Default to a reasonable number of iterations if runtime is not specified
            cmd.extend(["-i", "10"])
            
        if self.use_hrperf:
            cmd.append("-p")
            
        if self.silent_mode:
            cmd.append("-q")
            
        return cmd
    
    def start(self, blocking: bool = False) -> Optional[subprocess.CompletedProcess]:
        """
        Start the STREAM benchmark.
        
        Args:
            blocking: If True, wait for the benchmark to complete and return results.
                     If False (default), run in the background.
                     
        Returns:
            If blocking, returns the CompletedProcess instance.
            If non-blocking, returns None.
        """
        if self.process is not None and self.process.poll() is None:
            logger.warning("STREAM benchmark is already running")
            return None
            
        cmd = self.build_command()
        logger.debug(f"Running STREAM benchmark: {' '.join(cmd)}")
        
        if blocking:
            # Run in blocking mode and return results
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE if self.silent_mode else None,
                stderr=subprocess.PIPE,
                text=True
            )
            return result
        else:
            # Run in non-blocking mode
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL if self.silent_mode else None,
                stderr=subprocess.PIPE
            )
            
            # Start a monitor thread
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(
                target=self._monitor_process,
                daemon=True
            )
            self.monitor_thread.start()
            return None
    
    def stop(self):
        """Stop the STREAM benchmark if it's running."""
        if self.process is not None and self.process.poll() is None:
            logger.debug("Stopping STREAM benchmark")
            # Signal the monitor thread to stop
            self.stop_event.set()
            
            # Try to terminate the process gracefully first
            self.process.terminate()
            
            # Give it a moment to clean up
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                logger.warning("STREAM benchmark did not terminate gracefully, forcing kill")
                self.process.kill()
            
            # Wait for monitor thread to finish
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1)
    
    def is_running(self) -> bool:
        """
        Check if the STREAM benchmark is currently running.
        
        Returns:
            True if running, False otherwise.
        """
        return self.process is not None and self.process.poll() is None
    
    def get_resource_usage(self) -> Dict[str, float]:
        """
        Get resource usage statistics for the running benchmark.
        
        Returns:
            Dictionary with resource usage information or empty dict if not running.
        """
        if not self.is_running():
            return {}
            
        try:
            proc = psutil.Process(self.process.pid)
            with proc.oneshot():
                cpu_percent = proc.cpu_percent()
                mem_info = proc.memory_info()
                io_counters = proc.io_counters() if hasattr(proc, 'io_counters') else None
                
            result = {
                'cpu_percent': cpu_percent,
                'memory_rss_mb': mem_info.rss / (1024 * 1024),
                'memory_vms_mb': mem_info.vms / (1024 * 1024),
            }
            
            if io_counters:
                result.update({
                    'io_read_mb': io_counters.read_bytes / (1024 * 1024),
                    'io_write_mb': io_counters.write_bytes / (1024 * 1024),
                })
                
            return result
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return {}
    
    def _monitor_process(self):
        """Background thread to monitor the STREAM process."""
        while not self.stop_event.is_set():
            # Check if process has finished
            if self.process.poll() is not None:
                returncode = self.process.returncode
                stderr = self.process.stderr.read() if self.process.stderr else None
                
                if returncode != 0 and stderr:
                    logger.error(f"STREAM benchmark failed with code {returncode}: {stderr}")
                elif returncode != 0:
                    logger.error(f"STREAM benchmark failed with code {returncode}")
                else:
                    logger.debug("STREAM benchmark completed successfully")
                    
                # Process has finished, exit the monitoring loop
                break
                
            # Sleep before checking again
            time.sleep(0.1)
