import React from "react";
import styles from "./PipelineVisualiser.module.css";

const stages = ["Build", "Test", "Stage", "Deploy"]; //change this to accomodate backend later

const PipelineVisualiser = () => {
  return (
    <div className={styles.card}>
        <h3>Pipeline Visualiser</h3>

        <div className={styles.internalContainer}>
            <div className={styles.flow}>
                {stages.map((stage, i) => (
                <React.Fragment key={i}>
                    <div className={styles.stage}>{stage}</div>
                    {i < stages.length - 1 && <span className={styles.arrow}>→</span>}
                </React.Fragment>
                ))}
            </div>
        </div>

    </div>
  );
};

export default PipelineVisualiser;