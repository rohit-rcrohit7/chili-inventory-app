# Recreate Streamlit Google Sheets version after reset

google_sheets_streamlit_code = """
import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

st.set_page_config(page_title="CHILI Inventory Manager (Google Sheets)", layout="wide")
st.title("📦 CHILI Inventory Management Dashboard")

# Define scope and authorize with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    dict(st.secrets["gcp_service_account"]), scope)
client = gspread.authorize(credentials)

# Open the Google Sheets
inventory_sheet = client.open("CHILI Inventory").worksheet("Inventory")
audit_sheet = client.open("CHILI Inventory").worksheet("Audit Log")

# Helper: Load sheet to DataFrame
def load_sheet(sheet):
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# Helper: Append row to sheet
def append_row(sheet, row_list):
    sheet.append_row(row_list)

inventory = load_sheet(inventory_sheet)
audit_log = load_sheet(audit_sheet)

# Sidebar for adding new item
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
        submitted = st.form_submit_button("Add Item")
        if submitted and user:
            new_row = [
                item_type, item_id, description, serial, qty_available, qty_total,
                status, str(date_added), "", "", "", "", location, condition,
                "", "", ""
            ]
            append_row(inventory_sheet, new_row)
            append_row(audit_sheet, [str(datetime.datetime.now()), user, "Add Item", item_id, f"{qty_total} added as {item_type}"])
            st.success("Item added and logged to Google Sheet!")

# Check-in / Check-out
st.sidebar.header("🔄 Check In/Out")
with st.sidebar.form("checkout_form"):
    user = st.text_input("Your Name (Check In/Out)")
    item_id = st.selectbox("Select Item ID", inventory["Item ID"].dropna().unique())
    action = st.radio("Action", ["Check Out", "Check In"])
    comment = st.text_input("Notes")
    date_now = datetime.date.today()
    expected_return = st.date_input("Expected Return Date (for Check Out)", date_now)
    submitted_io = st.form_submit_button("Submit")
    if submitted_io and user:
        row_idx = inventory.index[inventory["Item ID"] == item_id][0] + 2  # offset for 1-based + header
        if action == "Check Out":
            inventory_sheet.update(f"G{row_idx}", "Checked Out")
            inventory_sheet.update(f"I{row_idx}", user)
            inventory_sheet.update(f"J{row_idx}", str(date_now))
            inventory_sheet.update(f"K{row_idx}", str(expected_return))
        else:
            inventory_sheet.update(f"G{row_idx}", "In Stock")
            inventory_sheet.update(f"L{row_idx}", str(date_now))
        append_row(audit_sheet, [str(datetime.datetime.now()), user, action, item_id, comment])
        st.success(f"{action} successful for item {item_id}")

# Display inventory
st.subheader("📊 Inventory Summary Table")
st.dataframe(inventory, use_container_width=True)

# Chart
st.subheader("📈 Inventory Status Overview")
status_counts = inventory["Status"].value_counts()
st.bar_chart(status_counts)

# Filter
st.subheader("🔍 Filter by Item Type")
filter_type = st.selectbox("Filter Type", ["All"] + inventory["Item Type"].dropna().unique().tolist())
if filter_type != "All":
    st.dataframe(inventory[inventory["Item Type"] == filter_type], use_container_width=True)

# Download
st.download_button("📥 Download Inventory CSV", inventory.to_csv(index=False), "inventory.csv", "text/csv")
st.download_button("📥 Download Audit Log CSV", audit_log.to_csv(index=False), "audit_log.csv", "text/csv")

# Audit log view
st.subheader("📒 Audit Log")
st.dataframe(audit_log.sort_values("Timestamp", ascending=False), use_container_width=True)
"""

# Save to file
gsheet_app_path = "/mnt/data/chili_inventory_google_sheets.py"
with open(gsheet_app_path, "w") as f:
    f.write(google_sheets_streamlit_code)

gsheet_app_path
