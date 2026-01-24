import streamlit as st
import requests
import pandas as pd
import time

# --- Configuration ---
AUTH_BASE_URL = "https://services.dealshare.in/scmuserservice/api/v1/auth"
LOGISTICS_BASE_URL = "https://services.dealshare.in/logisticservice/api/v1/trip"
LASTMILE_BASE_URL = "https://services.dealshare.in/lastmileservice/api/v1"

# Default headers needed for all requests
BASE_HEADERS = {
    "app-type": "SCM_RIDER_APP",
    "device-id": "62adca42-92bd-4bca-852b-c23792ad139e", 
    "app-version": "1.0.0",
    "content-type": "application/json",
    "accept-encoding": "gzip",
    "user-agent": "okhttp/4.12.0"
}

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
    url = f"{LOGISTICS_BASE_URL}/trip-shipment-details/{trip_id}/{shipment_id}"
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
    """Fetches cart details to extract Order IDs for delivery."""
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

# --- STEP 1: LOGIN ---
if st.session_state.step == 'login':
    st.title("ðŸ›µ Rider Login")
    mobile = st.text_input("Mobile Number", max_chars=10)
    if st.button("Send OTP"):
        with st.spinner("Sending..."):
            resp = send_otp_api(mobile)
            if resp and resp.status_code == 200:
                st.session_state.mobile = mobile
                st.session_state.step = 'verify'
                st.success("OTP Sent!")
                st.rerun()
            else:
                st.error(f"Failed to send OTP: {resp.status_code if resp else 'Err'}")

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
                st.session_state.auth_tokens = {
                    "access": data.get("accessToken"),
                    "refresh": data.get("refreshToken")
                }
                st.session_state.step = 'dashboard'
                st.success("Logged In!")
                st.rerun()
            else:
                st.error("Invalid OTP")

# --- STEP 3: DASHBOARD ---
elif st.session_state.step == 'dashboard':
    st.title("ðŸ“¦ Rider Dashboard")
    
    # Sidebar
    with st.sidebar:
        st.write(f"User: **{st.session_state.mobile}**")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    # --- TOP CONTROL BAR ---
    col_refresh, col_status = st.columns([1, 2])
    
    with col_refresh:
        # Refresh Button
        if st.button("🔄 Fetch Pending Orders", type="primary", use_container_width=True):
            with st.spinner("Refreshing..."):
                st.session_state.trip_data = None # Clear old data
                tokens = st.session_state.auth_tokens
                resp = get_assigned_trip(tokens['access'], tokens['refresh'])
                if resp and resp.status_code == 200:
                    st.session_state.trip_data = resp.json().get("data", {})
                    st.toast("Orders Refreshed!", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Failed to fetch trip.")

    # Auto-fetch logic: If no trip data is loaded, fetch it automatically
    if st.session_state.trip_data is None:
        with st.spinner("Loading assigned orders..."):
            tokens = st.session_state.auth_tokens
            resp = get_assigned_trip(tokens['access'], tokens['refresh'])
            if resp and resp.status_code == 200:
                st.session_state.trip_data = resp.json().get("data", {})
                st.rerun()
            else:
                st.error("Could not fetch assigned trip automatically.")

    st.divider()

    # --- DISPLAY ORDERS ---
    if st.session_state.trip_data:
        td = st.session_state.trip_data
        
        if td.get('isNextShipmentAvailable'):
            trip_id = td.get('tripId')
            shipment_id = td.get('nextShipmentId')
            
            # Fetch specific details for the trip
            tokens = st.session_state.auth_tokens
            # Using st.cache_data logic loosely or just fetching directly. 
            # For simplicity in this app, we fetch directly to ensure realtime status.
            ship_resp = get_shipment_details(trip_id, shipment_id, tokens['access'], tokens['refresh'])
            
            if ship_resp and ship_resp.status_code == 200:
                full_data = ship_resp.json().get("data", {})
                shipments_list = full_data.get("shipments", [])
                
                if shipments_list:
                    st.subheader(f"📦 Pending Shipments: {len(shipments_list)}")
                    
                    # Iterate through all shipments in the list
                    for idx, shipment in enumerate(shipments_list):
                        current_shipment_id = shipment.get("shipment_id")
                        
                        # Create a card-like container for each shipment
                        with st.container(border=True):
                            # Header with status
                            h1, h2 = st.columns([3, 1])
                            with h1:
                                st.markdown(f"**#{idx + 1} - {shipment.get('customer_name', 'Unknown')}**")
                            with h2:
                                st.caption(f"{shipment.get('status', 'Pending')}")
                            
                            # 1. Customer & Location
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.write(f"📞 {shipment.get('customer_number', 'N/A')}")
                                st.write(f"🏠 {shipment.get('customer_address', 'N/A')}")
                            
                            with col2:
                                cust_lat = shipment.get("customer_latitude")
                                cust_lng = shipment.get("customer_longitude")
                                
                                if cust_lat and cust_lng:
                                    map_url = f"https://www.google.com/maps/search/?api=1&query={cust_lat},{cust_lng}"
                                    st.link_button("🗺️ Map", map_url, use_container_width=True)
                                else:
                                    st.warning("No GPS")
                            
                            # 2. Payment Info
                            st.info(f"**Payment:** {shipment.get('mode_of_payment')} | **COD:** ₹ {shipment.get('cod_amount', 0)}")

                            # 3. Items (SKUs)
                            with st.expander("🛒 View Items"):
                                skus = shipment.get("skus", [])
                                if skus:
                                    for item in skus:
                                        ic1, ic2 = st.columns([1, 4])
                                        with ic1:
                                            img_link = item.get("image_link")
                                            if img_link:
                                                st.image(img_link, width=60)
                                        with ic2:
                                            st.write(f"**{item.get('name')}**")
                                            st.write(f"Qty: {item.get('total_quantity')}")
                                else:
                                    st.write("No items details.")

                            # 4. ONE CLICK ACTION
                            st.write("---")
                            # Unique key for button using shipment_id to ensure every order has its own button
                            if st.button(f"⚡ Complete Delivery (Order #{current_shipment_id})", type="primary", use_container_width=True, key=f"btn_{current_shipment_id}"):
                                if cust_lat and cust_lng:
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    try:
                                        # STEP 1: Mark Arrived
                                        status_text.write("📍 Marking Arrived...")
                                        progress_bar.progress(25)
                                        
                                        arrived_resp = mark_arrived_api(
                                            current_shipment_id, cust_lat, cust_lng, 
                                            tokens['access'], tokens['refresh']
                                        )
                                        
                                        if arrived_resp and arrived_resp.status_code == 200:
                                            # STEP 2: Fetch Order IDs
                                            status_text.write("📦 Fetching Order Details...")
                                            progress_bar.progress(50)
                                            
                                            cart_resp = get_trip_details_cart(trip_id, current_shipment_id, tokens['access'], tokens['refresh'])
                                            
                                            if cart_resp and cart_resp.status_code == 200:
                                                cart_data = cart_resp.json().get("data", [])
                                                order_ids = []
                                                for cart_item in cart_data:
                                                    for detail in cart_item.get("cartwise_order_details", []):
                                                        for order in detail.get("orders_list", []):
                                                            order_ids.append(order.get("order_id"))
                                                
                                                if order_ids:
                                                    # STEP 3: Mark Delivered
                                                    status_text.write("✅ Processing Payment & Delivery...")
                                                    progress_bar.progress(75)
                                                    
                                                    del_resp = mark_delivered_api(
                                                        current_shipment_id, order_ids, shipment.get('cod_amount', 0),
                                                        cust_lat, cust_lng,
                                                        tokens['access'], tokens['refresh']
                                                    )
                                                    
                                                    if del_resp and del_resp.status_code == 200:
                                                        progress_bar.progress(100)
                                                        status_text.success("🎉 Order Completed Successfully!")
                                                        st.balloons()
                                                        time.sleep(2)
                                                        st.session_state.trip_data = None # Force refresh next load
                                                        st.rerun()
                                                    else:
                                                        status_text.error(f"Delivery Failed. Status: {del_resp.status_code}")
                                                        if del_resp: st.write(del_resp.text)
                                                else:
                                                    status_text.error("No Order IDs found. Cannot deliver.")
                                            else:
                                                status_text.error("Failed to fetch cart details.")
                                        else:
                                            status_text.error(f"Failed to Mark Arrived. Status: {arrived_resp.status_code}")
                                    except Exception as e:
                                        status_text.error(f"An error occurred: {e}")
                                else:
                                    st.error("GPS Coordinates missing for this customer.")
                            
                else:
                    st.warning("No shipment data found in list.")
            else:
                st.error("Failed to load shipment details.")
        else:
            st.info("No active shipments available. Enjoy your break! ☕")
