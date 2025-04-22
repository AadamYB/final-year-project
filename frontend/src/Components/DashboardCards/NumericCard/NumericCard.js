import React from "react";
import styles from "./NumericCard.module.css";

const NumericCard = ({ label, value  }) => (
  <div className={styles.card}>
    <h1 className={styles.label}>{label}</h1>
    <p className={styles.value}>{value}</p>
  </div>
);

export default NumericCard;