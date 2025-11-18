import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from docx import Document
from docx.shared import Inches
from constants import DOCUMENTATION_CSV_PATH, DOCUMENTATION_DOCX_PATH
from intersections.TC2 import intersection

# Output Word document
OUTPUT_DOCX = DOCUMENTATION_DOCX_PATH / "traffic_analysis_report.docx"


def plot_scalability(csv_folder: Path):
    """
    Objective 1: Line chart of avg_queue_length vs total_flow for all CSVs in scalability_assessment.
    All scenarios are plotted on a single chart with precise gridlines.
    """
    plt.figure(figsize=(10, 6))

    colors = ['#4E79A7', '#E15759', '#59A14F', '#F28E2B',  '#76B7B2']

    for idx, csv_file in enumerate(csv_folder.glob("*.csv")):
        df = pd.read_csv(csv_file)
        df = df.sort_values("total_flow")
        plt.plot(df["total_flow"], df["avg_queue_length"],
                 marker='o', linestyle='-', linewidth=2,
                 color=colors[idx % len(colors)],
                 label=csv_file.stem)

    plt.title(
        "Scalability Assessment: Average Queue Length vs Traffic Volume", fontsize=14)
    plt.xlabel("Total Traffic Volume (vehicles)", fontsize=12)
    plt.ylabel("Average Queue Length", fontsize=12)
    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)
    plt.legend(title="Scenario", fontsize=10)

    # Major and minor grids
    plt.grid(which='major', linestyle='-',
             linewidth=0.8, color='gray', alpha=0.7)
    plt.grid(which='minor', linestyle='--',
             linewidth=0.5, color='gray', alpha=0.4)
    plt.minorticks_on()

    plt.tight_layout()

    img_path = csv_folder / "scalability_summary_line.png"
    plt.savefig(img_path)
    plt.close()

    return img_path


def plot_comparative_analysis(csv_file: Path):
    """
    Objective 2: Bar charts for traffic efficiency metrics.
    """
    df = pd.read_csv(csv_file)

    # Metrics dictionary: CSV column -> display label
    metrics = {
        "avg_delay_timeLoss": "Average Delay Time (s)",
        "avg_waiting_time": "Average Waiting Time (s)",
        "avg_stops": "Average Stops",
        "avg_duration": "Average Travel Time (s)"
    }

    doc_plots = []

    colors = ['#E15759', '#59A14F', '#4E79A7', '#F28E2B',  '#76B7B2']

    for metric, label in metrics.items():
        plt.figure(figsize=(6, 4))
        plt.bar(df["signal_plan_name"], df[metric], color=colors[:len(df)])
        plt.title(f"Traffic Efficiency: {label}")
        plt.ylabel(label)
        plt.xlabel("Signal Plan")
        plt.xticks(rotation=15)
        plt.tight_layout()

        img_path = csv_file.parent / f"{metric}_bar.png"
        plt.savefig(img_path, dpi=150)
        plt.close()
        doc_plots.append(img_path)

    return doc_plots


def plot_signal_plans(csv_file: Path):
    """
    Objective 3: Horizontal stacked bar chart showing phase durations (green, amber, red) per signal plan.
    Each bar represents the full cycle of one signal plan, with durations annotated.
    """
    import numpy as np

    df = pd.read_csv(csv_file)
    phases = ["phase_1", "phase_2", "phase_3"]
    colors = ['green', 'gold', 'red']  # Green, Amber, All Red
    doc_plots = []

    plt.figure(figsize=(10, 6))

    # Positions for bars
    y = np.arange(len(df))
    bar_height = 0.6

    for i, row in df.iterrows():
        left_stack = 0  # start from zero for each signal plan
        for phase in phases:
            durations = [row[f"{phase}_green"],
                         row[f"{phase}_amber"], row[f"{phase}_all_red"]]
            for dur, color in zip(durations, colors):
                plt.barh(y[i], dur, left=left_stack,
                         height=bar_height, color=color, edgecolor='black')
                # Annotate the duration inside the bar
                if dur > 0:
                    plt.text(
                        left_stack + dur / 2, y[i], str(dur), va='center', ha='center', color='black', fontsize=9)
                left_stack += dur  # update left position for next segment

    plt.yticks(y, df["signal_plan_name"])
    plt.xlabel("Duration (s)")
    plt.title("Signal Plan Phase Allocation (Full Cycle)")
    plt.tight_layout()

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor='green', edgecolor='black', label='Green'),
                       Patch(facecolor='gold', edgecolor='black', label='Amber'),
                       Patch(facecolor='red', edgecolor='black', label='All Red')]
    plt.legend(handles=legend_elements, loc='upper right')

    img_path = csv_file.parent / "signal_plans_summary_horizontal.png"
    plt.savefig(img_path, dpi=300)
    plt.close()

    return img_path


def create_word_report(output_path: Path, scalability_img, comparative_imgs, signal_plan_img):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    doc.add_heading("Traffic Simulation Analysis Report", 0)

    # ----------------------------------------
    # Objective 1
    # ----------------------------------------
    doc.add_heading("Objective 1: Scalability Assessment", level=1)

    doc.add_paragraph(
        "This section evaluates how the intersection performs under increasing traffic demand. "
        "The line chart shows the relationship between total traffic volume and the resulting "
        "average queue length for different simulation scenarios.\n\n"
        "Interpretation:\n"
        "- A stable and efficient signal plan should show a gradual increase in queue length as traffic volume rises.\n"
        "- Sharp spikes or nonlinear increases typically indicate that the signal timing is no longer sufficient.\n"
        "- Comparing curves allows us to identify which scenarios scale best under heavier congestion."
    )

    doc.add_picture(str(scalability_img), width=Inches(6))
    doc.add_paragraph(scalability_img.stem)

    # ----------------------------------------
    # Objective 2
    # ----------------------------------------
    doc.add_heading("Objective 2: Traffic Flow Efficiency", level=1)

    doc.add_paragraph(
        "This section compares traffic signal plans across key operational metrics:\n"
        "- Average Delay Time (s)\n"
        "- Average Waiting Time (s)\n"
        "- Average Number of Stops\n"
        "- Average Travel Time (s)\n\n"
        "Interpretation:\n"
        "- Lower values across all metrics generally indicate smoother traffic flow.\n"
        "- A signal plan with low delay but high stops may be overly restrictive.\n"
        "- A plan with lower travel time but higher waiting time may prioritize certain movements.\n"
        "- These charts help identify which signal plan provides the best overall efficiency."
    )

    for img in comparative_imgs:
        doc.add_picture(str(img), width=Inches(6))
        doc.add_paragraph(img.stem)

    # ----------------------------------------
    # Objective 3
    # ----------------------------------------
    doc.add_heading("Objective 3: Signal Plan Phase Allocation", level=1)

    doc.add_paragraph(
        "This section visualizes the complete signal cycle structure for each plan. "
        "Each bar represents the full cycle length, showing the distribution of green, amber, "
        "and all-red intervals.\n\n"
        "Interpretation:\n"
        "- Longer green times correspond to heavier or prioritized movements.\n"
        "- Excessively long red phases may cause unnecessary delay.\n"
        "- Balanced phase allocation typically improves throughput and reduces queue buildup.\n"
        "- By comparing cycles across plans, we can determine which timing strategy is most efficient."
    )

    doc.add_picture(str(signal_plan_img), width=Inches(6))
    doc.add_paragraph(signal_plan_img.stem)

    doc.save(output_path)


if __name__ == "__main__":
    DOCUMENTATION_CSV_PATH.mkdir(parents=True, exist_ok=True)
    DOCUMENTATION_DOCX_PATH.mkdir(parents=True, exist_ok=True)

    # --- Generate charts ---
    scalability_img = plot_scalability(
        DOCUMENTATION_CSV_PATH / intersection.name / "scalability_assessment")
    comparative_imgs = plot_comparative_analysis(
        DOCUMENTATION_CSV_PATH / intersection.name / "comparative_analysis.csv")
    signal_plan_img = plot_signal_plans(
        DOCUMENTATION_CSV_PATH / intersection.name / "signal_plans.csv")

    # --- Create Word doc ---
    create_word_report(OUTPUT_DOCX, scalability_img,
                       comparative_imgs, signal_plan_img)
