from coinbase_client import CoinbaseClient

def test_products():
    print("Testing CoinbaseClient.get_tradable_symbols()...")
    client = CoinbaseClient()
    if not client.authenticate():
        print("❌ Authentication failed!")
        return

    try:
        symbols = client.get_tradable_symbols()
        print(f"✅ Found {len(symbols)} symbols.")
        if len(symbols) > 0:
            print(f"Sample: {symbols[:5]}")
        else:
            print("⚠️ List is empty. Possible API change or permission issue.")
            
            # Debug raw response
            print("Debugging raw response...")
            try:
                products = client.client.get_products()
                print(f"Raw Type: {type(products)}")
                if hasattr(products, 'products'):
                    print(f"Products count: {len(products.products)}")
                    print(f"First Item: {products.products[0]}")
                else:
                    print(f"Raw content: {products}")
            except Exception as e:
                print(f"Raw Debug Error: {e}")

    except Exception as e:
        print(f"❌ Error calling get_tradable_symbols: {e}")

if __name__ == "__main__":
    test_products()
