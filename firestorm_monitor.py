import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
BASE_URL = "https://www.firestormcards.co.uk/one%20piece"

def get_all_products():
    """Scrape all products from all pages"""
    all_products = []
    page = 1
    
    while True:
        try:
            url = f"{BASE_URL}?pagenumber={page}&orderby=15"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            products = soup.find_all('div', class_='item-box')
            
            if not products:
                break
            
            for product in products:
                title_elem = product.find('h2', class_='product-title')
                if not title_elem:
                    continue
                    
                title_link = title_elem.find('a')
                if not title_link:
                    continue
                
                product_title = title_link.get_text(strip=True)
                product_url = "https://www.firestormcards.co.uk" + title_link.get('href', '')
                
                sku_elem = product.find('strong', string='SKU:')
                sku = ""
                if sku_elem and sku_elem.next_sibling:
                    sku = sku_elem.next_sibling.strip()
                
                stock_elem = product.find('strong', string='Stock Qty:')
                stock_qty = 0
                if stock_elem and stock_elem.next_sibling:
                    try:
                        stock_qty = int(stock_elem.next_sibling.strip())
                    except (ValueError, AttributeError):
                        stock_qty = 0
                
                price_elem = product.find('span', class_='price')
                price = ""
                if price_elem:
                    price = price_elem.get_text(strip=True)
                
                img_elem = product.find('img')
                image_url = ""
                if img_elem:
                    image_url = "https://www.firestormcards.co.uk" + img_elem.get('src', '')
                
                all_products.append({
                    'title': product_title,
                    'sku': sku,
                    'url': product_url,
                    'stock_qty': stock_qty,
                    'price': price,
                    'image': image_url
                })
            
            print(f"📄 Page {page}: Found {len(products)} products")
            page += 1
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    return all_products

def send_discord_notification(title, description, color, products):
    """Send Discord webhook notification"""
    if not DISCORD_WEBHOOK:
        print("⚠️ No Discord webhook configured!")
        return
    
    try:
        embeds = [{
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "Firestorm Cards Monitor"}
        }]
        
        for product in products[:10]:
            embed = {
                "title": product['title'],
                "url": product['url'],
                "color": color,
                "fields": [
                    {
                        "name": "Stock",
                        "value": f"**{product['stock_qty']}** available",
                        "inline": True
                    },
                    {
                        "name": "Price",
                        "value": product['price'],
                        "inline": True
                    }
                ]
            }
            
            if product.get('image'):
                embed["thumbnail"] = {"url": product['image']}
            
            if product.get('old_stock') is not None:
                embed["fields"].insert(0, {
                    "name": "Stock Change",
                    "value": f"{product['old_stock']} → {product['stock_qty']}",
                    "inline": True
                })
            
            embeds.append(embed)
        
        data = {"embeds": embeds}
        
        response = requests.post(DISCORD_WEBHOOK, json=data, timeout=10)
        response.raise_for_status()
        print(f"✅ Discord notification sent")
        
    except Exception as e:
        print(f"❌ Error sending Discord notification: {e}")

def load_known_products():
    """Load previously tracked products"""
    try:
        with open('firestorm_products.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("📝 No previous data found")
        return {}
    except json.JSONDecodeError:
        print("⚠️ Corrupted data, starting fresh")
        return {}

def save_known_products(products):
    """Save current products"""
    try:
        products_dict = {p['sku']: p for p in products if p['sku']}
        with open('firestorm_products.json', 'w') as f:
            json.dump(products_dict, f, indent=2)
        print("💾 Data saved")
    except Exception as e:
        print(f"❌ Error saving: {e}")

def main():
    print("=" * 50)
    print(f"⏰ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Firestorm Cards Monitor")
    print("=" * 50)
    
    current_products = get_all_products()
    
    if not current_products:
        print("⚠️ No products found")
        return
    
    print(f"📦 Total products found: {len(current_products)}")
    
    known_products = load_known_products()
    
    if not known_products:
        print(f"📦 First run - saving {len(current_products)} products")
        save_known_products(current_products)
        return
    
    restocked = []
    increased_stock = []
    new_products = []
    
    for product in current_products:
        sku = product['sku']
        if not sku:
            continue
        
        if sku not in known_products:
            if product['stock_qty'] > 0:
                new_products.append(product)
        else:
            old_product = known_products[sku]
            old_stock = old_product.get('stock_qty', 0)
            new_stock = product['stock_qty']
            
            if old_stock == 0 and new_stock > 0:
                product['old_stock'] = old_stock
                restocked.append(product)
            elif new_stock > old_stock and old_stock > 0:
                product['old_stock'] = old_stock
                increased_stock.append(product)
    
    if restocked:
        print(f"🔔 {len(restocked)} product(s) RESTOCKED!")
        for p in restocked:
            print(f"   ✨ {p['title']}: 0 → {p['stock_qty']}")
        send_discord_notification(
            "🔔 RESTOCK ALERT!",
            f"{len(restocked)} product(s) back in stock!",
            3066993,
            restocked
        )
    
    if increased_stock:
        print(f"📈 {len(increased_stock)} product(s) got more stock")
        for p in increased_stock:
            print(f"   📦 {p['title']}: {p['old_stock']} → {p['stock_qty']}")
        send_discord_notification(
            "📈 Stock Increased",
            f"{len(increased_stock)} product(s) got more stock!",
            3447003,
            increased_stock
        )
    
    if new_products:
        print(f"🆕 {len(new_products)} NEW product(s) added!")
        for p in new_products:
            print(f"   🎉 {p['title']} ({p['stock_qty']} in stock)")
        send_discord_notification(
            "🆕 New Products Added!",
            f"{len(new_products)} new product(s) available!",
            15844367,
            new_products
        )
    
    if not restocked and not increased_stock and not new_products:
        print("✅ No changes detected")
    
    save_known_products(current_products)

if __name__ == "__main__":
    main()
