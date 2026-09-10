
import streamlit as st
import data_manager as dm
import os
from datetime import datetime


# =========================================================
# YOUR SCREENSHOT FOLDER PATH
# CHANGE ONLY THIS PATH
# =========================================================

SCREENSHOT_FOLDER = r"C:\Users\dell\OneDrive\Desktop\ARG Internship\SafeVisionAI\SafeVisionAI-detections\output\screenshots"


# =========================================================
# PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="Employee Details",
    layout="wide"
)


# =========================================================
# GET SELECTED EMPLOYEE
# =========================================================

person_id = st.session_state.get("selected_person_id")

if person_id is None:

    st.title("Employee Details")
    st.warning("No employee selected.")

    if st.button("← Back to Dashboard"):
        st.switch_page("dashboard.py")

    st.stop()


# =========================================================
# GET EMPLOYEE DATA
# =========================================================

people = dm.get_all_people_status()

employee = None

for person in people:

    if str(person["person_id"]) == str(person_id):
        employee = person
        break


if employee is None:

    st.title("Employee Details")
    st.error("Employee not found.")

    if st.button("← Back to Dashboard"):
        st.switch_page("dashboard.py")

    st.stop()


# =========================================================
# EMPLOYEE INFORMATION
# =========================================================

st.title("Employee Details")

st.subheader("Employee Information")

col1, col2, col3 = st.columns(3)

with col1:
    st.write("**Employee ID**")
    st.write(employee.get("person_id", "Unknown"))

with col2:
    st.write("**Name**")
    st.write(employee.get("name", "Unknown"))

with col3:
    st.write("**Department**")
    st.write(employee.get("department", "Unassigned"))


st.divider()


# =========================================================
# CURRENT STATUS
# =========================================================

st.subheader("Current Status")

if employee.get("violating"):
    st.error("🔴 VIOLATING")
else:
    st.success("🟢 SAFE")


st.divider()


# =========================================================
# CURRENT PPE STATUS
# =========================================================

st.subheader("Current PPE Status")

equipment = [
    "helmet",
    "vest",
    "boots",
    "goggles",
    "gloves"
]

col1, col2, col3, col4, col5 = st.columns(5)

columns = [col1, col2, col3, col4, col5]

for column, item in zip(columns, equipment):

    with column:

        st.write(f"**{item.capitalize()}**")

        value = employee.get(item)

        if value is True:
            st.success("Present")

        elif value is False:
            st.error("Missing")

        else:
            st.warning("Unknown")


st.divider()


# =========================================================
# VIOLATION HISTORY
# =========================================================

st.subheader("Violation History")

violations = dm.get_violations_for(person_id)


if not violations:

    st.info("No violations recorded for this employee.")

else:

    st.write(f"Total Violations: **{len(violations)}**")

    st.divider()

    for number, violation in enumerate(violations, start=1):

        st.markdown(f"### Violation #{number}")


        # -------------------------------------------------
        # DATE / TIME
        # -------------------------------------------------

        timestamp = violation.get("timestamp")

        if timestamp:

            try:

                date_time = datetime.fromtimestamp(
                    timestamp
                ).strftime("%Y-%m-%d %H:%M:%S")

            except:

                date_time = str(timestamp)

        else:

            date_time = "Unknown"


        st.write(f"**Date / Time:** {date_time}")


        # -------------------------------------------------
        # FRAME
        # -------------------------------------------------

        st.write(
            f"**Frame:** {violation.get('frame', 'Unknown')}"
        )


        # -------------------------------------------------
        # MISSING PPE
        # -------------------------------------------------

        missing = violation.get("missing", [])

        if missing:

            missing_text = ", ".join(
                item.capitalize()
                for item in missing
            )

            st.write(
                f"**Missing PPE:** {missing_text}"
            )

        else:

            st.write("**Missing PPE:** Unknown")


        # -------------------------------------------------
        # SCREENSHOT
        # -------------------------------------------------

        screenshot = violation.get("screenshot")

        if screenshot:

            # Get only the filename from detections.json
            screenshot_name = os.path.basename(screenshot)

            # Combine your folder path + screenshot filename
            screenshot_path = os.path.join(
                SCREENSHOT_FOLDER,
                screenshot_name
            )

            # Show screenshot
            if os.path.exists(screenshot_path):

                st.write("**Violation Screenshot:**")

                st.image(
                    screenshot_path,
                    caption=f"Violation #{number}",
                    width=600
                )

            else:

                st.warning(
                    f"Screenshot not found: {screenshot_name}"
                )

        else:

            st.warning("No screenshot recorded.")


        st.divider()


# =========================================================
# BACK TO DASHBOARD
# =========================================================

if st.button("← Back to Dashboard"):

    st.switch_page("dashboard.py")

