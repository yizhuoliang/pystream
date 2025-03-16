"""
Basic tests for the PySTREAM package.
"""

import unittest
import time
import os
import sys
import subprocess
from pystream import StreamBenchmark, StreamOperation

class TestStreamBenchmark(unittest.TestCase):
    """Test the StreamBenchmark class."""
    
    def test_initialization(self):
        """Test that the benchmark initializes correctly."""
        stream = StreamBenchmark()
        self.assertIsNotNone(stream)
        self.assertFalse(stream.is_running())
    
    def test_blocking_run(self):
        """Test running the benchmark in blocking mode."""
        stream = StreamBenchmark(
            threads=2,
            array_size=10000,  # Small array for quick test
            operation=StreamOperation.COPY
        )
        # Run with small number of iterations for quick test
        stream.set_silent_mode(True)
        result = stream.start(blocking=True)
        self.assertEqual(result.returncode, 0)
    
    def test_non_blocking_run(self):
        """Test running the benchmark in non-blocking mode."""
        stream = StreamBenchmark(
            threads=2,
            array_size=10000,  # Small array for quick test
            operation=StreamOperation.COPY
        )
        # Run for a short time
        stream.set_runtime(0.5)  # Half a second
        stream.start(blocking=False)
        
        # Check that it's running
        self.assertTrue(stream.is_running())
        
        # Wait for it to finish
        time.sleep(1)
        
        # Should be done now
        self.assertFalse(stream.is_running())
    
    def test_stop(self):
        """Test stopping the benchmark."""
        stream = StreamBenchmark(
            threads=2,
            array_size=100000,  # Larger array so it won't finish immediately
            operation=StreamOperation.TRIAD
        )
        # Set to run for a long time
        stream.set_runtime(10)
        stream.start(blocking=False)
        
        # Check that it's running
        self.assertTrue(stream.is_running())
        
        # Stop it
        stream.stop()
        
        # Should be stopped now
        self.assertFalse(stream.is_running())
    
    def test_resource_usage(self):
        """Test getting resource usage information."""
        stream = StreamBenchmark(
            threads=2,
            array_size=100000,
            operation=StreamOperation.TRIAD
        )
        stream.set_runtime(3)
        stream.start(blocking=False)
        
        # Wait a moment for it to get going
        time.sleep(0.5)
        
        # Get resource usage
        usage = stream.get_resource_usage()
        
        # Should have some basic information
        self.assertIn('cpu_percent', usage)
        self.assertIn('memory_rss_mb', usage)
        
        # Clean up
        stream.stop()

if __name__ == '__main__':
    unittest.main()
