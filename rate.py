import streamlit as st
import requests
import json
import os
from datetime import datetime
import time

# --- Configuration ---
AUTH_BASE_URL = "https://services.dealshare.in/scmuserservice/api/v1/auth"
LOGISTICS_BASE_URL = "https://services.dealshare.in/logisticservice/api/v1/trip"
LASTMILE_BASE_URL = "https://services.dealshare.in/lastmileservice/api/v1"

ACCOUNTS_FILE = "saved_accounts.json"
STATS_FILE = "daily_stats.json"

BASE_HEADERS = {
    "app-type": "SCM_RIDER_APP",
    "device-id": "62adca42-92bd-4bca-852b-c23792ad139e",
    "app-version": "1.0.0",
    "content-type": "application/json; charset=UTF-8",
    "accept-encoding": "gzip",
    "user-agent": "okhttp/4.12.0",
}

# --- Persistence Functions ---

def load_json(filepath, default_val):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except:
            return default_val
    return default_val

def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

def get_daily_stats():
    stats = load_json(STATS_FILE, {"date": "", "delivered_items": {}, "total_cash": 0, "total_orders": 0})
    today = datetime.now().strftime("%Y-%m-%d")
    # Reset stats if it's a new day
    if stats["date"] != today:
        stats = {"date": today, "delivered_items": {}, "total_cash": 0, "total_orders": 0}
        save_json(STATS_FILE, stats)
    return stats

def update_daily_stats(shipment):
    stats = get_daily_stats()
    
    # Update Items
    skus = shipment.get('skus', [])
    for item in skus:
        name = item.get('name', 'Unknown Item')
        qty = int(item.get('total_quantity', 0))
        stats["delivered_items"][name] = stats["delivered_items"].get(name, 0) + qty
    
    # Update Cash and Orders
    stats["total_cash"] += float(shipment.get('cod_amount', 0))
    stats["total_orders"] += 1
    
    save_json(STATS_FILE, stats)
    return stats

# --- API Functions ---

def api_request(method, url, headers, json_data=None):
    try:
        if method == "GET":
            return requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            return requests.post(url, headers=headers, json=json_data, timeout=10)
        elif method == "PUT":
            return requests.put(url, headers=headers, json=json_data, timeout=10)
    except Exception as e:
        st.error(f"Network Error: {e}")
        return None

# --- UI Components ---

def display_achievement_card(stats):
    st.markdown(f"""
        <div class="metric-card">
            <p style="color: #94a3b8; font-size: 0.8rem; margin: 0;">TODAY'S ACHIEVEMENT</p>
            <h1 style="margin: 0; color: white;">₹{stats['total_cash']:,.0f}</h1>
            <div style="display: flex; gap: 20px; margin-top: 15px; border-top: 1px solid #334155; padding-top: 10px;">
                <div><p style="font-size: 0.7rem; color: #94a3b8; margin:0;">ORDERS</p><b>{stats['total_orders']}</b></div>
                <div><p style="font-size: 0.7rem; color: #94a3b8; margin:0;">TOTAL ITEMS</p><b>{sum(stats['delivered_items'].values())}</b></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if stats["delivered_items"]:
        with st.expander("📊 View Delivered Items Breakdown", expanded=True if st.session_state.step == 'view_stats' else False):
            for name, qty in stats["delivered_items"].items():
                col_n, col_q = st.columns([4, 1])
                col_n.write(f" {name}")
                col_q.write(f"**x{qty}**")

# --- App Logic ---

st.set_page_config(page_title="Rider Pro", page_icon="📦", layout="centered")

# Custom CSS for Mobile Feel
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { border-radius: 12px; height: 3em; font-weight: bold; }
    .metric-card {
        background-color: #1e293b;
        color: white;
        padding: 20px;
        border-radius: 20px;
        margin-bottom: 20px;
    }
    .order-card {
        background-color: white;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #e2e8f0;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'step' not in st.session_state: st.session_state.step = 'login'
if 'auth' not in st.session_state: st.session_state.auth = None
if 'mobile' not in st.session_state: st.session_state.mobile = ""

# --- LOGIN STEP ---
if st.session_state.step == 'login':
    st.title("🚀 Rider Login")
    mobile = st.text_input("Mobile Number", value=st.session_state.mobile, max_chars=10)
    
    col1, col2 = st.columns(2)
    
    if col1.button("Send OTP", use_container_width=True, type="primary"):
        if len(mobile) == 10:
            resp = api_request("POST", f"{AUTH_BASE_URL}/login", BASE_HEADERS, 
                               {"hashCode": "abc123", "mobileNumber": mobile, "provider": "MOBILE_OTP"})
            if resp and resp.status_code == 200:
                st.session_state.mobile = mobile
                st.session_state.step = 'verify'
                st.rerun()
        else:
            st.error("Enter valid 10-digit number")
            
    if col2.button("📊 Total Data", use_container_width=True):
        st.session_state.step = 'view_stats'
        st.rerun()

# --- VIEW STATS STEP (Public Access) ---
elif st.session_state.step == 'view_stats':
    st.title("📈 Daily Summary")
    stats = get_daily_stats()
    display_achievement_card(stats)
    
    if st.button("⬅️ Back to Login", use_container_width=True):
        st.session_state.step = 'login'
        st.rerun()

# --- VERIFY STEP ---
elif st.session_state.step == 'verify':
    st.title("🔑 Verify OTP")
    otp = st.text_input("Enter OTP", type="password")
    if st.button("Login", use_container_width=True, type="primary"):
        resp = api_request("POST", f"{AUTH_BASE_URL}/verify-otp", BASE_HEADERS, 
                           {"mobileNumber": st.session_state.mobile, "otp": otp})
        if resp and resp.status_code == 200:
            data = resp.json().get("data", {})
            st.session_state.auth = {"access": data.get("accessToken"), "refresh": data.get("refreshToken")}
            st.session_state.step = 'dashboard'
            st.rerun()
        else:
            st.error("Invalid OTP")

# --- DASHBOARD STEP ---
elif st.session_state.step == 'dashboard':
    stats = get_daily_stats()
    
    # Sidebar
    with st.sidebar:
        st.write(f"Logged in: **{st.session_state.mobile}**")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    # --- TODAY'S ACHIEVEMENT (MAIN PAGE SUMMARY) ---
    display_achievement_card(stats)

    # Fetch Data Section
    headers = BASE_HEADERS.copy()
    headers["authorization-access"] = st.session_state.auth["access"]
    headers["authorization-refresh"] = st.session_state.auth["refresh"]

    if st.button("🔄 Refresh Orders", use_container_width=True):
        st.cache_data.clear()

    # --- FETCH TRIP DATA ---
    trip_resp = api_request("GET", f"{LOGISTICS_BASE_URL}/assigned-trip", headers)
    if trip_resp and trip_resp.status_code == 200:
        trip_data = trip_resp.json().get("data", {})
        trip_id = trip_data.get("tripId")
        
        if trip_id:
            ship_resp = api_request("GET", f"{LOGISTICS_BASE_URL}/trip-shipment-details/{trip_id}", headers)
            if ship_resp and ship_resp.status_code == 200:
                shipments = ship_resp.json().get("data", {}).get("shipments", [])
                
                # --- BHASKAR SCHOOL AUTO LOGIC ---
                bhaskar_orders = [s for s in shipments if "bhaskar school" in str(s.get("customer_address", "")).lower() 
                                 and s.get("status", "").lower() not in ['delivered', 'completed']]
                
                if bhaskar_orders:
                    st.warning(f"⚡ Auto-delivering {len(bhaskar_orders)} Bhaskar School orders...")
                    for s in bhaskar_orders:
                        # 1. Arrived
                        api_request("PUT", f"{LASTMILE_BASE_URL}/delivery/arrived-at-location/{s['shipment_id']}", headers,
                                   {"latitude": str(s['customer_latitude']), "longitude": str(s['customer_longitude'])})
                        # 2. Get Cart for Order IDs
                        cart_resp = api_request("GET", f"{LOGISTICS_BASE_URL}/trip-details-cart/{trip_id}/{s['shipment_id']}", headers)
                        order_ids = []
                        if cart_resp and cart_resp.status_code == 200:
                            for cart in cart_resp.json().get("data", []):
                                for detail in cart.get("cartwise_order_details", []):
                                    for o in detail.get("orders_list", []): order_ids.append(o.get("order_id"))
                        # 3. Deliver
                        if order_ids:
                            api_request("POST", f"{LASTMILE_BASE_URL}/cod-payment/cash-payment", headers,
                                       {"cod_amount": str(s['cod_amount']), "latitude": str(s['customer_latitude']), 
                                        "longitude": str(s['customer_longitude']), "order_ids": order_ids, "shipment_id": int(s['shipment_id'])})
                            update_daily_stats(s)
                    st.success("Bhaskar School Orders Done!")
                    st.rerun()

                # --- DISPLAY PENDING ORDERS ---
                st.subheader(f"📦 Pending Tasks")
                for s in shipments:
                    if s.get("status", "").lower() in ['delivered', 'completed']: continue
                    
                    with st.container():
                        st.markdown(f"""<div class="order-card">
                            <b>{s.get('customer_name')}</b> | 💰 ₹{s.get('cod_amount')}<br/>
                            <small>📍 {s.get('customer_address')}</small>
                        </div>""", unsafe_allow_html=True)
                        
                        cols = st.columns(2)
                        if cols[0].button(f"📍 Map #{s['shipment_id']}", use_container_width=True):
                            st.write(f"Redirecting: https://www.google.com/maps/search/?api=1&query={s['customer_latitude']},{s['customer_longitude']}")
                        
                        if cols[1].button(f"✅ Deliver #{s['shipment_id']}", type="primary", use_container_width=True):
                            with st.spinner("Processing..."):
                                # Arrive
                                api_request("PUT", f"{LASTMILE_BASE_URL}/delivery/arrived-at-location/{s['shipment_id']}", headers,
                                           {"latitude": str(s['customer_latitude']), "longitude": str(s['customer_longitude'])})
                                # Cart
                                cart_resp = api_request("GET", f"{LOGISTICS_BASE_URL}/trip-details-cart/{trip_id}/{s['shipment_id']}", headers)
                                order_ids = [o.get("order_id") for cart in cart_resp.json().get("data", []) 
                                             for d in cart.get("cartwise_order_details", []) 
                                             for o in d.get("orders_list", [])]
                                # Deliver
                                if order_ids:
                                    api_request("POST", f"{LASTMILE_BASE_URL}/cod-payment/cash-payment", headers,
                                               {"cod_amount": str(s['cod_amount']), "latitude": str(s['customer_latitude']), 
                                                "longitude": str(s['customer_longitude']), "order_ids": order_ids, "shipment_id": int(s['shipment_id'])})
                                    update_daily_stats(s)
                                    st.toast(f"Order {s['shipment_id']} Delivered!")
                                    time.sleep(1)
                                    st.rerun()
        else:
            st.info("No active trip found.")
    else:
        st.error("Could not fetch trip data. Session might have expired.")
