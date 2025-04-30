import React, { useState, useEffect } from "react";
import styles from "../styles/DebugPage.module.css";
import BuildListCard from "../Components/DebugCards/BuildListCard/BuildListCard";
import BreakpointTracker from "../Components/DebugCards/BreakpointTracker/BreakpointTracker";
import StreamLogs from "../Components/DebugCards/StreamLogs/StreamLogs";
import DebugConsole from "../Components/DebugCards/DebugConsole/DebugConsole";
import io from "socket.io-client";

const socket = io("http://13.40.55.105:5000");

const stageOrder = ["setup", "build", "test"];

const initialBreakpointStates = {
  setup: { before: false, after: false },
  build: { before: false, after: false },
  test: { before: false, after: false },
};

const buildData = [
  { status: "Pending", prName: "Software 0.3 update tests", date: "21/03/25", time: "18:04" },
  { status: "Failed", prName: "Software 1.4 update tests", date: "21/03/25", time: "13:34" },
  { status: "Passed", prName: "Software 0.2 update tests", date: "21/03/25", time: "07:54" },
];

const DebugPage = () => {
  const [repoTitle, setRepoTitle] = useState("");
  const [selectedBuild, setSelectedBuild] = useState(buildData[0]);
  const [isPaused, setIsPaused] = useState(false);
  const [resumeTarget, setResumeTarget] = useState(null);
  const [resumedPoint, setResumedPoint] = useState(null);
  const [canEditBreakpoints, setCanEditBreakpoints] = useState(false);
  const [breakpoints, setBreakpoints] = useState(initialBreakpointStates);
  const [activeStage, setActiveStage] = useState({
    stage: "setup",
    step: "Cloning main repo",
  });
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    socket.on("log", (data) => {
      setLogs((prevLogs) => [...prevLogs, data.log]);
    });

    socket.on("pause-configured", ({ breakpoints }) => {
      console.log("🧩 Initial breakpoints configured from backend:", breakpoints);
      setBreakpoints(breakpoints);
    });
  

    socket.on("debug-session-started", (data) => {
      console.log("⭐ Debugging repo:", data.repo_title);
      setRepoTitle(data.repo_title);
      setResumedPoint(null);
    });

    socket.on("allow-breakpoint-edit", ({ stage, when }) => {
      console.log("✅ Breakpoints can now be edited");
      setCanEditBreakpoints(true);
      setIsPaused(true);
      setResumeTarget({ stage: stage.toLowerCase(), type: when.toLowerCase() });
    });

    socket.on("active-stage-update", (data) => {
      console.log("🛠 Stage changed to:", data.stage);
      setActiveStage({ stage: data.stage, step: "" });
      setResumeTarget(null);
      setResumedPoint(null); // Reset resume visuals
    });

    return () => {
      socket.off("log");
      socket.off("allow-breakpoint-edit");
      socket.off("active-stage-update");
      socket.off("debug-session-started");
      socket.off("pause-configured");
    };
  }, []);

  const toggleBreakpoint = (stage, type) => {
    if (!canEditBreakpoints) return;
  
    const isResumePoint = resumeTarget?.stage === stage && resumeTarget?.type === type;
    const isPastStage = stageOrder.indexOf(stage) < stageOrder.indexOf(activeStage.stage);
  
    // Prevent toggling past or already resumed breakpoints
    if (isPastStage || (resumedPoint?.stage === stage && resumedPoint?.type === type)) return;
  
    setBreakpoints((prev) => {
      const currentValue = prev[stage][type];
  
      const updated = {
        ...prev,
        [stage]: {
          ...prev[stage],
          [type]: !currentValue, // toggle normally
        },
      };
  
      socket.emit("update-breakpoints", updated);
  
      if (isResumePoint && currentValue === true) {
        socket.emit("resume");
        setIsPaused(false);
        setCanEditBreakpoints(false);
        setResumedPoint({ stage, type });
      }
  
      return updated;
    });
  };

  return (
    <div className={styles.page}>
      <div className={styles.listContainer}>
        {buildData.map((build, id) => (
          <BuildListCard
            key={id}
            status={build.status}
            prName={build.prName}
            date={build.date}
            time={build.time}
            isActive={selectedBuild.prName === build.prName}
            onClick={() => setSelectedBuild(build)}
          />
        ))}
      </div>

      <div className={styles.mainContentContainer}>
        <h1 className={styles.buildTitle}>
          <img
            src={`${process.env.PUBLIC_URL}/icons/pending.png`}
            alt={selectedBuild.status}
            className={styles.statusIcon}
          />
          {selectedBuild.status} - {selectedBuild.prName}
        </h1>

        <hr />

        <BreakpointTracker
          activeStage={activeStage}
          breakpoints={breakpoints}
          onToggleBreakpoint={toggleBreakpoint}
          socket={socket}
          canEdit={canEditBreakpoints}
          resumeTarget={resumeTarget}
          resumedPoint={resumedPoint}
          isPaused={isPaused}
        />

        <StreamLogs logs={logs} />
        <DebugConsole repoTitle={repoTitle} />
      </div>
    </div>
  );
};

export default DebugPage;