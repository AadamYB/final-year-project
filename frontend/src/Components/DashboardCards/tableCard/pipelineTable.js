import React from "react";
import styles from "./pipelineTable.module.css";

const PipelineTable = ({ builds }) => {
  return (
    <div className={styles.pipelineTable}>
      <h2>Pipeline Runs</h2>
      <div className={styles.tableContainer}>
        <table>
          <thead>
            <tr>
              <th>Build Name</th>
              <th>Clone</th>
              <th>Build</th>
              <th>Test</th>
              <th>Deploy</th>
            </tr>
          </thead>
          <tbody>
            {builds.map((build) => (
              <tr key={build.id}>
                <td>{build.pr_name}</td>
                {["Clone", "Build", "Test", "Deploy"].map((stage) => {
                  const stageObj = build.stage_status?.find((s) => s.name === stage);
                  const status = stageObj?.status;

                  let className = styles.inactive;
                  if (status === "success") className = styles.success;
                  else if (status === "failed") className = styles.failed;
                  else if (status === "active") className = styles.active;

                  return (
                    <td className={className} key={stage}>
                      {stageObj ? stage : ""}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PipelineTable;