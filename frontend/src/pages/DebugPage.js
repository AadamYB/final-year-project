import React, { useState } from "react";
import styles from "../styles/DebugPage.module.css";
import BuildListCard from "../Components/DebugCards/BuildListCard/BuildListCard";
import BreakpointTracker from "../Components/DebugCards/BreakpointTracker/BreakpointTracker";
import StreamLogs from "../Components/DebugCards/StreamLogs/StreamLogs";
import DebugConsole from "../Components/DebugCards/DebugConsole/DebugConsole";

const mockLogs = [
    "[2025-01-14     17:54:46 ] RUNNING CMD mkdir tmp-repo",
    "[2025-01-14     17:54:48 ] RUNNING CMD cd tmp-repo",
    "[2025-01-14     17:55:09 ] git clone https://github.com/user/repo.git",
    "[2025-01-14     17:55:10 ] Cloning into ‘...’ ...",
    "[2025-01-14     17:55:50 ] remote: Counting objects: 100, done.",
    "[2025-01-14     17:56:03 ] remote: Compressing objects: 100% (84/84), done.",
    "[2025-01-14     17:56:04 ] remove: Total 100 (delta 16), reused 100 (delta 16)",
    "[2025-01-14     17:56:09 ] Unpacking objects: 100% (100/100), done.",
    "[2025-01-14     17:56:09 ] 🐞STARTING LIVE DEBUGGING SESSION🪲",
    "[2025-01-14     17:56:09 ] LOGS PAUSED ⏸️",
  ];

const initialBreakpointStates = {
  setup: { before: "inactive", after: "inactive" },
  build: { before: "inactive", after: "inactive" },
  test: { before: "inactive", after: "inactive" },
};

const buildData = [
  {
    status: "Pending",
    prName: "Software 0.3 update tests",
    date: "21/03/25",
    time: "18:04"
  },
  {
    status: "Failed",
    prName: "Software 1.4 update tests",
    date: "21/03/25",
    time: "13:34"
  },
  {
    status: "Passed",
    prName: "Software 0.2 update tests",
    date: "21/03/25",
    time: "07:54"
  },
];

const DebugPage = () => {
  const [selectedBuild, setSelectedBuild] = useState(buildData[0]);
  const [breakpoints, setBreakpoints] = useState(initialBreakpointStates);
  const [activeStep, setActiveStep] = useState({
    stage: "setup",
    step: "Cloning main repo",
  });

  // this function is used to allow users to interrupt their pipelines
  const toggleBreakpoint = (stage, type) => {
    setBreakpoints((prev) => {
      const current = prev[stage][type];
      let next;
      switch (current) {
        case "inactive":
          next = "pause";
          break;
        case "pause":
          next = "waiting";
          break;
        case "waiting":
          next = "play";
          break;
        case "play":
          next = "done";
          break;
        case "done":
          next = "inactive";
          break;
        default:
          next = "inactive";
      }

      return {
        ...prev,
        [stage]: {
          ...prev[stage],
          [type]: next,
        },
      };
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
            {selectedBuild.status === "Passed" && (
                <img
                src={`${process.env.PUBLIC_URL}/icons/pending.png`}
                alt="Passed"
                className={styles.statusIcon}
                />
            )}
            {selectedBuild.status === "Failed" && (
                <img
                src={`${process.env.PUBLIC_URL}/icons/pending.png`}
                alt="Failed"
                className={styles.statusIcon}
                />
            )}
            {selectedBuild.status === "Pending" && (
                <img
                src={`${process.env.PUBLIC_URL}/icons/pending.png`}
                alt="Pending"
                className={styles.statusIcon}
                />
            )}
            {selectedBuild.status} - {selectedBuild.prName}
            </h1>

        <hr/>

        <BreakpointTracker
          activeStage={activeStep}
          breakpoints={breakpoints}
          onToggleBreakpoint={toggleBreakpoint}
        />

        <StreamLogs logs={mockLogs} />
        <DebugConsole data={selectedBuild} />
      </div>
    </div>
  );
};

export default DebugPage;