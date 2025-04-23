import React from "react";
import styles from "./StreamLogs.module.css";

const StreamLogs = ({ logs = [] }) => {
  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Stream logs</h3>
      <div className={styles.logContent}>
        {logs.map((line, i) => (
          <div key={i} className={styles.logLine}>
            &gt; {line}
          </div>
        ))}
      </div>
    </div>
  );
};

export default StreamLogs;