import json
from flask import Flask, request, jsonify
import pandas as pd
import io
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from joblib import load
import gc

app = Flask(__name__)
# Load the trained model
rf_classifier = load("./models/prescription_model.joblib")


@app.route("/pre-defined", methods=["POST"])
def process_json():
    try:
        json_data = request.get_json()
        dataframe = pd.DataFrame(json_data)
        reports_wc, reports_cy, reports_ny, report_plantName = (
            generate_individual_reports(dataframe)
        )
        return jsonify(
            {
                "withered_reports": reports_wc,
                "crop_yield": reports_cy,
                "net_yield": reports_ny,
                "plant": report_plantName,
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/predict-prescription", methods=["POST"])
def predict_prescription():
    try:
        # Get input data from the request
        data = request.get_json()

        # Initialize an empty list to store predictions for each input instance
        predictions = []

        # Iterate over each input instance
        for instance in data:
            # Extract features from the input data
            crop_yield = float(instance["crop_yield"])  # Ensure crop_yield is a float
            withered_crops = float(
                instance["withered_crops"]
            )  # Ensure withered_crops is a float

            # Make prediction based on the provided features
            prediction = rf_classifier.predict([[withered_crops, crop_yield]])

            # Split the predicted prescription string based on "., "
            prescription_steps = prediction[0].split("., ")

            # Append the list of prescription steps to the predictions list
            predictions.append({"predicted_prescription": prescription_steps})

        return jsonify(predictions)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/growth-rate", methods=["POST"])
def compare_growth():
    try:
        data = request.get_json()
        average_growth = data.get("average_growth")
        recent_growth = data.get("recent_growth")

        if average_growth is None or recent_growth is None:
            return jsonify({"error": "Missing data"}), 400

        # values
        result = compare_growth(average_growth, recent_growth)

        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def calculate_percentage_increase(average_growth, recent_growth):
    if average_growth == 0:
        return "No significant increase in growth rate."

    percentage_increase = ((recent_growth - average_growth) / abs(average_growth)) * 100
    return percentage_increase


# messasges pati conditions
def compare_growth(average_growth, recent_growth):
    if recent_growth > average_growth:
        percentage_increase = calculate_percentage_increase(
            average_growth, recent_growth
        )
        return f"You're doing well! Recent plant growth is higher than average growth by {percentage_increase:.2f}%."
    elif recent_growth < average_growth:
        return f"Your plant has a lower growth rate that is lower than your usual {average_growth:.2f}%."
    else:
        return "No significant increase in growth rate."


def generate_individual_reports(dataframe):
    # Lists to store messages for each plant
    report_wc = []
    report_cy = []
    report_ny = []
    report_plantname = []

    terrible_wc = "The withered crops have significantly impacted yield. Immediate action is needed"
    bad_wc = "The number of withered crops is concerning and impacting yield"
    good_wc = "The withered crops count is zero, indicating excellent crop health and minimal losses during cultivation. "
    mild_wc = "There are some losses due to withered crops, but they're manageable"

    excellent_cy = "Crop yield is exceptional!"
    bad_cy = "Crop yield is below expectations"
    average_cy = "crop yield is satisfactory"
    terrible_cy = "Crop yield is disastrously low"

    excellent_ny = "Net yield exceeds expectations"
    bad_ny = "Net yield is lower than anticipated"
    average_ny = "Net yield is performing average"
    terrible_ny = "Net yield is negative, indicating significant losses"

    for index, row in dataframe.iterrows():
        report = f"Report for {['plant']} crop:\n"
        report_plantname = row["plant"]
        # Analyze withered crops
        if row["type"] == 1:
            if row["withered_crops"] >= 5:
                report += f"Withered crops have significantly impacted yield. Immediate action is needed. "
                report_wc.append(terrible_wc)
            elif 0 < row["withered_crops"] < 5:
                report += (
                    f"The number of withered crops is concerning and impacting yield "
                )
                report_wc.append(bad_wc)
            elif row["withered_crops"] == 0:
                report += f"The withered crops count is zero, indicating excellent crop health and minimal losses during cultivation. This suggests effective pest control, optimal water management, and overall favorable growing conditions. Keep up the good work! "
                report_wc.append(good_wc)
            else:
                report += f"There are some losses due to withered crops, but they're manageable "
                report_wc.append(mild_wc)
        elif row["type"] == 0:
            if row["withered_crops"] > 5:
                report += f"Withered crops have significantly impacted yield. Immediate action is needed. "
                report_wc.append(terrible_wc)
            elif row["withered_crops"] >= 3:
                report += (
                    f"The number of withered crops is concerning and impacting yield "
                )
                report_wc.append(bad_wc)
            elif 1 <= row["withered_crops"] < 3:
                report += f"There are some losses due to withered crops, but they're manageable "
                report_wc.append(mild_wc)
            else:
                report_wc.append(good_wc)

        # Analyze crop yield
        if row["crop_yield"] >= 5 and row["type"] == 1:
            report += f"  "
            report_cy.append(average_cy)
        elif row["crop_yield"] < 5 and row["type"] == 1:
            report += f"crop yield is below expectations "
            report_cy.append(bad_cy)
        elif row["crop_yield"] < 0 and row["type"] == 1:
            report += f"crop yield is disastrously low "
            report_cy.append(terrible_cy)
        elif row["crop_yield"] >= 10 and row["type"] == 1:
            report += f"Crop yield is exceptional! "
            report_cy.append(excellent_cy)

        # Analyze net yield
        if row["net_yield"] >= 12 and row["type"] == 1:
            report += f"net yield exceeds expectations.\n"
            report_ny.append(excellent_ny)
        elif row["net_yield"] >= 8 and row["type"] == 1:
            report += f"net yield is performing average. \n"
            report_ny.append(average_ny)
        elif row["net_yield"] < 8 and row["type"] == 1:
            report += f"net yield is below expectations\n"
            report_ny.append(bad_ny)
        elif row["net_yield"] < 0 and row["type"] == 1:
            report += f"net yield is negative, indicating significant losses\n"
            report_ny.append(terrible_ny)

        # type 0

        #  crop yield
        if row["crop_yield"] == 1 and row["type"] == 0:
            report += f"crop yield is satisfactory "
            report_cy.append(average_cy)
        elif row["crop_yield"] < 1 and row["crop_yield"] > 0 and row["type"] == 0:
            report += f"Crop yield is below expectations, "
            report_cy.append(bad_cy)
        elif row["crop_yield"] < 0 and row["type"] == 0:
            report += f"Crop yield is disastrously low, "
            report_cy.append(terrible_cy)
        elif row["crop_yield"] > 1 and row["type"] == 0:
            report += f"Crop yield is exceptional! "
            report_cy.append(excellent_cy)

        # net yield
        if row["net_yield"] == row["planted_qty"] and row["type"] == 0:
            report += f"net yield is performing average. \n"
            report_ny.append(average_ny)
        elif row["net_yield"] > row["planted_qty"] and row["type"] == 0:
            report += f"net yield exceeds expectationsyield is commendable. \n"
            report_ny.append(excellent_ny)
        elif row["net_yield"] < row["planted_qty"] and row["type"] == 0:
            report += f"net yield is lower than anticipated\n"
            report_ny.append(bad_ny)
        elif row["net_yield"] < 0 and row["type"] == 0:
            report += f"net yield is negative, indicating significant losses\n"
            report_ny.append(terrible_ny)

    return report_wc, report_cy, report_ny, report_plantname


if __name__ == "__main__":
    app.run(host="0.0.0.0")
