import React from "react";
import styles from "../styles/App.module.css";
import SemiCircularProgressBar from "../Components/SemiCircularProgressBar";
import NumericCard from "../Components/DashboardCards/NumericCard/NumericCard";


const Dashboard = () => {
  return (

    <div className={styles.section}>
      <div className={styles.container}>
        <div className={styles.progressBarContainer}>
          <h1>unit-tests</h1>
          <SemiCircularProgressBar value={5} gauge="Low" unit="mins" denominator="60" />
        </div>
      </div>
      <div className={styles.container}>
        <div className={styles.progressBarContainer}>
          <h1>failure rate</h1>
          <SemiCircularProgressBar value={60} gauge="Moderate" unit="%" denominator="100" />
        </div>
      </div>
      <div className={styles.container}>
        <div className={styles.progressBarContainer}>
          <h1>integration-tests</h1>
          <SemiCircularProgressBar value={90} gauge="High" unit="mins" denominator="100" />
        </div>
      </div>
      <div className={styles.container}>
        <div className={styles.progressBarContainer}>
          <h1>lint</h1>
          <SemiCircularProgressBar value={11} gauge="Very High" unit="mins" denominator="12" />
        </div>
      </div>
      <div className={styles.container}>
        <h1>Active Builds</h1>
        <NumericCard label="Active Builds" value={5} />
      </div>
      <div className={styles.container}>
        <h1>Releases</h1>
        <NumericCard label="Releases" value={1} />
      </div>
      <div className={styles.container}>
        <h1>Pull Requests</h1>
        <NumericCard label="Pull Requests" value={21} />
      </div>

    </div>

  );
};

export default Dashboard;