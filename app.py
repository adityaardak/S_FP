import io
import re
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components


APP_TITLE = "Pay Lens AI"
DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "dataset for project - updated.xlsx"
POWER_BI_EMBED_URL = (
    "https://app.powerbi.com/reportEmbed"
    "?reportId=1e511742-2023-4ada-ac80-7f3d96043a1a"
    "&autoAuth=true"
    "&ctid=ad06ef22-d6dc-4a55-b4c1-c3a158f5f147"
    "&actionBarEnabled=true"
    "&reportCopilotInEmbed=true"
)

REQUIRED_COLUMNS = {
    "employee_name",
    "department",
    "net_salary_paid_including_variable_pay",
    "market_positioning_ratio",
}

PALETTE = {
    "navy": "#0B1F3A",
    "teal": "#18B7A3",
    "amber": "#F5B544",
    "red": "#D6544A",
    "slate": "#5E6C84",
    "panel": "#FFFFFF",
    "canvas": "#F3F7FB",
    "text": "#11233F",
    "muted": "#64748B",
}


def normalize_column_name(column_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(column_name).strip().lower())
    return normalized.strip("_")


def standardize_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    df = dataframe.copy()
    df.columns = [normalize_column_name(column) for column in df.columns]

    if "employee_name" in df.columns:
        df["employee_name"] = df["employee_name"].astype(str).str.strip()
    if "department" in df.columns:
        df["department"] = df["department"].astype(str).str.strip()

    numeric_columns = [
        "ctc_annual",
        "fixed_salary_monthly",
        "variable_pay_monthly",
        "basic_salary",
        "hra",
        "allowances",
        "pf_deduction",
        "professional_tax",
        "monthly_work_hours",
        "monthly_overtime_hours",
        "per_hr_regular_pay",
        "per_hour_overtime_pay",
        "overtime_paid",
        "net_salary_paid_excluding_variable_pay",
        "net_salary_paid_including_variable_pay",
        "market_positioning_ratio",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "date_of_joining" in df.columns:
        df["date_of_joining"] = pd.to_datetime(df["date_of_joining"], errors="coerce")

    missing_columns = REQUIRED_COLUMNS.difference(df.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required columns: {missing_list}")

    return df


def pick_best_sheet(excel_file: pd.ExcelFile) -> str:
    best_sheet = excel_file.sheet_names[0]
    best_score = -1
    for sheet_name in excel_file.sheet_names:
        sample = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=5)
        normalized_columns = {normalize_column_name(column) for column in sample.columns}
        score = len(REQUIRED_COLUMNS.intersection(normalized_columns))
        if score > best_score:
            best_score = score
            best_sheet = sheet_name
    return best_sheet


def assign_pay_status(ratio: float) -> str:
    if pd.isna(ratio):
        return "unknown"
    if abs(ratio - 1.0) < 1e-9:
        return "fairly positioned"
    return "underpaid" if ratio < 1.0 else "overpaid"


def calculate_pay_corrections(dataframe: pd.DataFrame) -> pd.DataFrame:
    df = dataframe.copy()
    current_salary = pd.to_numeric(
        df["net_salary_paid_including_variable_pay"],
        errors="coerce",
    )
    market_ratio = pd.to_numeric(df["market_positioning_ratio"], errors="coerce")

    df["pay_status"] = market_ratio.apply(assign_pay_status)
    df["corrected_salary"] = current_salary.div(market_ratio)
    df.loc[market_ratio <= 0, "corrected_salary"] = pd.NA
    df["monthly_adjustment"] = df["corrected_salary"] - current_salary
    df["annual_adjustment"] = df["monthly_adjustment"] * 12
    df["corrected_ratio"] = 1.00

    if "market_positioning_index" not in df.columns:
        df["market_positioning_index"] = df["pay_status"]
    else:
        df["market_positioning_index"] = (
            df["market_positioning_index"].astype(str).str.strip().str.lower()
        )

    return df


@st.cache_data(show_spinner=False)
def load_default_data(default_path: str) -> pd.DataFrame:
    path = Path(default_path)
    if path.suffix.lower() == ".csv":
        raw_df = pd.read_csv(path)
    else:
        excel_file = pd.ExcelFile(path)
        sheet_name = pick_best_sheet(excel_file)
        raw_df = pd.read_excel(path, sheet_name=sheet_name)
    return calculate_pay_corrections(standardize_dataframe(raw_df))


@st.cache_data(show_spinner=False)
def load_uploaded_data(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    extension = Path(file_name).suffix.lower()
    file_buffer = io.BytesIO(file_bytes)
    if extension == ".csv":
        raw_df = pd.read_csv(file_buffer)
    else:
        excel_file = pd.ExcelFile(file_buffer)
        sheet_name = pick_best_sheet(excel_file)
        raw_df = pd.read_excel(excel_file, sheet_name=sheet_name)
    return calculate_pay_corrections(standardize_dataframe(raw_df))


def load_data(uploaded_file) -> tuple[pd.DataFrame, str]:
    if uploaded_file is not None:
        dataframe = load_uploaded_data(uploaded_file.getvalue(), uploaded_file.name)
        return dataframe, uploaded_file.name
    dataframe = load_default_data(str(DEFAULT_DATA_PATH))
    return dataframe, DEFAULT_DATA_PATH.name


def filter_by_employee(dataframe: pd.DataFrame, employee_name: str) -> pd.DataFrame:
    if not employee_name:
        return dataframe.copy()
    return dataframe[dataframe["employee_name"] == employee_name].copy()


def filter_by_department(dataframe: pd.DataFrame, department_name: str) -> pd.DataFrame:
    if not department_name:
        return dataframe.copy()
    return dataframe[dataframe["department"] == department_name].copy()


def filter_by_pay_status(dataframe: pd.DataFrame, pay_status: str) -> pd.DataFrame:
    if pay_status == "all":
        return dataframe.copy()
    return dataframe[dataframe["pay_status"] == pay_status].copy()


def calculate_budget_impact(dataframe: pd.DataFrame) -> dict:
    if dataframe.empty:
        return {
            "current_salary": 0.0,
            "corrected_salary": 0.0,
            "monthly_adjustment": 0.0,
            "annual_adjustment": 0.0,
            "current_ratio": 0.0,
            "employees_affected": 0,
        }

    return {
        "current_salary": dataframe["net_salary_paid_including_variable_pay"].sum(),
        "corrected_salary": dataframe["corrected_salary"].sum(skipna=True),
        "monthly_adjustment": dataframe["monthly_adjustment"].sum(skipna=True),
        "annual_adjustment": dataframe["annual_adjustment"].sum(skipna=True),
        "current_ratio": dataframe["market_positioning_ratio"].mean(),
        "employees_affected": int(len(dataframe)),
    }


def format_inr(value: float) -> str:
    absolute_value = abs(float(value))
    formatted = f"{absolute_value:,.0f}"
    prefix = "-" if value < 0 else ""
    return f"{prefix}₹{formatted}"


def generate_summary_message(
    dataframe: pd.DataFrame,
    selection_mode: str,
    selected_employee: str,
    selected_department: str,
) -> str:
    if dataframe.empty:
        return "No employees match the current filters, so there is no correction impact to simulate yet."

    monthly_adjustment = dataframe["monthly_adjustment"].sum(skipna=True)
    annual_adjustment = dataframe["annual_adjustment"].sum(skipna=True)
    employee_count = len(dataframe)

    if selection_mode == "Employee" and employee_count == 1:
        employee_name = dataframe["employee_name"].iloc[0]
        if monthly_adjustment > 0:
            return (
                f"{employee_name} needs a monthly increase of {format_inr(monthly_adjustment)} "
                "to reach fair pay positioning."
            )
        if monthly_adjustment < 0:
            return (
                f"{employee_name} appears over market by {format_inr(abs(monthly_adjustment))} "
                "per month."
            )
        return f"{employee_name} is already positioned at a fair market ratio."

    if selection_mode == "Department":
        department_label = selected_department or "this department"
        if annual_adjustment > 0:
            return (
                f"Fixing all selected employees in {department_label} will increase annual payroll by "
                f"{format_inr(annual_adjustment)}."
            )
        if annual_adjustment < 0:
            return (
                f"Realigning the selected employees in {department_label} would reduce annual payroll by "
                f"{format_inr(abs(annual_adjustment))}."
            )
        return f"The selected employees in {department_label} are already aligned to fair pay positioning."

    if monthly_adjustment > 0:
        return (
            f"Correcting pay for {employee_count} employees increases monthly payroll by "
            f"{format_inr(monthly_adjustment)} and annual payroll by {format_inr(annual_adjustment)}."
        )
    if monthly_adjustment < 0:
        return (
            f"Realigning pay for {employee_count} employees reduces monthly payroll by "
            f"{format_inr(abs(monthly_adjustment))} and annual payroll by {format_inr(abs(annual_adjustment))}."
        )
    return "The selected employees are already fairly positioned against the market."


def build_comparison_chart(metrics: dict) -> go.Figure:
    categories = ["Current Salary", "Adjustment", "Corrected Salary"]
    values = [
        metrics["current_salary"],
        metrics["monthly_adjustment"],
        metrics["corrected_salary"],
    ]
    colors = [
        PALETTE["navy"],
        PALETTE["amber"] if metrics["monthly_adjustment"] >= 0 else PALETTE["red"],
        PALETTE["teal"],
    ]

    figure = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                marker_color=colors,
                text=[format_inr(value) for value in values],
                textposition="outside",
                hovertemplate="%{x}<br>%{text}<extra></extra>",
            )
        ]
    )
    figure.update_layout(
        height=360,
        margin=dict(l=12, r=12, t=30, b=10),
        paper_bgcolor=PALETTE["panel"],
        plot_bgcolor=PALETTE["panel"],
        font=dict(color=PALETTE["text"], family="Segoe UI"),
        yaxis=dict(
            title="Monthly Compensation",
            gridcolor="rgba(17, 35, 63, 0.08)",
            zerolinecolor="rgba(17, 35, 63, 0.15)",
            tickprefix="₹",
        ),
        xaxis=dict(showgrid=False),
        showlegend=False,
    )
    return figure


def get_summary_insights(dataframe: pd.DataFrame) -> dict:
    underpaid_df = dataframe[dataframe["pay_status"] == "underpaid"].copy()
    overpaid_df = dataframe[dataframe["pay_status"] == "overpaid"].copy()

    correction_by_department = (
        underpaid_df.groupby("department", dropna=False)["annual_adjustment"]
        .sum()
        .sort_values(ascending=False)
    )
    highest_department = correction_by_department.index[0] if not correction_by_department.empty else "N/A"
    highest_budget = correction_by_department.iloc[0] if not correction_by_department.empty else 0.0

    return {
        "underpaid_count": int(len(underpaid_df)),
        "overpaid_count": int(len(overpaid_df)),
        "estimated_budget": underpaid_df["annual_adjustment"].sum(skipna=True),
        "highest_department": highest_department,
        "highest_budget": highest_budget,
    }


def render_metric_card(title: str, value: str, accent: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-accent" style="background:{accent};"></div>
            <div class="metric-label">{title}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_box(insights: dict) -> None:
    st.markdown(
        f"""
        <div class="summary-box">
            <div class="summary-title">Portfolio Correction Snapshot</div>
            <div class="summary-grid">
                <div class="summary-item">
                    <span>Total Underpaid Employees</span>
                    <strong>{insights["underpaid_count"]}</strong>
                </div>
                <div class="summary-item">
                    <span>Total Overpaid Employees</span>
                    <strong>{insights["overpaid_count"]}</strong>
                </div>
                <div class="summary-item">
                    <span>Total Estimated Correction Budget</span>
                    <strong>{format_inr(insights["estimated_budget"])}</strong>
                </div>
                <div class="summary-item">
                    <span>Department Needing Highest Correction</span>
                    <strong>{insights["highest_department"]} ({format_inr(insights["highest_budget"])})</strong>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    f"""
    <style>
        .stApp {{
            background:
                radial-gradient(circle at top right, rgba(24, 183, 163, 0.14), transparent 22%),
                linear-gradient(180deg, #F8FBFF 0%, {PALETTE["canvas"]} 100%);
            color: {PALETTE["text"]};
        }}
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 2.5rem;
            max-width: 1280px;
        }}
        .hero {{
            background: linear-gradient(135deg, {PALETTE["navy"]} 0%, #163A63 62%, #1F4D7A 100%);
            border-radius: 24px;
            padding: 1.8rem 1.8rem 1.5rem 1.8rem;
            color: white;
            box-shadow: 0 18px 40px rgba(11, 31, 58, 0.18);
            margin-bottom: 1.2rem;
        }}
        .hero h1 {{
            margin: 0;
            font-size: 2.2rem;
            font-weight: 700;
        }}
        .hero p {{
            margin: 0.6rem 0 0 0;
            color: rgba(255,255,255,0.85);
            max-width: 760px;
            line-height: 1.55;
            font-size: 1rem;
        }}
        .section-title {{
            color: {PALETTE["navy"]};
            font-size: 1.2rem;
            font-weight: 700;
            margin: 1.4rem 0 0.8rem 0;
        }}
        .panel {{
            background: {PALETTE["panel"]};
            border-radius: 22px;
            padding: 1.2rem;
            box-shadow: 0 16px 36px rgba(17, 35, 63, 0.08);
            border: 1px solid rgba(17, 35, 63, 0.05);
        }}
        .dashboard-frame {{
            background: {PALETTE["panel"]};
            border-radius: 20px;
            padding: 0.75rem;
            box-shadow: 0 16px 36px rgba(17, 35, 63, 0.08);
            border: 1px solid rgba(17, 35, 63, 0.05);
            overflow: hidden;
        }}
        .simulator-note {{
            border-left: 4px solid {PALETTE["teal"]};
            background: rgba(24, 183, 163, 0.08);
            color: {PALETTE["text"]};
            border-radius: 14px;
            padding: 0.95rem 1rem;
            margin: 1rem 0 1.15rem 0;
            font-weight: 500;
        }}
        .metric-card {{
            background: {PALETTE["panel"]};
            border-radius: 20px;
            padding: 1rem 1rem 1.05rem 1rem;
            box-shadow: 0 14px 28px rgba(17, 35, 63, 0.07);
            border: 1px solid rgba(17, 35, 63, 0.06);
            position: relative;
            min-height: 124px;
        }}
        .metric-accent {{
            width: 48px;
            height: 5px;
            border-radius: 999px;
            margin-bottom: 0.95rem;
        }}
        .metric-label {{
            color: {PALETTE["muted"]};
            font-size: 0.9rem;
            margin-bottom: 0.45rem;
        }}
        .metric-value {{
            color: {PALETTE["text"]};
            font-size: 1.45rem;
            font-weight: 700;
            line-height: 1.25;
        }}
        .message-box {{
            background: linear-gradient(135deg, rgba(11, 31, 58, 0.96), rgba(22, 58, 99, 0.92));
            color: white;
            border-radius: 22px;
            padding: 1.15rem 1.2rem;
            box-shadow: 0 18px 36px rgba(11, 31, 58, 0.18);
            margin: 0.5rem 0 1rem 0;
            font-size: 1.02rem;
            line-height: 1.6;
        }}
        .summary-box {{
            background: linear-gradient(180deg, #FDFEFF 0%, #F8FBFF 100%);
            border-radius: 22px;
            padding: 1.15rem;
            border: 1px solid rgba(17, 35, 63, 0.08);
            box-shadow: 0 14px 28px rgba(17, 35, 63, 0.06);
            margin-top: 0.8rem;
        }}
        .summary-title {{
            font-size: 1rem;
            font-weight: 700;
            color: {PALETTE["navy"]};
            margin-bottom: 0.9rem;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 0.75rem;
        }}
        .summary-item {{
            background: white;
            border-radius: 16px;
            padding: 0.95rem;
            border: 1px solid rgba(17, 35, 63, 0.06);
        }}
        .summary-item span {{
            display: block;
            color: {PALETTE["muted"]};
            font-size: 0.85rem;
            margin-bottom: 0.35rem;
        }}
        .summary-item strong {{
            color: {PALETTE["text"]};
            font-size: 1rem;
        }}
        div[data-baseweb="select"] > div {{
            border-radius: 14px !important;
        }}
        div[role="radiogroup"] {{
            gap: 0.65rem;
        }}
        @media (max-width: 768px) {{
            .hero h1 {{
                font-size: 1.8rem;
            }}
            .block-container {{
                padding-top: 1.2rem;
            }}
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <h1>Pay Lens AI</h1>
        <p>
            A focused payroll analytics workspace that keeps the Power BI salary dashboard visible
            while giving leaders one premium decision layer: the Live Pay Correction Simulator.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-title">Payroll Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-frame">', unsafe_allow_html=True)
components.html(
    f"""
    <iframe
        title="pay lens - BI dashboard"
        width="100%"
        height="560"
        src="{POWER_BI_EMBED_URL}"
        frameborder="0"
        allowfullscreen="true">
    </iframe>
    """,
    height=570,
)
st.markdown("</div>", unsafe_allow_html=True)
st.caption(
    "The embedded report may prompt for Power BI access if your organization requires authentication."
)

st.markdown(
    '<div class="section-title">Live Pay Correction Simulator</div>',
    unsafe_allow_html=True,
)

with st.container():
    control_col, upload_col = st.columns([2.2, 1.0])
    with control_col:
        selection_mode = st.radio(
            "Selection Mode",
            options=["Employee", "Department", "All Flagged Employees"],
            horizontal=True,
        )
    with upload_col:
        uploaded_file = st.file_uploader(
            "Upload Payroll CSV/Excel",
            type=["csv", "xlsx", "xls"],
            help="Optional. Upload a fresh payroll extract to drive the simulator.",
        )

    try:
        payroll_df, data_source_label = load_data(uploaded_file)
    except Exception as error:
        st.error(f"Unable to load payroll data: {error}")
        st.stop()

    pay_status_filter = st.selectbox(
        "Pay Status Filter",
        options=["all", "underpaid", "overpaid"],
        format_func=lambda value: value.replace("_", " ").title(),
    )

    choice_pool = filter_by_pay_status(payroll_df, pay_status_filter)

    employee_options = sorted(choice_pool["employee_name"].dropna().unique().tolist())
    department_options = sorted(choice_pool["department"].dropna().unique().tolist())

    filter_col_1, filter_col_2 = st.columns(2)
    with filter_col_1:
        selected_employee = st.selectbox(
            "Employee",
            options=employee_options if employee_options else [""],
            index=0,
            disabled=selection_mode != "Employee" or not employee_options,
            placeholder="Choose an employee",
        )
    with filter_col_2:
        selected_department = st.selectbox(
            "Department",
            options=department_options if department_options else [""],
            index=0,
            disabled=selection_mode != "Department" or not department_options,
            placeholder="Choose a department",
        )

    st.caption(f"Simulator data source: {data_source_label}")

    scoped_df = filter_by_pay_status(payroll_df, pay_status_filter)
    if selection_mode == "Employee":
        scoped_df = filter_by_employee(scoped_df, selected_employee)
    elif selection_mode == "Department":
        scoped_df = filter_by_department(scoped_df, selected_department)
    else:
        scoped_df = scoped_df[scoped_df["pay_status"].isin(["underpaid", "overpaid"])].copy()

    metrics = calculate_budget_impact(scoped_df)
    summary_message = generate_summary_message(
        scoped_df,
        selection_mode,
        selected_employee,
        selected_department,
    )
    insights = get_summary_insights(payroll_df)

    st.markdown(
        f'<div class="simulator-note">{summary_message}</div>',
        unsafe_allow_html=True,
    )

    first_row = st.columns(4)
    with first_row[0]:
        render_metric_card("Current Salary", format_inr(metrics["current_salary"]), PALETTE["navy"])
    with first_row[1]:
        render_metric_card("Corrected Salary", format_inr(metrics["corrected_salary"]), PALETTE["teal"])
    with first_row[2]:
        adjustment_color = PALETTE["amber"] if metrics["monthly_adjustment"] >= 0 else PALETTE["red"]
        render_metric_card(
            "Monthly Adjustment Needed",
            format_inr(metrics["monthly_adjustment"]),
            adjustment_color,
        )
    with first_row[3]:
        annual_color = PALETTE["amber"] if metrics["annual_adjustment"] >= 0 else PALETTE["red"]
        render_metric_card(
            "Annual Payroll Impact",
            format_inr(metrics["annual_adjustment"]),
            annual_color,
        )

    second_row = st.columns(3)
    with second_row[0]:
        render_metric_card(
            "Current Market Positioning Ratio",
            f"{metrics['current_ratio']:.2f}" if metrics["employees_affected"] else "0.00",
            PALETTE["navy"],
        )
    with second_row[1]:
        render_metric_card("Corrected Ratio", "1.00", PALETTE["teal"])
    with second_row[2]:
        render_metric_card(
            "Employees Affected Count",
            str(metrics["employees_affected"]),
            PALETTE["red"] if metrics["employees_affected"] else PALETTE["slate"],
        )

    st.plotly_chart(build_comparison_chart(metrics), use_container_width=True)
    render_summary_box(insights)
