import React from "react";
import styles from "./YamlEditor.module.css";

const YamlEditorCard = ({ yamlText, onChange }) => {
  return (
    <div className={styles.card}>
      <h3>Edit YAML file Configuration</h3>
      <textarea
        value={yamlText}
        onChange={onChange}
        className={styles.editor}
        spellCheck={false}
      />
      <div className={styles.buttonRow}>
        <button className={styles.save}>Save</button>
        <button className={styles.reset}>Reset</button>
      </div>
    </div>
  );
};

export default YamlEditorCard;