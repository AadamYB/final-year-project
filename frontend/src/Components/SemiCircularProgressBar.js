import React from "react";
import { CircularProgressbar } from "react-circular-progressbar";
import "react-circular-progressbar/dist/styles.css";
import styles from "./SemiCircularProgressBar.module.css";

const SemiCircularProgressBar = ({ value, gauge }) => {

 
  const uvIndexMax = (value/11) * 100; // Calculate the percentage of the Gauge(trail) to be filled(path)

  const getProgressBarColour = (gauge) => {
    console.log("Received gauge:", gauge);

    switch (gauge) {
      case "Low":
        return "#00ff00"; // Green for Low
      case "Moderate":
        return "#ffcc00"; // Yellow for Moderate
      case "High":
        return "#ff6600"; // Orange for High
      case "Very High":
        return "#ff0000"; // Red for Very High
      case "Extreme":
        return "#800080"; // Purple for Extreme
      default:
        return "#000000"; // Default colour
    }
  };

  return (
    <div className={styles.progressBarContainer}>
      <CircularProgressbar
        value={uvIndexMax} // The prop that controls the percentage of the trail getting filled by path
        text={`${value}`}
        circleRatio = {0.6}
        styles={{
          trail:{
            strokeLinecap: 'butt',
            transform:"rotate(-108deg)",
            transformOrigin: "center center",
            stroke: "#fff"
          },
          path: {
            strokeLinecap: 'butt',
            transform: "rotate(-108deg)", // Rotate the semi-circle 90 degrees
            transformOrigin: "center center",
            stroke: getProgressBarColour(gauge) // Function that fills the path in a specific colour
          },
          text: {
            fill: "#fff",
          },
        }}
        strokeWidth={15}
      />
    </div>
  );
};

export default SemiCircularProgressBar;