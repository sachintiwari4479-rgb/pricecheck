import streamlit as st
import requests
import json
import warnings
import pandas as pd
import os
from pandas.errors import SettingWithCopyWarning
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# --- CONFIGURATION & WARNING SUPPRESSION ---
warnings.simplefilter('ignore', InsecureRequestWarning)
warnings.filterwarnings("ignore", category=SettingWithCopyWarning)

# --- CONSTANTS ---
DEALS_FILE = "jiomart_hot_deals.csv"
# BASE_URL fallback if direct URI is missing
BASE_URL = "https://www.jiomart.com/"

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="JioMart Price Analyzer",
    page_icon="🛒",
    layout="wide"
)

# --- CUSTOM CSS FOR ATTRACTIVE UI ---
st.markdown("""
    <style>
    .product-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
        transition: transform 0.2s;
    }
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 12px rgba(0,0,0,0.15);
    }
    .hot-deal-card {
        background-color: #fff5f5;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.2);
        margin-bottom: 20px;
        border: 2px solid #ff4b4b;
        position: relative;
        transition: transform 0.2s;
    }
    .hot-deal-card:hover {
        transform: translateY(-5px);
    }
    .card-img-top {
        width: 100%;
        height: 180px;
        object-fit: contain;
        margin-bottom: 12px;
        border-radius: 8px;
    }
    .deal-badge {
        background-color: #ff4b4b;
        color: white;
        padding: 5px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8em;
        display: inline-block;
        margin-bottom: 10px;
    }
    .price-main {
        font-size: 1.4em;
        font-weight: bold;
        color: #1f77b4;
    }
    .price-mrp {
        text-decoration: line-through;
        color: #888;
        font-size: 0.9em;
    }
    .metric-box {
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 8px;
        text-align: center;
    }
    /* Link Button Styling */
    a.product-link {
        text-decoration: none;
        background-color: #007bff;
        color: white !important;
        padding: 8px 15px;
        border-radius: 5px;
        font-size: 0.9em;
        display: block;
        margin-top: 15px;
        text-align: center;
    }
    a.product-link:hover {
        background-color: #0056b3;
    }
    </style>
""", unsafe_allow_html=True)


# --- HELPER FUNCTIONS FOR AUTO-SAVE ---
def load_saved_deals():
    if os.path.exists(DEALS_FILE):
        return pd.read_csv(DEALS_FILE)
    # Added 'Product_URL' to columns
    return pd.DataFrame(
        columns=["Title", "Selling_Price", "MRP", "Discount_Percent", "Store_ID", "Reference_Label", "Product_URL",
                 "Date_Added"])


def save_deals_to_csv(new_deals):
    if not new_deals:
        return 0

    existing_df = load_saved_deals()
    new_df = pd.DataFrame(new_deals)
    new_df['Date_Added'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')

    if not existing_df.empty:
        # Filter duplicates based on Title and Selling Price
        existing_keys = set(zip(existing_df["Title"], existing_df["Selling_Price"]))
        new_df = new_df[~new_df.apply(lambda x: (x["Title"], x["Selling_Price"]) in existing_keys, axis=1)]

    if not new_df.empty:
        # Align columns to ensure URL field exists if appending to old CSV
        if not existing_df.empty and "Product_URL" not in existing_df.columns:
            existing_df["Product_URL"] = ""

        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
        updated_df.to_csv(DEALS_FILE, index=False)
        return len(new_df)
    return 0


# --- APP HEADER ---
st.title("🛒 JioMart Price Analyzer")
st.markdown("Search for products and find the **best rates**, **discounts**, and **hidden deals**.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Saved Deals")
    st.info("Products with >40% discount are auto-saved here.")

    # Session state initialization for toggle
    if "show_saved_list" not in st.session_state:
        st.session_state.show_saved_list = False

    # Toggle Button
    if st.button("Toggle Saved List"):
        st.session_state.show_saved_list = not st.session_state.show_saved_list

    # Show List Logic
    if st.session_state.show_saved_list:
        df_saved = load_saved_deals()
        if not df_saved.empty:
            # Configure dataframe to show links as clickable
            st.dataframe(
                df_saved,
                hide_index=True,
                column_config={
                    "Product_URL": st.column_config.LinkColumn("Link")
                }
            )

            # Download Button
            csv = df_saved.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download CSV",
                csv,
                "jiomart_hot_deals.csv",
                "text/csv",
                key='download-csv'
            )

            # Clear List Button (Now works correctly because it's not nested in a False state)
            if st.button("🗑️ Clear Saved List"):
                if os.path.exists(DEALS_FILE):
                    os.remove(DEALS_FILE)
                    st.success("List cleared!")
                    # Reload the page to reflect changes
                    st.rerun()
        else:
            st.warning("No deals saved yet.")

# --- MAIN INPUT ---
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Enter Product Name (e.g., 'Mother Dairy', 'Ghee')",
                              placeholder="Type product name here...")
    with col2:
        st.write("")  # Spacer
        st.write("")  # Spacer
        search_clicked = st.button("🔍 Search & Analyze", use_container_width=True, type="primary")


# --- ANALYSIS LOGIC ---
def analyze_product_variants(buybox_mrp_lines):
    try:
        df = pd.DataFrame([line.split('|') for line in buybox_mrp_lines])

        if df.empty or df.shape[1] < 9:
            return None

        # Column mapping
        df.columns = [f"Col_{i}" for i in range(df.shape[1])]
        df.rename(columns={'Col_0': 'Store_ID', 'Col_4': 'MRP', 'Col_5': 'Selling_Price', 'Col_8': 'Discount_Percent'},
                  inplace=True)

        # Data Cleaning
        df_prices = df[['Store_ID', 'MRP', 'Selling_Price', 'Discount_Percent']].copy()
        df_prices['MRP'] = pd.to_numeric(df_prices['MRP'], errors='coerce').fillna(0)
        df_prices['Selling_Price'] = pd.to_numeric(df_prices['Selling_Price'], errors='coerce').fillna(float('inf'))
        df_prices['Discount_Percent'] = pd.to_numeric(df_prices['Discount_Percent'], errors='coerce').fillna(0)

        df_prices = df_prices[df_prices['Selling_Price'] != float('inf')]

        if df_prices.empty:
            return None

        # Analysis
        best_rate = df_prices.loc[df_prices['Selling_Price'].idxmin()]
        # Sort unique selling prices ascending (Lowest to Highest)
        top_prices = df_prices.sort_values(by='Selling_Price').drop_duplicates(subset=['Selling_Price'])

        # Determine Reference Price (Prioritize 3rd lowest, then 2nd lowest)
        reference_price = 0
        ref_label = ""
        valid_comparison = False

        if len(top_prices) >= 3:
            reference_price = top_prices.iloc[2]['Selling_Price']  # 3rd Lowest
            ref_label = "vs 3rd Best"
            valid_comparison = True
        elif len(top_prices) == 2:
            reference_price = top_prices.iloc[1]['Selling_Price']  # 2nd Lowest
            ref_label = "vs 2nd Best"
            valid_comparison = True
        else:
            # Only 1 unique price available, no comparison possible against other sellers
            reference_price = best_rate['Selling_Price']
            ref_label = "Best Price"
            valid_comparison = False

        # Calculate Discount based on Reference Price (NOT MRP)
        best_price = best_rate['Selling_Price']
        diff = reference_price - best_price

        pct_less = 0.0
        if valid_comparison and reference_price > 0:
            pct_less = (diff / reference_price * 100)

        comparison_data = {
            "valid": valid_comparison,
            "ref_price": reference_price,
            "ref_label": ref_label,
            "pct_less": pct_less
        }

        return {
            "best": best_rate,
            "top_3": top_prices.head(3),
            "comparison": comparison_data
        }

    except Exception as e:
        return None


# --- MAIN SEARCH LOGIC ---
if search_clicked and query:
    with st.spinner(f"Searching JioMart for '{query}'..."):
        try:
            url = "https://www.jiomart.com/trex/autoSearch"

            headers = {
                "Host": "www.jiomart.com",
                "Connection": "keep-alive",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                "Content-Type": "application/json",
                "Accept": "*/*",
                "Origin": "https://www.jiomart.com",
                "Referer": f"https://www.jiomart.com/search?q={query}",
                "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,hi;q=0.7",
                "Cache-Control": "no-cache",
                # NOTE: Cookies expire. If the script stops working, update this string.
                "Cookie": "ajs_anonymous_id=6f8e1a0f-6c90-439f-918f-003969e5fe4a; _ga_F1NJ1E2HJ2=GS2.1.s1751013819$o1$g1$t1751013834$j45$l0$h0; _gcl_au=1.1.1033579185.1764401199; _ALGOLIA=anonymous-90064b63-ef63-45e4-842b-d6c4a9d03047; new_customer=false; WZRK_G=ffb84e9eec5d4ad69e4d18473fd1d87e; nms_mgo_state_code=RJ; _gid=GA1.2.1806390998.1765188925; nms_mgo_city=Jodhpur; nms_mgo_pincode=342003; _ga=GA1.1.1362582137.1751012504; AKA_A2=A; RT=\"z=1&dm=www.jiomart.com&si=8dddc3d9-4195-40f7-8c8a-37b94d74d8e1&ss=miyuco88&sl=1&tt=1lr&rl=1\"; __tr_luptv=1765300564122; WZRK_S_88R-W4Z-495Z=%7B%22s%22%3A1765299718%2C%22t%22%3A1765300612%2C%22p%22%3A7%7D; _ga_XHR9Q2M3VV=GS2.1.s1765299723$o37$g1$t1765300612$j57$l1$h1151985791"
            }

            payload = {
                "query": query,
                "pageSize": 50,
                "visitorId": "anonymous-6465068b-fd56-4e0e-8cba-cc31da8dbe7f",
                "filter": "attributes.status:ANY(\"active\") AND (attributes.mart_availability:ANY(\"JIO\", \"JIO_WA\")) AND (attributes.available_regions:ANY(\"PANINDIABOOKS\", \"PANINDIACRAFT\", \"PANINDIADIGITAL\", \"PANINDIAFASHION\", \"PANINDIAFURNITURE\", \"TH91\", \"PANINDIAGROCERIES\", \"PANINDIAHOMEANDKITCHEN\", \"PANINDIAHOMEIMPROVEMENT\", \"PANINDIAJEWEL\", \"PANINDIALOCALSHOPS\", \"PANINDIASTL\", \"PANINDIAWELLNESS\")) AND ((attributes.inv_stores_1p:ANY(\"ALL\", \"U3FP\", \"VLOR\", \"254\", \"N892\", \"60\", \"270\", \"SF11\", \"SF40\", \"SX9A\", \"SC28\", \"SK1M\", \"R810\", \"SZ9U\", \"R696\", \"SJ93\", \"R396\", \"SE40\", \"S3TP\", \"SLKO\", \"R406\") OR attributes.inv_stores_3p:ANY(\"ALL\", \"3PQXWBTGFC02\", \"3PS0T7LTFC06\", \"3PKXPHZAFC02\", \"3PQZUIDAFC02\", \"3PUSUYR4FC03\", \"3P7IYTP8FC04\", \"3PPKDT3ONFC26\", \"3P87THZUFC02\", \"3P0YYXK1FC01\", \"3PMXGPK6FC02\", \"3PPJ4O5I8FC07\", \"3PCGEVZFFC03\", \"3PT79I5BFC02\", \"3PMBAR4CFC04\", \"groceries_zone_non-essential_services\", \"general_zone\", \"groceries_zone_essential_services\", \"fashion_zone\", \"electronics_zone\"))) AND ( NOT attributes.vertical_code:ANY(\"ALCOHOL\"))",
                "canonicalFilter": "attributes.status:ANY(\"active\") AND (attributes.mart_availability:ANY(\"JIO\", \"JIO_WA\")) AND (attributes.available_regions:ANY(\"PANINDIABOOKS\", \"PANINDIACRAFT\", \"PANINDIADIGITAL\", \"PANINDIAFASHION\", \"PANINDIAFURNITURE\", \"TH91\", \"PANINDIAGROCERIES\", \"PANINDIAHOMEANDKITCHEN\", \"PANINDIAHOMEIMPROVEMENT\", \"PANINDIAJEWEL\", \"PANINDIALOCALSHOPS\", \"PANINDIASTL\", \"PANINDIAWELLNESS\")) AND ((attributes.inv_stores_1p:ANY(\"ALL\", \"U3FP\", \"VLOR\", \"254\", \"N892\", \"60\", \"270\", \"SF11\", \"SF40\", \"SX9A\", \"SC28\", \"SK1M\", \"R810\", \"SZ9U\", \"R696\", \"SJ93\", \"R396\", \"SE40\", \"S3TP\", \"SLKO\", \"R406\") OR attributes.inv_stores_3p:ANY(\"ALL\", \"3PQXWBTGFC02\", \"3PS0T7LTFC06\", \"3PKXPHZAFC02\", \"3PQZUIDAFC02\", \"3PUSUYR4FC03\", \"3P7IYTP8FC04\", \"3PPKDT3ONFC26\", \"3P87THZUFC02\", \"3P0YYXK1FC01\", \"3PMXGPK6FC02\", \"3PPJ4O5I8FC07\", \"3PCGEVZFFC03\", \"3PT79I5BFC02\", \"3PMBAR4CFC04\", \"groceries_zone_non-essential_services\", \"general_zone\", \"groceries_zone_essential_services\", \"fashion_zone\", \"electronics_zone\"))) AND ( NOT attributes.vertical_code:ANY(\"ALCOHOL\"))",
                "searchMode": "PRODUCT_SEARCH_ONLY",
                "branch": "projects/sr-project-jiomart-jfront-prod/locations/global/catalogs/default_catalog/branches/0",
                "userInfo": {"userId": "9085981DD77759FDB8984C4EBF9A14B02DC30F7B9D15776719EF587A723C3E24"},
                "spellCorrectionSpec": {"mode": "AUTO"},
                "queryExpansionSpec": {"condition": "AUTO", "pinUnexpandedResults": True}
            }

            response = requests.post(url, headers=headers, json=payload, verify=False)
            response.raise_for_status()
            data = response.json()
            results = data.get('results', [])

            if not results:
                st.warning(f"No results found for '{query}'.")
            else:
                st.success(f"Found {len(results)} products (Showing Top 50).")

                # --- LAYOUT: 2 PRODUCTS PER ROW ---
                cols = st.columns(2)

                # List to collect Hot Deals for auto-saving
                hot_deals_to_save = []

                for i, result in enumerate(results):
                    product = result.get('product', {})
                    title = product.get('title', 'Unknown Product')

                    # --- DATA EXTRACTION (Updated) ---
                    # Access the first variant which contains specific images and links
                    variants = product.get('variants', [{}])
                    first_variant = variants[0] if variants else {}
                    variant_attrs = first_variant.get('attributes', {})

                    # 1. Product Link Extraction
                    product_link = ""

                    # Candidates for URL in order of preference
                    candidates = [
                        product.get('uri'),  # Root URI
                        first_variant.get('uri'),  # Variant URI
                        variant_attrs.get('uri'),  # Variant Attributes URI
                        product.get('url_path'),  # Root URL Path
                        first_variant.get('url_path')  # Variant URL Path
                    ]

                    for candidate in candidates:
                        if candidate:
                            if isinstance(candidate, str) and candidate.startswith('http'):
                                product_link = candidate
                            elif isinstance(candidate, str):
                                product_link = f"{BASE_URL}{candidate.lstrip('/')}"

                            if product_link:
                                break

                    if not product_link:
                        product_link = "https://www.jiomart.com"

                    # 2. Product Image Extraction
                    # Primary: variants -> images -> uri
                    image_url = ""
                    variant_images = first_variant.get('images', [])
                    if variant_images:
                        image_url = variant_images[0].get('uri', '')

                    # Fallback: product root -> images -> uri/url
                    if not image_url:
                        root_images = product.get('images', [])
                        if root_images:
                            image_url = root_images[0].get('uri', '') or root_images[0].get('url', '')

                    if not image_url:
                        image_url = "https://www.jiomart.com/assets/ds2web/jds-icons/jiomart-logo.svg"

                    buybox_text = variant_attrs.get('buybox_mrp', {}).get('text')

                    if buybox_text:
                        analysis = analyze_product_variants(buybox_text)

                        if analysis:
                            best = analysis['best']
                            comp = analysis['comparison']

                            # LOGIC: Strictly use the calculated pct_less for badge and metrics
                            discount_pct = comp['pct_less']
                            discount_label = comp['ref_label'] if comp['valid'] else "Discount (N/A)"

                            is_hot_deal = discount_pct > 40

                            # --- AUTO SAVE LOGIC ---
                            if is_hot_deal:
                                hot_deals_to_save.append({
                                    "Title": title,
                                    "Selling_Price": best["Selling_Price"],
                                    "MRP": best["MRP"],
                                    "Discount_Percent": discount_pct,
                                    "Store_ID": best["Store_ID"],
                                    "Reference_Label": discount_label,
                                    "Product_URL": product_link
                                })

                            # --- RENDER CARD ---
                            card_class = "hot-deal-card" if is_hot_deal else "product-card"

                            # Use alternating columns for grid layout
                            with cols[i % 2]:
                                with st.container():
                                    st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

                                    # Product Image
                                    st.markdown(f'<img src="{image_url}" class="card-img-top">', unsafe_allow_html=True)

                                    # Title & Badge
                                    st.markdown(f"<h5>{i + 1}. {title}</h5>", unsafe_allow_html=True)
                                    if is_hot_deal:
                                        st.markdown(f'<span class="deal-badge">🔥 {discount_pct:.1f}% OFF</span>',
                                                    unsafe_allow_html=True)

                                    # Metrics
                                    m1, m2 = st.columns(2)
                                    with m1:
                                        st.markdown(
                                            f'<div class="metric-box"><div class="price-mrp">MRP ₹{best["MRP"]:.2f}</div><div class="price-main">₹{best["Selling_Price"]:.2f}</div></div>',
                                            unsafe_allow_html=True)
                                    with m2:
                                        st.metric(discount_label, f"{discount_pct:.1f}%")
                                        st.caption(f"Store: {best['Store_ID']}")

                                    # Insight
                                    if comp['valid']:
                                        st.info(
                                            f"Save **{comp['pct_less']:.1f}%** compared to the {comp['ref_label']} (₹{comp['ref_price']:.2f}).")
                                    else:
                                        st.info("Comparison: Only 1 seller available (0% discount relative to others).")

                                    # Link Button
                                    st.markdown(
                                        f'<a href="{product_link}" target="_blank" class="product-link">🔗 View on JioMart</a>',
                                        unsafe_allow_html=True)

                                    # Expandable Data
                                    with st.expander("Compare Prices"):
                                        st.dataframe(
                                            analysis['top_3'][['Selling_Price', 'MRP', 'Discount_Percent', 'Store_ID']],
                                            hide_index=True,
                                            use_container_width=True
                                        )

                                    st.markdown('</div>', unsafe_allow_html=True)

                # --- PROCESS AUTO SAVE ---
                if hot_deals_to_save:
                    saved_count = save_deals_to_csv(hot_deals_to_save)
                    if saved_count > 0:
                        st.toast(f"✅ Auto-saved {saved_count} new hot deals to Saved List!", icon="💾")

        except Exception as e:
            st.error(f"An error occurred: {e}")

elif search_clicked and not query:
    st.warning("Please enter a product name to search.")
