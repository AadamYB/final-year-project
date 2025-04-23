import React from "react";
import styles from "./BuildListCard.module.css";
import clsx from "clsx";

const BuildListCard = ({ status, prName, date, time, onClick, isActive }) => {
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
    <div
      className={clsx(styles.card, isActive && styles.activeCard)}
      onClick={onClick}
    >
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

export default BuildListCard;