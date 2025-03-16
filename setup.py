from setuptools import setup, find_packages, Extension
from setuptools.command.build_py import build_py
import subprocess
import os
import sys
import platform
import shutil

class StreamBuild(build_py):
    """Custom build command for STREAM benchmark C code."""
    
    def run(self):
        # First run the regular build_py
        build_py.run(self)
        
        # Navigate to the C source directory
        c_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pystream', 'c_src')
        
        # Get the build directory path for the package
        build_dir = os.path.join(self.build_lib, 'pystream', 'c_src')
        
        # Store the current directory
        cwd = os.getcwd()
        
        try:
            # Change to the C source directory
            os.chdir(c_src_dir)
            
            # Run make to build the C program
            subprocess.check_call(['make', 'clean'])
            
            # Check if libnuma is available
            numa_available = self._check_numa_available()
            
            if numa_available:
                print("NUMA support detected, building with NUMA support")
                build_cmd = ['make', 'USE_NUMA=1']
            else:
                print("NUMA support not detected, building without NUMA support")
                build_cmd = ['make']
                
            # Build with appropriate configuration
            subprocess.check_call(build_cmd)
            
            # Make sure the build directory exists
            os.makedirs(build_dir, exist_ok=True)
            
            # Copy the built executable to the build directory
            if os.path.exists('stream'):
                shutil.copy('stream', build_dir)
                print(f"Copied stream executable to {build_dir}")
            else:
                print("WARNING: stream executable not found after build!")
            
            # Move back to the original directory
            os.chdir(cwd)
            
        except Exception as e:
            print(f"Error building STREAM benchmark: {e}")
            os.chdir(cwd)  # Ensure we return to the original directory
            raise
    
    def _check_numa_available(self):
        """Check if libnuma is available on the system."""
        try:
            # Check if we can find the libnuma library
            result = subprocess.run(
                ["ldconfig", "-p"], 
                capture_output=True, 
                text=True
            )
            if "libnuma.so" in result.stdout:
                return True
                
            # Alternative check for macOS and other systems
            result = subprocess.run(
                ["find", "/usr/lib", "/usr/local/lib", "-name", "libnuma*"], 
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                return True
                
            # Check for the header file
            if os.path.exists("/usr/include/numa.h") or os.path.exists("/usr/local/include/numa.h"):
                return True
                
            return False
        except Exception as e:
            print(f"Error checking for NUMA support: {e}")
            return False

# Define packages explicitly, including c_src directory
packages = find_packages(include=['pystream', 'pystream.*'])

# Ensure pystream.c_src is included
if 'pystream.c_src' not in packages:
    packages.append('pystream.c_src')

setup(
    name="pystream",
    version="0.1.0",
    description="Python wrapper for STREAM memory bandwidth benchmark",
    author="Your Name",
    author_email="your.email@example.com",
    packages=packages,
    include_package_data=True,
    package_data={
        'pystream': ['c_src/*'],
        'pystream.c_src': ['*'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.6",
    cmdclass={
        'build_py': StreamBuild,
    },
    install_requires=[
        'psutil',  # For process management
    ],
)
