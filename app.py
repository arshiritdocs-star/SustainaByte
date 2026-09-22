import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from auditor.architectures import get_architectures
from auditor.lifecycle_math import Workload, calculate_lifecycle_impact


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SustainaByte | Sustainable AI Auditor",
    page_icon="🌱",
    layout="wide"
)


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


# ============================================================
# CONSTANTS
# ============================================================

GRID_CARBON_INTENSITY = 0.45


# ============================================================
# ARCHITECTURE CALCULATIONS
# ============================================================

architectures = get_architectures()

workload = Workload(
    inference_count=requests,
    training_hours=workload_hours,
    carbon_intensity_gco2_per_kwh=GRID_CARBON_INTENSITY * 1000
)

results = []

for architecture in architectures:

    impact = calculate_lifecycle_impact(
        architecture=architecture,
        workload=workload
    )

    results.append(
        {
            "Architecture": architecture.name,
            "Latency (ms)": architecture.estimated_latency_ms,
            "Accuracy (%)": architecture.estimated_accuracy * 100,
            "Hardware Carbon (kg)": impact["hardware"]["embodied_carbon_kg"],
            "Inference Energy (kWh)": impact["energy"]["inference_energy_kwh"],
            "Inference Carbon (kg)": (
                impact["energy"]["inference_energy_kwh"]
                * GRID_CARBON_INTENSITY
            ),
            "Storage (GB)": impact["storage"]["total_storage_gb"],
            "Networking Energy (kWh)": impact["networking"]["network_energy_kwh"],
            "Retraining Energy (kWh)": impact["retraining"]["retraining_energy_kwh"],
            "Total Energy (kWh)": impact["energy"]["total_energy_kwh"],
            "Total Carbon (kg)": impact["carbon"]["total_carbon_kg"],
        }
    )


df = pd.DataFrame(results)


# ============================================================
# SLA EVALUATION
# ============================================================

df["Latency OK"] = df["Latency (ms)"] <= max_latency

df["Accuracy OK"] = df["Accuracy (%)"] >= min_accuracy

df["SLA Met"] = df["Latency OK"] & df["Accuracy OK"]


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
            "Hardware Carbon (kg)",
            "Inference Energy (kWh)",
            "Inference Carbon (kg)",
            "Storage (GB)",
            "Networking Energy (kWh)",
            "Retraining Energy (kWh)",
            "Total Energy (kWh)",
            "Total Carbon (kg)",
        ]
    ],
    use_container_width=True
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
    use_container_width=True
)


# ============================================================
# RECOMMENDATION
# ============================================================

st.header("🌱 Recommendation")

eligible = df[df["SLA Met"]]

if len(eligible) > 0:

    recommended = eligible.loc[
        eligible["Total Carbon (kg)"].idxmin()
    ]

    st.success(
        f"Recommended Architecture: **{recommended['Architecture']}**"
    )

    st.write(
        f"Total Carbon: **{recommended['Total Carbon (kg)']:.2f} kg CO₂e**"
    )

else:

    st.warning(
        "No architecture satisfies both the latency and accuracy constraints."
    )


# ============================================================
# CHARTS
# ============================================================

st.header("📊 Sustainability Analysis")


# Energy comparison

fig_energy = px.bar(
    df,
    x="Architecture",
    y="Total Energy (kWh)",
    title="Total Energy Consumption"
)

st.plotly_chart(
    fig_energy,
    use_container_width=True
)


# Carbon comparison

fig_carbon = px.bar(
    df,
    x="Architecture",
    y="Total Carbon (kg)",
    title="Total Carbon Impact"
)

st.plotly_chart(
    fig_carbon,
    use_container_width=True
)


# Latency comparison

fig_latency = px.bar(
    df,
    x="Architecture",
    y="Latency (ms)",
    title="Architecture Latency"
)

st.plotly_chart(
    fig_latency,
    use_container_width=True
)


# Accuracy comparison

fig_accuracy = px.bar(
    df,
    x="Architecture",
    y="Accuracy (%)",
    title="Architecture Accuracy"
)

st.plotly_chart(
    fig_accuracy,
    use_container_width=True
)


# Carbon vs accuracy

fig_tradeoff = px.scatter(
    df,
    x="Accuracy (%)",
    y="Total Carbon (kg)",
    text="Architecture",
    title="Accuracy vs Carbon Impact"
)

fig_tradeoff.update_traces(
    textposition="top center"
)

st.plotly_chart(
    fig_tradeoff,
    use_container_width=True
)
