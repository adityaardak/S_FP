# Pay Lens AI 💼

**Pay Lens AI** is a Streamlit-based payroll analytics web application that helps HR leaders and finance teams visualise salary data and simulate pay corrections against market benchmarks.

---

## Overview

Pay Lens AI combines an embedded Power BI dashboard with an interactive **Live Pay Correction Simulator** to give decision-makers a single, polished workspace for salary equity analysis.

---

## Features

- **Payroll Dashboard** – Embeds a Power BI report that visualises salary distribution, department breakdowns, and market positioning ratios in real time.
- **Live Pay Correction Simulator** – Interactively simulate the cost impact of correcting underpaid or overpaid employees, scoped by:
  - Individual employee
  - Department
  - All flagged employees
- **Pay Status Classification** – Automatically classifies each employee as *underpaid*, *overpaid*, or *fairly positioned* based on their market positioning ratio.
- **Budget Impact Metrics** – Displays current salary, corrected salary, monthly adjustment needed, annual payroll impact, market positioning ratio, and employees affected.
- **Salary Comparison Chart** – Plotly bar chart comparing current salary, adjustment, and corrected salary side by side.
- **Portfolio Correction Snapshot** – Summary panel showing total underpaid/overpaid counts, estimated correction budget, and the department requiring the highest correction spend.
- **Custom Data Upload** – Upload your own payroll CSV or Excel file to drive the simulator with fresh data.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | [Streamlit](https://streamlit.io/) |
| Data processing | [Pandas](https://pandas.pydata.org/) |
| Visualisation | [Plotly](https://plotly.com/python/) |
| BI Dashboard | [Microsoft Power BI](https://powerbi.microsoft.com/) (embedded iframe) |
| Data format | Excel (`.xlsx`) / CSV |

---

## Getting Started

### Prerequisites

- Python 3.9+

### Installation

```bash
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Data

The app ships with a default dataset (`dataset for project - updated.xlsx`). You can also upload your own payroll file (CSV or Excel) directly in the app. The file must contain at least the following columns (column names are normalised automatically):

- `employee_name`
- `department`
- `net_salary_paid_including_variable_pay`
- `market_positioning_ratio`

---

## Project Files

| File | Description |
|---|---|
| `app.py` | Main Streamlit application |
| `requirements.txt` | Python dependencies |
| `dataset for project - updated.xlsx` | Sample payroll dataset |
| `pay lens - BI dashboard.pbix` | Power BI desktop report file |
| `PAY LENS - VISUALISING SALARY TRUTH WITH BI & AI.pptx` | Project presentation |
| `PAY LENS - visualising salary truth with BI & AI (report).pdf` | Project report |
| `pay - lens .pdf` | Additional documentation |