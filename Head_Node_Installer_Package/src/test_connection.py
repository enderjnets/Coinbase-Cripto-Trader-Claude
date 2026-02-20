from config import Config
from coinbase.rest import RESTClient
import sys

def test_connectivity():
    print("--- Testing Coinbase Connectivity ---")
    
    api_key, api_secret = Config.get_api_keys()
    
    if not api_key or not api_secret:
        print("❌ Error: API Keys not found.")
        print("Please place 'cdp_api_key.json' in the project root or set COINBASE_API_KEY_NAME and COINBASE_API_KEY_PRIVATE_KEY environment variables.")
        sys.exit(1)
        
    print(f"✅ Credentials found. Key Name: ...{api_key[-5:] if api_key else 'None'}")
    
    try:
        # Initialize Client
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        
        # Test request: Get User Accounts
        print("Attempting to fetch accounts...")
        accounts = client.get_accounts()
        
        if accounts:
            print(f"✅ Connection Successful! Retreived {len(accounts.accounts)} accounts.")
            for acc in accounts.accounts[:3]: # Print first 3
                # Check if acc is dict or object
                currency = getattr(acc, 'currency', None) or acc.get('currency')
                bal = getattr(acc, 'available_balance', None) or acc.get('available_balance')
                val = getattr(bal, 'value', None) or bal.get('value')
                print(f" - {currency}: {val}")
        else:
            print("⚠️ Connection successful but no accounts returned (unexpected).")

    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_connectivity()
