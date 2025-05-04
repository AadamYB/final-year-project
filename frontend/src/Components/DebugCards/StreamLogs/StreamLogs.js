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

  let inErrorBlock = false;
  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Stream logs</h3>
      <div className={styles.logContent}>
        {logs.map((line, i) => {
          const isErrorLine = line.includes("❌") 

          if (isErrorLine) inErrorBlock = true;
          const isEndOfBlock = line.trim() === "" || (/^\[.*\]/.test(line) && !isErrorLine);
          if (inErrorBlock && isEndOfBlock) inErrorBlock = false;
          const lineClass = inErrorBlock ? styles.error : getLogClass(line);

          return (
            <div key={i} className={`${styles.logLine} ${lineClass}`}>
              &gt; {line}
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

export default StreamLogs;