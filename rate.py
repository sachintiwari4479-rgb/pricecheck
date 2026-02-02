import streamlit as st
import requests
import pandas as pd
import time
import json
import os

# --- Configuration ---
AUTH_BASE_URL = "https://services.dealshare.in/scmuserservice/api/v1/auth"
LOGISTICS_BASE_URL = "https://services.dealshare.in/logisticservice/api/v1/trip"
LASTMILE_BASE_URL = "https://services.dealshare.in/lastmileservice/api/v1"
ACCOUNTS_FILE = "saved_accounts.json"

# Default headers needed for all requests
BASE_HEADERS = {
    "app-type": "SCM_RIDER_APP",
    "device-id": "62adca42-92bd-4bca-852b-c23792ad139e", 
    "app-version": "1.0.0",
    "content-type": "application/json; charset=UTF-8",
    "accept-encoding": "gzip",
    "user-agent": "okhttp/4.12.0",
    "cache-control": "no-cache"
}

# --- Account Management Functions ---

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_account(mobile, tokens):
    accounts = load_accounts()
    accounts[mobile] = tokens
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=4)

# --- API Functions ---

def send_otp_api(mobile_number):
    url = f"{AUTH_BASE_URL}/login"
    payload = {
        "hashCode": "abc123",
        "mobileNumber": mobile_number,
        "provider": "MOBILE_OTP"
    }
    try:
        return requests.post(url, headers=BASE_HEADERS, json=payload)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def verify_otp_api(mobile_number, otp):
    url = f"{AUTH_BASE_URL}/verify-otp"
    payload = {"mobileNumber": mobile_number, "otp": otp}
    try:
        return requests.post(url, headers=BASE_HEADERS, json=payload)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def get_assigned_trip(access_token, refresh_token):
    url = f"{LOGISTICS_BASE_URL}/assigned-trip"
    headers = BASE_HEADERS.copy()
    headers["authorization-access"] = access_token
    headers["authorization-refresh"] = refresh_token
    try:
        return requests.get(url, headers=headers)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def get_shipment_details(trip_id, shipment_id, access_token, refresh_token):
    """
    Fetches shipment details. 
    If shipment_id is None, it tries to fetch ALL shipments for the trip.
    """
    if shipment_id:
        url = f"{LOGISTICS_BASE_URL}/trip-shipment-details/{trip_id}/{shipment_id}"
    else:
        url = f"{LOGISTICS_BASE_URL}/trip-shipment-details/{trip_id}"
        
    headers = BASE_HEADERS.copy()
    headers["authorization-access"] = access_token
    headers["authorization-refresh"] = refresh_token
    try:
        return requests.get(url, headers=headers)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def mark_arrived_api(shipment_id, lat, lng, access_token, refresh_token):
    url = f"{LASTMILE_BASE_URL}/delivery/arrived-at-location/{shipment_id}"
    headers = BASE_HEADERS.copy()
    headers["authorization-access"] = access_token
    headers["authorization-refresh"] = refresh_token
    
    payload = {
        "latitude": str(lat),
        "longitude": str(lng)
    }
    
    try:
        return requests.put(url, headers=headers, json=payload)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def get_trip_details_cart(trip_id, shipment_id, access_token, refresh_token):
    url = f"{LOGISTICS_BASE_URL}/trip-details-cart/{trip_id}/{shipment_id}"
    headers = BASE_HEADERS.copy()
    headers["authorization-access"] = access_token
    headers["authorization-refresh"] = refresh_token
    try:
        return requests.get(url, headers=headers)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

def mark_delivered_api(shipment_id, order_ids, cod_amount, lat, lng, access_token, refresh_token):
    url = f"{LASTMILE_BASE_URL}/cod-payment/cash-payment"
    headers = BASE_HEADERS.copy()
    headers["authorization-access"] = access_token
    headers["authorization-refresh"] = refresh_token
    
    payload = {
        "cod_amount": str(cod_amount),
        "latitude": str(lat),
        "longitude": str(lng),
        "order_ids": order_ids,
        "shipment_id": int(shipment_id)
    }
    
    try:
        return requests.post(url, headers=headers, json=payload)
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# --- Main App UI ---

st.set_page_config(page_title="Rider Dashboard", layout="centered")

# Initialize Session State
if 'step' not in st.session_state: st.session_state.step = 'login'
if 'auth_tokens' not in st.session_state: st.session_state.auth_tokens = {}
if 'trip_data' not in st.session_state: st.session_state.trip_data = None
if 'all_shipments' not in st.session_state: st.session_state.all_shipments = []
if 'mobile' not in st.session_state: st.session_state.mobile = ""

# --- STEP 1: LOGIN ---
if st.session_state.step == 'login':
    st.title("ðŸ›µ Rider Login")
    
    saved_accounts = load_accounts()
    saved_numbers = list(saved_accounts.keys())
    
    use_saved = False
    selected_account = None

    if saved_numbers:
        st.subheader("Saved Accounts")
        selected_num = st.selectbox("Select stored number:", ["-- New Number --"] + saved_numbers)
        
        if selected_num != "-- New Number --":
            use_saved = True
            selected_account = saved_accounts[selected_num]
            if st.button(f"🚀 Auto-Login as {selected_num}", type="primary"):
                with st.spinner("Attempting Auto-Login..."):
                    # Test token validity by fetching trip
                    tokens = selected_account
                    resp = get_assigned_trip(tokens['access'], tokens['refresh'])
                    
                    if resp and resp.status_code in [200, 404]: # 404 might mean no trip but token valid
                        st.session_state.auth_tokens = tokens
                        st.session_state.mobile = selected_num
                        st.session_state.step = 'dashboard'
                        st.success("Auto-Login Successful!")
                        st.rerun()
                    else:
                        st.error("Session Expired. Please login with OTP.")
                        use_saved = False # Fallback to OTP

    if not use_saved:
        st.subheader("New Login")
        mobile = st.text_input("Mobile Number", max_chars=10, value=st.session_state.mobile)
        if st.button("Send OTP"):
            if len(mobile) == 10:
                with st.spinner("Sending..."):
                    resp = send_otp_api(mobile)
                    if resp and resp.status_code == 200:
                        st.session_state.mobile = mobile
                        st.session_state.step = 'verify'
                        st.success("OTP Sent!")
                        st.rerun()
                    else:
                        st.error(f"Failed to send OTP: {resp.status_code if resp else 'Err'}")
            else:
                st.warning("Enter valid 10-digit number")

# --- STEP 2: VERIFY ---
elif st.session_state.step == 'verify':
    st.title("ðŸ”‘ Verify OTP")
    st.write(f"OTP sent to: {st.session_state.mobile}")
    otp = st.text_input("Enter OTP", type="password")
    if st.button("Verify"):
        with st.spinner("Verifying..."):
            resp = verify_otp_api(st.session_state.mobile, otp)
            if resp and resp.status_code == 200:
                data = resp.json().get("data", {})
                tokens = {
                    "access": data.get("accessToken"),
                    "refresh": data.get("refreshToken")
                }
                # SAVE ACCOUNT
                save_account(st.session_state.mobile, tokens)
                
                st.session_state.auth_tokens = tokens
                st.session_state.step = 'dashboard'
                st.success("Logged In & Saved!")
                st.rerun()
            else:
                st.error("Invalid OTP")

# --- STEP 3: DASHBOARD ---
elif st.session_state.step == 'dashboard':
    st.title("ðŸ“¦ Rider Dashboard")
    
    with st.sidebar:
        st.write(f"User: **{st.session_state.mobile}**")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    if st.button("🔄 Fetch Pending Orders", type="primary", use_container_width=True):
        st.session_state.trip_data = None 
        st.session_state.all_shipments = []
        st.rerun()

    # --- DATA FETCHING ---
    if st.session_state.trip_data is None:
        with st.spinner("Loading Trip & Orders..."):
            tokens = st.session_state.auth_tokens
            trip_resp = get_assigned_trip(tokens['access'], tokens['refresh'])
            
            if trip_resp and trip_resp.status_code == 200:
                trip_data = trip_resp.json().get("data", {})
                st.session_state.trip_data = trip_data
                trip_id = trip_data.get('tripId')
                next_shipment_id = trip_data.get('nextShipmentId')
                
                if trip_id:
                    full_resp = get_shipment_details(trip_id, None, tokens['access'], tokens['refresh'])
                    if full_resp and full_resp.status_code == 200:
                         full_data = full_resp.json().get("data", {})
                         st.session_state.all_shipments = full_data.get("shipments", [])
                    else:
                        # Fallback
                        if next_shipment_id:
                            single_resp = get_shipment_details(trip_id, next_shipment_id, tokens['access'], tokens['refresh'])
                            if single_resp and single_resp.status_code == 200:
                                single_data = single_resp.json().get("data", {})
                                st.session_state.all_shipments = single_data.get("shipments", [])
                st.rerun()
            else:
                st.error("Could not fetch assigned trip details.")

    # --- STATS CALCULATION ---
    shipments_list = st.session_state.all_shipments
    trip_data = st.session_state.trip_data

    if shipments_list:
        total_cod_expected = 0
        total_cod_collected = 0
        total_items_qty = 0
        
        for s in shipments_list:
            cod = float(s.get('cod_amount', 0))
            status = str(s.get('status', '')).lower()
            
            total_cod_expected += cod
            if status in ['delivered', 'completed']:
                total_cod_collected += cod
            
            skus = s.get('skus', [])
            for item in skus:
                total_items_qty += int(item.get('total_quantity', 0))

        # --- DISPLAY SUMMARY ---
        st.markdown("### 📊 Trip Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Collect Target", f"₹{total_cod_expected:,.0f}")
        m2.metric("Cash Collected", f"₹{total_cod_collected:,.0f}")
        m3.metric("Total Items", f"{total_items_qty}")
        st.divider()

        # --- AUTO-DELIVERY LOGIC (Bhaskar School) ---
        auto_orders = []
        for s in shipments_list:
            addr = str(s.get("customer_address", "")).lower()
            status = str(s.get("status")).lower()
            if "bhaskar school" in addr and status not in ['delivered', 'completed']:
                auto_orders.append(s)
        
        if auto_orders:
            st.warning(f"🚀 Detected {len(auto_orders)} 'Bhaskar School' orders. Auto-delivering...")
            bar = st.progress(0)
            tokens = st.session_state.auth_tokens
            trip_id = trip_data.get('tripId')
            
            for i, shipment in enumerate(auto_orders):
                current_shipment_id = shipment.get("shipment_id")
                cust_lat = shipment.get("customer_latitude")
                cust_lng = shipment.get("customer_longitude")
                cod_amount = shipment.get("cod_amount", 0)

                if cust_lat and cust_lng:
                    try:
                        mark_arrived_api(current_shipment_id, cust_lat, cust_lng, tokens['access'], tokens['refresh'])
                        cart_resp = get_trip_details_cart(trip_id, current_shipment_id, tokens['access'], tokens['refresh'])
                        order_ids = []
                        if cart_resp and cart_resp.status_code == 200:
                            c_data = cart_resp.json().get("data", [])
                            for c in c_data:
                                for d in c.get("cartwise_order_details", []):
                                    for o in d.get("orders_list", []):
                                        order_ids.append(o.get("order_id"))
                        if order_ids:
                            mark_delivered_api(current_shipment_id, order_ids, cod_amount, cust_lat, cust_lng, tokens['access'], tokens['refresh'])
                    except: pass
                bar.progress((i + 1) / len(auto_orders))
            
            st.success("Auto-delivery complete!")
            time.sleep(1)
            st.session_state.trip_data = None
            st.rerun()
        
        # --- ORDER LIST ---
        st.subheader(f"📦 Orders List")
        trip_id = trip_data.get('tripId')
        
        for idx, shipment in enumerate(shipments_list):
            current_shipment_id = shipment.get("shipment_id")
            with st.container(border=True):
                h1, h2 = st.columns([3, 1])
                with h1:
                    st.markdown(f"**Order #{idx + 1}**")
                    st.write(f"👤 **{shipment.get('customer_name', 'Unknown')}**")
                with h2:
                    status = shipment.get('status', 'Pending')
                    if str(status).lower() in ['delivered', 'completed']:
                        st.success(status)
                    else:
                        st.info(status)
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"📞 {shipment.get('customer_number', 'N/A')}")
                    st.caption(f"🏠 {shipment.get('customer_address', 'N/A')}")
                
                with col2:
                    cust_lat = shipment.get("customer_latitude")
                    cust_lng = shipment.get("customer_longitude")
                    if cust_lat and cust_lng:
                        map_url = f"https://www.google.com/maps/search/?api=1&query={cust_lat},{cust_lng}"
                        st.link_button("🗺️ Map", map_url, use_container_width=True)
                
                st.write(f"💰 **COD: ₹ {shipment.get('cod_amount', 0)}** | Mode: {shipment.get('mode_of_payment')}")

                with st.expander("🛒 View Items"):
                    skus = shipment.get("skus", [])
                    for item in skus:
                        ic1, ic2 = st.columns([1, 4])
                        with ic1:
                            if item.get("image_link"): st.image(item.get("image_link"), width=50)
                        with ic2:
                            st.write(f"{item.get('name')} (Qty: {item.get('total_quantity')})")

                st.write("---")
                btn_key = f"btn_deliver_{current_shipment_id}"
                
                if str(shipment.get('status')).lower() not in ['delivered', 'completed']:
                    if st.button(f"⚡ Complete Order #{current_shipment_id}", key=btn_key, type="primary", use_container_width=True):
                        if cust_lat and cust_lng:
                            tokens = st.session_state.auth_tokens
                            p_bar = st.progress(0)
                            status_txt = st.empty()
                            try:
                                status_txt.write("📍 Arriving...")
                                p_bar.progress(30)
                                mark_arrived_api(current_shipment_id, cust_lat, cust_lng, tokens['access'], tokens['refresh'])
                                
                                status_txt.write("📦 Fetching Cart...")
                                p_bar.progress(60)
                                cart_resp = get_trip_details_cart(trip_id, current_shipment_id, tokens['access'], tokens['refresh'])
                                order_ids = []
                                if cart_resp and cart_resp.status_code == 200:
                                    c_data = cart_resp.json().get("data", [])
                                    for c in c_data:
                                        for d in c.get("cartwise_order_details", []):
                                            for o in d.get("orders_list", []):
                                                order_ids.append(o.get("order_id"))
                                
                                if order_ids:
                                    status_txt.write("✅ Delivering...")
                                    p_bar.progress(80)
                                    del_resp = mark_delivered_api(
                                        current_shipment_id, order_ids, shipment.get('cod_amount', 0),
                                        cust_lat, cust_lng, tokens['access'], tokens['refresh']
                                    )
                                    if del_resp and del_resp.status_code == 200:
                                        p_bar.progress(100)
                                        status_txt.success("Done!")
                                        st.balloons()
                                        time.sleep(1)
                                        st.session_state.trip_data = None
                                        st.rerun()
                                    else:
                                        status_txt.error("Delivery Failed")
                                else:
                                    status_txt.error("No Orders found")
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.error("No GPS coordinates")
                else:
                    st.success("✅ Order Completed")
    else:
        st.info("No active trip data.")
