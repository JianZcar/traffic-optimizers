import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import os


# --- Configuration ---
def generate_traffic_report(xml_file: str, output_image: str) -> None:
    """
    Generates a comprehensive traffic analysis report from SUMO tripinfo XML.

    Args:
        xml_file (str): Path to SUMO's tripinfo.xml file
        output_image (str): Path to save the output visualization image

    Outputs:
        - Visualization image with traffic metrics
        - CSV file with aggregated statistics (same base name as output_image)
    """
    # --- Parse XML and Create DataFrame ---
    try:
        root = ET.parse(xml_file).getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return
    except FileNotFoundError:
        print(f"XML file not found: {xml_file}")
        return

    records = []
    for trip in root.findall('tripinfo'):
        records.append({
            'id': trip.get('id'),
            'depart': float(trip.get('depart', 0.0)),
            'arrival': float(trip.get('arrival', 0.0)),
            'duration': float(trip.get('duration', 0.0)),
            'routeLength': float(trip.get('routeLength', 0.0)),
            'waitingTime': float(trip.get('waitingTime', 0.0)),
            'stopTime': float(trip.get('stopTime', 0.0)),
            'timeLoss': float(trip.get('timeLoss', 0.0)),
            'departDelay': float(trip.get('departDelay', 0.0)),
            'waitingCount': int(trip.get('waitingCount', 0)),
            'route': trip.get('id').split('.')[0],
        })

    if not records:
        print("No trip data found in XML file")
        return

    df = pd.DataFrame(records)

    # --- Calculate Aggregate Statistics ---
    summary = {
        'total_trips': len(df),
        'avg_duration': df['duration'].mean(),
        'total_simulation_time': df['arrival'].max() - df['depart'].min(),
        'avg_speed_kmh': (df['routeLength'].sum() / df['duration'].sum() * 3.6).round(2),
        'avg_time_loss': df['timeLoss'].mean(),
        'total_waiting_time': df['waitingTime'].sum(),
        'avg_waiting_time': df['waitingTime'].mean(),
        'total_stops': df['waitingCount'].sum(),
        'delayed_departures': (df['departDelay'] > 0).sum(),
        'avg_depart_delay': df.loc[df['departDelay'] > 0, 'departDelay'].mean(),
        'total_distance_km': (df['routeLength'].sum() / 1000).round(2),
    }

    # --- Export Aggregate CSV ---
    csv_path = os.path.splitext(output_image)[0] + '_summary.csv'
    pd.DataFrame([summary]).to_csv(csv_path, index=False)
    print(f"Aggregate statistics saved to {csv_path}")

    # --- Visualization ---
    plt.figure(figsize=(16, 18), dpi=300)

    plt.figure(figsize=(16, 18), dpi=300)

    # 1) Histogram of trip durations
    ax1 = plt.subplot(3, 1, 1)
    ax1.hist(df['duration'], bins=20)
    ax1.set_title("Distribution of Trip Durations")
    ax1.set_xlabel("Duration (s)")
    ax1.set_ylabel("Number of Trips")

    # 2) Bar chart of average waiting time per route
    ax2 = plt.subplot(3, 1, 2)
    wait_by_route = df.groupby(
        'route')['waitingTime'].mean().sort_values(ascending=False)
    ax2.bar(wait_by_route.index, wait_by_route.values)
    ax2.set_title("Average Waiting Time by Route")
    ax2.set_xlabel("Route ID")
    ax2.set_ylabel("Waiting Time (s)")
    plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')

    # 3) Scatter: time loss vs route length
    ax3 = plt.subplot(3, 1, 3)
    ax3.scatter(df['routeLength'], df['timeLoss'], alpha=0.7)
    ax3.set_title("Time Loss vs. Route Length")
    ax3.set_xlabel("Route Length (m)")
    ax3.set_ylabel("Time Loss (s)")

    plt.tight_layout()
    plt.savefig(output_image)
    plt.close()
    print(f"Visualization saved to {output_image}")
