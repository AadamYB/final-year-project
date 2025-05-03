import { useParams } from "react-router-dom";
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


const DebugPage = () => {
  const { buildId } = useParams();
  const [buildData, setBuildData] = useState([]);
  const [repoTitle, setRepoTitle] = useState("");
  const [selectedBuild, setSelectedBuild] = useState(null);
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
    const fetchExecutionData = async () => {
      try {
        const res = await fetch(`http://13.40.55.105:5000/executions/${buildId}`);
        const data = await res.json();
        if (data?.logs) {
          const logLines = data.logs.split("\n");
          setLogs(logLines);
        }
        if (data?.repo_title) {
          setRepoTitle(data.repo_title);
        }
      } catch (err) {
        console.error("❌ Failed to fetch logs:", err);
      }
    };

    const fetchBuildList = async () => {
      try {
        const res = await fetch("http://13.40.55.105:5000/executions");
        const data = await res.json();
        setBuildData(data);
    
        // Optional: auto-select the first one if not already selected
        if (!selectedBuild && data.length > 0) {
          setSelectedBuild(data[0]);
        }
      } catch (err) {
        console.error("❌ Failed to fetch build list:", err);
      }
    };
  
    if (buildId) {
      fetchExecutionData();
      localStorage.setItem("lastBuildId", buildId);
    }

    fetchBuildList();

    socket.on("log", (data) => {
      setLogs((prevLogs) => [...prevLogs, data.log]);
    });

    socket.on("build-started", (data) => {
      console.log("🚀 Build started:", data);
    
      setSelectedBuild({
        status: data.status,
        prName: data.pr_name,
        date: new Date(data.timestamp).toLocaleDateString("en-GB"),
        time: new Date(data.timestamp).toLocaleTimeString("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
        }),
      });
    
      setRepoTitle(data.repo_title);
    });

    socket.on("pause-configured", ({ breakpoints }) => {
      console.log("🧩 Initial breakpoints configured from backend:", breakpoints);
      setBreakpoints(breakpoints);
    });

    socket.on("debug-session-started", (data) => {
      console.log("⭐ Debugging repo:", data.repo_title);
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
      socket.off("build-started");
      socket.off("allow-breakpoint-edit");
      socket.off("active-stage-update");
      socket.off("debug-session-started");
      socket.off("pause-configured");
    };
  }, [buildId, selectedBuild]);

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

  const getStatusIcon = (status) => {
    switch (status?.toLowerCase()) {
      case "passed":
        return `${process.env.PUBLIC_URL}/icons/passed.png`;
      case "failed":
        return `${process.env.PUBLIC_URL}/icons/failed.png`;
      case "pending":
      default:
        return `${process.env.PUBLIC_URL}/icons/pending.png`;
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.listContainer}>
        {buildData.map((build) => (
          <BuildListCard
            key={build.id}
            status={build.status}
            prName={build.pr_name}
            date={build.date}
            time={build.time}
            isActive={selectedBuild?.id === build.id}
            onClick={() => setSelectedBuild(build)}
          />
        ))}
      </div>

      {selectedBuild ? (
        <div className={styles.mainContentContainer}>
          <h1 className={styles.buildTitle}>
          {selectedBuild.status && (
            <img
              src={getStatusIcon(selectedBuild.status)}
              alt={selectedBuild.status}
              className={styles.statusIcon}
            />
          )}
            {selectedBuild.status} - {selectedBuild.pr_name}
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
          <DebugConsole repoTitle={repoTitle} isPaused={isPaused} />
        </div>
      ) : (
        <div className={styles.mainContentContainer}>
          <h1 className={styles.buildTitle}>🔍 Select a build from the left</h1>
        </div>
      )}
    </div>
  );
};

export default DebugPage;