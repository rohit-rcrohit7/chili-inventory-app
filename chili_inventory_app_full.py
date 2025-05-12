
import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="CHILI Inventory Manager (Google Sheets)", layout="wide")
st.title("📦 CHILI Inventory Management Dashboard")

# Authorize with Google Sheets using Streamlit secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    dict(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(credentials)

# Open or create Google Sheets
spreadsheet = client.open("CHILI Inventory")

# Ensure worksheet with headers
def ensure_worksheet(title, headers, rows=100, cols=25):
    try:
        ws = spreadsheet.worksheet(title)
        existing_headers = ws.row_values(1)
        if existing_headers != headers:
            ws.delete_rows(1)
            ws.insert_row(headers, index=1)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)
        ws.insert_row(headers, index=1)
    return ws

# Define expected headers
inventory_headers = [
    "Item Type", "Item ID", "Item Description", "Serial Number", "Quantity Available",
    "Total Quantity", "Status", "Date Added", "Checked Out By", "Checked Out Date",
    "Expected Return Date", "Actual Return Date", "Location (Current)", "Condition Notes",
    "Last Verified By", "Last Verified Date", "Comments/Notes", "Checked Out Location"
]
audit_headers = ["Timestamp", "User", "Action", "Item ID", "Details"]

# Ensure both sheets exist
inventory_sheet = ensure_worksheet("Inventory", inventory_headers)
audit_sheet = ensure_worksheet("Audit Log", audit_headers)

def load_sheet(sheet, headers):
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        for col in headers:
            if col not in df.columns:
                df[col] = ""
        return df[headers]
    except:
        return pd.DataFrame(columns=headers)

def append_row(sheet, row_list):
    sheet.append_row(row_list)

inventory = load_sheet(inventory_sheet, inventory_headers)
audit_log = load_sheet(audit_sheet, audit_headers)

# Add new inventory item
with st.sidebar:
    st.header("➕ Add New Inventory Item")
    with st.form("add_item_form"):
        user = st.text_input("Your Name")
        item_type = st.selectbox("Item Type", [
            "Air Gradient (Indoor)", "Air Gradient (Outdoor)", "Petri Dish", "Filter", "Pump",
            "Other", "Passive Sampler", "Radiello", "Radon Monitor", "Thermal Comfort Monitor"
        ])
        item_id = st.text_input("Item ID")
        description = st.text_input("Description")
        serial = st.text_input("Serial Number")
        qty_total = st.number_input("Total Quantity", min_value=0)
        qty_available = st.number_input("Quantity Available", min_value=0, max_value=int(qty_total))
        status = st.selectbox("Status", ["In Stock", "Checked Out", "Under Maintenance", "Lost"])
        date_added = st.date_input("Date Added", datetime.date.today())
        location = st.text_input("Current Location")
        condition = st.text_area("Condition Notes")
        comments = st.text_area("Comments/Notes")
        submitted = st.form_submit_button("Add Item")
        if submitted and user:
            new_row = [
                item_type, item_id, description, serial, qty_available, qty_total,
                status, str(date_added), "", "", "", "", location, condition,
                "", "", comments, ""
            ]
            append_row(inventory_sheet, new_row)
            inventory = load_sheet(inventory_sheet, inventory_headers)
            append_row(audit_sheet, [str(datetime.datetime.now()), user, "Add Item", item_id, f"{qty_total} added as {item_type}"])
            st.success("Item added and logged to Google Sheet!")

# Verification section
st.sidebar.header("✅ Verify Inventory Item")
with st.sidebar.form("verify_form"):
    verifier = st.text_input("Your Name (Verify)")
    verify_item_ids = inventory["Item ID"].dropna().astype(str).unique().tolist()
    verify_item_id = st.selectbox("Select Item ID to Verify", verify_item_ids if verify_item_ids else ["No items available"])
    verify_comment = st.text_input("Verification Notes (optional)")
    verify_submit = st.form_submit_button("Verify")
    if verify_submit and verifier and verify_item_id != "No items available":
        row_idx = inventory.index[inventory["Item ID"].astype(str) == verify_item_id][0] + 2
        today_str = str(datetime.date.today())
        inventory_sheet.update(f"O{row_idx}", [[verifier]])
        inventory_sheet.update(f"P{row_idx}", [[today_str]])
        append_row(audit_sheet, [str(datetime.datetime.now()), verifier, "Verify", verify_item_id, verify_comment])
        inventory = load_sheet(inventory_sheet, inventory_headers)
        st.success(f"Verified item {verify_item_id}")

# Check-in/out section
st.sidebar.header("🔄 Check In/Out")
with st.sidebar.form("checkout_form"):
    user = st.text_input("Your Name (Check In/Out)")
    item_ids = inventory["Item ID"].dropna().astype(str).unique().tolist()
    item_id = st.selectbox("Select Item ID", item_ids if item_ids else ["No items available"])
    checkout_location = st.text_input("Checked Out To (Location / Site)")
    action = st.radio("Action", ["Check Out", "Check In"])
    comment = st.text_input("Notes")
    date_now = datetime.date.today()
    expected_return = st.date_input("Expected Return Date (for Check Out)", date_now)
    submitted_io = st.form_submit_button("Submit")
    if submitted_io and user and item_id != "No items available":
        row_idx = inventory.index[inventory["Item ID"].astype(str) == item_id][0] + 2
        if action == "Check Out":
            inventory_sheet.update(f"G{row_idx}", [["Checked Out"]])
            inventory_sheet.update(f"I{row_idx}", [[user]])
            inventory_sheet.update(f"J{row_idx}", [[str(date_now)]])
            inventory_sheet.update(f"K{row_idx}", [[str(expected_return)]])
            inventory_sheet.update(f"R{row_idx}", [[checkout_location]])
        else:
            inventory_sheet.update(f"G{row_idx}", [["In Stock"]])
            inventory_sheet.update(f"L{row_idx}", [[str(date_now)]])
            inventory_sheet.update(f"R{row_idx}", [[""]])
        append_row(audit_sheet, [str(datetime.datetime.now()), user, action, item_id, f"{comment} → {checkout_location}"])
        inventory = load_sheet(inventory_sheet, inventory_headers)
        st.success(f"{action} successful for item {item_id}")

# Display inventory
st.subheader("📊 Inventory Summary Table")
if not inventory.empty:
    st.dataframe(inventory.astype(str), use_container_width=True)
else:
    st.info("No inventory data yet.")

# Inventory chart
st.subheader("📈 Inventory Status Overview")
if not inventory.empty:
    st.bar_chart(inventory["Status"].value_counts())
else:
    st.info("No status data to visualize.")

# Item filter
st.subheader("🔍 Filter by Item Type")
if not inventory.empty:
    filter_type = st.selectbox("Filter Type", ["All"] + inventory["Item Type"].dropna().unique().tolist())
    if filter_type != "All":
        st.dataframe(inventory[inventory["Item Type"] == filter_type].astype(str), use_container_width=True)

# Downloads
st.download_button("📥 Download Inventory CSV", inventory.to_csv(index=False), "inventory.csv", "text/csv")
st.download_button("📥 Download Audit Log CSV", audit_log.to_csv(index=False), "audit_log.csv", "text/csv")

# Audit log display
st.subheader("📒 Audit Log")
if not audit_log.empty:
    st.dataframe(audit_log.sort_values("Timestamp", ascending=False).astype(str), use_container_width=True)
else:
    st.info("No audit entries yet.")
