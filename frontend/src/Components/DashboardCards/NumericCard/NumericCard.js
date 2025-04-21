import React from "react";
import styles from "./NumericCard.module.css";

const NumericCard = ({ label, value }) => (
  <div className={styles.card}>
    <p className={styles.label}>{label}</p>
    <p className={styles.value}>{value}</p>
  </div>
);

export default NumericCard;