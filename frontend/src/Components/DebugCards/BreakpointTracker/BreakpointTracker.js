import React from "react";
import styles from "./BreakpointTracker.module.css";

const stageData = {
  setup: ["Cloning main repo"],
  build: ["Building docker image"],
  test: ["Running integration tests"],
};

const BreakpointButton = ({ stage, type, state, onClick, socket, canEdit }) => {
  let icon = null;
  let backColour = "#ccc";
  let cursorStyle = canEdit ? "pointer" : "not-allowed";
  let opacity = canEdit ? 1 : 0.5;

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

  const handleClick = () => {
    if (!canEdit) return; 
    if (state === "pause" && socket) {
      socket.emit("pause");
      onClick();
    } else if (state === "waiting" && socket) {
      socket.emit("resume"); 
    } else {
      onClick();
    }
  };

  return (
    <div
      onClick={handleClick}
      className={styles.breakpoint}
      style={{ backgroundColor: backColour, cursor: cursorStyle, opacity: opacity  }}
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

const BreakpointTracker = ({ activeStage, breakpoints, onToggleBreakpoint, socket }) => {
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
                    socket={socket}
                  />

                  <div className={styles.stepLabel}>{step}</div>

                  <BreakpointButton
                    stage={stage}
                    type="after"
                    state={breakpoints[stage]?.after || "inactive"}
                    onClick={() => onToggleBreakpoint(stage, "after")}
                    socket={socket}
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