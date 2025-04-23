import React from "react";
import { CircularProgressbar } from "react-circular-progressbar";
import "react-circular-progressbar/dist/styles.css";
import styles from "./SemiCircularProgressBar.module.css";

const SemiCircularProgressBar = ({ value, gauge, unit, denominator}) => {

 
  const percentage = (value/denominator) * 100; // Calculate the percentage of the Gauge(trail) to be filled(path)

  const getProgressBarColour = (gauge) => {
    console.log("Received gauge:", gauge);

    switch (gauge) {
      case "Low":
        return "#07C900"; // Green for Low
      case "Moderate":
        return "#E5B300"; // Yellow for Moderate
      case "High":
        return "#ff6600"; // Orange for High
      case "Very High":
        return "#C20000"; // Red for Very High
      default:
        return "#858585"; // Default colour
    }
  };

  return (
    <div className={styles.progressBarContainer}>
      <CircularProgressbar
        value={percentage} // The prop that controls the percentage of the trail getting filled by path
        text={`${value} ${unit}`} // The prop that controls the text in the middle
        circleRatio = {0.6}
        styles={{
          trail:{
            strokeLinecap: 'butt',
            transform:"rotate(-108deg)",
            transformOrigin: "center center",
            stroke: "#858585"
          },
          path: {
            strokeLinecap: 'butt',
            transform: "rotate(-108deg)", // Rotate the semi-circle so thatit sits horizontally
            transformOrigin: "center center",
            stroke: getProgressBarColour(gauge) // Function that fills the path in a specific colour
          },
          text: {
            fontSize: 15,
            fill: getProgressBarColour(gauge),
          },
        }}
        strokeWidth={15}
      />
    </div>
  );
};

export default SemiCircularProgressBar;