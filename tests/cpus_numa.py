"""
Example of using PySTREAM with CPU affinity and NUMA control.

This example demonstrates how to create memory bandwidth pressure
on specific CPU cores and NUMA nodes.
"""

import time
import logging
from pystream import StreamBenchmark, StreamOperation

# Enable logging to see detailed information
logging.basicConfig(level=logging.INFO)

def main():
    print("PySTREAM Example with CPU and NUMA control")
    
    # Create a benchmark instance with specific CPU and NUMA settings
    # This will create memory pressure only on cores 0, 2 and NUMA node 0
    stream = StreamBenchmark(
        threads=2,                   # Use 2 threads for the benchmark
        array_size=200000000,        # Large array to ensure bandwidth pressure
        operation=StreamOperation.TRIAD,  # TRIAD operation (most memory intensive)
        cpus=[0, 2],                 # Pin threads to cores 0 and 2
        numa_nodes=[0]               # Use only memory from NUMA node 0
    )
    
    # Configure for runtime mode (run for 30 seconds)
    stream.set_runtime(30)
    
    # Run non-blocking so we can continue with other work
    print("\nStarting STREAM benchmark in the background...")
    stream.start(blocking=False)
    
    # Check if it's running
    if stream.is_running():
        print("STREAM benchmark is running in the background")
    
    # Monitor while it runs
    start_time = time.time()
    try:
        while stream.is_running() and (time.time() - start_time < 30):
            # Get resource usage information
            usage = stream.get_resource_usage()
            
            # Print current status
            print(f"\nSTREAM Benchmark Status (after {time.time() - start_time:.1f} seconds):")
            for key, value in usage.items():
                print(f"  {key}: {value:.2f}")
            
            # Do some work here while STREAM runs in the background
            print("\nYour application is running while STREAM creates memory pressure...")
            
            # Sleep a bit before checking again
            time.sleep(5)
    
    except KeyboardInterrupt:
        print("\nUser interrupted, stopping benchmark...")
    finally:
        # Make sure to stop the benchmark
        stream.stop()
        print("\nSTREAM benchmark stopped")
    
    # Now run in blocking mode with output to see the results
    print("\nRunning STREAM benchmark in blocking mode with output...")
    stream.set_silent_mode(False)    # Enable output
    stream.set_runtime(5)            # Short run for demonstration
    result = stream.start(blocking=True)
    
    # Print results
    if result.returncode == 0:
        print("\nBenchmark completed successfully!")
    else:
        print(f"\nBenchmark failed with return code {result.returncode}")
        if result.stderr:
            print(f"Error: {result.stderr}")

if __name__ == "__main__":
    main()
