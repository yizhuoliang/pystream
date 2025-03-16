"""
PySTREAM - Python wrapper for the STREAM memory bandwidth benchmark.

This package allows you to run the STREAM benchmark from Python,
primarily to generate memory bandwidth pressure for testing and benchmarking.
"""

from .benchmark import StreamBenchmark, StreamOperation

__version__ = "0.1.0"
__all__ = ["StreamBenchmark", "StreamOperation"]
