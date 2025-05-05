import { useNavigate, useParams } from "react-router-dom";
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
  const navigate = useNavigate();
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

  // Fetch list of builds
  useEffect(() => {
    const fetchBuildList = async () => {
      try {
        const res = await fetch("http://13.40.55.105:5000/executions");
        const data = await res.json();
        setBuildData(data);
      } catch (err) {
        console.error("❌ Failed to fetch build list:", err);
      }
    };
    fetchBuildList();
  }, []);

  // Sync selected build with the URL param
  useEffect(() => {
    const match = buildData.find((b) => b.id === buildId);
    setSelectedBuild(match || null);
  }, [buildId, buildData]);

  // Fetch individual build logs & title
  useEffect(() => {
    const fetchExecutionData = async () => {
      try {
        const res = await fetch(`http://13.40.55.105:5000/executions/${buildId}`);
        const data = await res.json();

        if (data?.logs) setLogs(data.logs.split("\n"));
        if (data?.repo_title) setRepoTitle(data.repo_title);
        if (data?.active_stage) setActiveStage({ stage: data.active_stage, step: "" });
        if (data?.is_paused) {
          setIsPaused(true);

          if (data.pause_stage && data.pause_type) {
            setResumeTarget({
              stage: data.pause_stage.toLowerCase(),
              type: data.pause_type.toLowerCase(),
            });
          }

        }
        setBreakpoints({
          setup: { before: false, after: false },
          build: { before: false, after: false },
          test: { before: false, after: false },
          ...data.breakpoints, // overwrite defaults with server values if present
        });
        console.log(data)

        const editableStatuses = ["Pending"];
        setCanEditBreakpoints(editableStatuses.includes(data.status));
        
      } catch (err) {
        console.error("❌ Failed to fetch logs:", err);
      }
    };

    if (buildId) {
      fetchExecutionData();
      localStorage.setItem("lastBuildId", buildId);
    }
  }, [buildId]);

  useEffect(() => {
    socket.on("log", (data) => {
      if (data.build_id === buildId) {
        setLogs((prevLogs) => [...prevLogs, data.log]);
      }
    });

    socket.on("build-started", (data) => {
      console.log("🚀 Build started:", data);
      setRepoTitle(data.repo_title);
    });

    socket.on("pause-configured", ({ breakpoints }) => {
      setBreakpoints(breakpoints);
    });

    socket.on("debug-session-started", () => {
      setResumedPoint(null);
    });

    socket.on("allow-breakpoint-edit", ({ stage, when }) => {
      setCanEditBreakpoints(true);
      setIsPaused(true);
      setResumeTarget({ stage: stage.toLowerCase(), type: when.toLowerCase() });
    });

    socket.on("active-stage-update", ({ stage }) => {
      setActiveStage({ stage, step: "" });
      setResumeTarget(null);
      setResumedPoint(null);
    });

    return () => {
      socket.off("log");
      socket.off("build-started");
      socket.off("pause-configured");
      socket.off("debug-session-started");
      socket.off("allow-breakpoint-edit");
      socket.off("active-stage-update");
    };
  }, [buildId]);

  const toggleBreakpoint = (stage, type) => {
    if (!canEditBreakpoints) return;

    const isResumePoint = resumeTarget?.stage === stage && resumeTarget?.type === type;
    const isPastStage = stageOrder.indexOf(stage) < stageOrder.indexOf(activeStage.stage);

    if (isPastStage || (resumedPoint?.stage === stage && resumedPoint?.type === type)) return;

    setBreakpoints((prev) => {
      const nextState = !prev[stage][type];
    
      const updated = {
        ...prev,
        [stage]: {
          ...prev[stage],
          [type]: nextState,
        },
      };
    
      socket.emit("update-breakpoints", {
        breakpoints: updated,
        build_id: buildId,
      });
    
      if (isResumePoint && nextState) {
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
            onClick={() => {
              navigate(`/debug/${build.id}`);
            }}
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
          <DebugConsole buildId={buildId} repoTitle={repoTitle} isPaused={isPaused} />
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