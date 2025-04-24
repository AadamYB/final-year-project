import React, { useState } from "react";
import styles from "./UploadSelectCard.module.css";
import Select from "react-select";
import { CODE_SNIPPETS } from "../../../constants/yamlTemplates";

const UploadSelectCard = ({ onUpload, onTemplateChange }) => {
  const options = [
    { value: "python", label: "Python CI" },
    { value: "nodejs", label: "NodeJS Deploy" },
    { value: "default", label: "Default" },
  ];

  const handleTemplateChange = (selectedOption) => {
    if (selectedOption?.value && CODE_SNIPPETS[selectedOption.value]) {
      onTemplateChange(CODE_SNIPPETS[selectedOption.value]);
    }
  };

  return (
    <div className={styles.card}>
      <h3>Upload YAML File</h3>

      <input 
        type="file" 
        onChange={onUpload} 
        className={styles.upload} 
      />

      <h3>Existing Templates</h3>
      <Select 
        className={styles.select}
        options={options}
        placeholder="Select Template"
        onChange={handleTemplateChange}
      />
    </div>
  );
};

export default UploadSelectCard;