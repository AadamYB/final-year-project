import React, { useEffect, useRef } from "react";
import styles from "./StreamLogs.module.css";

const getLogClass = (line) => {
  if (line.includes("✅")) return styles.success;
  if (line.includes("❌")) return styles.error;
  if (line.includes("⚠️")) return styles.warning;
  if (line.includes("🚀") || line.includes("🔍") || line.includes("💅")) return styles.info;
  return styles.default;
};

const StreamLogs = ({ logs = [] }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Stream logs</h3>
      <div className={styles.logContent}>
        {logs.map((line, i) => (
          <div key={i} className={`${styles.logLine} ${getLogClass(line)}`}>
            &gt; {line}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default StreamLogs;