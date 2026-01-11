import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime

# Configuration
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')  # Set this in Render environment variables
URL = "https://routeonecards.co.uk/one-piece/"
CHECK_INTERVAL = 60  # Check every 60 seconds

def get_products():
    """Scrape all products from the page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        products = []
        
        # Find all product items
        product_items = soup.find_all('li', class_='product')
        
        for item in product_items:
            # Get product title
            title_elem = item.find('h2', class_='woocommerce-loop-product__title')
            # Get product link
            link_elem = item.find('a', class_='woocommerce-LoopProduct-link')
            
            if title_elem and link_elem:
                product_url = link_elem.get('href', '')
                product_title = title_elem.get_text(strip=True)
                
                # Get image if available
                img_elem = item.find('img')
                image_url = img_elem.get('src', '') if img_elem else ''
                
                products.append({
                    'title': product_title,
                    'url': product_url,
                    'image': image_url
                })
        
        return products
    
    except Exception as e:
        print(f"Error fetching products: {e}")
        return []

def send_discord_notification(product):
    """Send Discord webhook notification for new product"""
    if not DISCORD_WEBHOOK:
        print("⚠️ No Discord webhook configured!")
        return
    
    try:
        embed = {
            "title": "🆕 New One Piece Product Added!",
            "description": product['title'],
            "url": product['url'],
            "color": 15844367,  # Orange color
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": "Route One Cards Monitor"
            }
        }
        
        # Add image if available
        if product.get('image'):
            embed["thumbnail"] = {"url": product['image']}
        
        data = {
            "embeds": [embed]
        }
        
        response = requests.post(DISCORD_WEBHOOK, json=data, timeout=10)
        response.raise_for_status()
        print(f"✅ Discord notification sent for: {product['title']}")
        
    except Exception as e:
        print(f"❌ Error sending Discord notification: {e}")

def load_known_products():
    """Load previously seen products from file"""
    try:
        with open('known_products.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("📝 No previous data found, starting fresh")
        return []
    except json.JSONDecodeError:
        print("⚠️ Corrupted data file, starting fresh")
        return []

def save_known_products(products):
    """Save current products to file"""
    try:
        with open('known_products.json', 'w') as f:
            json.dump(products, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving products: {e}")

def main():
    """Main monitoring loop"""
    print("=" * 50)
    print("🔍 One Piece Restock Monitor Started")
    print(f"📍 Monitoring: {URL}")
    print(f"⏱️  Check interval: {CHECK_INTERVAL} seconds")
    print(f"🔔 Discord webhook: {'Configured ✅' if DISCORD_WEBHOOK else 'Not configured ❌'}")
    print("=" * 50)
    
    # Initial load to populate database on first run
    initial_products = get_products()
    if initial_products:
        known_products = load_known_products()
        if not known_products:  # First run
            print(f"📦 Found {len(initial_products)} existing products (not sending notifications)")
            save_known_products(initial_products)
    
    while True:
        try:
            print(f"\n⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for new products...")
            
            # Get current products
            current_products = get_products()
            
            if not current_products:
                print("⚠️ No products found (might be a connection issue)")
                time.sleep(CHECK_INTERVAL)
                continue
            
            # Load known products
            known_products = load_known_products()
            
            # Find new products by comparing URLs
            known_urls = {p['url'] for p in known_products}
            new_products = [p for p in current_products if p['url'] not in known_urls]
            
            if new_products:
                print(f"🎉 Found {len(new_products)} NEW product(s)!")
                for product in new_products:
                    print(f"   📦 {product['title']}")
                    print(f"   🔗 {product['url']}")
                    send_discord_notification(product)
                
                # Update known products
                save_known_products(current_products)
                print("💾 Database updated")
            else:
                print(f"✅ No new products (Total: {len(current_products)})")
            
        except KeyboardInterrupt:
            print("\n\n👋 Monitor stopped by user")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        # Wait before next check
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
```

---

## **What this script does:**

✅ **Scrapes the One Piece page** every 60 seconds  
✅ **Detects new products** by comparing URLs  
✅ **Sends Discord notifications** with product name, link, and image  
✅ **Saves product database** to `known_products.json`  
✅ **Error handling** for network issues  
✅ **Clean logging** so you can see what's happening  
✅ **First-run handling** (won't spam notifications for existing products)

---

## **Files you need:**

**requirements.txt:**
```
requests
beautifulsoup4