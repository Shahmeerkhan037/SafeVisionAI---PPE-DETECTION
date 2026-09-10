import streamlit as st
import data_manager as dm
import time

# =========================================================
# PAGE SETUP
# =========================================================

st.set_page_config(
    page_title="SafeVisionAI Dashboard",
    layout="wide"
)

st.title("SafeVisionAI Dashboard")
st.subheader("Employee Overview")

# =========================================================
# LOAD EMPLOYEES
# =========================================================

people = dm.get_all_people_status()

# =========================================================
# EMPLOYEE TABLE
# =========================================================

if not people:

    st.info("No employees detected yet.")

else:

    # Table header
    col1, col2, col3, col4 = st.columns([1, 3, 2, 2])

    with col1:
        st.write("**Employee ID**")

    with col2:
        st.write("**Name**")

    with col3:
        st.write("**Violation Status**")

    with col4:
        st.write("**Action**")

    st.divider()

    # Every employee
    for person in people:

        person_id = person["person_id"]

        current_name = person.get("name", "Unknown")

        department = person.get(
            "department",
            "Unassigned"
        )

        # Current violation status
        if person.get("violating"):
            status = "🔴 Violating"
        else:
            status = "🟢 Safe"

        # -------------------------------------------------
        # ROW
        # -------------------------------------------------

        col1, col2, col3, col4 = st.columns([1, 3, 2, 2])

        # Employee ID
        with col1:
            st.write(person_id)

        # Editable name
        with col2:

            new_name = st.text_input(
                "Name",
                value=current_name,
                key=f"name_{person_id}",
                label_visibility="collapsed"
            )

        # Status
        with col3:
            st.write(status)

        # Buttons
        with col4:

            if st.button(
                "Save Name",
                key=f"save_{person_id}"
            ):

                dm.save_employee(
                    person_id,
                    new_name,
                    department
                )

                st.success("Name saved!")

                st.rerun()

            if st.button(
                "View Details",
                key=f"details_{person_id}"
            ):

                st.session_state["selected_person_id"] = person_id

                st.switch_page(
                    "pages/1_Employee_Details.py"
                )

        st.divider()

# =========================================================
# AUTO REFRESH
# =========================================================

time.sleep(3)
st.rerun()