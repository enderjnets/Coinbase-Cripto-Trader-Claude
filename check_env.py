import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")
print("System Path:")
for p in sys.path:
    print(f" - {p}")

try:
    import coinbase
    print(f"Coinbase package found at: {coinbase.__file__}")
    print(f"Coinbase dir: {dir(coinbase)}")
except ImportError as e:
    print(f"Error importing coinbase: {e}")

try:
    from coinbase.rest import RESTClient
    print("Successfully imported RESTClient")
except ImportError as e:
    print(f"Error importing RESTClient: {e}")
