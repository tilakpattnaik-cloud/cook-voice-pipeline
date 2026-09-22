import json
import random
random.seed(42)

def mock_rating_count(rating):
    """
    Real review-count data isn't available here — this is fabricated stand-in
    data, explicitly flagged as such. Deliberately produces some values under
    20 so the "established vs unproven" tiering logic has something real to
    differentiate, rather than every rated item trivially clearing the bar.
    """
    if rating is None:
        return None
    if random.random() < 0.2:
        return random.randint(3, 19)
    return random.randint(20, 3000)

# (item, category, [(brand, size, price, rating_or_None), ...])
CATALOG_DATA = [
    # --- Vegetables & Fruits ---
    ("Onion", "Vegetables", [("loose", "1kg", 42, None), ("Freshveg", "1kg", 48, 4.1)]),
    ("Potato", "Vegetables", [("loose", "1kg", 32, None), ("Freshveg", "1kg", 38, 4.0)]),
    ("Tomato", "Vegetables", [("loose", "1kg", 45, None), ("Freshveg", "1kg", 52, 4.0)]),
    ("Ginger", "Vegetables", [("loose", "250g", 30, None)]),
    ("Garlic", "Vegetables", [("loose", "250g", 45, None)]),
    ("Green Chilli", "Vegetables", [("loose", "100g", 10, None)]),
    ("Lemon", "Vegetables", [("loose", "4 pcs", 20, None)]),
    ("Coriander Leaves", "Vegetables", [("loose", "1 bunch", 12, None)]),
    ("Cucumber", "Vegetables", [("loose", "500g", 25, None)]),
    ("Cabbage", "Vegetables", [("loose", "1 pc", 30, None)]),
    ("Cauliflower", "Vegetables", [("loose", "1 pc", 35, None)]),
    ("Spinach", "Vegetables", [("loose", "250g", 20, None)]),
    ("Bottle Gourd", "Vegetables", [("loose", "1 pc", 28, None)]),
    ("Brinjal", "Vegetables", [("loose", "500g", 30, None)]),
    ("Capsicum", "Vegetables", [("loose", "500g", 40, None)]),
    ("Carrot", "Vegetables", [("loose", "500g", 28, None)]),
    ("Beans", "Vegetables", [("loose", "250g", 25, None)]),
    ("Green Peas", "Vegetables", [("loose", "500g", 45, None), ("Frozen - Safal", "500g", 65, 4.2)]),
    ("Okra (Bhindi)", "Vegetables", [("loose", "500g", 32, None)]),
    ("Bitter Gourd", "Vegetables", [("loose", "500g", 35, None)]),
    ("Radish", "Vegetables", [("loose", "500g", 22, None)]),
    ("Beetroot", "Vegetables", [("loose", "500g", 30, None)]),
    ("Sweet Corn", "Vegetables", [("loose", "2 pcs", 30, None)]),
    ("Mushroom", "Vegetables", [("loose", "200g", 45, None)]),
    ("Pumpkin", "Vegetables", [("loose", "500g", 25, None)]),
    ("Drumstick", "Vegetables", [("loose", "250g", 30, None)]),
    ("Ridge Gourd", "Vegetables", [("loose", "500g", 28, None)]),
    ("Snake Gourd", "Vegetables", [("loose", "500g", 28, None)]),
    ("Ash Gourd", "Vegetables", [("loose", "500g", 25, None)]),
    ("Colocasia (Arbi)", "Vegetables", [("loose", "500g", 32, None)]),
    ("Yam", "Vegetables", [("loose", "500g", 35, None)]),
    ("Sweet Potato", "Vegetables", [("loose", "500g", 30, None)]),
    ("Apple", "Fruits", [("loose", "1kg", 180, None), ("Washington", "1kg", 220, 4.3)]),
    ("Banana", "Fruits", [("loose", "1 dozen", 55, None)]),
    ("Mango", "Fruits", [("Alphonso", "1kg", 250, 4.5)]),
    ("Papaya", "Fruits", [("loose", "1 pc", 40, None)]),
    ("Pomegranate", "Fruits", [("loose", "1kg", 160, None)]),
    ("Watermelon", "Fruits", [("loose", "1 pc", 60, None)]),
    ("Orange", "Fruits", [("loose", "1kg", 90, None)]),
    ("Grapes", "Fruits", [("loose", "500g", 70, None)]),
    ("Pineapple", "Fruits", [("loose", "1 pc", 55, None)]),
    ("Guava", "Fruits", [("loose", "500g", 40, None)]),
    ("Kiwi", "Fruits", [("loose", "3 pcs", 85, None)]),
    ("Chikoo", "Fruits", [("loose", "500g", 45, None)]),

    # --- Grocery & Pantry ---
    ("Salt", "Grocery", [("Tata", "1kg", 28, 4.5), ("loose", "500g", 15, None)]),
    ("Sugar", "Grocery", [("Madhur", "1kg", 48, 4.2)]),
    ("Jaggery", "Grocery", [("loose", "500g", 55, None)]),
    ("Toor Dal", "Grocery", [("Tata Sampann", "1kg", 165, 4.4), ("Fortune", "1kg", 158, 4.1)]),
    ("Chana Dal", "Grocery", [("Tata Sampann", "1kg", 130, 4.3)]),
    ("Moong Dal", "Grocery", [("Tata Sampann", "1kg", 140, 4.3)]),
    ("Rajma", "Grocery", [("Tata Sampann", "1kg", 150, 4.2)]),
    ("Chole (Kabuli Chana)", "Grocery", [("Tata Sampann", "1kg", 120, 4.2)]),
    ("Moong Whole", "Grocery", [("Tata Sampann", "1kg", 145, 4.1)]),
    ("Basmati Rice", "Grocery", [("India Gate", "1kg", 145, 4.5), ("Daawat", "1kg", 138, 4.2)]),
    ("Sona Masoori Rice", "Grocery", [("Fortune", "5kg", 340, 4.3)]),
    ("Idli Rice", "Grocery", [("loose", "1kg", 60, None)]),
    ("Rice Flour", "Grocery", [("Rajdhani", "500g", 45, 4.0)]),
    ("Ragi Flour", "Grocery", [("Aashirvaad", "500g", 65, 4.2)]),
    ("Wheat Flour (Atta)", "Grocery", [("Aashirvaad", "5kg", 275, 4.6), ("Fortune Chakki Fresh", "5kg", 260, 4.3)]),
    ("Multigrain Atta", "Grocery", [("Aashirvaad", "5kg", 320, 4.4)]),
    ("Sunflower Oil", "Grocery", [("Fortune", "1L", 165, 4.3), ("Saffola", "1L", 178, 4.4)]),
    ("Mustard Oil", "Grocery", [("Fortune", "1L", 175, 4.2)]),
    ("Groundnut Oil", "Grocery", [("Dhara", "1L", 210, 4.3)]),
    ("Ghee", "Grocery", [("Amul", "500ml", 295, 4.7), ("Patanjali", "500ml", 270, 4.3)]),
    ("Butter", "Grocery", [("Amul", "500g", 255, 4.6)]),
    ("Milk", "Grocery", [("Amul Taaza", "500ml", 30, 4.6), ("Mother Dairy", "500ml", 28, 4.4)]),
    ("Buttermilk (Chaas)", "Grocery", [("Amul", "200ml", 15, 4.3)]),
    ("Lassi", "Grocery", [("Amul", "200ml", 25, 4.3)]),
    ("Curd", "Grocery", [("Amul", "400g", 45, 4.5), ("Mother Dairy", "400g", 42, 4.3)]),
    ("Paneer", "Grocery", [("Amul", "200g", 95, 4.5), ("Mother Dairy", "200g", 90, 4.3)]),
    ("Bread", "Grocery", [("Britannia", "400g", 45, 4.0), ("Modern", "400g", 42, 3.9)]),
    ("Eggs", "Grocery", [("Farm Fresh", "6 pcs", 48, 4.2), ("Farm Fresh", "12 pcs", 90, 4.2)]),
    ("Tea", "Grocery", [("Tata Tea Premium", "250g", 130, 4.4), ("Red Label", "250g", 125, 4.3)]),
    ("Coffee", "Grocery", [("Bru", "100g", 145, 4.2), ("Nescafe Classic", "100g", 165, 4.5)]),
    ("Turmeric Powder", "Grocery", [("Everest", "100g", 38, 4.3), ("MDH", "100g", 35, 4.2)]),
    ("Red Chilli Powder", "Grocery", [("Everest", "100g", 45, 4.3), ("MDH", "100g", 42, 4.2)]),
    ("Coriander Powder", "Grocery", [("Everest", "100g", 35, 4.2)]),
    ("Garam Masala", "Grocery", [("Everest", "100g", 55, 4.4), ("MDH", "100g", 52, 4.3)]),
    ("Chaat Masala", "Grocery", [("MDH", "100g", 48, 4.3)]),
    ("Sambar Masala", "Grocery", [("MTR", "200g", 65, 4.4)]),
    ("Biryani Masala", "Grocery", [("Everest", "100g", 60, 4.3)]),
    ("Kitchen King Masala", "Grocery", [("MDH", "100g", 55, 4.2)]),
    ("Amchur (Dry Mango Powder)", "Grocery", [("Everest", "100g", 40, 4.1)]),
    ("Cumin Seeds", "Grocery", [("Everest", "100g", 60, 4.3)]),
    ("Mustard Seeds", "Grocery", [("loose", "100g", 25, None)]),
    ("Fenugreek Seeds", "Grocery", [("loose", "100g", 22, None)]),
    ("Kasuri Methi", "Grocery", [("Everest", "50g", 35, 4.2)]),
    ("Ajwain (Carom Seeds)", "Grocery", [("loose", "100g", 30, None)]),
    ("Black Pepper", "Grocery", [("Everest", "50g", 55, 4.3)]),
    ("Star Anise", "Grocery", [("loose", "50g", 45, None)]),
    ("Cinnamon", "Grocery", [("loose", "50g", 35, None)]),
    ("Cloves", "Grocery", [("loose", "50g", 60, None)]),
    ("Cardamom", "Grocery", [("loose", "50g", 120, None)]),
    ("Bay Leaf", "Grocery", [("loose", "25g", 20, None)]),
    ("Asafoetida (Hing)", "Grocery", [("Everest", "50g", 65, 4.2)]),
    ("Besan (Gram Flour)", "Grocery", [("Rajdhani", "1kg", 95, 4.2)]),
    ("Poha", "Grocery", [("loose", "500g", 45, None)]),
    ("Semolina (Suji)", "Grocery", [("Rajdhani", "1kg", 55, 4.1)]),
    ("Sabudana", "Grocery", [("loose", "500g", 60, None)]),
    ("Vermicelli", "Grocery", [("Bambino", "200g", 40, 4.0)]),
    ("Corn Flakes", "Grocery", [("Kellogg's", "500g", 210, 4.3)]),
    ("Oats", "Grocery", [("Quaker", "1kg", 180, 4.5)]),
    ("Muesli", "Grocery", [("Bagrry's", "500g", 220, 4.3)]),
    ("Soya Chunks", "Grocery", [("Nutrela", "200g", 45, 4.2)]),
    ("Glucose Biscuits", "Grocery", [("Parle-G", "200g", 20, 4.4)]),
    ("Cream Biscuits", "Grocery", [("Britannia Good Day", "150g", 30, 4.3)]),
    ("Rusk", "Grocery", [("Britannia", "300g", 55, 4.1)]),
    ("Namkeen Mix", "Grocery", [("Haldiram's", "200g", 65, 4.3), ("Bikano", "200g", 60, 4.1)]),
    ("Instant Noodles", "Grocery", [("Maggi", "280g (4 pack)", 56, 4.5)]),
    ("Pasta", "Grocery", [("Sunfeast Pasta Treat", "400g", 95, 4.1)]),
    ("Coconut", "Grocery", [("loose", "1 pc", 35, None)]),
    ("Dry Coconut", "Grocery", [("loose", "200g", 60, None)]),
    ("Cashews", "Grocery", [("Nutraj", "500g", 425, 4.3), ("Happilo", "200g", 180, 4.0)]),
    ("Almonds", "Grocery", [("Nutraj", "500g", 480, 4.4)]),
    ("Raisins", "Grocery", [("Nutraj", "200g", 95, 4.2)]),
    ("Honey", "Grocery", [("Dabur", "500g", 210, 4.4)]),
    ("Peanut Butter", "Grocery", [("Pintola", "510g", 320, 4.5)]),
    ("Chocolate Spread", "Grocery", [("Nutella", "350g", 375, 4.6)]),
    ("Tomato Ketchup", "Grocery", [("Kissan", "950g", 145, 4.4), ("Maggi", "950g", 140, 4.3)]),
    ("Soy Sauce", "Grocery", [("Ching's Secret", "200g", 65, 4.2)]),
    ("Schezwan Sauce", "Grocery", [("Ching's Secret", "250g", 95, 4.3)]),
    ("Mayonnaise", "Grocery", [("Veeba", "250g", 95, 4.2)]),
    ("Mango Pickle", "Grocery", [("Mother's Recipe", "400g", 120, 4.4)]),
    ("Papad", "Grocery", [("Lijjat", "200g", 65, 4.3)]),
    ("Cornflour", "Grocery", [("Weikfield", "100g", 30, 4.1)]),
    ("Baking Powder", "Grocery", [("Weikfield", "100g", 35, 4.0)]),
    ("Baking Soda", "Grocery", [("Weikfield", "100g", 25, 4.0)]),
    ("Yeast", "Grocery", [("Gloripan", "50g", 45, 4.1)]),
    ("Custard Powder", "Grocery", [("Weikfield", "200g", 65, 4.2)]),
    ("Vanilla Ice Cream", "Grocery", [("Amul", "700ml", 150, 4.4)]),
    ("Frozen Paratha", "Grocery", [("ID Fresh", "5 pcs", 90, 4.2)]),
    ("Chocolate Bar", "Grocery", [("Cadbury Dairy Milk", "50g", 50, 4.6)]),
    ("Aerated Drink", "Grocery", [("Coca-Cola", "750ml", 40, 4.2), ("Pepsi", "750ml", 40, 4.1)]),
    ("Fruit Juice", "Grocery", [("Tropicana", "1L", 115, 4.3), ("Real", "1L", 110, 4.2)]),
    ("Energy Drink", "Grocery", [("Sting", "250ml", 20, 4.0)]),

    # --- Household & Cleaning ---
    ("Floor Cleaner", "Cleaning", [("Lizol", "975ml", 199, 4.5), ("Domex", "1L", 180, 4.2)]),
    ("Glass Cleaner", "Cleaning", [("Colin", "500ml", 99, 4.4)]),
    ("Toilet Cleaner", "Cleaning", [("Harpic", "1L", 115, 4.5), ("Domex", "1L", 110, 4.3)]),
    ("Bathroom Cleaner", "Cleaning", [("Harpic Bathroom", "500ml", 105, 4.3)]),
    ("Phenyl", "Cleaning", [("Kiwikleen", "1L", 85, 4.0)]),
    ("Dishwash Liquid", "Cleaning", [("Vim", "500ml", 110, 4.5), ("Pril", "425ml", 99, 4.2)]),
    ("Dishwash Bar", "Cleaning", [("Vim", "155g x3", 45, 4.4)]),
    ("Detergent Powder", "Cleaning", [("Surf Excel", "1kg", 130, 4.5), ("Ariel", "1kg", 145, 4.4)]),
    ("Detergent Liquid", "Cleaning", [("Surf Excel Matic", "1L", 220, 4.4)]),
    ("Fabric Softener", "Cleaning", [("Comfort", "860ml", 165, 4.3)]),
    ("Liquid Blue (Fabric Whitener)", "Cleaning", [("Ujala", "180ml", 45, 4.1)]),
    ("Stain Remover", "Cleaning", [("Vanish", "500ml", 210, 4.3)]),
    ("Handwash", "Cleaning", [("Dettol", "200ml", 99, 4.5), ("Lifebuoy", "190ml", 85, 4.2)]),
    ("Hand Sanitizer", "Cleaning", [("Dettol", "200ml", 120, 4.4)]),
    ("Room Freshener", "Cleaning", [("Godrej Aer", "220ml", 165, 4.3)]),
    ("Air Freshener Spray", "Cleaning", [("Odonil", "270ml", 145, 4.2)]),
    ("Naphthalene Balls", "Cleaning", [("Odopic", "200g", 55, 4.0)]),
    ("Mosquito Repellent", "Cleaning", [("Good Knight", "45ml refill", 85, 4.4), ("All Out", "45ml refill", 80, 4.3)]),
    ("Cockroach Gel", "Cleaning", [("HIT", "35g", 145, 4.3)]),
    ("Rat Glue Trap", "Cleaning", [("Lizol", "1 pc", 40, 3.9)]),
    ("Garbage Bags", "Cleaning", [("Ecogen", "30 pcs, Medium", 95, 4.2)]),
    ("Scrub Pad", "Cleaning", [("Scotch-Brite", "2 pcs", 45, 4.3)]),
    ("Utensil Scrub Bar", "Cleaning", [("Vim", "1 pc", 20, 4.2)]),
    ("Sponge Wipe", "Cleaning", [("Scotch-Brite", "1 pc", 35, 4.1)]),
    ("Wet Wipes", "Cleaning", [("Bella", "80 pcs", 145, 4.2)]),
    ("Broom", "Cleaning", [("Gala", "1 pc", 120, 4.2)]),
    ("Mop", "Cleaning", [("Scotch-Brite", "1 pc", 250, 4.3)]),
    ("Cleaning Gloves", "Cleaning", [("Tuffy", "1 pair", 55, 4.0)]),
    ("Shoe Polish", "Cleaning", [("Cherry Blossom", "50ml", 45, 4.1)]),
    ("Shoe Brush", "Cleaning", [("loose", "1 pc", 60, None)]),
    ("Toilet Paper", "Cleaning", [("Origami", "4 rolls", 145, 4.3)]),
    ("Tissue Paper", "Cleaning", [("Origami", "100 pulls", 65, 4.2)]),
]


def build_catalog():
    catalog = []
    for idx, (item, category, variants) in enumerate(CATALOG_DATA):
        for v_idx, (brand, size, price, rating) in enumerate(variants):
            platform = "Blinkit" if (idx + v_idx) % 2 == 0 else "Zepto"
            catalog.append({
                "item": item,
                "category": category,
                "brand": brand,
                "size": size,
                "price": price,
                "rating": rating,
                "rating_count": mock_rating_count(rating),
                "platform": platform,
            })
    return catalog


if __name__ == "__main__":
    catalog = build_catalog()
    unique_items = len(CATALOG_DATA)
    with open("data/catalog/mock_catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(catalog)} SKU lines across {unique_items} unique items.")
    print("Saved to data/catalog/mock_catalog.json")