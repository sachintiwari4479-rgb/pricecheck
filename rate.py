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
    "user-agent": "okhttp/4.12.0",
    "cache-control": "no-cache"
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
    """
    Fetches shipment details. 
    If shipment_id is None, it tries to fetch ALL shipments for the trip (if API supports it).
    """
    if shipment_id:
        url = f"{LOGISTICS_BASE_URL}/trip-shipment-details/{trip_id}/{shipment_id}"
    else:
        # Try fetching full trip details without specific shipment ID
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
    if st.button("🔄 Fetch Pending Orders", type="primary", use_container_width=True):
        st.session_state.trip_data = None # Clear trip data to force refresh
        st.session_state.all_shipments = [] # Clear list
        st.rerun()

    # --- DATA FETCHING LOGIC ---
    if st.session_state.trip_data is None:
        with st.spinner("Loading Trip & Orders..."):
            tokens = st.session_state.auth_tokens
            
            # 1. Get Assigned Trip to get Trip ID
            trip_resp = get_assigned_trip(tokens['access'], tokens['refresh'])
            
            if trip_resp and trip_resp.status_code == 200:
                trip_data = trip_resp.json().get("data", {})
                st.session_state.trip_data = trip_data
                trip_id = trip_data.get('tripId')
                next_shipment_id = trip_data.get('nextShipmentId')
                
                if trip_id:
                    # 2. Attempt to fetch ALL shipments using just Trip ID
                    # We pass None for shipment_id to try the trip-level endpoint
                    full_resp = get_shipment_details(trip_id, None, tokens['access'], tokens['refresh'])
                    
                    if full_resp and full_resp.status_code == 200:
                         # API supported fetching list!
                         full_data = full_resp.json().get("data", {})
                         st.session_state.all_shipments = full_data.get("shipments", [])
                    else:
                        # Fallback: API is strict, only allows specific shipment ID
                        if next_shipment_id:
                            single_resp = get_shipment_details(trip_id, next_shipment_id, tokens['access'], tokens['refresh'])
                            if single_resp and single_resp.status_code == 200:
                                single_data = single_resp.json().get("data", {})
                                st.session_state.all_shipments = single_data.get("shipments", [])
                
                st.rerun()
            else:
                st.error("Could not fetch assigned trip details.")

    st.divider()

    # --- RENDER LIST ---
    shipments_list = st.session_state.all_shipments
    trip_data = st.session_state.trip_data
    
    if shipments_list and trip_data:
        st.subheader(f"📦 Orders ({len(shipments_list)})")
        trip_id = trip_data.get('tripId')
        
        # LOOP THROUGH ALL ORDERS
        for idx, shipment in enumerate(shipments_list):
            current_shipment_id = shipment.get("shipment_id")
            
            # Card Container
            with st.container(border=True):
                # Header
                h1, h2 = st.columns([3, 1])
                with h1:
                    st.markdown(f"**Order #{idx + 1}**")
                    st.write(f"👤 **{shipment.get('customer_name', 'Unknown')}**")
                with h2:
                    status = shipment.get('status', 'Pending')
                    if status.lower() == 'delivered':
                        st.success(status)
                    else:
                        st.info(status)
                
                # Details
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
                
                # Payment
                st.write(f"💰 **COD: ₹ {shipment.get('cod_amount', 0)}** | Mode: {shipment.get('mode_of_payment')}")

                # Items Accordion
                with st.expander("🛒 View Items"):
                    skus = shipment.get("skus", [])
                    for item in skus:
                        ic1, ic2 = st.columns([1, 4])
                        with ic1:
                            if item.get("image_link"): st.image(item.get("image_link"), width=50)
                        with ic2:
                            st.write(f"{item.get('name')} (Qty: {item.get('total_quantity')})")

                # --- INDIVIDUAL DELIVERY BUTTON ---
                st.write("---")
                btn_key = f"btn_deliver_{current_shipment_id}"
                
                # Only show button if not delivered (simple check based on status text)
                if str(shipment.get('status')).lower() not in ['delivered', 'completed']:
                    if st.button(f"⚡ Complete Order #{current_shipment_id}", key=btn_key, type="primary", use_container_width=True):
                        if cust_lat and cust_lng:
                            # START PROCESS
                            tokens = st.session_state.auth_tokens
                            p_bar = st.progress(0)
                            status_txt = st.empty()
                            
                            try:
                                # 1. Arrive
                                status_txt.write("📍 Arriving...")
                                p_bar.progress(30)
                                mark_arrived_api(current_shipment_id, cust_lat, cust_lng, tokens['access'], tokens['refresh'])
                                
                                # 2. Get Order IDs
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
                                    # 3. Deliver
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
                                        # Force refresh list
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
        if st.session_state.trip_data:
            st.info("No shipments found in this trip.")
        else:
            st.info("No trip data loaded. Click Refresh.")
