import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
URL = "https://routeonecards.co.uk/one-piece/"

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
        
        product_items = soup.find_all('li', class_='product')
        
        for item in product_items:
            title_elem = item.find('h2', class_='woocommerce-loop-product__title')
            link_elem = item.find('a', class_='woocommerce-LoopProduct-link')
            
            if title_elem and link_elem:
                product_url = link_elem.get('href', '')
                product_title = title_elem.get_text(strip=True)
                
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
    """Send Discord webhook notification"""
    if not DISCORD_WEBHOOK:
        print("⚠️ No Discord webhook configured!")
        return
    
    try:
        embed = {
            "title": "🆕 New One Piece Product Added!",
            "description": product['title'],
            "url": product['url'],
            "color": 15844367,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "Route One Cards Monitor"}
        }
        
        if product.get('image'):
            embed["thumbnail"] = {"url": product['image']}
        
        data = {"embeds": [embed]}
        
        response = requests.post(DISCORD_WEBHOOK, json=data, timeout=10)
        response.raise_for_status()
        print(f"✅ Discord notification sent for: {product['title']}")
        
    except Exception as e:
        print(f"❌ Error sending Discord notification: {e}")

def load_known_products():
    """Load previously seen products"""
    try:
        with open('known_products.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("📝 No previous data found")
        return []
    except json.JSONDecodeError:
        print("⚠️ Corrupted data, starting fresh")
        return []

def save_known_products(products):
    """Save current products"""
    try:
        with open('known_products.json', 'w') as f:
            json.dump(products, f, indent=2)
        print("💾 Data saved")
    except Exception as e:
        print(f"❌ Error saving: {e}")

def main():
    print("=" * 50)
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking for new products...")
    print("=" * 50)
    
    current_products = get_products()
    
    if not current_products:
        print("⚠️ No products found (connection issue?)")
        return
    
    known_products = load_known_products()
    
    # First run - just save products
    if not known_products:
        print(f"📦 First run - saving {len(current_products)} existing products")
        save_known_products(current_products)
        return
    
    # Find new products
    known_urls = {p['url'] for p in known_products}
    new_products = [p for p in current_products if p['url'] not in known_urls]
    
    if new_products:
        print(f"🎉 Found {len(new_products)} NEW product(s)!")
        for product in new_products:
            print(f"   📦 {product['title']}")
            print(f"   🔗 {product['url']}")
            send_discord_notification(product)
        save_known_products(current_products)
    else:
        print(f"✅ No new products (Total: {len(current_products)})")

if __name__ == "__main__":
    main()