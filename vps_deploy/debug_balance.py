from trading_bot import bot_instance
import time

print("Testing get_balance()...")
start = time.time()
bal = bot_instance.get_balance()
end = time.time()
print(f"Balance: {bal}")
print(f"Time taken: {end - start:.2f}s")
