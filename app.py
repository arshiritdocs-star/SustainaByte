import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from auditor.architectures import get_architectures
from auditor.lifecycle_math import calculate_lifecycle_impact


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="SustainaByte | Sustainable AI Auditor",
    page_icon="🍃",
    layout="wide"
)


# ==================================================
# CONSTANTS
# ==================================================

GRID_CARBON_INTENSITY = 0.45


# ==================================================
# TITLE AND INTRODUCTION
# ==================================================

st.title("🍃 SustainaByte")

st.subheader(
    "Sustainable AI Lifecycle Auditor"
)

st.markdown(
    """
    Evaluate AI architectures based on environmental impact,
    accuracy and latency requirements.

    **Goal:** Identify architectures that satisfy enterprise
    SLA requirements while minimizing estimated lifecycle carbon.
    """
)

st.divider()


# ==================================================
# SIDEBAR: ENTERPRISE REQUIREMENTS
# ==================================================

st.sidebar.header("⚙️ Enterprise Requirements")

st.sidebar.caption(
    "Adjust the workload and SLA requirements to compare architectures."
)


requests = st.sidebar.number_input(
    "Number of AI requests",
    min_value=1,
    value=100000,
    step=10000
)


workload_hours = st.sidebar.number_input(
    "Workload duration (hours)",
    min_value=1.0,
    value=100.0,
    step=10.0
)


maximum_latency = st.sidebar.number_input(
    "Maximum latency (ms)",
    min_value=1.0,
    value=80.0,
    step=5.0
)


minimum_accuracy = st.sidebar.number_input(
    "Minimum accuracy (%)",
    min_value=0.0,
    max_value=100.0,
    value=88.0,
    step=1.0
)


pue = st.sidebar.number_input(
    "Power Usage Effectiveness (PUE)",
    min_value=1.0,
    max_value=5.0,
    value=1.4,
    step=0.1
)


st.sidebar.caption(
    """
    PUE is the ratio of total facility energy to IT equipment energy.
    The values used in this prototype are assumptions, not direct
    measurements of a production data center.
    """
)


# ==================================================
# LOAD ARCHITECTURES
# ==================================================

architectures = get_architectures()


# ==================================================
# CALCULATE IMPACTS
# ==================================================

results_list = []


for architecture in architectures:

    impact = calculate_lifecycle_impact(
        architecture=architecture,
        requests=requests,
        workload_hours=workload_hours,
        pue=pue
    )

    is_eligible = (
        architecture.estimated_latency_ms <= maximum_latency
        and architecture.estimated_accuracy * 100 >= minimum_accuracy
    )

    # Convert networking and retraining energy to carbon.
    networking_carbon = (
        impact["networking_energy_kwh"]
        * GRID_CARBON_INTENSITY
    )

    retraining_carbon = (
        impact["retraining_energy_kwh"]
        * GRID_CARBON_INTENSITY
    )

    results_list.append({

        "Architecture": architecture.name,

        "Latency (ms)": architecture.estimated_latency_ms,

        "Accuracy (%)": architecture.estimated_accuracy * 100,

        "Eligible": "Yes" if is_eligible else "No",

        "Hardware Carbon (kg)": (
            impact["hardware_carbon_kg"]
        ),

        "Inference Energy (kWh)": (
            impact["inference_energy_kwh"]
        ),

        "Inference Carbon (kg)": (
            impact["inference_carbon_kg"]
        ),

        "Storage (GB-hours)": (
            impact["storage_impact_gb_hours"]
        ),

        "Networking Energy (kWh)": (
            impact["networking_energy_kwh"]
        ),

        "Networking Carbon (kg)": (
            networking_carbon
        ),

        "Retraining Energy (kWh)": (
            impact["retraining_energy_kwh"]
        ),

        "Retraining Carbon (kg)": (
            retraining_carbon
        ),

        "Total Energy (kWh)": (
            impact["total_energy_kwh"]
        ),

        "Total Carbon (kg)": (
            impact["total_carbon_kg"]
        )
    })


results_df = pd.DataFrame(results_list)


# ==================================================
# SLA SUMMARY
# ==================================================

st.header("📋 Enterprise SLA Summary")


sla_col1, sla_col2, sla_col3, sla_col4 = st.columns(4)


with sla_col1:

    st.metric(
        "Maximum Latency",
        f"{maximum_latency:.0f} ms"
    )


with sla_col2:

    st.metric(
        "Minimum Accuracy",
        f"{minimum_accuracy:.1f}%"
    )


with sla_col3:

    st.metric(
        "Total Requests",
        f"{requests:,}"
    )


with sla_col4:

    eligible_count = int(
        (results_df["Eligible"] == "Yes").sum()
    )

    st.metric(
        "Eligible Architectures",
        f"{eligible_count}/{len(results_df)}"
    )


st.divider()


# ==================================================
# ARCHITECTURE COMPARISON
# ==================================================

st.header("🏗️ Architecture Comparison")


comparison_columns = [
    "Architecture",
    "Latency (ms)",
    "Accuracy (%)",
    "Eligible",
    "Total Energy (kWh)",
    "Total Carbon (kg)"
]


st.dataframe(
    results_df[comparison_columns].round(3),
    use_container_width=True,
    hide_index=True
)


# ==================================================
# SLA STATUS
# ==================================================

st.header("🔍 SLA Evaluation")


for _, row in results_df.iterrows():

    if row["Eligible"] == "Yes":

        st.success(
            f"✅ {row['Architecture']} satisfies "
            f"the latency and accuracy requirements."
        )

    else:

        latency_pass = row["Latency (ms)"] <= maximum_latency

        accuracy_pass = row["Accuracy (%)"] >= minimum_accuracy

        reasons = []

        if not latency_pass:
            reasons.append("latency requirement not met")

        if not accuracy_pass:
            reasons.append("accuracy requirement not met")

        st.warning(
            f"⚠️ {row['Architecture']}: "
            + ", ".join(reasons)
            + "."
        )


st.divider()


# ==================================================
# RECOMMENDATION
# ==================================================

st.header("🌱 Architecture Recommendation")


eligible_df = results_df[
    results_df["Eligible"] == "Yes"
].copy()


if eligible_df.empty:

    st.warning(
        "No architecture satisfies both the latency "
        "and accuracy requirements."
    )

    st.info(
        "Try adjusting the SLA requirements or adding "
        "another architecture preset."
    )

else:

    # Select the lowest estimated carbon among eligible options.
    recommended_row = eligible_df.loc[
        eligible_df["Total Carbon (kg)"].idxmin()
    ]

    recommended_name = recommended_row["Architecture"]

    st.success(
        f"Recommended eligible architecture: {recommended_name}"
    )

    recommendation_col1, recommendation_col2, recommendation_col3 = (
        st.columns(3)
    )

    with recommendation_col1:

        st.metric(
            "Architecture",
            recommended_name
        )

    with recommendation_col2:

        st.metric(
            "Estimated Carbon",
            f"{recommended_row['Total Carbon (kg)']:.2f} kg"
        )

    with recommendation_col3:

        st.metric(
            "Estimated Energy",
            f"{recommended_row['Total Energy (kWh)']:.2f} kWh"
        )

    st.info(
        f"""
        **Why this architecture?**

        {recommended_name} satisfies the selected latency and
        accuracy constraints and has the lowest estimated total
        carbon among the eligible architectures.

        Latency: {recommended_row['Latency (ms)']:.1f} ms

        Accuracy: {recommended_row['Accuracy (%)']:.1f}%
        """
    )


st.divider()


# ==================================================
# CHART 1: TOTAL CARBON COMPARISON
# ==================================================

st.header("📊 Total Carbon Comparison")


st.caption(
    "Unit: kg CO₂e. Lower values indicate lower estimated carbon "
    "under the selected workload assumptions."
)


carbon_chart = px.bar(
    results_df,
    x="Architecture",
    y="Total Carbon (kg)",
    color="Architecture",
    text_auto=".2f",
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

st.header("⚡ Energy Consumption Breakdown")


st.caption(
    "Unit: kWh. Only energy-based categories are shown in this chart."
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
    title="Estimated Energy Consumption by Category",
    text_auto=".3f"
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
# CHART 3: STORAGE FOOTPRINT
# ==================================================

st.header("💾 Storage Footprint Comparison")


st.caption(
    "Unit: GB-hours. Storage footprint is displayed separately "
    "because it is not directly comparable with kg CO₂e or kWh."
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

st.header("🎯 Latency vs Accuracy")


st.caption(
    "Architectures should be below the maximum latency and above "
    "the minimum accuracy to satisfy both constraints."
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


# Vertical SLA boundary: maximum latency.
latency_accuracy_chart.add_vline(
    x=maximum_latency,
    line_dash="dash",
    annotation_text="Maximum latency",
    annotation_position="top right"
)


# Horizontal SLA boundary: minimum accuracy.
latency_accuracy_chart.add_hline(
    y=minimum_accuracy,
    line_dash="dash",
    annotation_text="Minimum accuracy",
    annotation_position="bottom right"
)


latency_accuracy_chart.update_layout(
    xaxis_title="Latency (ms)",
    yaxis_title="Accuracy (%)",
    yaxis=dict(range=[
        max(0, results_df["Accuracy (%)"].min() - 5),
        min(100, results_df["Accuracy (%)"].max() + 5)
    ])
)


st.plotly_chart(
    latency_accuracy_chart,
    use_container_width=True
)


# ==================================================
# CHART 5: CARBON COMPONENT BREAKDOWN
# ==================================================

st.header("🌍 Carbon Component Breakdown")


st.caption(
    "Carbon categories are displayed in kg CO₂e. Storage is excluded "
    "because the current storage metric is measured in GB-hours."
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


carbon_components_long = carbon_components.melt(
    id_vars="Architecture",
    var_name="Carbon Category",
    value_name="Carbon (kg)"
)


carbon_components_chart = px.bar(
    carbon_components_long,
    x="Architecture",
    y="Carbon (kg)",
    color="Carbon Category",
    barmode="group",
    title="Estimated Carbon by Lifecycle Component",
    text_auto=".3f"
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
# DETAILED RESULTS
# ==================================================

st.header("📄 Detailed Calculation Results")


with st.expander("View detailed calculation results"):

    st.dataframe(
        results_df.round(4),
        use_container_width=True,
        hide_index=True
    )

    csv_data = results_df.to_csv(index=False).encode("utf-8")


    st.download_button(
        label="⬇️ Download Results as CSV",
        data=csv_data,
        file_name="sustainabyte_results.csv",
        mime="text/csv"
    )


# ==================================================
# ASSUMPTIONS AND LIMITATIONS
# ==================================================

st.divider()

st.header("ℹ️ Assumptions and Limitations")


st.markdown(
    f"""
    - Grid carbon intensity: **{GRID_CARBON_INTENSITY} kg CO₂e/kWh**.
    - PUE is provided as a user-controlled scenario input.
    - Architecture specifications are illustrative preset values.
    - Energy and carbon values are estimates, not direct measurements.
    - Storage is reported in GB-hours and should not be directly
      compared with carbon or energy quantities.
    - The recommendation selects the lowest estimated carbon among
      architectures satisfying the selected SLA requirements.
    """
)


st.caption(
    """
    SustainaByte | Prototype for sustainable AI lifecycle analysis.
    """
)
