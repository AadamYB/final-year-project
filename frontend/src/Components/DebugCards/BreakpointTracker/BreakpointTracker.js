import React from "react";
import styles from "./BreakpointTracker.module.css";

const stageData = {
  setup: ["Cloning main repo"],
  build: ["Building docker image"],
  test: ["Running integration tests"],
};

const determineVisualState = ({
  stage,
  type,
  isActive,
  isPaused,
  resumeTarget,
  resumedPoint,
  stageIndex,
  activeIndex,
}) => {
  const isCurrentPause =
    isPaused &&
    resumeTarget?.stage === stage &&
    resumeTarget?.type === type;

  const wasResumed =
    resumedPoint?.stage === stage &&
    resumedPoint?.type === type;

  const isFuture = stageIndex >= activeIndex;

  if (wasResumed) {
    return { icon: "tick.png", backgroundColor: "#64D755", canClick: false };
  }

  if (isCurrentPause) {
    return { icon: "play.png", backgroundColor: "#FEA602", canClick: true };
  }

  if (isActive) {
    return { icon: "pause.png", backgroundColor: "#ccc", canClick: isFuture };
  }

  return { icon: null, backgroundColor: "#ccc", canClick: isFuture };
};

const BreakpointButton = ({ icon, backgroundColor, onClick, canClick }) => {
  const handleClick = () => {
    if (!canClick) return;
    onClick();
  };

  return (
    <div
      onClick={handleClick}
      className={styles.breakpoint}
      style={{
        backgroundColor,
        cursor: canClick ? "pointer" : "not-allowed",
        opacity: canClick ? 1 : 0.4,
      }}
    >
      {icon ? (
        <img
          src={`${process.env.PUBLIC_URL}/icons/${icon}`}
          alt={icon}
          className={styles.breakpointIcon}
        />
      ) : (
        <div className={styles.inactiveDot}></div>
      )}
    </div>
  );
};

const BreakpointTracker = ({
  activeStage,
  breakpoints,
  onToggleBreakpoint,
  socket,
  canEdit,
  isPaused,
  resumeTarget,
  resumedPoint,
}) => {
  const stageOrder = ["setup", "build", "test"];
  const activeIndex = stageOrder.indexOf(activeStage.stage);

  return (
    <div className={styles.card}>
      <h3>Configure breakpoints</h3>
      <hr />
      <div className={styles.groupContainer}>
        {Object.entries(stageData).map(([stage, steps]) => {
          const isActiveStage = activeStage.stage === stage;
          const stageIndex = stageOrder.indexOf(stage);

          return (
            <div
              key={stage}
              className={styles.stageContainer}
              style={{
                border: isActiveStage ? "3px solid #04a447" : "",
                boxShadow: isActiveStage
                  ? "0 0 10px #04a447"
                  : "inset 0 0 3px rgba(255, 255, 255, 0.1)",
              }}
            >
              <h4>{stage.charAt(0).toUpperCase() + stage.slice(1)}</h4>
              <div className={styles.options}>
                {steps.map((step) => {
                  const beforeState = determineVisualState({
                    stage,
                    type: "before",
                    isActive: breakpoints[stage]?.before,
                    isPaused,
                    resumeTarget,
                    resumedPoint,
                    stageIndex,
                    activeIndex,
                  });

                  const afterState = determineVisualState({
                    stage,
                    type: "after",
                    isActive: breakpoints[stage]?.after,
                    isPaused,
                    resumeTarget,
                    resumedPoint,
                    stageIndex,
                    activeIndex,
                  });

                  return (
                    <div key={step} className={styles.stepRow}>
                      <BreakpointButton
                        icon={beforeState.icon}
                        backgroundColor={beforeState.backgroundColor}
                        onClick={() => onToggleBreakpoint(stage, "before")}
                        canClick={canEdit && beforeState.canClick}
                      />
                      <div className={styles.stepLabel}>{step}</div>
                      <BreakpointButton
                        icon={afterState.icon}
                        backgroundColor={afterState.backgroundColor}
                        onClick={() => onToggleBreakpoint(stage, "after")}
                        canClick={canEdit && afterState.canClick}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default BreakpointTracker;