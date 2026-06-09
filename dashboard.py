import streamlit as st
import pandas as pd
import datetime
import hashlib
import json
import os

# 1. Page Configuration (Must be first)
st.set_page_config(page_title="IIM Shillong Secure Hub", page_icon="🔐", layout="wide")

st.title("🔐 Secure Personalized Timetable & Attendance Hub")

# File Targets
MASTER_EXCEL_FILE = 'Term - IV Schedule PGP (2025-27).xlsx'
SHEET_NAME = 'Final schedule Term - IV- A4'
USER_DATA_FILE = 'user_profiles.json'

def hash_passkey(passkey: str) -> str:
    return hashlib.sha256(passkey.encode()).hexdigest()

# 2. Optimized Excel Loader
@st.cache_data
def load_master_matrix():
    try:
        df = pd.read_excel(MASTER_EXCEL_FILE, sheet_name=SHEET_NAME)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'Unnamed: 1' in df.columns:
            df = df.rename(columns={'Unnamed: 1': 'Date'})
        else:
            df.rename(columns={df.columns[1]: 'Date'}, inplace=True)
            
        if 'Days' in df.columns:
            df = df.rename(columns={'Days': 'DayOfWeek'})
        elif len(df.columns) > 2:
            df.rename(columns={df.columns[2]: 'DayOfWeek'}, inplace=True)
            
        df['Date'] = df['Date'].astype(str).str.strip()
        df['parsed_date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df = df.dropna(subset=['parsed_date'])
        return df
    except Exception as e:
        st.error(f"❌ Error reading Excel file: {e}")
        return None

df_master = load_master_matrix()
if df_master is None or df_master.empty:
    st.stop()

# 3. Dynamic Subject Extraction & System Exclusions
time_columns = ['9:00-10:30 hrs', '10:45-12:15 hrs', '12:30-14:00 hrs', '15:00-16:30 hrs', '16:45-18:15 hrs', '18:30-20:00 hrs', '20:15- 21:45 hrs']
time_columns = [col for col in time_columns if col in df_master.columns]

SYSTEM_EXCLUSIONS = {
    '', 'Registration', 'END TERM EXAMINATION', 'MID TERM EXAMINATION', 'OSCA (mid Term)',
    'INDEPENDENCE DAY', 'MILAD-UN-NABI', 'MUHARRAM', 'nan', 'None', 'Class Day'
}

all_subjects = set()
for col in time_columns:
    for val in df_master[col].dropna().unique():
        val_str = str(val).strip()
        if '/' in val_str:
            all_subjects.update([item.strip() for item in val_str.split('/')])
        else:
            all_subjects.add(val_str)

selectable_subjects = sorted(list(all_subjects - SYSTEM_EXCLUSIONS))

# 4. JSON Profile Management (Persistent Storage)
def load_user_profiles():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_profiles(profiles):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(profiles, f, indent=4)

if 'profiles' not in st.session_state:
    st.session_state.profiles = load_user_profiles()
if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None

# --- SIDEBAR: SECURE GATEWAY ---
st.sidebar.header("🔑 Secure Gateway")
auth_mode = st.sidebar.radio("Choose Action:", ["Login", "Register New User"])

if auth_mode == "Register New User":
    st.sidebar.subheader("✨ Register Private Profile")
    reg_name = st.sidebar.text_input("Name:", key="reg_name", placeholder="e.g., Niket Gupta").strip()
    reg_key = st.sidebar.text_input("Create Passkey:", type="password", key="reg_key")
    
    if st.sidebar.button("Register Profile", use_container_width=True):
        if not reg_name or not reg_key:
            st.sidebar.error("Please fill out both fields.")
        elif reg_name in st.session_state.profiles:
            st.sidebar.error("This username is already taken.")
        else:
            st.session_state.profiles[reg_name] = {
                "key_hash": hash_passkey(reg_key),
                "subjects": [s for s in selectable_subjects if s in ['SIMCO(S2)', 'FIS', 'DAP', 'CS(S2)', 'CRM']],
                "attendance": {}
            }
            save_user_profiles(st.session_state.profiles)
            st.sidebar.success("Registration complete! Switch to Login mode.")

else:
    st.sidebar.subheader("🔒 Sign In")
    login_name = st.sidebar.text_input("Username:", key="login_name").strip()
    login_key = st.sidebar.text_input("Passkey:", type="password", key="login_key")
    
    col_log, col_out = st.sidebar.columns(2)
    with col_log:
        if st.button("Log In", use_container_width=True):
            if login_name in st.session_state.profiles and st.session_state.profiles[login_name]["key_hash"] == hash_passkey(login_key):
                st.session_state.authenticated_user = login_name
                st.rerun()
            else:
                st.sidebar.error("Invalid username or passkey.")
    with col_out:
        if st.button("Log Out", use_container_width=True):
            st.session_state.authenticated_user = None
            st.rerun()

# --- BLOCKED GATEWAY ---
if st.session_state.authenticated_user is None:
    st.warning("🔒 This workspace is locked. Please log in or register via the sidebar to access your dashboard.")
    st.stop()

current_user = st.session_state.authenticated_user
st.sidebar.markdown(f"### 🟢 Active Session: **{current_user}**")

# Manage Electives securely using Form wrapper
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Customize Enrolled Courses")

with st.sidebar.form(key="elective_form"):
    chosen_subjects = st.multiselect(
        "Select your active courses:",
        options=selectable_subjects,
        default=st.session_state.profiles[current_user]["subjects"]
    )
    submit_button = st.form_submit_button("💾 Save Subject Changes", use_container_width=True)
    
    if submit_button:
        st.session_state.profiles[current_user]["subjects"] = chosen_subjects
        save_user_profiles(st.session_state.profiles)
        st.toast("Courses modified securely!")
        st.rerun()

# Fetch active course list
updated_subjects = st.session_state.profiles[current_user]["subjects"]

# Timeline Baseline Configurations
st.sidebar.markdown("---")
st.sidebar.header("📆 Timeline Baseline")
real_today = datetime.date.today()
min_date = df_master['parsed_date'].min()
max_date = df_master['parsed_date'].max()

default_date = real_today if min_date <= real_today <= max_date else datetime.date(2026, 6, 10)
today = st.sidebar.date_input("Today's Reference Date:", default_date)
free_horizon = st.sidebar.slider("Lookahead horizon for free days:", 7, 30, 14)

# --- REPARSE ENGINE ---
parsed_rows = []
for _, row in df_master.iterrows():
    current_date = row['parsed_date']
    day_name = row.get('DayOfWeek', 'Class Day')
    
    for col in time_columns:
        cell_val = str(row[col]).strip() if pd.notna(row[col]) else ""
        if not cell_val or cell_val in SYSTEM_EXCLUSIONS:
            continue
            
        matched_subject = None
        if '/' in cell_val:
            options = [o.strip() for o in cell_val.split('/')]
            for option in options:
                if option in updated_subjects:
                    matched_subject = option
                    break
        else:
            if cell_val in updated_subjects:
                matched_subject = cell_val
                
        if matched_subject:
            parsed_rows.append({
                'Date': current_date,
                'Day': day_name,
                'Time Slot': col,
                'Subject': matched_subject
            })

df_filtered = pd.DataFrame(parsed_rows) if parsed_rows else pd.DataFrame(columns=['Date', 'Day', 'Time Slot', 'Subject'])

# --- MAIN RENDER HUB PORTAL ---
if df_filtered.empty:
    st.warning("⚠️ No personalized course data found matching your choices. Use the form in the sidebar to add electives.")
else:
    next_day = today + datetime.timedelta(days=1)
    next_week_start = today + datetime.timedelta(days=1)
    next_week_end = today + datetime.timedelta(days=7)
    
    # Left-side tracking analytics completely removed, layout shifted to centerpiece tabs
    tab_today, tab_tomorrow, tab_week, tab_free, tab_analytics, tab_all = st.tabs([
        "📅 Today's Agenda", 
        "🌅 Tomorrow's Preview", 
        "📆 Rolling Week Outlook", 
        "🏖️ Free Days Tracker",
        "📊 Comprehensive Analytics",
        "🗂️ Entire Term Logs"
    ])
    
    # USER DATA ATTENDANCE BINDING DIRECTORY
    user_attendance_dict = st.session_state.profiles[current_user]["attendance"]

    # TAB 1: TODAY'S ACTIVE DIARY
    with tab_today:
        st.subheader(f"Schedule for Today: {today.strftime('%A, %b %d, %Y')}")
        today_df = df_filtered[df_filtered['Date'] == today]
        
        if not today_df.empty:
            st.info("Log your active status updates directly as they happen today.")
            for idx, row in today_df.iterrows():
                col1, col2, col3 = st.columns([2, 3, 2])
                key_str = f"{row['Date']}_{row['Time Slot']}"
                current_val = user_attendance_dict.get(key_str, "")
                
                with col1:
                    st.markdown(f"**⏰ {row['Time Slot']}**")
                with col2:
                    st.markdown(f"📖 `{row['Subject']}`")
                with col3:
                    options = ["", "Y", "N"]
                    def_idx = options.index(current_val) if current_val in options else 0
                    choice = st.selectbox(
                        "Status", options=options, index=def_idx, key=f"today_log_{key_str}",
                        format_func=lambda x: "🕒 Scheduled" if x == "" else ("✅ Attended" if x == "Y" else "❌ Absent")
                    )
                    if choice != current_val:
                        st.session_state.profiles[current_user]["attendance"][key_str] = choice
                        save_user_profiles(st.session_state.profiles)
                        st.rerun()
        else:
            st.success("🎉 No active classes scheduled matching your courses today!")

    # TAB 2: TOMORROW'S PREVIEW
    with tab_tomorrow:
        st.subheader(f"Agenda for Tomorrow: {next_day.strftime('%A, %b %d, %Y')}")
        tomorrow_df = df_filtered[df_filtered['Date'] == next_day]
        if not tomorrow_df.empty:
            st.dataframe(tomorrow_df[['Time Slot', 'Subject']].reset_index(drop=True), use_container_width=True)
        else:
            st.success("🎉 Freedom! No academic sessions scheduled for tomorrow.")

    # TAB 3: ROLLING WEEK VIEW
    with tab_week:
        st.subheader(f"Outlook: {next_week_start.strftime('%b %d')} to {next_week_end.strftime('%b %d, %Y')}")
        week_df = df_filtered[(df_filtered['Date'] >= next_week_start) & (df_filtered['Date'] <= next_week_end)]
        if not week_df.empty:
            st.dataframe(week_df.sort_values(by=['Date', 'Time Slot']).reset_index(drop=True)[['Date', 'Day', 'Time Slot', 'Subject']], use_container_width=True)
        else:
            st.info("No active courses found for the coming rolling 7 days.")

    # TAB 4: FREE DAYS HORIZON
    with tab_free:
        st.subheader(f"🏖️ Available Free Days (Next {free_horizon} Days)")
        all_days = [today + datetime.timedelta(days=i) for i in range(1, free_horizon + 1)]
        busy_days = set(df_filtered['Date'].unique())
        free_days = [d for d in all_days if d not in busy_days]
        if free_days:
            st.dataframe(pd.DataFrame({'Calendar Date': free_days, 'Day of Week': [d.strftime('%A') for d in free_days]}), use_container_width=True)
        else:
            st.warning("No completely free days found in your targeted horizon roadmap.")

    # NEW TAB 5: CENTRALIZED COMPREHENSIVE ATTENDANCE ANALYTICS MATRIX
    with tab_analytics:
        st.subheader("📊 Subject-Wise Presence & Absence Audit")
        st.markdown("This tracker separates core academic data into overall milestones and dynamic compliance indicators.")
        
        # Build comprehensive data dictionary mapping performance vectors
        analytics_data = []
        
        for sub in updated_subjects:
            sub_total_df = df_filtered[df_filtered['Subject'] == sub]
            total_term_classes = len(sub_total_df)
            
            # Counter metrics
            attended, absent, unmarked = 0, 0, 0
            for _, r in sub_total_df.iterrows():
                key = f"{r['Date']}_{r['Time Slot']}"
                status = user_attendance_dict.get(key, "")
                if status == 'Y':
                    attended += 1
                elif status == 'N':
                    absent += 1
                else:
                    unmarked += 1
            
            logged_classes = attended + absent
            compliance_pct = (attended / logged_classes * 100) if logged_classes > 0 else 100.0
            
            # Safe calculation tracking threshold limits (75% rule)
            consecutive_needed = 0
            if compliance_pct < 75.0 and logged_classes > 0:
                # Math ceiling loop to find safe margin balance recovery vectors
                temp_att, temp_logged = attended, logged_classes
                while (temp_att / temp_logged * 100) < 75.0:
                    temp_att += 1
                    temp_logged += 1
                    consecutive_needed += 1
            
            analytics_data.append({
                "Subject": sub,
                "Total Term Sessions": total_term_classes,
                "Logged Attended (✅)": attended,
                "Logged Absent (❌)": absent,
                "Remaining/Unmarked": unmarked,
                "Logged Attendance Ratio": compliance_pct,
                "Recovery Target Status": f"🚨 Attend next {consecutive_needed} classes" if consecutive_needed > 0 else "🍏 Compliant"
            })
            
        df_analytics_matrix = pd.DataFrame(analytics_data)
        
        # Display Summary cards
        c_tot, c_att, c_abs = st.columns(3)
        c_tot.metric("Total Term Classes Enrolled", len(df_filtered))
        c_att.metric("Total Sessions Attended Across Board", sum(d['Logged Attended (✅)'] for d in analytics_data))
        c_abs.metric("Total Logged Absences", sum(d['Logged Absent (❌)'] for d in analytics_data))
        
        st.markdown("---")
        st.markdown("#### Detailed Attendance & Compliance Register")
        
        # Style formatting helper for Streamlit table matrix grid view
        def highlight_shortfall(val):
            if '🚨' in str(val):
                return 'background-color: #fce8e6; color: #a51d24; font-weight: bold;'
            elif '🍏' in str(val):
                return 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
            return ''
            
        styled_df = df_analytics_matrix.style.format({
            "Logged Attendance Ratio": "{:.1f}%"
        }).map(highlight_shortfall, subset=["Recovery Target Status"])
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # TAB 6: GLOBAL ROADMAP ENTRIES
    with tab_all:
        st.subheader("🗂️ Entire Filtered Term Roadmap Archive")
        display_term = df_filtered.sort_values(by=['Date', 'Time Slot']).copy()
        display_term['Timeline Context'] = display_term['Date'].apply(lambda x: '⏸️ Past' if x < today else '▶️ Active')
        
        # Pull tracking maps directly into the data matrix framework for simple comprehensive auditing
        display_term['Logged Status'] = display_term.apply(lambda r: user_attendance_dict.get(f"{r['Date']}_{r['Time Slot']}", "🕒 Scheduled"), axis=1)
        display_term['Logged Status'] = display_term['Logged Status'].replace({'Y': '✅ Attended', 'N': '❌ Absent'})
        
        st.dataframe(display_term.reset_index(drop=True)[['Date', 'Day', 'Time Slot', 'Subject', 'Timeline Context', 'Logged Status']], use_container_width=True)