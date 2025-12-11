import streamlit as st
import requests
import json
import warnings
import pandas as pd
from pandas.errors import SettingWithCopyWarning
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# --- CONFIGURATION & WARNING SUPPRESSION ---
warnings.simplefilter('ignore', InsecureRequestWarning)
warnings.filterwarnings("ignore", category=SettingWithCopyWarning)

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
    }
    .hot-deal-card {
        background-color: #fff5f5;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.2);
        margin-bottom: 20px;
        border: 2px solid #ff4b4b;
        position: relative;
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
        font-size: 1.5em;
        font-weight: bold;
        color: #1f77b4;
    }
    .price-mrp {
        text-decoration: line-through;
        color: #888;
        font-size: 1em;
    }
    .metric-box {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- APP HEADER ---
st.title("🛒 JioMart Price Analyzer")
st.markdown("Search for products and find the **best rates**, **discounts**, and **hidden deals**.")

# --- SIDEBAR / INPUT ---
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
        top_3 = df_prices.sort_values(by='Selling_Price').drop_duplicates(subset=['Selling_Price']).head(3)

        # 3rd Best Comparison
        comparison_data = {}
        if len(top_3) >= 3:
            third_best = top_3.iloc[2]['Selling_Price']
            best = best_rate['Selling_Price']
            diff = third_best - best
            pct_less = (diff / third_best * 100) if third_best > 0 else 0
            comparison_data = {
                "valid": True,
                "third_price": third_best,
                "pct_less": pct_less
            }
        else:
            comparison_data = {"valid": False}

        return {
            "best": best_rate,
            "top_3": top_3,
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
                "Cookie": "ajs_anonymous_id=6f8e1a0f-6c90-439f-918f-003969e5fe4a; _ga_F1NJ1E2HJ2=GS2.1.s1751013819$o1$g1$t1751013834$j45$l0$h0; _gcl_au=1.1.1033579185.1764401199; _ALGOLIA=anonymous-90064b63-ef63-45e4-842b-d6c4a9d03047; new_customer=false; WZRK_G=ffb84e9eec5d4ad69e4d18473fd1d87e; nms_mgo_state_code=RJ; _gid=GA1.2.1806390998.1765188925; nms_mgo_city=Jodhpur; nms_mgo_pincode=342003; _ga=GA1.1.1362582137.1751012504; AKA_A2=A; RT=\"z=1&dm=www.jiomart.com&si=8dddc3d9-4195-40f7-8c8a-37b94d74d8e1&ss=miyuco88&sl=1&tt=1lr&rl=1\"; __tr_luptv=1765300564122; WZRK_S_88R-W4Z-495Z=%7B%22s%22%3A1765299718%2C%22t%22%3A1765300612%2C%22p%22%3A7%7D; _ga_XHR9Q2M3VV=GS2.1.s1765299723$o37$g1$t1765300612$j57$l1$h1151985791"
            }

            payload = {"query":query,"pageSize":50,"visitorId":"anonymous-6465068b-fd56-4e0e-8cba-cc31da8dbe7f","filter":"attributes.status:ANY(\"active\") AND (attributes.mart_availability:ANY(\"JIO\", \"JIO_WA\")) AND (attributes.available_regions:ANY(\"PANINDIABOOKS\", \"PANINDIACRAFT\", \"PANINDIADIGITAL\", \"PANINDIAFASHION\", \"PANINDIAFURNITURE\", \"TH91\", \"PANINDIAGROCERIES\", \"PANINDIAHOMEANDKITCHEN\", \"PANINDIAHOMEIMPROVEMENT\", \"PANINDIAJEWEL\", \"PANINDIALOCALSHOPS\", \"PANINDIASTL\", \"PANINDIAWELLNESS\")) AND ((attributes.inv_stores_1p:ANY(\"ALL\", \"U3FP\", \"VLOR\", \"254\", \"N892\", \"60\", \"270\", \"SF11\", \"SF40\", \"SX9A\", \"SC28\", \"SK1M\", \"R810\", \"SZ9U\", \"R696\", \"SJ93\", \"R396\", \"SE40\", \"S3TP\", \"SLKO\", \"R406\") OR attributes.inv_stores_3p:ANY(\"ALL\", \"3PQXWBTGFC02\", \"3PS0T7LTFC06\", \"3PKXPHZAFC02\", \"3PQZUIDAFC02\", \"3PUSUYR4FC03\", \"3P7IYTP8FC04\", \"3PPKDT3ONFC26\", \"3P87THZUFC02\", \"3P0YYXK1FC01\", \"3PMXGPK6FC02\", \"3PPJ4O5I8FC07\", \"3PCGEVZFFC03\", \"3PT79I5BFC02\", \"3PMBAR4CFC04\", \"groceries_zone_non-essential_services\", \"general_zone\", \"groceries_zone_essential_services\", \"fashion_zone\", \"electronics_zone\"))) AND ( NOT attributes.vertical_code:ANY(\"ALCOHOL\"))","canonicalFilter":"attributes.status:ANY(\"active\") AND (attributes.mart_availability:ANY(\"JIO\", \"JIO_WA\")) AND (attributes.available_regions:ANY(\"PANINDIABOOKS\", \"PANINDIACRAFT\", \"PANINDIADIGITAL\", \"PANINDIAFASHION\", \"PANINDIAFURNITURE\", \"TH91\", \"PANINDIAGROCERIES\", \"PANINDIAHOMEANDKITCHEN\", \"PANINDIAHOMEIMPROVEMENT\", \"PANINDIAJEWEL\", \"PANINDIALOCALSHOPS\", \"PANINDIASTL\", \"PANINDIAWELLNESS\")) AND ((attributes.inv_stores_1p:ANY(\"ALL\", \"U3FP\", \"VLOR\", \"254\", \"N892\", \"60\", \"270\", \"SF11\", \"SF40\", \"SX9A\", \"SC28\", \"SK1M\", \"R810\", \"SZ9U\", \"R696\", \"SJ93\", \"R396\", \"SE40\", \"S3TP\", \"SLKO\", \"R406\") OR attributes.inv_stores_3p:ANY(\"ALL\", \"3PQXWBTGFC02\", \"3PS0T7LTFC06\", \"3PKXPHZAFC02\", \"3PQZUIDAFC02\", \"3PUSUYR4FC03\", \"3P7IYTP8FC04\", \"3PPKDT3ONFC26\", \"3P87THZUFC02\", \"3P0YYXK1FC01\", \"3PMXGPK6FC02\", \"3PPJ4O5I8FC07\", \"3PCGEVZFFC03\", \"3PT79I5BFC02\", \"3PMBAR4CFC04\", \"groceries_zone_non-essential_services\", \"general_zone\", \"groceries_zone_essential_services\", \"fashion_zone\", \"electronics_zone\"))) AND ( NOT attributes.vertical_code:ANY(\"ALCOHOL\"))","searchMode":"PRODUCT_SEARCH_ONLY","branch":"projects/sr-project-jiomart-jfront-prod/locations/global/catalogs/default_catalog/branches/0","userInfo":{"userId":"9085981DD77759FDB8984C4EBF9A14B02DC30F7B9D15776719EF587A723C3E24"},"spellCorrectionSpec":{"mode":"AUTO"},"queryExpansionSpec":{"condition":"AUTO","pinUnexpandedResults":true}}

            response = requests.post(url, headers=headers, json=payload, verify=False)
            response.raise_for_status()
            data = response.json()
            results = data.get('results', [])

            if not results:
                st.warning(f"No results found for '{query}'.")
            else:
                st.success(f"Found {len(results)} products.")

                for i, result in enumerate(results):
                    product = result.get('product', {})
                    title = product.get('title', 'Unknown Product')
                    buybox_text = product.get('variants', [{}])[0].get('attributes', {}).get('buybox_mrp', {}).get(
                        'text')

                    if buybox_text:
                        analysis = analyze_product_variants(buybox_text)

                        if analysis:
                            best = analysis['best']

                            # LOGIC UPDATE: Determine which discount to use
                            # If we have 3rd best comparison data, use THAT as the primary discount for logic/display.
                            # Otherwise, fallback to the standard MRP discount.
                            if analysis['comparison']['valid']:
                                discount_pct = analysis['comparison']['pct_less']
                                discount_label = "vs 3rd Best"
                            else:
                                discount_pct = best['Discount_Percent']
                                discount_label = "Discount"

                            is_hot_deal = discount_pct > 30

                            # --- RENDER CARD ---
                            # Determine class based on discount
                            card_class = "hot-deal-card" if is_hot_deal else "product-card"

                            with st.container():
                                # Open Card HTML wrapper
                                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

                                # Header
                                col_head, col_badge = st.columns([4, 1])
                                with col_head:
                                    st.markdown(f"### {i + 1}. {title}")
                                with col_badge:
                                    if is_hot_deal:
                                        # Show the calculated discount in the badge
                                        st.markdown(f'<span class="deal-badge">🔥 {discount_pct:.1f}% OFF</span>',
                                                    unsafe_allow_html=True)

                                # Main Metrics
                                m_col1, m_col2, m_col3 = st.columns(3)
                                with m_col1:
                                    st.markdown(
                                        f'<div class="metric-box"><div class="price-mrp">MRP ₹{best["MRP"]:.2f}</div><div class="price-main">₹{best["Selling_Price"]:.2f}</div></div>',
                                        unsafe_allow_html=True)
                                with m_col2:
                                    # Show the appropriate discount label
                                    st.metric(discount_label, f"{discount_pct:.1f}%")
                                with m_col3:
                                    st.metric("Store ID", str(best["Store_ID"]))

                                # Comparison Text / Value Insight
                                # If we are already showing the "vs 3rd Best" in the main metric,
                                # we can show the MRP discount here for context.
                                if analysis['comparison']['valid']:
                                    comp = analysis['comparison']
                                    st.info(
                                        f"📉 **Value Insight:** Calculated against 3rd best price (₹{comp['third_price']:.2f}). (Standard MRP Discount is {best['Discount_Percent']}%)")
                                else:
                                    # If only MRP discount is available
                                    st.info(f"ℹ️ **Info:** Standard discount calculated from MRP.")

                                # Data Table (Top 3)
                                with st.expander("See Top 3 Price Options"):
                                    st.dataframe(
                                        analysis['top_3'][['Selling_Price', 'MRP', 'Discount_Percent', 'Store_ID']],
                                        hide_index=True,
                                        use_container_width=True
                                    )

                                # Close Card HTML wrapper
                                st.markdown('</div>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"An error occurred: {e}")

elif search_clicked and not query:

    st.warning("Please enter a product name to search.")

