from auditor.auth import (
    init_auth_db,
    is_registered,
    register_user,
    request_otp,
    register_and_send_otp,
    verify_otp,
)
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from auditor.architectures import get_architectures
from auditor.lifecycle_math import (
    Workload,
    calculate_lifecycle_impact
)

from auditor.gemini_auditor import run_lifecycle_audit

from auditor.sync_engine import (
    init_db,
    is_connected,
    get_pending_audits_count,
    get_all_audits,
    reconcile_pending_audits,
    start_background_reconciler
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SustainaByte | Sustainable AI Auditor",
    page_icon="🌱",
    layout="wide"
)
# ==================================================
# AUTHENTICATION
# ==================================================

init_auth_db()
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "login_email" not in st.session_state:
    st.session_state["login_email"] = ""

if "otp_sent" not in st.session_state:
    st.session_state["otp_sent"] = False

if "register_email" not in st.session_state:
    st.session_state["register_email"] = ""

if "register_otp_sent" not in st.session_state:
    st.session_state["register_otp_sent"] = False

# ==================================================
# LOGIN SCREEN
# ==================================================

if not st.session_state["authenticated"]:

    st.title("🍃 SustainaByte")
    st.subheader("🔐 Secure Authentication")

    auth_mode = st.radio(
        "Choose an option",
        ["Login", "Register"],
        horizontal=True
    )

    # ---------------- REGISTER ----------------
    if auth_mode == "Register":

        st.markdown("### Create your account")

        register_email = st.text_input(
            "Email Address",
            placeholder="you@example.com"
        ).strip().lower()

        if st.button(
            "📧 Send Registration OTP",
            use_container_width=True
        ):
            if not register_email:
                st.error("Please enter your email address.")

            elif is_registered(register_email):
                st.error("This email is already registered. Please login.")

            else:
                success, message = register_and_send_otp(
                    register_email
                )

                if success:
                    st.session_state["register_email"] = register_email
                    st.session_state["register_otp_sent"] = True
                    st.success("OTP sent to your email.")

                else:
                    st.error(message)

        if st.session_state.get("register_otp_sent", False):

            st.divider()

            st.markdown("### 🔢 Verify Registration OTP")

            registration_otp = st.text_input(
                "Enter 6-digit OTP",
                max_chars=6,
                type="password",
                key="registration_otp"
            )

            if st.button(
                "✅ Verify & Create Account",
                use_container_width=True
            ):

                success, message = verify_otp(
                    st.session_state["register_email"],
                    registration_otp
                )

                if success:

                    register_user(
                        st.session_state["register_email"]
                    )

                    st.session_state["register_otp_sent"] = False
                    st.session_state["otp_sent"] = False

                    st.success(
                        "Account created successfully! "
                        "You can now login."
                    )

                    st.rerun()

                else:
                    st.error(message)

    # ---------------- LOGIN ----------------
    else:

        st.markdown("### Login")

        login_email = st.text_input(
            "Registered Email",
            placeholder="you@example.com"
        ).strip().lower()

        if st.button(
            "📧 Send Login OTP",
            use_container_width=True
        ):

            if not login_email:
                st.error("Please enter your email address.")

            elif not is_registered(login_email):
                st.error(
                    "This email is not registered. "
                    "Please register first."
                )

            else:

                success, message = request_otp(
                    login_email
                )

                if success:
                    st.session_state["login_email"] = login_email
                    st.session_state["otp_sent"] = True
                    st.success("OTP sent to your email.")

                else:
                    st.error(message)

        if st.session_state.get("otp_sent", False):

            st.divider()

            st.markdown("### 🔢 Verify Login OTP")

            login_otp = st.text_input(
                "Enter 6-digit OTP",
                max_chars=6,
                type="password",
                key="login_otp"
            )

            if st.button(
                "✅ Verify OTP",
                use_container_width=True
            ):

                success, message = verify_otp(
                    st.session_state["login_email"],
                    login_otp
                )

                if success:

                    st.session_state["authenticated"] = True
                    st.session_state["otp_sent"] = False

                    st.success("Login successful!")

                    st.rerun()

                else:
                    st.error(message)

    st.stop()

# ============================================================
# TITLE
# ============================================================

st.title("🌱 SustainaByte")
st.subheader("Sustainable AI Lifecycle Auditor")

st.write(
    "Estimate the energy, carbon, storage, networking, hardware, "
    "and retraining impact of different AI architectures."
)


# ============================================================
# OFFLINE LEDGER & SYNC INITIALIZATION
# ============================================================

if "init_done" not in st.session_state:
    init_db()
    start_background_reconciler(interval_sec=5)
    st.session_state["init_done"] = True


# ============================================================
# CONNECTIVITY STATUS
# ============================================================

st.divider()

col_status, col_sync = st.columns([4, 1])

with col_status:

    if is_connected():

        st.success(
            f"🟢 *System Online* | Cloud Gemini Active | "
            f"Queue: {get_pending_audits_count()}"
        )

    else:

        st.warning(
            f"🟠 *Network Offline* | Local Math Active | "
            f"Unsynced: {get_pending_audits_count()}"
        )


with col_sync:

    if st.button(
        "🔄 Force Sync",
        use_container_width=True
    ):

        reconcile_pending_audits()
        st.rerun()


st.divider()


# ============================================================
# SIDEBAR INPUTS
# ============================================================

st.sidebar.header("⚙️ Workload Parameters")


requests = st.sidebar.number_input(
    "Number of Requests",
    min_value=1,
    value=100000
)


workload_hours = st.sidebar.number_input(
    "Workload Hours",
    min_value=0.0,
    value=100.0
)


max_latency = st.sidebar.number_input(
    "Maximum Latency (ms)",
    min_value=0.0,
    value=80.0
)


min_accuracy = st.sidebar.number_input(
    "Minimum Accuracy (%)",
    min_value=0.0,
    max_value=100.0,
    value=88.0
)


pue = st.sidebar.number_input(
    "PUE",
    min_value=1.0,
    value=1.4
)


st.sidebar.divider()

simulated_outage = st.sidebar.toggle(
    "Simulate Network Outage",
    value=False
)


# ============================================================
# CONSTANTS
# ============================================================

GRID_CARBON_INTENSITY = 0.45


# ============================================================
# WORKLOAD
# ============================================================

workload = Workload(
    inference_count=requests,
    training_hours=workload_hours,
    carbon_intensity_gco2_per_kwh=(
        GRID_CARBON_INTENSITY * 1000
    ),
    pue=pue,
    retraining_training_hours=1.0
)


# ============================================================
# ARCHITECTURE CALCULATIONS
# ============================================================

architectures = get_architectures()

results = []


for architecture in architectures:

    impact = calculate_lifecycle_impact(
        architecture=architecture,
        workload=workload
    )

    results.append(
        {
            # ========================================================
            # REQUIRED BY gemini_auditor.py
            # ========================================================

            "name": architecture.name,

            "latency_ms":
                architecture.estimated_latency_ms,

            "accuracy":
                architecture.estimated_accuracy * 100,

            "total_lifecycle_carbon_kg":
                impact["carbon"]["total_carbon_kg"],


            # ========================================================
            # EXISTING DASHBOARD FIELDS
            # ========================================================

            "Architecture":
                architecture.name,

            "Latency (ms)":
                architecture.estimated_latency_ms,

            "Accuracy (%)":
                architecture.estimated_accuracy * 100,

            "Inference Energy (kWh)":
                impact["energy"][
                    "inference_energy_kwh"
                ],

            "Inference Carbon (kg)":
                impact["energy"][
                    "inference_energy_kwh"
                ] * GRID_CARBON_INTENSITY,

            "Total Energy (kWh)":
                impact["energy"][
                    "total_energy_kwh"
                ],

            "Operational Carbon (kg)":
                impact["carbon"][
                    "operational_carbon_kg"
                ],

            "Hardware Carbon (kg)":
                impact["hardware"][
                    "embodied_carbon_kg"
                ],

            "Total Carbon (kg)":
                impact["carbon"][
                    "total_carbon_kg"
                ],

            "Storage (GB)":
                impact["storage"][
                    "total_storage_gb"
                ],

            "Networking Energy (kWh)":
                impact["networking"][
                    "network_energy_kwh"
                ],

            "Networking (GB)":
                impact["networking"][
                    "total_network_gb"
                ],

            "Retraining Energy (kWh)":
                impact["retraining"][
                    "retraining_energy_kwh"
                ],

            "Retraining Carbon (kg)":
                impact["retraining"][
                    "retraining_carbon_kg"
                ],

            "Retraining Runs":
                impact["retraining"][
                    "retraining_runs"
                ],
        }
    )


df = pd.DataFrame(results)


# ============================================================
# CHECK ARCHITECTURE COUNT
# ============================================================

if len(df) != 4:

    st.error(
        f"Expected 4 architectures, but received {len(df)}."
    )

    st.stop()


# ============================================================
# SLA EVALUATION
# ============================================================

df["Latency OK"] = (
    df["Latency (ms)"]
    <= max_latency
)


df["Accuracy OK"] = (
    df["Accuracy (%)"]
    >= min_accuracy
)


df["SLA Met"] = (
    df["Latency OK"]
    & df["Accuracy OK"]
)


# ============================================================
# NORMALIZED SUSTAINABILITY SCORE
# ============================================================

def normalize_inverse(series):

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:

        return pd.Series(
            [100.0] * len(series),
            index=series.index
        )

    return (
        100
        * (maximum - series)
        / (maximum - minimum)
    )


energy_score = normalize_inverse(
    df["Total Energy (kWh)"]
)


carbon_score = normalize_inverse(
    df["Total Carbon (kg)"]
)


storage_score = normalize_inverse(
    df["Storage (GB)"]
)


network_score = normalize_inverse(
    df["Networking (GB)"]
)


retraining_score = normalize_inverse(
    df["Retraining Carbon (kg)"]
)


latency_score = normalize_inverse(
    df["Latency (ms)"]
)


df["Sustainability Score"] = (
    energy_score
    + carbon_score
    + storage_score
    + network_score
    + retraining_score
    + latency_score
) / 6


# ============================================================
# SLA SUMMARY
# ============================================================

st.header("📋 SLA Summary")

col1, col2, col3 = st.columns(3)


with col1:

    st.metric(
        "Maximum Latency",
        f"{max_latency:.1f} ms"
    )


with col2:

    st.metric(
        "Minimum Accuracy",
        f"{min_accuracy:.1f}%"
    )


with col3:

    st.metric(
        "PUE",
        f"{pue:.2f}"
    )


# ============================================================
# ARCHITECTURE COMPARISON
# ============================================================

st.header("🏗️ Architecture Comparison")


st.dataframe(
    df[
        [
            "Architecture",
            "Latency (ms)",
            "Accuracy (%)",
            "Inference Energy (kWh)",
            "Inference Carbon (kg)",
            "Total Energy (kWh)",
            "Total Carbon (kg)",
        ]
    ],
    use_container_width=True,
    hide_index=True
)


st.dataframe(
    df[
        [
            "Architecture",
            "Storage (GB)",
            "Networking Energy (kWh)",
            "Retraining Energy (kWh)",
            "Hardware Carbon (kg)",
            "Sustainability Score",
        ]
    ],
    use_container_width=True,
    hide_index=True
)


# ============================================================
# SLA EVALUATION
# ============================================================

st.header("🎯 SLA Evaluation")


st.dataframe(
    df[
        [
            "Architecture",
            "Latency (ms)",
            "Accuracy (%)",
            "Latency OK",
            "Accuracy OK",
            "SLA Met",
        ]
    ],
    use_container_width=True,
    hide_index=True
)


# ============================================================
# SIX PILLARS
# ============================================================

st.header("🌱 Six-Pillar Lifecycle Impact")


st.dataframe(
    df[
        [
            "Architecture",
            "Total Energy (kWh)",
            "Total Carbon (kg)",
            "Storage (GB)",
        ]
    ],
    use_container_width=True,
    hide_index=True
)


st.dataframe(
    df[
        [
            "Architecture",
            "Networking (GB)",
            "Hardware Carbon (kg)",
            "Retraining Carbon (kg)",
        ]
    ],
    use_container_width=True,
    hide_index=True
)


# ============================================================
# RECOMMENDATION
# ============================================================

st.header("🌱 Recommendation")


eligible = df[df["SLA Met"]]


if len(eligible) > 0:

    recommended = eligible.loc[
        eligible["Sustainability Score"].idxmax()
    ]

    st.success(
        f"Recommended Architecture: "
        f"**{recommended['Architecture']}**"
    )

    st.write(
        f"Sustainability Score: "
        f"**{recommended['Sustainability Score']:.2f}/100**"
    )

    st.write(
        f"Total Carbon: "
        f"**{recommended['Total Carbon (kg)']:.2f} kg CO₂e**"
    )

else:

    st.warning(
        "No architecture satisfies both "
        "the latency and accuracy constraints."
    )


# ============================================================
# GEMINI ECO-NUTRITION LABEL
# ============================================================

st.header("🍃 Gemini Eco-Nutrition Label")


audited_models = df[
    [
        "name",
        "accuracy",
        "latency_ms",
        "total_lifecycle_carbon_kg"
    ]
].to_dict("records")


workload_desc = (
    f"AI workload with {requests:,} inference requests, "
    f"{workload_hours} operating hours, "
    f"PUE {pue}, "
    f"minimum accuracy requirement of {min_accuracy}%, "
    f"and maximum latency requirement of {max_latency} ms."
)


audit_result = run_lifecycle_audit(
    workload_desc=workload_desc,
    target_acc=min_accuracy,
    max_lat=max_latency,
    audited_models=audited_models
)


st.markdown(audit_result)


# ============================================================
# CHARTS
# ============================================================

st.header("📊 Sustainability Analysis")


# Use one complete copy for every chart.
# This prevents accidental slicing of the Transformer
# or other architectures.

chart_df = df.copy()


# ============================================================
# ENERGY
# ============================================================

fig_energy = px.bar(
    chart_df,
    x="Architecture",
    y="Total Energy (kWh)",
    title="Total Energy Consumption"
)

st.plotly_chart(
    fig_energy,
    use_container_width=True
)


# ============================================================
# CARBON
# ============================================================

fig_carbon = px.bar(
    chart_df,
    x="Architecture",
    y="Total Carbon (kg)",
    title="Total Carbon Impact"
)

st.plotly_chart(
    fig_carbon,
    use_container_width=True
)


# ============================================================
# LATENCY
# ============================================================

fig_latency = px.bar(
    chart_df,
    x="Architecture",
    y="Latency (ms)",
    title="Architecture Latency"
)

st.plotly_chart(
    fig_latency,
    use_container_width=True
)


# ============================================================
# ACCURACY
# ============================================================

fig_accuracy = px.bar(
    chart_df,
    x="Architecture",
    y="Accuracy (%)",
    title="Architecture Accuracy"
)

st.plotly_chart(
    fig_accuracy,
    use_container_width=True
)


# ============================================================
# NETWORKING
# ============================================================

fig_network = px.bar(
    chart_df,
    x="Architecture",
    y="Networking Energy (kWh)",
    title="Networking Energy"
)

st.plotly_chart(
    fig_network,
    use_container_width=True
)


# ============================================================
# RETRAINING
# ============================================================

fig_retraining = px.bar(
    chart_df,
    x="Architecture",
    y="Retraining Carbon (kg)",
    title="Retraining Carbon Impact"
)

st.plotly_chart(
    fig_retraining,
    use_container_width=True
)


# ============================================================
# ACCURACY VS CARBON
# ============================================================

fig_tradeoff = px.scatter(
    chart_df,
    x="Accuracy (%)",
    y="Total Carbon (kg)",
    text="Architecture",
    size="Sustainability Score",
    title="Accuracy vs Carbon Impact"
)

fig_tradeoff.update_traces(
    textposition="top center"
)

st.plotly_chart(
    fig_tradeoff,
    use_container_width=True
)


# ============================================================
# SUSTAINABILITY SCORE
# ============================================================

fig_score = px.bar(
    chart_df,
    x="Architecture",
    y="Sustainability Score",
    title="Composite Sustainability Score",
    range_y=[0, 100]
)

st.plotly_chart(
    fig_score,
    use_container_width=True
)


# ============================================================
# RADAR CHART
# ============================================================

st.header("🕸️ Lifecycle Sustainability Radar")


radar_metrics = [
    "Energy Efficiency",
    "Carbon Efficiency",
    "Storage Efficiency",
    "Network Efficiency",
    "Retraining Efficiency",
    "Latency Efficiency",
]


score_columns = [
    energy_score,
    carbon_score,
    storage_score,
    network_score,
    retraining_score,
    latency_score,
]


fig_radar = go.Figure()


for index, architecture in enumerate(
    chart_df["Architecture"]
):

    values = [
        score_columns[0].iloc[index],
        score_columns[1].iloc[index],
        score_columns[2].iloc[index],
        score_columns[3].iloc[index],
        score_columns[4].iloc[index],
        score_columns[5].iloc[index],
    ]

    values.append(values[0])

    categories = radar_metrics + [
        radar_metrics[0]
    ]

    fig_radar.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            name=architecture
        )
    )


fig_radar.update_layout(
    polar=dict(
        radialaxis=dict(
            visible=True,
            range=[0, 100]
        )
    ),
    title="Architecture Lifecycle Sustainability Profile",
    showlegend=True,
    legend=dict(
        title="Architecture",
        orientation="v",
        x=1.02,
        y=1
    )
)


st.plotly_chart(
    fig_radar,
    use_container_width=True
)


# ============================================================
# OFFLINE AUDIT HISTORY
# ============================================================

st.header("🗃️ Offline Audit Ledger")


try:

    audit_history = get_all_audits()

    if audit_history:

        st.dataframe(
            pd.DataFrame(audit_history),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No audit records are currently stored."
        )

except Exception as e:

    st.info(
        f"Audit ledger unavailable: {e}"
    )
