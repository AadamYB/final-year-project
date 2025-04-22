// src/Components/DashboardCards/BuildCard/BuildCard.jsx

import React from "react";
import styles from "./BuildCard.module.css";

const BuildCard = ({ status, prName, date, time }) => {
  const getStatusIcon = (status) => {
    switch (status.toLowerCase()) {
      case "passed":
        return `${process.env.PUBLIC_URL}/icons/passed.png`;
      case "failed":
        return `${process.env.PUBLIC_URL}/icons/failed.png`;
      case "pending":
        return `${process.env.PUBLIC_URL}/icons/pending.png`;
      default:
        return `${process.env.PUBLIC_URL}/icons/unknown.png`;
    }
  };

  return (
    <div className={styles.card}>
      <div className={styles.row}>
        <img src={getStatusIcon(status)} alt={status} className={styles.icon} />
        <span className={styles.prText}>{status} - {prName}</span>
      </div>
      <div className={styles.row}>
        <span className={styles.meta}>{date}</span>
        <span className={styles.meta}>{time}</span>
      </div>
    </div>
  );
};

export default BuildCard;