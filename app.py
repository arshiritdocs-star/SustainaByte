import streamlit as st
import pandas as pd
import plotly.express as px

from auditor.architectures import (
    get_candidate_architectures
)

from auditor.lifecycle_math import (
    Workload,
    calculate_lifecycle_impact
)

from auditor.auth import (
    init_auth_db,
    is_registered,
    register_user,
    request_otp,
    register_and_send_otp,
    verify_otp
)

from auditor.gemini_auditor import (
    run_lifecycle_audit
)

from auditor.sync_engine import (
    init_db,
    is_connected,
    get_pending_audits_count,
    get_all_audits,
    save_audit,
    reconcile_pending_audits,
    start_background_reconciler
)


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="SustainaByte | Sustainable AI Auditor",
    page_icon="🍃",
    layout="wide"
)


# ==================================================
# DATABASE INITIALIZATION
# ==================================================

init_auth_db()
init_db()

if "reconciler_started" not in st.session_state:

    start_background_reconciler()

    st.session_state.reconciler_started = True


# ==================================================
# SESSION STATE
# ==================================================

if "authenticated" not in st.session_state:

    st.session_state.authenticated = False


if "user_email" not in st.session_state:

    st.session_state.user_email = ""


if "auth_mode" not in st.session_state:

    st.session_state.auth_mode = "Login"


if "otp_requested" not in st.session_state:

    st.session_state.otp_requested = False


if "registration_otp_requested" not in st.session_state:

    st.session_state.registration_otp_requested = False


# ==================================================
# AUTHENTICATION
# ==================================================

if not st.session_state.authenticated:

    st.title("🍃 SustainaByte")

    st.subheader(
        "Sustainable AI Lifecycle Auditor"
    )

    st.write(
        "Sign in to access the AI lifecycle "
        "sustainability dashboard."
    )

    st.divider()

    auth_mode = st.radio(
        "Account",
        [
            "Login",
            "Register"
        ],
        horizontal=True
    )

    st.session_state.auth_mode = auth_mode


    # ==================================================
    # LOGIN
    # ==================================================

    if auth_mode == "Login":

        st.header("🔐 Login")

        email = st.text_input(
            "Email address",
            key="login_email"
        )

        if st.button(
            "Send Login OTP",
            use_container_width=True
        ):

            if not email.strip():

                st.error(
                    "Please enter your email address."
                )

            elif not is_registered(email):

                st.error(
                    "This email is not registered."
                )

            else:

                success, message = request_otp(
                    email
                )

                if success:

                    st.session_state.user_email = (
                        email.strip().lower()
                    )

                    st.session_state.otp_requested = True

                    st.success(message)

                else:

                    st.error(message)


        if st.session_state.otp_requested:

            st.subheader(
                "Enter Login OTP"
            )

            login_otp = st.text_input(
                "6-digit OTP",
                max_chars=6,
                key="login_otp"
            )

            if st.button(
                "Verify Login OTP",
                use_container_width=True
            ):

                success, message = verify_otp(
                    st.session_state.user_email,
                    login_otp
                )

                if success:

                    st.session_state.authenticated = True

                    st.session_state.otp_requested = False

                    st.success(
                        "Login successful."
                    )

                    st.rerun()

                else:

                    st.error(message)


    # ==================================================
    # REGISTRATION
    # ==================================================

    else:

        st.header("📝 Register")

        email = st.text_input(
            "Email address",
            key="register_email"
        )

        if st.button(
            "Send Registration OTP",
            use_container_width=True
        ):

            if not email.strip():

                st.error(
                    "Please enter your email address."
                )

            elif is_registered(email):

                st.error(
                    "This email is already registered."
                )

            else:

                success, message = (
                    register_and_send_otp(
                        email
                    )
                )

                if success:

                    st.session_state.user_email = (
                        email.strip().lower()
                    )

                    st.session_state.registration_otp_requested = True

                    st.success(message)

                else:

                    st.error(message)


        if st.session_state.registration_otp_requested:

            st.subheader(
                "Enter Registration OTP"
            )

            registration_otp = st.text_input(
                "6-digit OTP",
                max_chars=6,
                key="registration_otp"
            )

            if st.button(
                "Verify Registration OTP",
                use_container_width=True
            ):

                success, message = verify_otp(
                    st.session_state.user_email,
                    registration_otp
                )

                if success:

                    registered = register_user(
                        st.session_state.user_email
                    )

                    if registered:

                        st.session_state.authenticated = True

                        st.session_state.registration_otp_requested = False

                        st.success(
                            "Registration successful."
                        )

                        st.rerun()

                    else:

                        st.error(
                            "Registration could not be completed."
                        )

                else:

                    st.error(message)


    st.stop()


# ==================================================
# CONSTANTS
# ==================================================

GRID_CARBON_INTENSITY = 0.45


# ==================================================
# HEADER
# ==================================================

st.title("🍃 SustainaByte")

st.subheader(
    "Sustainable AI Lifecycle Auditor"
)

st.markdown(
    """
    Describe what your AI system does and what kind
    of data it receives. SustainaByte identifies
    compatible architecture candidates and estimates
    their lifecycle environmental impact.
    """
)


# ==================================================
# USER INFORMATION
# ==================================================

user_col1, user_col2 = st.columns(
    [4, 1]
)

with user_col1:

    st.caption(
        f"Signed in as: {st.session_state.user_email}"
    )

with user_col2:

    if st.button(
        "Logout"
    ):

        st.session_state.authenticated = False

        st.session_state.user_email = ""

        st.session_state.otp_requested = False

        st.session_state.registration_otp_requested = False

        st.rerun()


st.divider()


# ==================================================
# AI SYSTEM PROFILE
# ==================================================

st.header(
    "🤖 Describe Your AI System"
)

st.write(
    "Tell SustainaByte what your AI system does "
    "and what type of data it processes."
)


task_type = st.selectbox(
    "What is your AI task?",
    [
        "Classification",
        "Regression",
        "Image Classification",
        "Text Classification",
        "Time-Series Forecasting"
    ]
)


input_type = st.selectbox(
    "What type of input data does your AI model receive?",
    [
        "Tabular",
        "Image",
        "Text",
        "Time-Series"
    ]
)


use_case = st.text_area(
    "Describe your AI system",
    placeholder=(
        "Example: Predict house prices using area, "
        "number of rooms, location and age of the house."
    ),
    height=100
)


# ==================================================
# DATASET CHARACTERISTICS
# ==================================================

st.subheader(
    "📊 Dataset Characteristics"
)


dataset_samples = st.number_input(
    "Number of training samples",
    min_value=1,
    value=100000,
    step=1000
)


if input_type in [
    "Tabular",
    "Time-Series"
]:

    input_features = st.number_input(
        "Number of input features",
        min_value=1,
        value=20,
        step=1
    )

else:

    input_features = st.number_input(
        "Average input size / features",
        min_value=1,
        value=100,
        step=1
    )


dataset_size_gb = st.number_input(
    "Dataset size (GB)",
    min_value=0.001,
    value=1.0,
    step=0.1
)


# ==================================================
# USAGE REQUIREMENTS
# ==================================================

st.subheader(
    "⚙️ Usage Requirements"
)


requests = st.number_input(
    "Inference Requests",
    min_value=1,
    value=100000,
    step=1000
)


workload_hours = st.number_input(
    "Workload Hours",
    min_value=0.0,
    value=100.0
)


max_latency = st.number_input(
    "Maximum Latency (ms)",
    min_value=0.0,
    value=80.0
)


min_accuracy = st.number_input(
    "Minimum Accuracy (%)",
    min_value=0.0,
    max_value=100.0,
    value=88.0
)


retraining_runs = st.number_input(
    "Retraining Runs per Year",
    min_value=0,
    value=4,
    step=1
)


pue = st.number_input(
    "PUE",
    min_value=1.0,
    value=1.4
)


# ==================================================
# SIDEBAR NETWORK
# ==================================================

st.sidebar.divider()

st.sidebar.header(
    "🌐 Network"
)


simulated_outage = st.sidebar.toggle(
    "Simulate Network Outage",
    value=False
)


# ==================================================
# AI SYSTEM PROFILE DISPLAY
# ==================================================

st.divider()

st.header(
    "🤖 AI System Profile"
)


profile_col1, profile_col2, profile_col3 = (
    st.columns(3)
)


with profile_col1:

    st.metric(
        "AI Task",
        task_type
    )


with profile_col2:

    st.metric(
        "Input Type",
        input_type
    )


with profile_col3:

    st.metric(
        "Dataset Size",
        f"{dataset_size_gb:.2f} GB"
    )


if use_case.strip():

    st.info(
        f"**Use Case:** {use_case}"
    )


# ==================================================
# FIND COMPATIBLE ARCHITECTURES
# ==================================================

architectures = get_candidate_architectures(
    task_type=task_type,
    input_type=input_type
)


if len(architectures) == 0:

    st.error(
        "No architecture in the current prototype "
        "supports this combination of task and input type."
    )

    st.info(
        "Try another task/input combination."
    )

    st.stop()


st.success(
    f"Found {len(architectures)} suitable "
    f"architecture(s) for your AI system."
)


# ==================================================
# NETWORK STATUS
# ==================================================

if simulated_outage:

    st.warning(
        "⚠️ Network outage simulation is enabled. "
        "The lifecycle calculation remains available "
        "locally."
    )

else:

    if is_connected():

        st.success(
            "🌐 Network connection available."
        )

    else:

        st.warning(
            "🌐 Network connection unavailable. "
            "Local audit mode is active."
        )


# ==================================================
# CREATE WORKLOAD
# ==================================================

workload = Workload(
    inference_count=int(requests),

    training_hours=float(
        workload_hours
    ),

    dataset_size_gb=float(
        dataset_size_gb
    ),

    carbon_intensity_gco2_per_kwh=(
        GRID_CARBON_INTENSITY * 1000
    ),

    pue=float(
        pue
    ),

    retraining_runs=int(
        retraining_runs
    ),

    retraining_training_hours=1.0
)


# ==================================================
# CALCULATE LIFECYCLE IMPACT
# ==================================================

results_list = []


for architecture in architectures:

    impact = calculate_lifecycle_impact(
        architecture=architecture,
        workload=workload
    )


    accuracy_percent = (
        architecture.estimated_accuracy
        * 100.0
    )


    latency_ms = (
        architecture.estimated_latency_ms
    )


    is_eligible = (
        latency_ms <= max_latency
        and accuracy_percent >= min_accuracy
    )


    results_list.append({

        "Architecture": architecture.name,

        "Latency (ms)": latency_ms,

        "Accuracy (%)": accuracy_percent,

        "Eligible": (
            "Yes"
            if is_eligible
            else "No"
        ),

        "Hardware Carbon (kg)": (
            impact[
                "hardware_carbon_kg"
            ]
        ),

        "Inference Energy (kWh)": (
            impact[
                "inference_energy_kwh"
            ]
        ),

        "Inference Carbon (kg)": (
            impact[
                "inference_carbon_kg"
            ]
        ),

        "Storage (GB-hours)": (
            impact[
                "storage_impact_gb_hours"
            ]
        ),

        "Networking Energy (kWh)": (
            impact[
                "networking_energy_kwh"
            ]
        ),

        "Networking Carbon (kg)": (
            impact[
                "networking_carbon_kg"
            ]
        ),

        "Retraining Energy (kWh)": (
            impact[
                "retraining_energy_kwh"
            ]
        ),

        "Retraining Carbon (kg)": (
            impact[
                "retraining_carbon_kg"
            ]
        ),

        "Total Energy (kWh)": (
            impact[
                "total_energy_kwh"
            ]
        ),

        "Total Carbon (kg)": (
            impact[
                "total_carbon_kg"
            ]
        )
    })


results_df = pd.DataFrame(
    results_list
)


# ==================================================
# SLA SUMMARY
# ==================================================

st.header(
    "📋 Enterprise SLA Summary"
)


sla_col1, sla_col2, sla_col3, sla_col4 = (
    st.columns(4)
)


with sla_col1:

    st.metric(
        "Maximum Latency",
        f"{max_latency:.0f} ms"
    )


with sla_col2:

    st.metric(
        "Minimum Accuracy",
        f"{min_accuracy:.1f}%"
    )


with sla_col3:

    st.metric(
        "Total Requests",
        f"{requests:,}"
    )


with sla_col4:

    eligible_count = int(
        (
            results_df["Eligible"]
            == "Yes"
        ).sum()
    )

    st.metric(
        "Eligible Architectures",
        f"{eligible_count}/{len(results_df)}"
    )


# ==================================================
# ARCHITECTURE COMPARISON
# ==================================================

st.divider()

st.header(
    "🏗️ Architecture Comparison"
)


comparison_columns = [
    "Architecture",
    "Latency (ms)",
    "Accuracy (%)",
    "Eligible",
    "Total Energy (kWh)",
    "Total Carbon (kg)"
]


st.dataframe(
    results_df[
        comparison_columns
    ].round(3),

    use_container_width=True,

    hide_index=True
)


# ==================================================
# SLA EVALUATION
# ==================================================

st.header(
    "🔍 SLA Evaluation"
)


for _, row in results_df.iterrows():

    if row["Eligible"] == "Yes":

        st.success(
            f"✅ {row['Architecture']} "
            f"satisfies the latency and "
            f"accuracy requirements."
        )

    else:

        latency_pass = (
            row["Latency (ms)"]
            <= max_latency
        )

        accuracy_pass = (
            row["Accuracy (%)"]
            >= min_accuracy
        )

        reasons = []


        if not latency_pass:

            reasons.append(
                "latency requirement not met"
            )


        if not accuracy_pass:

            reasons.append(
                "accuracy requirement not met"
            )


        st.warning(
            f"⚠️ {row['Architecture']}: "
            + ", ".join(reasons)
            + "."
        )


# ==================================================
# ARCHITECTURE SUMMARY
# ==================================================

st.divider()

st.header(
    "🌱 Sustainability Summary"
)


eligible_df = results_df[
    results_df["Eligible"] == "Yes"
].copy()


if eligible_df.empty:

    st.warning(
        "No architecture satisfies both "
        "the latency and accuracy requirements."
    )

else:

    lowest_carbon = eligible_df[
        "Total Carbon (kg)"
    ].min()

    lowest_energy = eligible_df[
        "Total Energy (kWh)"
    ].min()

    st.info(
        f"""
        **Eligible architecture count:** {len(eligible_df)}

        **Lowest estimated lifecycle carbon among eligible
        candidates:** {lowest_carbon:.4f} kg CO₂e

        **Lowest estimated lifecycle energy among eligible
        candidates:** {lowest_energy:.4f} kWh

        These are estimates based on the prototype's
        architecture and workload assumptions.
        """
    )


# ==================================================
# CHART 1: TOTAL CARBON
# ==================================================

st.header(
    "📊 Total Carbon Comparison"
)


st.caption(
    "Unit: kg CO₂e."
)


carbon_chart = px.bar(
    results_df,

    x="Architecture",

    y="Total Carbon (kg)",

    color="Architecture",

    text_auto=".4f",

    title="Estimated Total Lifecycle Carbon"
)


carbon_chart.update_layout(
    yaxis_title="Total Carbon (kg CO₂e)",

    xaxis_title="Architecture",

    showlegend=False
)


st.plotly_chart(
    carbon_chart,
    use_container_width=True
)


# ==================================================
# CHART 2: ENERGY BREAKDOWN
# ==================================================

st.header(
    "⚡ Energy Consumption Breakdown"
)


energy_columns = [
    "Inference Energy (kWh)",
    "Networking Energy (kWh)",
    "Retraining Energy (kWh)"
]


energy_data = results_df[
    ["Architecture"] + energy_columns
]


energy_long = energy_data.melt(
    id_vars="Architecture",

    var_name="Energy Category",

    value_name="Energy (kWh)"
)


energy_chart = px.bar(
    energy_long,

    x="Architecture",

    y="Energy (kWh)",

    color="Energy Category",

    barmode="group",

    title="Estimated Energy Consumption",

    text_auto=".4f"
)


energy_chart.update_layout(
    yaxis_title="Energy (kWh)",

    xaxis_title="Architecture"
)


st.plotly_chart(
    energy_chart,
    use_container_width=True
)


# ==================================================
# CHART 3: STORAGE
# ==================================================

st.header(
    "💾 Storage Footprint Comparison"
)


storage_chart = px.bar(
    results_df,

    x="Architecture",

    y="Storage (GB-hours)",

    color="Architecture",

    text_auto=".2f",

    title="Estimated Storage Footprint"
)


storage_chart.update_layout(
    yaxis_title="Storage (GB-hours)",

    xaxis_title="Architecture",

    showlegend=False
)


st.plotly_chart(
    storage_chart,
    use_container_width=True
)


# ==================================================
# CHART 4: LATENCY VS ACCURACY
# ==================================================

st.header(
    "🎯 Latency vs Accuracy"
)


latency_accuracy_chart = px.scatter(
    results_df,

    x="Latency (ms)",

    y="Accuracy (%)",

    color="Architecture",

    text="Architecture",

    size="Total Carbon (kg)",

    hover_data=[
        "Eligible",
        "Total Carbon (kg)",
        "Total Energy (kWh)"
    ],

    title="Architecture Performance and SLA Constraints"
)


latency_accuracy_chart.add_vline(
    x=max_latency,

    line_dash="dash",

    annotation_text="Maximum latency",

    annotation_position="top right"
)


latency_accuracy_chart.add_hline(
    y=min_accuracy,

    line_dash="dash",

    annotation_text="Minimum accuracy",

    annotation_position="bottom right"
)


latency_accuracy_chart.update_layout(
    xaxis_title="Latency (ms)",

    yaxis_title="Accuracy (%)",

    yaxis=dict(
        range=[
            max(
                0,
                results_df[
                    "Accuracy (%)"
                ].min() - 5
            ),

            min(
                100,
                results_df[
                    "Accuracy (%)"
                ].max() + 5
            )
        ]
    )
)


st.plotly_chart(
    latency_accuracy_chart,
    use_container_width=True
)


# ==================================================
# CHART 5: CARBON COMPONENTS
# ==================================================

st.header(
    "🌍 Carbon Component Breakdown"
)


carbon_columns = [
    "Hardware Carbon (kg)",
    "Inference Carbon (kg)",
    "Networking Carbon (kg)",
    "Retraining Carbon (kg)"
]


carbon_components = results_df[
    ["Architecture"] + carbon_columns
]


carbon_components_long = (
    carbon_components.melt(
        id_vars="Architecture",

        var_name="Carbon Category",

        value_name="Carbon (kg)"
    )
)


carbon_components_chart = px.bar(
    carbon_components_long,

    x="Architecture",

    y="Carbon (kg)",

    color="Carbon Category",

    barmode="group",

    title="Estimated Carbon by Lifecycle Component",

    text_auto=".4f"
)


carbon_components_chart.update_layout(
    yaxis_title="Carbon (kg CO₂e)",

    xaxis_title="Architecture"
)


st.plotly_chart(
    carbon_components_chart,

    use_container_width=True
)


# ==================================================
# GEMINI AUDIT
# ==================================================

st.divider()

st.header(
    "🧠 AI Sustainability Audit"
)


workload_desc = (
    f"AI system use case: "
    f"{use_case if use_case.strip() else 'Not provided'}. "

    f"Task type: {task_type}. "

    f"Input data type: {input_type}. "

    f"Training dataset contains approximately "
    f"{dataset_samples:,} samples and "
    f"{input_features:,} input features. "

    f"Dataset size is "
    f"{dataset_size_gb:.2f} GB. "

    f"The system handles "
    f"{requests:,} inference requests. "

    f"Operating workload is "
    f"{workload_hours} hours. "

    f"PUE is {pue}. "

    f"Retraining runs per year: "
    f"{retraining_runs}. "

    f"Minimum accuracy requirement is "
    f"{min_accuracy}%. "

    f"Maximum latency requirement is "
    f"{max_latency} ms."
)


audited_models = []


for _, row in results_df.iterrows():

    audited_models.append({

        "architecture": row[
            "Architecture"
        ],

        "accuracy": row[
            "Accuracy (%)"
        ],

        "latency_ms": row[
            "Latency (ms)"
        ],

        "energy_kwh": row[
            "Total Energy (kWh)"
        ],

        "carbon_kg": row[
            "Total Carbon (kg)"
        ],

        "storage_gb_hours": row[
            "Storage (GB-hours)"
        ]
    })


if st.button(
    "Generate Eco-Nutrition Label",
    use_container_width=True
):

    audit_text = run_lifecycle_audit(
        workload_desc=workload_desc,

        target_acc=min_accuracy,

        max_lat=max_latency,

        audited_models=audited_models
    )


    st.session_state.audit_text = (
        audit_text
    )

    save_audit(
        audit_text
    )


if "audit_text" in st.session_state:

    st.markdown(
        st.session_state.audit_text
    )


# ==================================================
# AUDIT HISTORY
# ==================================================

st.divider()

st.header(
    "📚 Audit History"
)


pending_count = (
    get_pending_audits_count()
)


history_col1, history_col2 = (
    st.columns(2)
)


with history_col1:

    st.metric(
        "Pending Local Audits",
        pending_count
    )


with history_col2:

    connection_status = (
        "Online"
        if is_connected()
        else "Offline"
    )

    st.metric(
        "Connection",
        connection_status
    )


if st.button(
    "Sync Pending Audits"
):

    reconcile_pending_audits()

    st.success(
        "Audit synchronization attempted."
    )

    st.rerun()


audit_history = get_all_audits()


if audit_history:

    history_df = pd.DataFrame(
        audit_history,

        columns=[
            "ID",
            "Created At",
            "Status",
            "Audit"
        ]
    )

    st.dataframe(
        history_df,

        use_container_width=True,

        hide_index=True
    )

else:

    st.info(
        "No audit history available yet."
    )


# ==================================================
# DETAILED RESULTS
# ==================================================

st.divider()

st.header(
    "📄 Detailed Calculation Results"
)


with st.expander(
    "View detailed calculation results"
):

    st.dataframe(
        results_df.round(4),

        use_container_width=True,

        hide_index=True
    )


    csv_data = (
        results_df
        .to_csv(index=False)
        .encode("utf-8")
    )


    st.download_button(
        label="⬇️ Download Results as CSV",

        data=csv_data,

        file_name=(
            "sustainabyte_results.csv"
        ),

        mime="text/csv"
    )


# ==================================================
# ASSUMPTIONS
# ==================================================

st.divider()

st.header(
    "ℹ️ Assumptions and Limitations"
)


st.markdown(
    f"""
    - Grid carbon intensity:
      **{GRID_CARBON_INTENSITY} kg CO₂e/kWh**.
    - PUE is a user-controlled scenario input.
    - Architecture specifications are illustrative
      prototype values.
    - Energy and carbon values are estimates, not
      direct measurements.
    - Estimated accuracy values are architecture
      presets and are not produced by training a model
      on the user's dataset.
    - Dataset sample count and feature count are used
      to characterize the workload and provide context
      to the audit.
    - Storage is reported in GB-hours.
    - The current prototype supports a limited set of
      architecture candidates.
    - Gemini analysis is optional and can operate in
      local debug mode.
    """
)


st.caption(
    """
    SustainaByte | Sustainable AI Lifecycle Auditor
    | Hackathon Prototype
    """
)
