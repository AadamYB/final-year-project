import React from "react";
import styles from "./BreakpointTracker.module.css";

const stageData = {
  setup: ["Cloning main repo"],
  build: ["Building docker image"],
  test: ["Running integration tests"],
};

const BreakpointButton = ({ stage, type, state, onClick }) => {
  let icon = null;
  let backColour = "#ccc";

  switch (state) {
    case "pause":
      icon = "pause.png";
      break;
    case "waiting":
      icon = "pause.png";
      backColour = "#FEA602";
      break;
    case "play":
      icon = "play.png";
      backColour = "#FEA602";
      break;
    case "done":
      icon = "tick.png";
      backColour = "#64D755";
      break;
    default:
      break; // no icon for "inactive" to mimic whats shown in the FIGMA design
  }

  return (
    <div
      onClick={onClick}
      className={styles.breakpoint}
      style={{ backgroundColor: backColour }}
    >
      {icon ? (
        <img
          src={`${process.env.PUBLIC_URL}/icons/${icon}`}
          alt={state}
          className={styles.breakpointIcon}
        />
      ) : (
        <div className={styles.inactiveDot}></div>
      )}
    </div>
  );
};

const BreakpointTracker = ({ activeStage, breakpoints, onToggleBreakpoint }) => {
  return (
    <div className={styles.card}>
      <h3>Configure breakpoints</h3>
      <hr/>
      <div className={styles.groupContainer}>
        {Object.entries(stageData).map(([stage, steps]) => (
          <div key={stage} className={styles.stageContainer}>
            <h4>{stage.charAt(0).toUpperCase() + stage.slice(1)}</h4>
            <div className={styles.options}>
              {steps.map((step) => (
                <div key={step} className={styles.stepRow}>
                  <BreakpointButton
                    stage={stage}
                    type="before"
                    state={breakpoints[stage]?.before || "inactive"}
                    onClick={() => onToggleBreakpoint(stage, "before")}
                  />

                  <div className={styles.stepLabel}>{step}</div>

                  <BreakpointButton
                    stage={stage}
                    type="after"
                    state={breakpoints[stage]?.after || "inactive"}
                    onClick={() => onToggleBreakpoint(stage, "after")}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default BreakpointTracker;