import random
import pandas as pd
import os
from data.georgia_real_data import GEORGIA_ECONOMIC_INDICATORS

class Store:
    def __init__(self, name, products_df):
        self.name = name
        self.products = products_df # DataFrame of products in this store
        self.sales_history = {} # product_id -> count of sales

    def get_price(self, product_id):
        row = self.products[self.products['id'] == product_id]
        if not row.empty:
            return float(row.iloc[0]['price'])
        return 999.0
    
    def record_sale(self, product_id):
        self.sales_history[product_id] = self.sales_history.get(product_id, 0) + 1

    def adjust_prices_by_demand(self):
        """Dynamic pricing: Increase price if demand is high."""
        for idx, row in self.products.iterrows():
            p_id = row['id']
            sales = self.sales_history.get(p_id, 0)
            if sales > 50: # Threshold for high demand
                self.products.at[idx, 'price'] *= 1.05
            elif sales < 2:
                self.products.at[idx, 'price'] *= 0.98
        self.sales_history = {} # Reset

    def get_random_by_category(self, category):
        cat_prods = self.products[self.products['category'] == category]
        if not cat_prods.empty:
            return cat_prods.sample(1).iloc[0].to_dict()
        return None

class Market:
    """Enhanced market with real product data ingestion and macro hooks.
    
    Supports live retail data through the shared retail connector.
    In practice this means:
    - try Supabase if configured
    - otherwise use local SQLite retail_data.db
    - fall back to a tiny mock store set only if both fail
    """
    
    def __init__(self, data_path="data/raw/georgian_market.csv", use_live_data=False, city_slug="tbilisi"):
        self.stores = []
        self.inflation_index = 1.0
        self.use_live_data = use_live_data
        self.city_slug = city_slug
        # ── Geostat macro parameters ───────────────────────────────────────
        macro = GEORGIA_ECONOMIC_INDICATORS
        self.annual_inflation = macro.get("inflation_rate_annual", 0.02)
        self.daily_inflation = self.annual_inflation / 365  # micro-adjustments per day
        
        if use_live_data:
            self._init_from_supabase()
        elif os.path.exists(data_path):
            self.raw_data = pd.read_csv(data_path)
            self.initialize_stores_from_data()
        else:
            self.initialize_mock_stores()
    
    def _init_from_supabase(self):
        """Load real-time product data. Try Supabase first, then local SQLite retail_data.db."""
        from data_pipeline.retail_connector import RetailConnector, DB_URL as RETAIL_DB_URL

        # Try Supabase if configured
        if RETAIL_DB_URL:
            try:
                connector = RetailConnector()
                self.raw_data = connector.to_market_dataframe(city_slug=self.city_slug)
                if not self.raw_data.empty:
                    self.initialize_stores_from_data()
                    print(f"✅ Live retail data loaded from Supabase: {len(self.raw_data)} products from {self.raw_data['store'].nunique()} stores")
                    return
                print("⚠️ Supabase retail data empty — trying local SQLite.")
            except Exception as e:
                print(f"⚠️ Could not load Supabase retail data: {e}")
                print("   Trying local SQLite fallback.")

        # Fallback to local SQLite
        try:
            connector = RetailConnector(db_url="sqlite")
            self.raw_data = connector.to_market_dataframe(city_slug=self.city_slug)
            if self.raw_data.empty:
                print("⚠️ Local retail data empty — falling back to mock stores.")
                self.initialize_mock_stores()
            else:
                self.initialize_stores_from_data()
                print(f"✅ Local retail data loaded: {len(self.raw_data)} products from {self.raw_data['store'].nunique()} stores")
        except Exception as e:
            print(f"⚠️ Could not load local retail data: {e}")
            print("   Falling back to mock stores.")
            self.initialize_mock_stores()

    def process_macro_cycle(self):
        """Called periodically to adjust global economy."""
        # Apply daily Geostat inflation (micro-adjustment)
        if self.daily_inflation > 0:
            self.apply_global_inflation(self.daily_inflation)
        
        # Random shock (0.1% chance per day) — capped at 2× daily rate
        if random.random() < 0.001:
            shock = self.daily_inflation * 2
            self.apply_global_inflation(shock)
            print(f"!!! MACRO ALERT: Inflation shock ({shock*100:.3f}%) detected !!!")
        
        for store in self.stores:
            store.adjust_prices_by_demand()

    def apply_global_inflation(self, rate):
        self.inflation_index *= (1 + rate)
        for store in self.stores:
            store.products['price'] *= (1 + rate)

    def initialize_stores_from_data(self):
        store_names = self.raw_data['store'].unique()
        for s_name in store_names:
            store_df = self.raw_data[self.raw_data['store'] == s_name]
            self.stores.append(Store(s_name, store_df))

    def initialize_mock_stores(self):
        # Fallback if CSV is missing
        data = [
            {"id": "m1", "name": "Milk 1L", "price": 4.5, "category": "Dairy", "store": "Spar"},
            {"id": "b1", "name": "Bread", "price": 1.2, "category": "Bakery", "store": "Spar"},
            {"id": "m1", "name": "Milk 1L", "price": 4.1, "category": "Dairy", "store": "Magniti"},
        ]
        self.raw_data = pd.DataFrame(data)
        self.initialize_stores_from_data()

    def get_cheapest_store_for_product(self, product_name):
        # Find product by name across all stores to find cheapest
        options = self.raw_data[self.raw_data['name'].str.contains(product_name, case=False)]
        if options.empty: return None
        cheapest = options.sort_values('price').iloc[0]
        store = next((s for s in self.stores if s.name == cheapest['store']), self.stores[0])
        return store, cheapest.to_dict()

    def get_stores(self):
        return self.stores
