
import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(page_title="CHILI Inventory Manager", layout="wide")
st.title("📦 CHILI Inventory Management Dashboard")

DATA_PATH = "chili_inventory.csv"
AUDIT_LOG_PATH = "chili_inventory_audit_log.csv"

# Load inventory and audit log
def load_data():
    if os.path.exists(DATA_PATH):
        inventory_df = pd.read_csv(DATA_PATH, parse_dates=["Date Added", "Checked Out Date", "Expected Return Date", "Actual Return Date", "Last Verified Date"])
    else:
        inventory_df = pd.DataFrame(columns=[
            "Item Type", "Item ID", "Item Description", "Serial Number", "Quantity Available",
            "Total Quantity", "Status", "Date Added", "Checked Out By", "Checked Out Date",
            "Expected Return Date", "Actual Return Date", "Location (Current)", "Condition Notes",
            "Last Verified By", "Last Verified Date", "Comments/Notes"
        ])
    if os.path.exists(AUDIT_LOG_PATH):
        audit_df = pd.read_csv(AUDIT_LOG_PATH, parse_dates=["Timestamp"])
    else:
        audit_df = pd.DataFrame(columns=["Timestamp", "User", "Action", "Item ID", "Details"])
    return inventory_df, audit_df

def save_data(inventory_df, audit_df):
    inventory_df.to_csv(DATA_PATH, index=False)
    audit_df.to_csv(AUDIT_LOG_PATH, index=False)

inventory, audit_log = load_data()

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
            new_row = pd.DataFrame([{
                "Item Type": item_type, "Item ID": item_id, "Item Description": description,
                "Serial Number": serial, "Quantity Available": qty_available,
                "Total Quantity": qty_total, "Status": status, "Date Added": pd.to_datetime(date_added),
                "Checked Out By": "", "Checked Out Date": pd.NaT, "Expected Return Date": pd.NaT,
                "Actual Return Date": pd.NaT, "Location (Current)": location, "Condition Notes": condition,
                "Last Verified By": "", "Last Verified Date": pd.NaT, "Comments/Notes": ""
            }])
            inventory = pd.concat([inventory, new_row], ignore_index=True)
            audit_log = pd.concat([audit_log, pd.DataFrame([{
                "Timestamp": datetime.datetime.now(), "User": user, "Action": "Add Item",
                "Item ID": item_id, "Details": f"{qty_total} added as {item_type}"
            }])], ignore_index=True)
            save_data(inventory, audit_log)
            st.success("Item added and logged successfully!")

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
        idx = inventory[inventory["Item ID"] == item_id].index[0]
        if action == "Check Out":
            inventory.at[idx, "Status"] = "Checked Out"
            inventory.at[idx, "Checked Out By"] = user
            inventory.at[idx, "Checked Out Date"] = pd.to_datetime(date_now)
            inventory.at[idx, "Expected Return Date"] = pd.to_datetime(expected_return)
        else:
            inventory.at[idx, "Status"] = "In Stock"
            inventory.at[idx, "Actual Return Date"] = pd.to_datetime(date_now)
        audit_log = pd.concat([audit_log, pd.DataFrame([{
            "Timestamp": datetime.datetime.now(), "User": user, "Action": action,
            "Item ID": item_id, "Details": comment
        }])], ignore_index=True)
        save_data(inventory, audit_log)
        st.success(f"{action} successful for item {item_id}")

# Inventory view
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

# Audit Log Viewer
st.subheader("📒 Audit Log")
st.dataframe(audit_log.sort_values("Timestamp", ascending=False), use_container_width=True)
